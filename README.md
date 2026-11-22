# AI Video-Clipping Website — OpenShorts + Groq + Backblaze B2

OpusClip-style website: upload a long video → AI finds the viral moments →
exports captioned 9:16 Shorts/Reels. Built on
[OpenShorts](https://github.com/mutonby/openshorts) (MIT core, 9,670 stars),
with the moment picker swapped from Gemini to **Groq** and clip storage
swapped from AWS S3 to **Backblaze B2**.

**Status: built + tested locally on 2026-11-22. NOT deployed.**
Public hosting is **Variant B** (Vercel frontend + Cloud Run Jobs worker +
Neon Postgres + B2) — see `DEPLOY.md`. It needs a card for Cloud Run, so
deployment is a separate, later step.

## What is in this repo

| Path | What it is |
|---|---|
| `openshorts/` | OpenShorts, vendored from upstream commit `60e7714` (`feat(remote): the quiet minutes can be for named workers only`, 2026-11-22). One local change only: `s3_uploader.py` — see below. Upstream `.git` removed; this tree is the release snapshot. |
| `openshorts/s3_uploader.py` | **The only code change.** Adds `S3_ENDPOINT_URL` support: when set, boto3 points at Backblaze B2 (or any S3-compatible store) instead of AWS, and public URLs use the `<endpoint>/<bucket>/<key>` form. Unset = upstream AWS behaviour, byte-for-byte. Verified by mocked-boto3 tests — see `local-test/TEST-RESULTS.md`. |
| `.env.example` | Groq + B2 + job settings. Placeholders only, never real keys. |
| `DEPLOY.md` | Variant B Cloud Run deploy steps (not run yet). |
| `local-test/` | Proof of the local test: sample video, transcript, Groq scores, 2 finished clips + frame, and `TEST-RESULTS.md` with the real numbers. |
| `local-test/scripts/` | The exact scripts used for the local test (transcribe → Groq score → cut/reframe/caption). They read keys from the environment only. |

## Architecture (Variant B)

```
Upload (Vercel frontend, static)
  → Cloud Run API service, scale-to-zero, 1 vCPU / 2 GiB  (enqueues only)
  → Cloud Run Job worker, 2 vCPU / 8 GiB, MAX_CONCURRENT_JOBS=1
       faster-whisper (local) → Groq gpt-oss-120b (moment picking)
       → ffmpeg 9:16 reframe + burned-in captions → Backblaze B2
  → job rows in Neon Postgres (SQLite locally) · clips served by B2 presigned URLs
```

Costs within free allowances: ~$0. After allowances ≈ $0.025/video
(Cloud Run) + ≈ $0.003/video (Groq 120b) + B2 ~$0.63/100 GB stored.
At 500 videos/mo ≈ $13/mo. Full numbers in the plan page
(`clipping-website-plan`).

## Run locally (a real machine, not this sandbox VM)

```bash
cp .env.example openshorts/.env   # fill in LLM_API_KEY + B2 keys
cd openshorts && docker compose up --build
# dashboard http://localhost:5175 · API http://localhost:8000
```

Requirements: Docker, 8 GB+ RAM. CPU-only: ~5–8 min per 8-min video.

## Known limits (verified 2026-11-22)

1. **Docker does not run in this sandbox VM** — `dockerd` fails on
   iptables/nftables (`Permission denied`), so the full `docker compose`
   stack was NOT run here. The pipeline was proven instead by running
   OpenShorts' own modules directly (see `local-test/TEST-RESULTS.md`).
2. **Groq + OpenShorts end-to-end works**, but only with a proxy-aware
   HTTP client in this sandbox: the VM's egress proxy URL breaks
   `httpx`'s default client (`InvalidURL: Invalid port`), and bare
   `python-urllib`/`python-httpx` user-agents get Cloudflare 1010 from
   Groq's front door. On a normal host (Cloud Run / VPS) there is no
   egress proxy and the stock client works — the Groq call itself was
   proven with the real `llm_backend.generate_json` code path.
3. **No Gemini key** → layout picker / silent-video path fall back to
   plain face-track crop; silent videos fail with a clear message.
   The bundled demo video (`demo-openshorts.mp4`) is effectively silent
   (−91 dB), so it cannot test transcription.
4. **B2 has no real keys yet** — placeholders only. The B2 patch is
   proven with mocked boto3, not against a live bucket. First live
   upload needs a real B2 application key.
5. Whisper `base` on robotic (espeak) speech mishears a few words
   (e.g. "Then score every segment" → "End core segment"). Real speech
   + `small` model will be cleaner; the pipeline itself is unaffected.
6. `cloud/` inside OpenShorts is under the OpenShorts Commercial
   Licence — it cannot be offered to third parties as a paid hosted
   service. The MIT core is what this repo uses.

## Secrets

No real key, token, or credential is in this repo. `.env` is git-ignored.
Every file was scanned for `gsk_`, `AKIA`, `AWS_SECRET`, bearer tokens,
and private keys before commit — clean.
