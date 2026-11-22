import json, time
import av
_orig_open = av.open
def _open_patched(*a, **k):
    k.pop("metadata_errors", None)
    return _orig_open(*a, **k)
av.open = _open_patched
from faster_whisper import WhisperModel
t0 = time.time()
model = WhisperModel("base", device="cpu", compute_type="int8")
print("model loaded in", round(time.time()-t0, 1), "s", flush=True)
t0 = time.time()
segments, info = model.transcribe("/home/hatch/workspace/clipping-website/openshorts/../local-test/sample-70s.mp4",
                                  word_timestamps=True, vad_filter=True)
segs = []
for s in segments:
    segs.append({"start": round(s.start, 2), "end": round(s.end, 2),
                 "text": s.text.strip(),
                 "words": [{"w": w.word, "start": round(w.start, 2), "end": round(w.end, 2)} for w in (s.words or [])]})
print("transcribed in", round(time.time()-t0, 1), "s; lang", info.language,
      "prob", round(info.language_probability, 2), "segments", len(segs), flush=True)
full = " ".join(s["text"] for s in segs)
print("WORDS:", len(full.split()))
print("TEXT:", full[:800])
with open("/home/hatch/workspace/clipping-website/local-test/transcript.json", "w") as f:
    json.dump({"language": info.language, "segments": segs}, f, indent=1)
