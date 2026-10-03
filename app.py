import time
import cv2 as cv
import mediapipe as mp
from mp_api.pose_landmarker_init import landmarker
from flask import Flask, render_template, Response
from flask import request
import webbrowser

camera = 0  # default camera
camera_running = False

app = Flask(__name__)


def find_cameras():
    cameras = []

    for camera in range(5):
        webcam = cv.VideoCapture(camera)

        if webcam.isOpened():
            cameras.append(camera)

        webcam.release()

    return cameras


@app.route("/select_camera", methods=["POST"])
def select_camera():
    global camera

    data = request.get_json()
    camera = int(data["camera"])
    print(camera)
    return "Camera Selected"


@app.route("/")  # when someone goes to the "/" (homepage) run the code underneath
def home():
    cameras = find_cameras()

    return render_template("index.html", cameras=cameras)  # homepage


def generate_frames():
    webcam = cv.VideoCapture(camera)

    while camera_running:
        is_true, frame = webcam.read()
        if not is_true:
            break

        resized_frame = cv.resize(frame, (640, 450), interpolation=cv.INTER_AREA)

        rgb_frame = cv.cvtColor(resized_frame, cv.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        result = landmarker.detect(mp_image)

        if result.pose_landmarks:
            pose = result.pose_landmarks[0]
            left_eye = pose[mp.tasks.vision.PoseLandmark.LEFT_EYE]
            right_eye = pose[mp.tasks.vision.PoseLandmark.RIGHT_EYE]

            left_eye_px_x = int(resized_frame.shape[1] * left_eye.x)
            left_eye_px_y = int(resized_frame.shape[0] * left_eye.y)

            right_eye_px_x = int(resized_frame.shape[1] * right_eye.x)
            right_eye_px_y = int(resized_frame.shape[0] * right_eye.y)

            cv.circle(
                resized_frame,
                (left_eye_px_x, left_eye_px_y),
                10,
                (255, 0, 0),
                thickness=-1,
            )
            cv.circle(
                resized_frame,
                (right_eye_px_x, right_eye_px_y),
                10,
                (0, 255, 0),
                thickness=-1,
            )

            cv.line(
                resized_frame,
                (left_eye_px_x, left_eye_px_y),
                (right_eye_px_x, right_eye_px_y),
                (0, 0, 0),
                thickness=3,
            )

        # takes the frame and compresses it to JPEG(buffer contains it)
        _ret, buffer = cv.imencode(
            ".jpg", resized_frame
        )  # "_" prefix means variable not used
        resized_frame = buffer.tobytes()  # converts encoded img to bytes for HTTP
        # below: streaming the footage
        yield (
            b"--resized_frame\r\nContent-Type: image/jpeg\r\n\r\n"
            + resized_frame
            + b"\r\n"
        )
        # yield vs return : yield -> "Here's one thing, I'll give you another thing later"
        #                  return-> "I'm done"
        #  b -> means bytes
        # Content-Type: image/jpeg -> a new frame is starting ; its a JPEG


@app.route("/video_feed")  # creates the location of our live stream
def video_feed():
    # runs when the browser asks for video feed
    return Response(
        generate_frames(), mimetype="multipart/x-mixed-replace; boundary=resized_frame"
    )
    # Response makes a HTTP response
    # generate_frames() tells the browser that the frames are coming from that
    # mimetype="multipart/x-mixed-replace; boundary=frame" -> tells brower, response has >1 images seperated in frames
    # "This is the magic that makes the MJPEG-style stream work."


@app.route("/start_camera", methods=["POST"])
def start_camera():
    global camera_running
    camera_running = True
    return "LIVE FEED IS ON"


@app.route("/stop_camera", methods=["POST"])
def stop_camera():
    global camera_running
    camera_running = False
    return "LIVE FEED IS OFF"


# THIS SHOULD ALWAYS RUN IN THE END
if __name__ == "__main__":
    webbrowser.open("http://127.0.0.1:5000")  # opens the local host in chrome
    app.run(debug=True, use_reloader=False)
