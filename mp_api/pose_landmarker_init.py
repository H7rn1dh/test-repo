import mediapipe as mp

BaseOptions = mp.tasks.BaseOptions
PoseLandmarker = mp.tasks.vision.PoseLandmarker
PoseLandmarkerOptions = mp.tasks.vision.PoseLandmarkerOptions

options = PoseLandmarkerOptions(
    base_options=BaseOptions(model_asset_path="mp_api/pose_landmarker_full.task")
)

landmarker = PoseLandmarker.create_from_options(options)

"""
on hackathon day, the file formating for mediapipe will the following:
FormCheck.ai
|
|---->mediapipe/
|        |---->pose_landmarker_full/lite.task
|
|---->pose_landmarker_init.py
|
|---->main.py
|
|--->index.html
...
...
...
"""


