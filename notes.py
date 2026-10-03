'''
webcam = cv.VideoCapture(1)

start_time = time.time()
fps = 0

while True:
    is_true, frame = webcam.read()
    flipped_frame = cv.flip(frame, 1)
    fps += 1

    if not is_true:
        break

    # converts bgr tp rgb because mediapipe doesn't accept rgb
    rgb_frame = cv.cvtColor(flipped_frame, cv.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

    result = landmarker.detect(mp_image)

    # pose landmarks is a 2d array of points
    # there is a list of landmarks for each person in the frame
    if result.pose_landmarks:
        nose = result.pose_landmarks[0][0]  # person one, landmark one(nose)
        left_eye = result.pose_landmarks[0][2]
        right_eye = result.pose_landmarks[0][5]

        # lines 36 to cv.imshow() should be a function
        x_nose = nose.x
        y_nose = nose.y

        x_left_eye = left_eye.x
        y_left_eye = left_eye.y

        x_right_eye = right_eye.x
        y_right_eye = right_eye.y

        # values need to be int because pixels cannot be floats
        pixel_x_nose = int(flipped_frame.shape[1] * x_nose)
        pixel_y_nose = int(flipped_frame.shape[0] * y_nose)

        pixel_x_eye_left = int(frame.shape[1] * x_left_eye)
        pixel_y_eye_left = int(frame.shape[0] * y_left_eye)

        pixel_x_eye_right = int(flipped_frame.shape[1] * x_right_eye)
        pixel_y_eye_right = int(flipped_frame.shape[0] * y_right_eye)

        cv.circle(
            flipped_frame,
            (pixel_x_nose, pixel_y_nose),
            10,
            (255, 0, 0),
            thickness=cv.FILLED,
        )
        cv.circle(
            flipped_frame,
            (pixel_x_eye_left, pixel_y_eye_left),
            10,
            (0, 0, 255),
            thickness=cv.FILLED,
        )
        cv.circle(
            flipped_frame,
            (pixel_x_eye_right, pixel_y_eye_right),
            10,
            (0, 0, 255),
            thickness=cv.FILLED,
        )

    elapsed = time.time() - start_time
    fps_total = fps / elapsed

    cv.imshow("WebCam Footage", flipped_frame)

    if cv.waitKey(1) & 0xFF == ord("q"):
        print(f"FPS: {fps_total}")
        break


"""
there is a slight problem with the code above
it returns an index error(out of range) when point is not found or is off the frame

CHATGPT:
You'll notice:
    if result.pose_landmarks:

This is extremely important.
What if MediaPipe doesn't see anyone?
Then there may be no pose.
Without this:
    pose = result.pose_landmarks[0]

your program could crash.
So:
    if result.pose_landmarks:

means:
Only try to access the person if MediaPipe actually detected one.
"""
"""
TO ANALYZE VIDEO - usefull for uploading videos and rating form
landmarker.detect_for_video(
    image,
    timestamp
)

ONCE THE BASICS ARE MADE
    Research advanceded architecture - live stream through mediapipe
    regulate jitter - find the average of a couple frames
"""

webcam.release()
cv.destroyAllWindows()
'''