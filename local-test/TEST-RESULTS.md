# Local test results — 2026-11-22

Run in this sandbox VM (4 vCPU, 7.7 GB RAM). Docker daemon does NOT run
here (`dockerd` fails on iptables/nftables), so the full `docker compose`
stack was not run. Each pipeline stage was instead proven with
OpenShorts' own code, run directly. Nothing below is claimed beyond
what actually ran.

## 1. Groq smoke test — PASS

- Key: user's Groq key, env-var only, never written to disk.
- `openai/gpt-oss-120b`, `response_format: json_schema`, small
  moment-picking prompt: **HTTP 200 in 1.13 s, 539 tokens**
  (358 prompt + 181 completion, incl. 129 reasoning). Returned valid
  JSON: 2 clips (0–12 s, score 85; 28–45 s, score 80).
- `openai/gpt-oss-20b` "Say ok": HTTP 200, 79 tokens.
- `GET /openai/v1/models` with the key: HTTP 200, lists
  `openai/gpt-oss-20b` / `gpt-oss-120b` (131,072 ctx).

## 2. Groq via OpenShorts' own `llm_backend.generate_json` — PASS (with a sandbox-only caveat)

- Stock `httpx` client **fails in this VM**: the egress proxy URL
  breaks httpx parsing (`InvalidURL: Invalid port: ':1]'`), and bare
  `python-urllib`/`python-httpx` user-agents get Cloudflare 1010 from
  Groq. This is a sandbox-egress quirk, not a Groq/OpenShorts bug.
- With a proxy-aware client (test harness only, not repo code) the
  real code path works: **2.02 s, 504 in + 319 out tokens**, 4 windows
  scored and pydantic-validated (hook window top, score 70; intro
  bottom, score 30). `json_schema` accepted (with `json_object`
  fallback built into the code).
- OpenShorts' own suite: `pytest tests/test_llm_backend.py` →
  **8 passed, 2 skipped** (skipped tests need the full heavy `main`
  import).

## 3. Transcription (faster-whisper, local) — PASS

- Model `base`, CPU int8. Sample: `sample-70s.mp4`, 39.9 s,
  1920×1080 h264 + AAC, 972,083 bytes, speech generated with
  espeak-ng (own scripted text, 101 words).
- **10.7 s transcribe, 7 segments, 101 words, lang en (prob 0.98),
  word-level timestamps.** Mostly accurate; base model misheard a few
  robotic-speech words ("Then score every segment" → "End core
  segment").
- The bundled `demo-openshorts.mp4` (41.8 s) is effectively silent
  (mean volume −91 dB) — Whisper correctly returned 0 segments, so
  it cannot test transcription.

## 4. End-to-end clip test — PASS

Groq scored the 7 real transcript windows in **2.86 s
(650 in + 817 out tokens)**. Top picks: 22.5–28.9 s (score 75),
11.7–17.3 s (score 70). Both were cut, center-cropped to 9:16,
scaled to 1080×1920, and rendered with burned-in SRT captions
(built from Whisper word timestamps, shifted to clip-relative time —
absolute SRT times do NOT display after an `-ss` seek; first attempt
had no visible captions, fixed and re-verified by frame).

| File | Window | Score | Size | Duration | Resolution |
|---|---|---|---|---|---|
| `clip1.mp4` | 22.46–28.88 s | 75 | 461,282 B | 6.43 s | 1080×1920 h264 + AAC |
| `clip2.mp4` | 11.66–17.26 s | 70 | 387,517 B | 5.60 s | 1080×1920 h264 + AAC |

Frame check at 2 s into clip 1: caption "End core segment for
surprise, emotion" visibly burned in (see `clip1-frame.png`).
Face tracking was NOT used in this test (MediaPipe/YOLOv8 need the
full Docker image); the crop is a center crop. Layout picking still
needs a Gemini key or accepts the plain face-track fallback.

## 5. Backblaze B2 patch — PASS (mocked boto3, no live bucket)

`openshorts/s3_uploader.py` now honours `S3_ENDPOINT_URL`.
Mocked-boto3 tests (`scripts/test_b2_patch.py`): endpoint_url passed
to boto3, B2 public URL form correct, AWS behaviour unchanged when
the var is unset, `upload_file_to_s3` passes the endpoint through.
**Not yet proven against a live B2 bucket — no B2 keys exist yet.**

## 6. NOT tested / still unverified

- Full `docker compose` stack (backend :8000 + dashboard :5175 +
  renderer :3100) — Docker daemon cannot start in this VM.
- Live B2 upload / presigned download.
- Groq + OpenShorts on a real host without the egress proxy
  (expected to work with the stock client; verify on first Cloud Run
  smoke test).
- Face-tracked (TRACK/SPLIT) reframe and Remotion caption styles —
  need the full image.
- Long videos (8+ min) and concurrent jobs.
