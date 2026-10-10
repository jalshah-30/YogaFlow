import os

# Force MediaPipe to use CPU before importing MediaPipe
os.environ["MEDIAPIPE_DISABLE_GPU"] = "1"

import streamlit as st
import cv2
import numpy as np
import pandas as pd
import mediapipe as mp
import joblib
import json
import time

from pathlib import Path

from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python import vision

from mediapipe.tasks.python.vision import (
    drawing_utils,
    drawing_styles,
    pose_landmarker
)


# ============================================================
# STREAMLIT CONFIG
# ============================================================

st.set_page_config(
    page_title="AI Yoga Coach",
    page_icon="🧘",
    layout="wide"
)


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

MODEL_PATH = BASE_DIR / "pose_landmarker.task"
CLASSIFIER_PATH = BASE_DIR / "yoga_pose_classifier.pkl"
REFERENCE_PATH = BASE_DIR / "yoga_reference_profiles.json"
CORRECTION_PATH = BASE_DIR / "yoga_correction_map.json"


# ============================================================
# CHECK FILES
# ============================================================

required_files = [
    MODEL_PATH,
    CLASSIFIER_PATH,
    REFERENCE_PATH,
    CORRECTION_PATH
]

missing_files = [
    str(path.name)
    for path in required_files
    if not path.exists()
]

if missing_files:

    st.error("Missing required files:")

    for file in missing_files:
        st.write(f"- {file}")

    st.stop()


# ============================================================
# LOAD RANDOM FOREST
# ============================================================

@st.cache_resource
def load_classifier():

    return joblib.load(
        CLASSIFIER_PATH
    )


classifier = load_classifier()


# ============================================================
# LOAD REFERENCE PROFILE
# ============================================================

@st.cache_data
def load_reference_profile():

    with open(
        REFERENCE_PATH,
        "r"
    ) as f:

        return json.load(f)


reference_profile = load_reference_profile()


# ============================================================
# LOAD CORRECTION MAP
# ============================================================

@st.cache_data
def load_correction_map():

    with open(
        CORRECTION_PATH,
        "r"
    ) as f:

        data = json.load(f)

    correction_map = {}

    for key, value in data.items():

        joint, direction = key.split("|")

        correction_map[
            (joint, direction)
        ] = value

    return correction_map


correction_map = load_correction_map()


# ============================================================
# CREATE MEDIAPIPE LANDMARKER
# ============================================================

def create_landmarker():

    st.write("Initializing AI pose detector...")

    base_options = BaseOptions(
        model_asset_path=str(
            MODEL_PATH
        ),
        delegate=BaseOptions.Delegate.CPU
    )

    options = vision.PoseLandmarkerOptions(

        base_options=base_options,

        running_mode=vision.RunningMode.IMAGE,

        num_poses=1,

        min_pose_detection_confidence=0.5,

        min_pose_presence_confidence=0.5,

        min_tracking_confidence=0.5,

        output_segmentation_masks=False
    )

    landmarker = (
        vision.PoseLandmarker.create_from_options(
            options
        )
    )

    return landmarker


# ============================================================
# ANGLE CALCULATION
# ============================================================

def calculate_angle(a, b, c):

    a = np.array(a)
    b = np.array(b)
    c = np.array(c)

    ba = a - b
    bc = c - b

    denominator = (
        np.linalg.norm(ba) *
        np.linalg.norm(bc)
    )

    if denominator == 0:

        return np.nan

    cosine_angle = (
        np.dot(ba, bc)
        / denominator
    )

    cosine_angle = np.clip(
        cosine_angle,
        -1.0,
        1.0
    )

    return float(
        np.degrees(
            np.arccos(
                cosine_angle
            )
        )
    )


# ============================================================
# LANDMARK POINT
# ============================================================

def get_point(
    landmarks,
    index
):

    landmark = landmarks[index]

    return [
        landmark.x,
        landmark.y,
        landmark.z
    ]


# ============================================================
# POSE ANGLES
# ============================================================

