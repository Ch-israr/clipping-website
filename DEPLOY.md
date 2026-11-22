# Deploy — Variant B (Cloud Run + Vercel + Neon + Backblaze B2)

**Not run yet. Do not run until: a card is on the Google Cloud account,
a B2 bucket + application key exist, and the Groq key is in Secret Manager.**

## 0. Prerequisites

- Google Cloud project with billing enabled (card required) + `gcloud` CLI.
- Vercel account (Hobby, frontend only — non-commercial on Hobby).
- Neon free Postgres project (or Supabase free).
- Backblaze B2: private bucket `clips-prod`, lifecycle rules
  (`uploads/` delete after 7 days, `clips/` after 30 days), application
  key restricted to that bucket.
- Groq API key in Google Secret Manager as `groq-key`.

## 1. Push this repo to GitHub (user creates the repo first)

Recommended name: **`Ch-israr/clipping-website`** (public).

```bash
# user creates the EMPTY public repo Ch-israr/clipping-website on github.com first
# (the GitHub App cannot create repos)
cd ~/workspace/clipping-website
git remote add origin https://github.com/Ch-israr/clipping-website.git
git push -u origin main
```

## 2. Build the worker image

```bash
cd openshorts
gcloud builds submit --tag gcr.io/PROJECT/clip-worker .
```

## 3. Cloud Run Job (the worker — the only place video work happens)

```bash
gcloud run jobs create clip-worker \
  --image gcr.io/PROJECT/clip-worker \
  --cpu 2 --memory 8Gi --task-timeout 6h --max-retries 1 \
  --set-env-vars LLM_BASE_URL=https://api.groq.com/openai/v1,LLM_MODEL=openai/gpt-oss-120b,MAX_CONCURRENT_JOBS=1,S3_ENDPOINT_URL=https://s3.us-west-004.backblazeb2.com,AWS_REGION=us-west-004,AWS_S3_BUCKET=clips-prod \
  --set-secrets LLM_API_KEY=groq-key:latest,AWS_ACCESS_KEY_ID=b2-key-id:latest,AWS_SECRET_ACCESS_KEY=b2-key:latest,DATABASE_URL=neon-url:latest
```

## 4. Cloud Run service (the API — enqueues only, never processes video)

```bash
gcloud run deploy clip-api \
  --image gcr.io/PROJECT/clip-worker \
  --cpu 1 --memory 2Gi --max-instances 2 --timeout 3600 --allow-unauthenticated
```

The API inserts a job row in Neon, then triggers the Job
(`gcloud run jobs execute clip-worker` / Jobs API). The Job claims the
row (`SELECT … FOR UPDATE SKIP LOCKED`), runs the pipeline, uploads
clips + metadata to B2, and marks the row done with the B2 keys.
Clip downloads are B2 presigned GET URLs (1–2 h TTL).

## 5. Frontend (Vercel)

Build `openshorts/dashboard/` as a static site and deploy to Vercel,
pointing it at the `clip-api` URL. Keep the dashboard's API base URL
in an env var, not hard-coded.

## 6. First live smoke test (after deploy)

1. Upload a 1–2 min video with real speech.
2. Confirm: job row → processing → done; 3–5 clips in B2; presigned
   URLs play; clips are 1080×1920 with burned-in captions.
3. Watch Groq usage: free tier caps at ~20–40 videos/day
   (8,000 TPM binds first, ~1 video/min). On 429, the worker backs
   off and retries with `gpt-oss-20b`.

## Scale later

- Job CPU/mem → 4 vCPU / 16 GiB; GPU worker (Cloud Run L4) for ~50 s/video.
- Second Job + Redis queue when concurrent users grow.
- Neon Launch / Supabase Pro when >1 GB metadata or pausing hurts.
