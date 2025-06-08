import cv2
import json
import easyocr
from pathlib import Path
from datetime import timedelta
from datetime import timedelta
from hanspell import spell_checker

# ---------- 설정 ----------
VIDEO_PATH            = "./input/video1.mp4"   # 입력 영상
OUTPUT_SRT            = "./output/subtitles.srt"     # SRT 결과
OUTPUT_JSON           = "./output/subtitles.json"    # JSON 결과
FRAME_INTERVAL_SEC    = 3.0                 # 몇 초마다 OCR?
KOREAN_RATIO_THRESHOLD= 0.6                 # 한글 글자 비율 최소치
CROP_BOTTOM_PCT       = 0.25                # 화면 하단 %만 OCR (0~1)
USE_GPU               = True               # GPU 사용 여부
# ---------------------------


def korean_ratio(text: str) -> float:
    """문자열 중 한글이 차지하는 비율(0~1)"""
    if not text:
        return 0.0
    kor = sum('가' <= c <= '힣' for c in text)
    return kor / len(text)


# 맞춤법 검사기
def correct_korean(text: str) -> str:
    """
    문자열에 한글이 일정 비율 이상 포함되면 Hanspell로 맞춤법 교정.
    API 호출 제한 대비 성능 균형을 위해 30자 이하 문장만 교정하도록 예시 설정.
    """
    if korean_ratio(text) < 0.3 or len(text) > 30:
        return text
    try:
        return spell_checker.check(text).checked
    except Exception:
        # 네트워크 오류·쿼터 초과 등 → 원본 유지
        return text


def extract_subtitles_with_easyocr() -> None:
    # 1) EasyOCR 초기화 (한글 + 영어)
    reader = easyocr.Reader(['ko', 'en'], gpu=USE_GPU)

    # 2) 비디오 준비
    cap = cv2.VideoCapture(VIDEO_PATH)
    if not cap.isOpened():
        raise FileNotFoundError(f"Cannot open video: {VIDEO_PATH}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    interval_frames = int(FRAME_INTERVAL_SEC * fps)

    subs = []           # 결과 저장용
    index = 1
    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % interval_frames == 0:
            # ── 2-1) 하단 일부만 크롭해 자막 집중 ──
            h, w = frame.shape[:2]
            y0 = int(h * (1 - CROP_BOTTOM_PCT))
            roi = frame[y0:h, 0:w]

            # ── 2-2) OCR 실행 ──
            results = reader.readtext(roi, detail=0, paragraph=False)

            # ── 2-3) 한글 비율 필터 + 중복 제거 ──
            texts = [
                t.strip() for t in results
                if korean_ratio(t) >= KOREAN_RATIO_THRESHOLD
            ]

            uniq = []
            for t in texts:
                t_corr = correct_korean(t)  # 맞춤법 교정 
                if not any(t in prev for prev in uniq):
                    uniq.append(t)

            # ── 2-4) 자막 블록 저장 ──
            if uniq:
                start_td = timedelta(seconds=frame_idx / fps)
                end_td   = timedelta(seconds=(frame_idx + interval_frames) / fps)
                subs.append({
                    "index": index,
                    "start": str(start_td)[:-3].replace('.', ','),
                    "end":   str(end_td)[:-3].replace('.', ','),
                    "text":  uniq
                })
                index += 1

        frame_idx += 1

    cap.release()

    # 3) SRT 저장
    with open(OUTPUT_SRT, "w", encoding="utf-8") as fsrt:
        for sub in subs:
            fsrt.write(f"{sub['index']}\n")
            fsrt.write(f"{sub['start']} --> {sub['end']}\n")
            fsrt.write("\n".join(sub['text']) + "\n\n")

    # 4) JSON 저장
    with open(OUTPUT_JSON, "w", encoding="utf-8") as fjson:
        json.dump(subs, fjson, ensure_ascii=False, indent=2)

    print(f"[완료] {len(subs)}개 자막을 SRT('{OUTPUT_SRT}') & JSON('{OUTPUT_JSON}')에 저장했습니다.")


if __name__ == "__main__":
    extract_subtitles_with_easyocr()