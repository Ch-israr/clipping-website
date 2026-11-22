import json, subprocess
BASE = "/home/hatch/workspace/clipping-website/local-test"
SRC = f"{BASE}/sample-70s.mp4"
tr = json.load(open(f"{BASE}/transcript.json"))
scores = json.load(open(f"{BASE}/groq_scores.json"))
top = sorted(scores["windows"], key=lambda x: -x["score"])[:2]
def fmt(t):
    t = max(0.0, t)
    return f"{int(t//3600):02d}:{int(t%3600//60):02d}:{t%60:06.3f}".replace(".", ",")
for n, w in enumerate(top, 1):
    lines, cur = [], []
    for s in tr["segments"]:
        for wd in s["words"]:
            if w["start"] <= wd["start"] < w["end"]:
                cur.append(wd)
                if len(cur) >= 6:
                    lines.append((cur[0]["start"]-w["start"], cur[-1]["end"]-w["start"], " ".join(x["w"].strip() for x in cur))); cur = []
    if cur: lines.append((cur[0]["start"]-w["start"], cur[-1]["end"]-w["start"], " ".join(x["w"].strip() for x in cur)))
    srt = "".join(f"{i}\n{fmt(a)} --> {fmt(b)}\n{t}\n\n" for i, (a, b, t) in enumerate(lines, 1))
    srt_path = f"{BASE}/clip{n}.srt"
    open(srt_path, "w").write(srt)
    out = f"{BASE}/clip{n}.mp4"
    r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", str(w["start"]), "-to", str(w["end"]), "-i", SRC,
        "-vf", f"crop=ih*9/16:ih,scale=1080:1920,subtitles={srt_path}:force_style='FontSize=28,PrimaryColour=&HFFFFFF&,OutlineColour=&H000000&,BorderStyle=1,Outline=2'",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-c:a", "aac", out], capture_output=True, text=True)
    print(f"CLIP {n} rc={r.returncode} srt_lines={len(lines)} first_line={lines[0][2] if lines else '-'}")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", "2", "-i", out, "-frames:v", "1", f"{BASE}/clip{n}-frame.png"], check=True)
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration,size",
        "-show_entries", "stream=codec_name,width,height", "-of", "default=noprint_wrappers=1", out],
        capture_output=True, text=True)
    print(probe.stdout.strip())