def calculate_pose_angles(
    landmarks
):

    return {

        "left_elbow": calculate_angle(
            get_point(landmarks, 11),
            get_point(landmarks, 13),
            get_point(landmarks, 15)
        ),

        "right_elbow": calculate_angle(
            get_point(landmarks, 12),
            get_point(landmarks, 14),
            get_point(landmarks, 16)
        ),

        "left_knee": calculate_angle(
            get_point(landmarks, 23),
            get_point(landmarks, 25),
            get_point(landmarks, 27)
        ),

        "right_knee": calculate_angle(
            get_point(landmarks, 24),
            get_point(landmarks, 26),
            get_point(landmarks, 28)
        ),

        "left_hip": calculate_angle(
            get_point(landmarks, 11),
            get_point(landmarks, 23),
            get_point(landmarks, 25)
        ),

        "right_hip": calculate_angle(
            get_point(landmarks, 12),
            get_point(landmarks, 24),
            get_point(landmarks, 26)
        ),

        "left_shoulder": calculate_angle(
            get_point(landmarks, 23),
            get_point(landmarks, 11),
            get_point(landmarks, 13)
        ),

        "right_shoulder": calculate_angle(
            get_point(landmarks, 24),
            get_point(landmarks, 12),
            get_point(landmarks, 14)
        )
    }


# ============================================================
# FEATURE EXTRACTION
# ============================================================

def extract_landmark_features(
    landmarks
):

    features = []

    for landmark in landmarks:

        features.extend([
            landmark.x,
            landmark.y,
            landmark.z,
            landmark.visibility
        ])

    return np.array(
        features,
        dtype=np.float32
    )


# ============================================================
# POSTURE EVALUATION
# ============================================================

def evaluate_posture(
    pose_name,
    angles,
    reference_profile
):

    if pose_name not in reference_profile:

        return {
            "score": 0,
            "issues": []
        }

    profile = reference_profile[
        pose_name
    ]

    scores = []
    issues = []

    for joint, current_angle in angles.items():

        if (
            joint not in profile
            or np.isnan(current_angle)
        ):

            continue

        lower = profile[
            joint
        ]["lower"]

        upper = profile[
            joint
        ]["upper"]

        if lower <= current_angle <= upper:

            scores.append(1.0)

        else:

            if current_angle < lower:

                difference = (
                    lower - current_angle
                )

                direction = "too_low"

            else:

                difference = (
                    current_angle - upper
                )

                direction = "too_high"

            joint_score = max(
                0.0,
                1.0 - difference / 45.0
            )

            scores.append(
                joint_score
            )

            issues.append({

                "joint": joint,

                "current": round(
                    float(current_angle),
                    1
                ),

                "expected_lower": round(
                    float(lower),
                    1
                ),

                "expected_upper": round(
                    float(upper),
                    1
                ),

                "direction": direction
            })

    score = (
        np.mean(scores) * 100
        if scores
        else 0
    )

    return {

        "score": round(
            float(score),
            1
        ),

        "issues": issues
    }


# ============================================================
# STATUS
# ============================================================

def get_posture_status(score):

    if score >= 90:

        return "Excellent"

    elif score >= 75:

        return "Good"

    elif score >= 60:

        return "Needs Improvement"

    return "Incorrect"


# ============================================================
# UI
# ============================================================

st.title("AI Yoga Coach")

st.caption(
    "Real-time yoga pose recognition and posture correction"
)


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.header("Yoga Coach")

start_camera = st.sidebar.checkbox(
    "Start Camera"
)


# ============================================================
# MAIN UI
# ============================================================

video_placeholder = st.empty()

col1, col2, col3 = st.columns(3)

pose_placeholder = col1.empty()
score_placeholder = col2.empty()
status_placeholder = col3.empty()

instruction_placeholder = st.empty()


# ============================================================
# CAMERA
# ============================================================

if not start_camera:

    st.info(
        "Enable 'Start Camera' to begin."
    )

    st.stop()


# ============================================================
# INITIALIZE MEDIAPIPE ONLY NOW
# ============================================================

try:

    landmarker = create_landmarker()

