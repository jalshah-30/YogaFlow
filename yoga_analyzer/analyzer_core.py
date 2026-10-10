import os

# Force MediaPipe to CPU
os.environ["MEDIAPIPE_DISABLE_GPU"] = "1"

from pathlib import Path
import json
import cv2
import numpy as np
import pandas as pd
import joblib
import mediapipe as mp

from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python import vision
from mediapipe.python.solutions import drawing_utils
from mediapipe.python.solutions import drawing_styles

from mediapipe.tasks.python.vision import pose_landmarker


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

MODEL_PATH = BASE_DIR / "pose_landmarker.task"
CLASSIFIER_PATH = BASE_DIR / "yoga_pose_classifier.pkl"
REFERENCE_PATH = BASE_DIR / "yoga_reference_profiles.json"
CORRECTION_PATH = BASE_DIR / "yoga_correction_map.json"


# ============================================================
# LOAD FILES
# ============================================================

classifier = joblib.load(CLASSIFIER_PATH)

with open(REFERENCE_PATH, "r") as f:
    reference_profile = json.load(f)

with open(CORRECTION_PATH, "r") as f:
    correction_data = json.load(f)


# Convert:

# "left_knee|too_low"

# into:

# ("left_knee", "too_low")

correction_map = {}

for key, value in correction_data.items():
    joint, direction = key.split("|")
    correction_map[(joint, direction)] = value


# ============================================================
# MEDIAPIPE LANDMARKER
# ============================================================

def create_landmarker():

    base_options = BaseOptions(
        model_asset_path=str(MODEL_PATH),
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

    return vision.PoseLandmarker.create_from_options(options)


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
        np.linalg.norm(ba)
        * np.linalg.norm(bc)
    )

    if denominator == 0:
        return np.nan

    cosine_angle = np.dot(ba, bc) / denominator

    cosine_angle = np.clip(
        cosine_angle,
        -1.0,
        1.0
    )

    return float(
        np.degrees(
            np.arccos(cosine_angle)
        )
    )


# ============================================================
# LANDMARK POINT
# ============================================================

def get_point(landmarks, index):

    landmark = landmarks[index]

    return [
        landmark.x,
        landmark.y,
        landmark.z
    ]


# ============================================================
# POSE ANGLES
# ============================================================

def calculate_pose_angles(landmarks):

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

def extract_landmark_features(landmarks):

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

    profile = reference_profile[pose_name]

    scores = []
    issues = []

    for joint, current_angle in angles.items():

        if (
            joint not in profile
            or np.isnan(current_angle)
        ):
            continue

        lower = profile[joint]["lower"]
        upper = profile[joint]["upper"]

        if lower <= current_angle <= upper:

            scores.append(1.0)

        else:

            if current_angle < lower:

                difference = lower - current_angle
                direction = "too_low"

            else:

                difference = current_angle - upper
                direction = "too_high"

            joint_score = max(
                0.0,
                1.0 - difference / 45.0
            )

            scores.append(joint_score)

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
# MAIN ANALYZER
# ============================================================

def analyze_image(image_bytes):

    # --------------------------------------------------------
    # Convert uploaded bytes to OpenCV image
    # --------------------------------------------------------

    np_array = np.frombuffer(
        image_bytes,
        np.uint8
    )

    frame = cv2.imdecode(
        np_array,
        cv2.IMREAD_COLOR
    )

    if frame is None:
        raise ValueError("Could not read the image.")

    # --------------------------------------------------------
    # BGR -> RGB
    # --------------------------------------------------------

    rgb_frame = cv2.cvtColor(
        frame,
        cv2.COLOR_BGR2RGB
    )

    # --------------------------------------------------------
    # MediaPipe image
    # --------------------------------------------------------

    mp_image = mp.Image(
        image_format=mp.ImageFormat.SRGB,
        data=rgb_frame
    )

    # --------------------------------------------------------
    # Create detector
    # --------------------------------------------------------

    landmarker = create_landmarker()

    try:

        result = landmarker.detect(mp_image)

        # ----------------------------------------------------
        # Check pose
        # ----------------------------------------------------

        if len(result.pose_landmarks) == 0:

            return {
                "success": False,
                "message": "No yoga pose detected."
            }

        # ----------------------------------------------------
        # Get landmarks
        # ----------------------------------------------------

        landmarks = result.pose_landmarks[0]

        # ----------------------------------------------------
        # Features
        # ----------------------------------------------------

        features = extract_landmark_features(
            landmarks
        )

        # ----------------------------------------------------
        # Verify features
        # ----------------------------------------------------

        if len(features) != classifier.n_features_in_:

            raise ValueError(
                f"Feature mismatch. "
                f"Model expects "
                f"{classifier.n_features_in_}, "
                f"received {len(features)}."
            )

        # ----------------------------------------------------
        # Classifier input
        # ----------------------------------------------------

        features_input = pd.DataFrame(
            [features],
            columns=classifier.feature_names_in_
        )

        # ----------------------------------------------------
        # Pose prediction
        # ----------------------------------------------------

        prediction = classifier.predict(
            features_input
        )

        predicted_pose = str(
            prediction[0]
        )

        # ----------------------------------------------------
        # Confidence
        # ----------------------------------------------------

        confidence = 0

        if hasattr(classifier, "predict_proba"):

            probabilities = classifier.predict_proba(
                features_input
            )

            confidence = float(
                np.max(probabilities) * 100
            )

        # ----------------------------------------------------
        # Body angles
        # ----------------------------------------------------

        angles = calculate_pose_angles(
            landmarks
        )

        # ----------------------------------------------------
        # Posture
        # ----------------------------------------------------

        posture_result = evaluate_posture(
            predicted_pose,
            angles,
            reference_profile
        )

        score = posture_result["score"]

        status = get_posture_status(score)

        # ----------------------------------------------------
        # Correction
        # ----------------------------------------------------

        if len(posture_result["issues"]) == 0:

            correction = (
                "Excellent! Keep holding the pose."
            )

        else:

            issue = posture_result["issues"][0]

            key = (
                issue["joint"],
                issue["direction"]
            )

            correction = correction_map.get(
                key,
                "Adjust your "
                + issue["joint"].replace(
                    "_",
                    " "
                )
                + "."
            )

        # ----------------------------------------------------
        # Draw skeleton
        # ----------------------------------------------------

        annotated_frame = np.copy(
            rgb_frame
        )
        annotated_bgr = cv2.cvtColor(
            annotated_frame,
            cv2.COLOR_RGB2BGR
        )

        # ----------------------------------------------------
        # Convert annotated image to JPEG
        # ----------------------------------------------------

        annotated_bgr = cv2.cvtColor(
            annotated_frame,
            cv2.COLOR_RGB2BGR
        )

        success, buffer = cv2.imencode(
            ".jpg",
            annotated_bgr
        )

        if success:

            import base64

            annotated_image = base64.b64encode(
                buffer
            ).decode("utf-8")

        else:

            annotated_image = None

        # ----------------------------------------------------
        # Return result
        # ----------------------------------------------------

        return {

            "success": True,

            "pose": predicted_pose,

            "confidence": round(
                confidence,
                1
            ),

            "score": round(
                score,
                1
            ),

            "status": status,

            "correction": correction,

            "issues": posture_result[
                "issues"
            ],

            "annotated_image": annotated_image
        }

    finally:

        landmarker.close()