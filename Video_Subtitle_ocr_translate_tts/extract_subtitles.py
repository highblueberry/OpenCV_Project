"""
1) ./input에 있는 video를 이용해 자막을 추출한다.
2) 추출한 자막으로 ./input./subtitles.json, ./input./subtitles.srt 저장
"""

import cv2, json, easyocr, statistics
from datetime import timedelta
from hanspell import spell_checker
from pathlib import Path

# ---------- 설정 ----------
VIDEO_PATH         = "./input/video2.mp4"
OUTPUT_SRT         = "./output/subtitles.srt"
OUTPUT_JSON        = "./output/subtitles.json"

FRAME_INTERVAL_SEC = 2.5        # OCR 주기
USE_GPU            = True      # GPU 사용?
MERGE_HORIZONTAL_GAP = 20       # 같은 줄 병합 시 허용 가로 간격(px)
KOREAN_RATIO_TH    = 0.6       # 자막 판단용 최소 한글 비율
MIN_WHRATIO        = 2.5        # 가로/세로 비
MIN_CHARS, MAX_CHARS = 4, 40    # 자막 글자 수 범위

# ★ 레이아웃 스캔 파라미터 ★
SCAN_SECONDS       = 3            # 앞쪽 3초만 샘플
SCAN_STRIDE_FRAMES = 5            # 매 5프레임마다 샘플
IQR_MARGIN_PX      = 10           # IQR 바깥 여유
MIN_ROI_RATIO      = 0.20        # 최소 ROI 폭 = 20 % H
FALLBACK_ROI       = (0.60, 1.00) # 스캔 실패 시 (y_start_ratio, y_end_ratio)
# ---------------------------

Path("./output").mkdir(exist_ok=True)


def korean_ratio(text: str) -> float:
    return sum('가' <= c <= '힣' for c in text) / max(1, len(text))

def correct_korean(text: str) -> str:
    """한글이 일정 비율 이상이면 Hanspell 교정."""
    if korean_ratio(text) < 0.3 or len(text) > 50:
        return text
    try:
        return spell_checker.check(text).checked
    except Exception:
        return text


"""
    EasyOCR results(detail=1: (box, text, conf)) →
    같은 y-라인 박스를 왼→오로 병합.
    return: list[(merged_box, merged_text)]
"""
def merge_line_boxes(results, gap=MERGE_HORIZONTAL_GAP):    
    if not results:
        return []

    # (1) y-중심으로 클러스터링
    centers = [(sum(pt[1] for pt in box) / 4, idx)
               for idx, (box, txt, conf) in enumerate(results)]
    clusters = []
    for cy, idx in sorted(centers, key=lambda x: x[0]):
        for cl in clusters:
            if abs(cl["cy"] - cy) < 20:          # 같은 줄로 본다
                cl["ids"].append(idx)
                cl["cy"] = (cl["cy"] * len(cl["ids"]) + cy) / (len(cl["ids"]) + 1)
                break
        else:                                   # 새 클러스터
            clusters.append({"cy": cy, "ids": [idx]})

    merged = []
    for cl in clusters:
        # (2) 같은 줄 안에서 x-좌표 기준 정렬
        line_ids = sorted(cl["ids"], key=lambda i: min(x for x, _ in results[i][0]))
        texts, x0, y0, x1, y1 = [], 1e9, 1e9, -1, -1
        for i in line_ids:
            box, txt, _ = results[i]
            texts.append(txt)
            xs = [p[0] for p in box]
            ys = [p[1] for p in box]
            x0, y0 = min(x0, *xs), min(y0, *ys)
            x1, y1 = max(x1, *xs), max(y1, *ys)
        merged.append(([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], " ".join(texts)))
    return merged


"""
    line_items: list[(box, text)]  ← 이미 가로로 병합된 '한 줄' 자막들
    v_gap     : 서로 다른 y-라인을 같은 블록으로 묶는 허용 세로거리(px)

    return list[{'box': merged_box, 'text_lines': [str, ...]}]
"""
def group_subtitle_blocks(line_items, v_gap=40):
    if not line_items:
        return []

    # y-기준 오름차순
    line_items.sort(key=lambda it: sum(p[1] for p in it[0]) / 4)

    blocks = []
    cur_box, cur_lines = line_items[0][0], [line_items[0][1]]

    def merge_box(b1, b2):
        xs = [p[0] for p in b1] + [p[0] for p in b2]
        ys = [p[1] for p in b1] + [p[1] for p in b2]
        return [(min(xs), min(ys)), (max(xs), min(ys)),
                (max(xs), max(ys)), (min(xs), max(ys))]

    for box, txt in line_items[1:]:
        cy_prev = sum(p[1] for p in cur_box) / 4
        cy_now  = sum(p[1] for p in box)     / 4
        if cy_now - cy_prev < v_gap:         # 같은 자막 블록
            cur_box   = merge_box(cur_box, box)
            cur_lines.append(txt)
        else:                                # 새 블록 시작
            blocks.append({'box': cur_box, 'text_lines': cur_lines})
            cur_box, cur_lines = box, [txt]
    blocks.append({'box': cur_box, 'text_lines': cur_lines})
    return blocks



