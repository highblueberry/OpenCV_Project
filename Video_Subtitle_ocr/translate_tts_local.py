"""
1) ./output/subtitles.json  (한국어)  ->  영어 번역 JSON
2) 같은 내용을 TTS로 합성해 subtitles_en.wav 저장
"""
import json, pathlib, torch, soundfile as sf
from transformers import MarianTokenizer, MarianMTModel
from TTS.api import TTS

# ---------- 경로 ----------
KOR_JSON   = "./output/subtitles.json"
ENG_JSON   = "./output/subtitles_en.json"
ENG_WAV    = "./output/subtitles_en.wav"
# --------------------------

# 1) MarianMT ko→en 번역기 로드 (CPU·GPU 자동)
print("loading MarianMT ko→en …")
tok = MarianTokenizer.from_pretrained("Helsinki-NLP/opus-mt-ko-en")
mt  = MarianMTModel.from_pretrained("Helsinki-NLP/opus-mt-ko-en").eval()
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
mt.to(DEVICE)

def translate_lines(lines):
    # 여러 줄(문장) → 영어 줄 리스트
    enc = tok(lines, return_tensors="pt", padding=True).to(DEVICE)
    with torch.no_grad():
        out = mt.generate(**enc, max_length=128)
    return tok.batch_decode(out, skip_special_tokens=True)

with open(KOR_JSON, encoding="utf-8") as f:
    subs_ko = json.load(f)

subs_en = []
for blk in subs_ko:
    en_lines = translate_lines(blk["text"])
    subs_en.append({**blk, "text": en_lines})

pathlib.Path(ENG_JSON).write_text(
        json.dumps(subs_en, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"영어 자막 저장 완료 → {ENG_JSON}")

# 2) Coqui-TTS 모델 로드 (Tacotron2-DDC)
print("loading Coqui-TTS (tacotron2-DDC) …")
tts = TTS(model_name="tts_models/en/ljspeech/tacotron2-DDC",
          progress_bar=False, gpu= torch.cuda.is_available())

full_text = " ".join(" ".join(b["text"]) for b in subs_en)
wav = tts.tts(full_text)

+ sf.write(ENG_WAV, wav, samplerate=tts.synthesizer.output_sample_rate, format="WAV")
+ print(f"WAV 저장완료 → {ENG_WAV}")