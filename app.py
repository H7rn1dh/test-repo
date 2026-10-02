import time
import cv2 as cv
import mediapipe as mp
from mp_api.pose_landmarker_init import landmarker
from flask import Flask, render_template, Response
from flask import request
import webbrowser

app = Flask(__name__)


@app.route("/")  # when someone goes to the "/" (homepage) run the code underneath
def home():
    return render_template("index.html")  # homepage


def generate_frames(webcam_num):
    webcam = cv.VideoCapture(webcam_num)

    while True:
        is_true, frame = webcam.read()
        if not is_true:
            break

        rgb_frame = cv.cvtColor(frame, cv.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        result = landmarker.detect(mp_image)

        if result.pose_landmarks:
            pose = result.pose_landmarks[0]
            left_eye = pose[mp.tasks.vision.PoseLandmark.LEFT_EYE]
            right_eye = pose[mp.tasks.vision.PoseLandmark.RIGHT_EYE]

            left_eye_px_x = int(frame.shape[1] * left_eye.x)
            left_eye_px_y = int(frame.shape[0] * left_eye.y)

            right_eye_px_x = int(frame.shape[1] * right_eye.x)
            right_eye_px_y = int(frame.shape[0] * right_eye.y)

            cv.circle(
                frame, (left_eye_px_x, left_eye_px_y), 10, (255, 0, 0), thickness=-1
            )
            cv.circle(
                frame, (right_eye_px_x, right_eye_px_y), 10, (0, 255, 0), thickness=-1
            )

            cv.line(
                frame,
                (left_eye_px_x, left_eye_px_y),
                (right_eye_px_x, right_eye_px_y),
                (0, 0, 0),
                thickness=3,
            )

        # takes the frame and compresses it to JPEG(buffer contains it)
        _ret, buffer = cv.imencode(".jpg", frame)  # "_" prefix means variable not used
        frame = buffer.tobytes()  # converts encoded img to bytes for HTTP
        # below: streaming the footage
        yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")
        # yield vs return : yield -> "Here's one thing, I'll give you another thing later"
        #                  return-> "I'm done"
        #  b -> means bytes
        # Content-Type: image/jpeg -> a new frame is starting ; its a JPEG


@app.route("/video_feed")  # creates the location of our live stream
def video_feed():
    # runs when the browser asks for video feed
    return Response(
        generate_frames(1), mimetype="multipart/x-mixed-replace; boundary=frame"
    )
    # Response makes a HTTP response
    # generate_frames() tells the browser that the frames are coming from that
    # mimetype="multipart/x-mixed-replace; boundary=frame" -> tells brower, response has >1 images seperated in frames
    # "This is the magic that makes the MJPEG-style stream work."


@app.route("/upload", methods=["POST"])# creates upload route
def upload():
    #runs when upload happens
    video = request.files["video"]
    video.save("uploads/input.mp4")
    return "Uploaded!"



# THIS SHOULD ALWAYS RUN IN THE END
if __name__ == "__main__":
    webbrowser.open("http://127.0.0.1:5000")  # opens the local host in chrome
    app.run(debug=True, use_reloader=False)

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