""" 
    ─────────────────────────────────────────────────────────
    레이아웃 스캔: 글자 수 8자 이상 + 한글비율 조건만 샘플링
    return : 자막을 검출할 ROI범위에 사용할 가로, 세로 길이 
    ─────────────────────────────────────────────────────────
""" 
def scan_layout(cap, reader, fps):
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    y_centers = []

    total_frames = int(fps * SCAN_SECONDS)          # 앞쪽 10초
    for f in range(0, total_frames, SCAN_STRIDE_FRAMES):
        cap.set(cv2.CAP_PROP_POS_FRAMES, f)
        ok, frame = cap.read()
        if not ok:
            break

        dets = reader.readtext(frame, detail=1, paragraph=False)
        for box, txt, _ in dets:
            txt_clean = txt.replace(" ", "")
            # ① 한글 비율 + ② 글자수 ≥ 8  ←★ 새 필터
            if korean_ratio(txt_clean) < KOREAN_RATIO_TH:
                continue
            if len(txt_clean) < 8:
                continue

            cy = sum(p[1] for p in box) / 4         # 박스 y-중심
            y_centers.append(cy)

    # 스캔 실패 → 하단 ROI 폴백
    if len(y_centers) < 3:
        return FALLBACK_ROI          # (0.60, 1.00)

    # IQR(25–75%) ± margin
    q1, q3 = statistics.quantiles(y_centers, n=4)[0], statistics.quantiles(y_centers, n=4)[2]
    y0 = max(0, q1 - IQR_MARGIN_PX)
    y1 = min(h, q3 + IQR_MARGIN_PX)

    # 폭이 20 % H 미만이면 중앙값 ±10 % H 로 확대
    if y1 - y0 < MIN_ROI_RATIO * h:
        mid  = (y0 + y1) / 2
        half = (MIN_ROI_RATIO / 2) * h
        y0   = max(0, mid - half)
        y1   = min(h, mid + half)

    return y0 / h, y1 / h            # 비율 반환


# 자막 검출
def extract_subtitles():
    reader = easyocr.Reader(['ko', 'en'], gpu=USE_GPU)
    cap = cv2.VideoCapture(VIDEO_PATH)
    if not cap.isOpened():
        raise FileNotFoundError(VIDEO_PATH)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0

    # ★ 레이아웃 스캔 실행
    roi_start_r, roi_end_r = scan_layout(cap, reader, fps)
    print(f"[SCAN] ROI 비율: {roi_start_r:.2f} – {roi_end_r:.2f}")

    # 본 OCR 루프를 위해 캡처 위치 리셋
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    interval = int(FRAME_INTERVAL_SEC * fps)

    subs, idx, frame_idx = [], 1, 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_idx % interval == 0:
            h, w = frame.shape[:2]
            y0 = int(h * roi_start_r)
            y1 = int(h * roi_end_r)
            roi = frame[y0:y1, 0:w]

            dets = reader.readtext(roi, detail=1, paragraph=False)
            dets = [([(x, y + y0) for x, y in box], txt, conf) for box, txt, conf in dets]

            merged  = merge_line_boxes(dets)
            blocks  = group_subtitle_blocks(merged)

            texts = []
            for blk in blocks:
                box = blk['box']
                txt = "\n".join(blk['text_lines'])
                x0, y0b = box[0]; x1, y1b = box[2]
                ww, hh = x1 - x0, y1b - y0b

                if (ww / max(hh, 1) < MIN_WHRATIO or
                    not (MIN_CHARS <= len(txt.replace("\n","")) <= MAX_CHARS*2) or
                    korean_ratio(txt) < KOREAN_RATIO_TH):
                    continue
                texts.append(correct_korean(txt))

            uniq = [t for t in texts if all(t not in s['text'] for s in subs[-3:])]
            if uniq:
                start = timedelta(seconds=frame_idx / fps)
                end   = timedelta(seconds=(frame_idx + interval) / fps)
                subs.append({
                    "index": idx,
                    "start": str(start)[:-3].replace('.', ','),
                    "end":   str(end)[:-3].replace('.', ','),
                    "text":  uniq
                })
                idx += 1
        frame_idx += 1
    cap.release()

    with open(OUTPUT_SRT, 'w', encoding='utf-8') as fsrt:
        for s in subs:
            fsrt.write(f"{s['index']}\n{s['start']} --> {s['end']}\n")
            fsrt.write("\n".join(s['text']) + "\n\n")
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as fj:
        json.dump(subs, fj, ensure_ascii=False, indent=2)
    print(f"[완료] {len(subs)}개 자막을 저장했습니다.")




if __name__ == "__main__":
    extract_subtitles()          # 한 글 자막 추출 → subtitles.json