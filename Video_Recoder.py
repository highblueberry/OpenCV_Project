import cv2 as cv

## 노트북 웹캠 
video_file = 0

## 저장된 파일 이름 변경
count = 1 # 파일 순서

## video writer format 지정
output_format = 'avi'
output_fourcc = 'XVID' 

# read video_file
video = cv.VideoCapture(video_file)

# recording state 
recording = False  ## 녹화 중 여부
flip = False  ## 좌우 반전 여부
output = None

if video.isOpened():
    fps = video.get(cv.CAP_PROP_FPS)
    wait_msec = int(1/ fps *1000)
     
    while True:
        valid, img = video.read()
        if not valid:
            break
    
    
        key = cv.waitKey(wait_msec)
        if key == ord(' '):
            if recording:
                recording = False
                output.release()
                output = None
                print('녹화 완료')
                count += 1
                
            else:
                # 녹화 output 파일명 설정
                output_file = f'Webcam_output_{count}.avi'
                
                fps = video.get(cv.CAP_PROP_FPS)
                h, w, *_ = img.shape
                is_color = (img.ndim > 2) and (img.shape[2] > 1)
                output = cv.VideoWriter(output_file, cv.VideoWriter_fourcc(*output_fourcc), fps, (w, h), is_color)
                recording = True
                print('녹화 시작')
          
        if key == 9:
            flip = not flip
            
        if flip:
            img = cv.flip(img, 1)
          
        ## 녹화 중일 떄만 파일 저장
        if recording and output is not None:
            output.write(img) 
            
            cv.circle(img, (20, 20), 10, (0, 0, 255), -1)    
          
        cv.imshow("Video Player", img)
        
        if key == 27: 
            break
         
    ## 녹화 종료시 파일 release
    if output is not None:
        output.release()
        
    output.release()
    cv.destroyAllWindows()
                   
                   