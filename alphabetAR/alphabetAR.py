import cv2 as cv
import numpy as np

def extract_frames_and_detect_corners(video_path, board_pattern, interval):
    objpoints = []  # 3D points
    imgpoints = []  # 2D points
    valid_images = []
    image_size = None

    # Prepare 3D object points for the checkerboard
    cols, rows = board_pattern
    objp = board_cellsize * np.array([
        [c, r, 0] for r in range(rows) for c in range(cols)
    ], dtype=np.float32)

    cap = cv.VideoCapture(video_path)
    assert cap.isOpened(), "비디오 파일을 열 수 없습니다."

    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % interval != 0:
            frame_idx += 1
            continue

        gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)

        found, corners = cv.findChessboardCorners(
            gray, board_pattern,
            cv.CALIB_CB_ADAPTIVE_THRESH + cv.CALIB_CB_NORMALIZE_IMAGE
        )

        print(f"[{frame_idx}] 코너 찾았나? => {found}")

        if found:
            print(f"[{frame_idx}] 코너 검출 성공")

            if image_size is None:
                image_size = gray.shape[::-1]

            corners2 = cv.cornerSubPix(
                gray, corners, (11,11), (-1,-1),
                (cv.TERM_CRITERIA_EPS + cv.TERM_CRITERIA_MAX_ITER, 30, 0.001)
            )
            objpoints.append(objp)
            imgpoints.append(corners2)
            valid_images.append(frame.copy())

            cv.drawChessboardCorners(frame, board_pattern, corners2, found)
            cv.imshow("Corners", frame)
            if cv.waitKey(1) & 0xFF == ord('q'):
                break

        frame_idx += 1

    cap.release()
    cv.destroyAllWindows()

    return objpoints, imgpoints, image_size, valid_images



def calibrate_camera(objpoints, imgpoints, image_size):
    if not objpoints or not imgpoints:
        raise RuntimeError("코너를 검출한 프레임이 없습니다. 캘리브레이션 실패.")

    ret, K, dist, rvecs, tvecs = cv.calibrateCamera(
        objpoints, imgpoints, image_size, None, None
    )
    return ret, K, dist, rvecs, tvecs



def draw_letter_A_3D(
    image, K, dist, rvec, tvec, board_pattern, board_cellsize
):
    cols, rows = board_pattern  # (가로, 세로)

    # === 중심 위치 계산: 체스판 중앙 기준 2칸 위, 1.5칸 왼쪽 ===
    center_x = (cols - 1) / 2 * board_cellsize - 1.5 * board_cellsize
    center_y = (rows - 1) / 2 * board_cellsize - 2 * board_cellsize
    offset = np.array([center_x, center_y, 0], dtype=np.float32)

    # === A의 점 좌표 정의 ===
    base_shape = np.array([
        [0.0, 1.0, 0],
        [0.5, 0.0, 0],
        [1.0, 1.0, 0],
        [0.3, 0.5, 0],
        [0.7, 0.5, 0]
    ], dtype=np.float32)

    scale = board_cellsize * 3
    pts_base = base_shape * scale
    pts_lifted = pts_base.copy()
    pts_lifted[:, 2] = -0.025  # 공중 A: Z축으로 올리기

    # === 위치 이동 (중심 기준) ===
    pts_base += offset
    pts_lifted += offset

    # === 3D → 2D 투영 ===
    proj_base, _ = cv.projectPoints(pts_base, rvec, tvec, K, dist)
    proj_lifted, _ = cv.projectPoints(pts_lifted, rvec, tvec, K, dist)
    proj_base = proj_base.reshape(-1, 2).astype(int)
    proj_lifted = proj_lifted.reshape(-1, 2).astype(int)

    # === 체스판 위 A (노란색) ===
    cv.line(image, proj_base[0], proj_base[1], (0, 255, 255), 2)  # 노랑
    cv.line(image, proj_base[1], proj_base[2], (0, 255, 255), 2)
    cv.line(image, proj_base[3], proj_base[4], (0, 255, 255), 2)

    # === 공중 A (파란색) ===
    cv.line(image, proj_lifted[0], proj_lifted[1], (255, 0, 0), 2)  # 파랑
    cv.line(image, proj_lifted[1], proj_lifted[2], (255, 0, 0), 2)
    cv.line(image, proj_lifted[3], proj_lifted[4], (255, 0, 0), 2)

    # === 연결선 (빨간색) ===
    for p1, p2 in zip(proj_base, proj_lifted):
        cv.line(image, p1, p2, (0, 0, 255), 1)

    return image



if __name__ == '__main__':
    # === 설정 ===
    video_path = "alphabetAR\data\chessboard2.avi"  # 비디오 경로
    board_pattern = (8, 6)              # 내부 코너 수
    frame_interval = 20
    board_cellsize = 0.025               # 1칸 실제 크기 (예: 2.5cm)

    # === 비디오 열기 ===
    video = cv.VideoCapture(video_path)
    assert video.isOpened(), '비디오를 열 수 없습니다.'

    # === VideoWriter 저장 설정 ===
    fourcc = cv.VideoWriter_fourcc(*'XVID')
    fps = video.get(cv.CAP_PROP_FPS)
    frame_size = (int(video.get(cv.CAP_PROP_FRAME_WIDTH)),
                int(video.get(cv.CAP_PROP_FRAME_HEIGHT)))
    out = cv.VideoWriter('alphabetAR//data/output_AR.mp4', fourcc, fps, frame_size)

    # === 체스보드 3D 좌표 미리 생성 ===
    objp = board_cellsize * np.array([
        [c, r, 0] for r in range(board_pattern[1]) for c in range(board_pattern[0])
    ], dtype=np.float32)
    
    # === 체스보드 인식하기 ===
    objpoints, imgpoints, image_size, valid_images = extract_frames_and_detect_corners(video_path, board_pattern, interval=frame_interval)
    
    # === 카메라 캘리브레이션 ===
    rms, K, dist, rvecs, tvecs = calibrate_camera(objpoints, imgpoints, image_size)

    # === 프레임 반복 ===
    while True:
        ret, img = video.read()

        # 이미지 읽기 실패 시 종료
        if not ret or img is None or img.size == 0:
            print("[경고] 이미지가 유효하지 않아서 종료합니다.")
            break

        success, corners = cv.findChessboardCorners(img, board_pattern)

        if success:
            # ✅ img가 유효한 게 확인된 후에만 cvtColor 수행
            gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)

            corners2 = cv.cornerSubPix(
                gray, corners, (11, 11), (-1, -1),
                (cv.TERM_CRITERIA_EPS + cv.TERM_CRITERIA_MAX_ITER, 30, 0.001)
            )

            ret, rvec, tvec = cv.solvePnP(objp, corners2, K, dist)

            # AR 그리기
            draw_letter_A_3D(img, K, dist, rvec, tvec, board_pattern, board_cellsize)

            # 카메라 자세 출력
            R, _ = cv.Rodrigues(rvec)
            C = -R.T @ tvec
            pos_text = f"Camera XYZ: [{C[0][0]:.3f}, {C[1][0]:.3f}, {C[2][0]:.3f}]"
            cv.putText(img, pos_text, (10, 30), cv.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        # 영상 저장
        out.write(img)

    # === 종료 ===
    video.release()
    out.release()
    cv.destroyAllWindows()