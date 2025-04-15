# OpenCV_Project

## 1. Video_Recoder
웹캠을 통화여 녹화를 하는 기본적인 Recoder 프로그램
 
### 기능
1. 스페이스바를 통한 녹화 시작 및 완료
2. 녹화된 파일은 순서대로 Webcam_output_1, Webcam_output_2 ... 의 이름을 가진다.
3. 녹화 중에는 왼쪽 위 빨간 점이 생겨 녹화 여부 인식 가능
4. Tab키를 통해서 좌우 반전 가능
5. ESC를 통해서 프로그램 종료


<img src="./Video_Recoder/Webcam_output_1.gif">

<br><br><br>


## 2. Simple_CartoonRendering
이미지를 넣으면 간단한 작업을 통해 카툰 랜더링하여 출력

### 기능
이미지의 edge 선을 따서 육안으로는 잘 보이지 않던 옷과 머리의 매무새    
그리고 옷의 구겨진 정도를 강조하여 표현하는 방식으로 카툰 랜더링을 진행한다.

### 한계점
간단한 형태의 피규어 이미지는 이러한 방식의 카툰 랜더링이 잘 먹힌다. ex) 드래곤볼, 주술회전   
하지만 복잡한 형태나 선이 매우 많은 피규어 이미지는 안 그래도 복잡한 형태의 이미지를 더 복잡하게만 만들 뿐 카툰 랜더링의 느낌이 덜하다.

<img src="./simple_CartoonRendering/dragonball.jpg">
<img src="./simple_CartoonRendering/result_dragonball.PNG">


<br><br><br>


## 3. Alphabet_AR
체스판 중앙에 알파벳 A를 3D 형태로 보여주는 AR기능

### 기능
카메라를 캘리브레이션하고 카메라의 자세를 구한다.  
이를 통해서 체스판 코너의 구석을 좌표계로 삼아서 알파벳 A를 AR로 보여주는 영상을 제작한다.

### 한계점 
알파벳 A만 가능하고 아직 다른 것은 불가능하다. 
AR로 구현하는 대상이 어떤 것인지에 따라 고쳐줘야하는 부분이 많다. 이를 자동으로 해결해주는 함수가 필요하다.   

<img src="./alphabetAR/data/output_AR.gif">