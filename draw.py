import cv2 as cv
import numpy as np

blank = np.zeros((500, 500, 3), dtype="uint8")  # makes a blank image
# (500, 500, 3) - giving the image hieght, width, colours (BGR)

# PAINTING THE CANVAS ONE COLOUR

# blank[:] = 0, 0, 255  # set the colour for all the pixels red

# blank[200:300] = 255, 0, 0  # sets the color for certain pixel range

# blank[200:300, 200:300] = 0, 255, 0  # sets the color for certain pixel range


# to fill in shapes, change thickness to cv.FILLED/ -1
# DRAWING A RECTANGLE
cv.rectangle(blank, (0, 0), (50, 100), (255, 255, 255), thickness=2)


# DRAWING A CIRCLE
cv.circle(
    blank, (blank.shape[1] // 2, blank.shape[0] // 2), 50, (123, 67, 167), thickness=2
)

# DRAWING A LINE
cv.line(
    blank,
    (50, 100),
    (blank.shape[1] // 2 - 39, blank.shape[0] // 2 - 39),
    (56, 148, 26),
    thickness=3,
)

# WRITE TEXT
cv.putText(blank, 'Hello World', (250,250), cv.FONT_HERSHEY_TRIPLEX, 1.0, (255,255,255), thickness=2)

cv.imshow("blank", blank)


# psyduck = cv.imread("./psyduck.jpg")  # creates matrix (reads image)

# creates a window and shows image; takes two arguements : window name, image
# cv.imshow("MP favorite pokemon", psyduck)

cv.waitKey(0)
