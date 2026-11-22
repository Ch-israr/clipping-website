import os, sys, time, json, subprocess
sys.path.insert(0, '/home/hatch/workspace/clipping-website/openshorts')
from urllib.parse import urlparse
import httpx
import llm_backend, gemini_worker

# Sandbox-only proxy-aware client (see Groq test notes). Stock code on a
# normal host needs no patch.
pu = urlparse(os.environ["https_proxy"])
proxy = httpx.Proxy(url=f"http://{pu.hostname}:{pu.port}", auth=(pu.username, pu.password))
def patched_client(**kw):
    return httpx.Client(timeout=llm_backend._timeout(), proxy=proxy,
        headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"}, **kw)
llm_backend._client = patched_client

BASE = "/home/hatch/workspace/clipping-website/local-test"
SRC = f"{BASE}/sample-70s.mp4"
with open(f"{BASE}/transcript.json") as f:
    tr = json.load(f)
segs = tr["segments"]
windows = [{"id": f"w{i}", "start": s["start"], "end": s["end"], "text": s["text"]} for i, s in enumerate(segs)]
prompt = ("Score these transcript windows for viral short-clip potential (0-100). "
  f"Windows: {json.dumps(windows)} "
  "Return JSON {\"windows\": [{\"id\": ..., \"start\": ..., \"end\": ..., \"score\": ..., \"reason\": \"...\"}]} with every window scored.")
t0 = time.time()
parsed, cost = llm_backend.generate_json(prompt, gemini_worker.ScoreResponse)
print("GROQ_SCORE latency_s", round(time.time()-t0, 2), "tokens", cost["input_tokens"], "+", cost["output_tokens"])
for w in sorted(parsed["windows"], key=lambda x: -x["score"]):
    print("  ", w["id"], round(w["start"],1), "-", round(w["end"],1), "score", w["score"], "-", w["reason"][:90])
top = sorted(parsed["windows"], key=lambda x: -x["score"])[:2]

def fmt(t):
    h, m = int(t//3600), int(t%3600//60)
    s = t % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")
for n, w in enumerate(top, 1):
    # SRT from words inside the window
    lines, cur, idx = [], [], 1
    for s in segs:
        for wd in s["words"]:
            if w["start"] <= wd["start"] < w["end"]:
                cur.append(wd)
                if len(cur) >= 6:
                    lines.append((cur[0]["start"], cur[-1]["end"], " ".join(x["w"].strip() for x in cur))); cur = []
    if cur: lines.append((cur[0]["start"], cur[-1]["end"], " ".join(x["w"].strip() for x in cur)))
    srt = "".join(f"{i}\n{fmt(a)} --> {fmt(b)}\n{t}\n\n" for i, (a, b, t) in enumerate(lines, 1))
    srt_path = f"{BASE}/clip{n}.srt"
    open(srt_path, "w").write(srt)
    out = f"{BASE}/clip{n}.mp4"
    cmd = ["ffmpeg", "-y", "-v", "error", "-ss", str(w["start"]), "-to", str(w["end"]), "-i", SRC,
           "-vf", f"crop=ih*9/16:ih,scale=1080:1920,subtitles={srt_path}:force_style='FontSize=28,PrimaryColour=&HFFFFFF&,OutlineColour=&H000000&,BorderStyle=1,Outline=2'",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-c:a", "aac", out]
    r = subprocess.run(cmd, capture_output=True, text=True)
    print(f"CLIP {n}: window {w['start']}-{w['end']} score {w['score']} rc={r.returncode} {r.stderr.strip()[:200]}")
    if r.returncode == 0:
        probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration,size",
            "-show_entries", "stream=codec_name,width,height", "-of", "default=noprint_wrappers=1", out],
            capture_output=True, text=True)
        print(f"CLIP {n} PROBE:\n{probe.stdout.strip()}")
with open(f"{BASE}/groq_scores.json", "w") as f:
    json.dump(parsed, f, indent=1)
