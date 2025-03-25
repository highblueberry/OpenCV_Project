import cv2 as cv
import numpy as np

# weight for addWeighted
alpha = 0.85

# Load the image
img = cv.imread("simple_CartoonRendering\dragonball.jpg")
#img = cv.imread("simple_CartoonRendering\ju.png")
#img = cv.imread("simple_CartoonRendering\onepiece.jpg")

# Convert the image to grayscale
gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)

# apply median blur
gray = cv.medianBlur(gray, 3)

# Get the Canny edge image
edge = cv.Canny(gray, 300, 300, apertureSize=5)

# Get the black edge with white background
edge_inv = cv.bitwise_not(edge)

# for applying addweighted convert edge to 3-channel
edge_3 = cv.cvtColor(edge_inv, cv.COLOR_GRAY2BGR)

# merge img, black edge
cartoon = cv.addWeighted(img, alpha, edge_3, 1-alpha, 1)
 
cv.imshow("Cartoon", cartoon)
cv.waitKey(0)
cv.destroyAllWindows()