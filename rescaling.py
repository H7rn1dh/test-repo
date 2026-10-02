import cv2 as cv


def resize(frame, scale=0.75):
    # works on : Images, Videos, Live Video
    width = int(frame.shape[1] * scale)
    height = int(frame.shape[0] * scale)

    dimensions = (width, height)

    return cv.resize(frame, dimensions, interpolation=cv.INTER_AREA)


def change_res(width, hieght):
    # works on Live Video
    webcam.set(3, width)
    webcam.set(4, hieght)


# READING IMAGES

psyduck = cv.imread("./psyduck.jpg")  # creates matrix (reads image)

# creates a window and shows image; takes two arguements : window name, image
cv.imshow("MP favorite pokemon", psyduck)

resized_img = resize(psyduck, 1.5)
cv.imshow("resized img", resized_img)

cv.waitKey(0)


# READING VIDEOS - from webcam

webcam = cv.VideoCapture(
    0
)  # takes int or path to a video ; int = camera, path = downloaded vid

change_res(1920, 1080)

while True:
    isTrue, frame = webcam.read()

    resized_frame = resize(frame, 1.5)

    cv.imshow("Resized", resized_frame)
    cv.imshow("Stream", frame)

    #print(frame.shape) - showed the res of the frame

    if cv.waitKey(20) & 0xFF == ord("q"):
        # if letter 'q' is pressed on keyboard, break and stop loop
        break

webcam.release()
cv.destroyAllWindows()
