import cv2 as cv
import numpy as np

psyduck = cv.imread("./psyduck.jpg")

# CONVERTING TO GREYSCALE
grey = cv.cvtColor(psyduck, cv.COLOR_BGR2GRAY)
cv.imshow("greyscale", grey)

# IMAGE BLUR - reducing noise
blur = cv.GaussianBlur(
    psyduck, (5, 5), cv.BORDER_DEFAULT
)  # increase (5,5) to higher number for greater blur (NUM MUST ALWAYS BE ODD)
cv.imshow("blurred", blur)

# EDGE CASCADE - edge detection
canny = cv.Canny(
    psyduck, 250, 250
)  # 2 nums at the end are the sensitivity of the detection
cv.imshow("canny", canny)

# IMAGE DILATION
dilated = cv.dilate(canny, (3, 3), iterations=3)
cv.imshow("dilated", dilated)

# EROSION
eroded = cv.erode(dilated, (3, 3), iterations=3)
cv.imshow("eroded", eroded)

# RESIZING
resized = cv.resize(psyduck, (500, 500), interpolation=cv.INTER_CUBIC)
# cv.INTER_AREA = shrinking ; cv.INTER_LINEAR & .INTER_CUBIC = enlarging
# cubic is slower, but the result is higher quality
cv.imshow("resized", resized)

# CROPING
# images are arrays, so we can use array slicing to cut of values -> making the image smaller
cropped = psyduck[:125, 25:-25]
cv.imshow("cropped", cropped)


# IMAGE TRANSFORMATION
def translate(img, x, y):
    trans_mat = np.float32([[1, 0, x], [0, 1, y]])
    dimensions = (psyduck.shape[1], psyduck.shape[0])
    return cv.warpAffine(psyduck, trans_mat, dimensions)


"""
-x --> left
-y --> up
x --> right
y --> down
"""

translated = translate(psyduck, 100, 100)
cv.imshow('translated', translated)

cv.imshow("canvas", psyduck)
cv.waitKey(0)