except Exception as e:

    st.error(
        "MediaPipe could not initialize."
    )

    st.code(
        str(e)
    )

    st.stop()


st.success(
    "AI pose detector initialized successfully."
)


# ============================================================
# OPEN CAMERA
# ============================================================

cap = cv2.VideoCapture(0)

if not cap.isOpened():

    st.error(
        "Could not access webcam."
    )

    landmarker.close()

    st.stop()


# ============================================================
# CAMERA LOOP
# ============================================================

try:

    while True:

        ret, frame = cap.read()

        if not ret:

            break

        # Mirror
        frame = cv2.flip(
            frame,
            1
        )

        # BGR → RGB
        rgb_frame = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB
        )

        # MediaPipe image
        mp_image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=rgb_frame
        )

        # Detect
        result = landmarker.detect(
            mp_image
        )

        # ====================================================
        # NO POSE
        # ====================================================

        if len(
            result.pose_landmarks
        ) == 0:

            video_placeholder.image(
                rgb_frame,
                channels="RGB",
                use_container_width=True
            )

            pose_placeholder.metric(
                "Pose",
                "Not detected"
            )

            score_placeholder.metric(
                "Correctness",
                "--"
            )

            status_placeholder.metric(
                "Status",
                "--"
            )

            instruction_placeholder.info(
                "Perform a yoga pose in front of the camera."
            )

            time.sleep(0.03)

            continue


        # ====================================================
        # LANDMARKS
        # ====================================================

        landmarks = (
            result.pose_landmarks[0]
        )


        # ====================================================
        # FEATURES
        # ====================================================

        features = (
            extract_landmark_features(
                landmarks
            )
        )


        # ====================================================
        # VERIFY 132 FEATURES
        # ====================================================

        if len(features) != classifier.n_features_in_:

            st.error(
                f"Feature mismatch: "
                f"Model expects "
                f"{classifier.n_features_in_}, "
                f"received "
                f"{len(features)}."
            )

            break


        # ====================================================
        # CLASSIFIER INPUT
        # ====================================================

        features_input = pd.DataFrame(
            [features],
            columns=classifier.feature_names_in_
        )


        # ====================================================
        # POSE PREDICTION
        # ====================================================

        prediction = classifier.predict(
            features_input
        )

        predicted_pose = prediction[0]


        # ====================================================
        # BODY ANGLES
        # ====================================================

        angles = calculate_pose_angles(
            landmarks
        )


        # ====================================================
        # POSTURE
        # ====================================================

        posture_result = evaluate_posture(
            predicted_pose,
            angles,
            reference_profile
        )

        score = posture_result[
            "score"
        ]

        status = get_posture_status(
            score
        )


        # ====================================================
        # CORRECTION
        # ====================================================

        if len(
            posture_result["issues"]
        ) == 0:

            correction = (
                "Excellent! Keep holding the pose."
            )

        else:

            issue = (
                posture_result["issues"][0]
            )

            key = (
                issue["joint"],
                issue["direction"]
            )

            correction = correction_map.get(
                key,
                "Adjust your "
                + issue["joint"]
                .replace("_", " ")
                + "."
            )


        # ====================================================
        # DRAW SKELETON
        # ====================================================

        annotated_frame = np.copy(
            rgb_frame
        )

        drawing_utils.draw_landmarks(
            annotated_frame,
            landmarks,
            pose_landmarker.PoseLandmarksConnections.POSE_LANDMARKS,
            drawing_styles.get_default_pose_landmarks_style()
        )


        # ====================================================
        # DISPLAY
        # ====================================================

        video_placeholder.image(
            annotated_frame,
            channels="RGB",
            use_container_width=True
        )

        pose_placeholder.metric(
            "Pose",
            predicted_pose
        )

        score_placeholder.metric(
            "Correctness",
            f"{score:.1f}%"
        )

        status_placeholder.metric(
            "Status",
            status
        )

        instruction_placeholder.warning(
            correction
        )

        time.sleep(0.03)


finally:

    cap.release()

    try:
        landmarker.close()
    except:
        pass