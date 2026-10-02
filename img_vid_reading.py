import cv2 as cv
import time

#READING IMAGES

psyduck = cv.imread('./psyduck.jpg') #creates matrix (reads image)

#creates a window and shows image; takes two arguements : window name, image
cv.imshow("MP favorite pokemon", psyduck)

cv.waitKey(0)

#READING VIDEOS - from webcam

webcam = cv.VideoCapture(1) #takes int or path to a video ; int = camera, path = downloaded vid

start_time = time.time()
fps = 0
while True:
    isTrue, frame = webcam.read()
    fps+=1


    cv.imshow('Stream', frame)

    if cv.waitKey(1) & 0xFF == ord('d'):
        #if letter 'd' is pressed on keyboard, break and stop loop
        elapsed = time.time() - start_time
        fps_total = fps / elapsed
        print(f"FPS: {fps_total}")
        break

webcam.release()
cv.destroyAllWindows()
