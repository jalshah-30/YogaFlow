from flask import (
    Flask,
    render_template,
    request,
    jsonify
)

from flask_cors import CORS

from database import db
from models import YogaPose, AnalysisResult
from yoga_analyzer.analyzer_core import analyze_image

import os


# ==========================================
# CREATE FLASK APPLICATION
# ==========================================

app = Flask(__name__)

CORS(app)


# ==========================================
# DATABASE CONFIGURATION
# ==========================================

BASE_DIR = os.path.abspath(
    os.path.dirname(__file__)
)

database_path = os.path.join(
    BASE_DIR,
    "yoga.db"
)

app.config["SQLALCHEMY_DATABASE_URI"] = (
    "sqlite:///" + database_path
)

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False


db.init_app(app)


# ==========================================
# CREATE DATABASE
# ==========================================

with app.app_context():

    db.create_all()


# ==========================================
# FRONTEND ROUTES
# ==========================================

@app.route("/")
def home():

    return render_template(
        "index.html"
    )


@app.route("/dashboard")
def dashboard():

    return render_template(
        "dashboard.html"
    )


@app.route("/poses")
def poses_page():

    return render_template(
        "poses.html"
    )


@app.route("/analyzer")
def analyzer_page():

    return render_template(
        "analyzer.html"
    )


# ==========================================
# GET ALL POSES
# READ
# ==========================================

@app.route(
    "/api/poses",
    methods=["GET"]
)
def get_poses():

    poses = YogaPose.query.order_by(
        YogaPose.id.desc()
    ).all()

    result = []

    for pose in poses:

        result.append({

            "id": pose.id,

            "name": pose.name,

            "englishName":
                pose.english_name,

            "difficulty":
                pose.difficulty,

            "duration":
                pose.duration,

            "benefits":
                pose.benefits,

            "description":
                pose.description,

            "createdAt":
                pose.created_at.isoformat()
                if pose.created_at
                else None

        })

    return jsonify(result), 200


# ==========================================
# GET SINGLE POSE
# READ
# ==========================================

@app.route(
    "/api/poses/<int:pose_id>",
    methods=["GET"]
)
def get_pose(pose_id):

    pose = YogaPose.query.get(
        pose_id
    )

    if pose is None:

        return jsonify({
            "error": "Pose not found"
        }), 404


    return jsonify({

        "id": pose.id,

        "name": pose.name,

        "englishName":
            pose.english_name,

        "difficulty":
            pose.difficulty,

        "duration":
            pose.duration,

        "benefits":
            pose.benefits,

        "description":
            pose.description

    }), 200


# ==========================================
# CREATE POSE
# CREATE
# ==========================================

@app.route(
    "/api/poses",
    methods=["POST"]
)
def create_pose():

    data = request.get_json()

    if not data:

        return jsonify({
            "error": "No data received"
        }), 400


    required_fields = [

        "name",
        "englishName",
        "difficulty",
        "duration",
        "benefits",
        "description"

    ]


    for field in required_fields:

        if not data.get(field):

            return jsonify({

                "error":
                    f"{field} is required"

            }), 400


    pose = YogaPose(

        name=data["name"].strip(),

        english_name=
            data["englishName"].strip(),

        difficulty=
            data["difficulty"].strip(),

        duration=
            data["duration"].strip(),

        benefits=
            data["benefits"].strip(),

        description=
            data["description"].strip()

    )


    db.session.add(pose)

    db.session.commit()


    return jsonify({

        "message":
            "Yoga pose created successfully",

        "pose": {

            "id": pose.id,

            "name": pose.name,

            "englishName":
                pose.english_name,

            "difficulty":
                pose.difficulty,

            "duration":
                pose.duration,

            "benefits":
                pose.benefits,

            "description":
                pose.description

        }

    }), 201


# ==========================================
# UPDATE POSE
# UPDATE
# ==========================================

@app.route(
    "/api/poses/<int:pose_id>",
    methods=["PUT"]
)
def update_pose(pose_id):

    pose = YogaPose.query.get(
        pose_id
    )

    if pose is None:

        return jsonify({
            "error": "Pose not found"
        }), 404


    data = request.get_json()


    required_fields = [

        "name",
        "englishName",
        "difficulty",
        "duration",
        "benefits",
        "description"

    ]


    for field in required_fields:

        if not data.get(field):

            return jsonify({

                "error":
                    f"{field} is required"

            }), 400


    pose.name = data["name"].strip()

    pose.english_name = \
        data["englishName"].strip()

    pose.difficulty = \
        data["difficulty"].strip()

    pose.duration = \
        data["duration"].strip()

    pose.benefits = \
        data["benefits"].strip()

    pose.description = \
        data["description"].strip()


    db.session.commit()


    return jsonify({

        "message":
            "Yoga pose updated successfully"

    }), 200


# ==========================================
# DELETE POSE
# DELETE
# ==========================================

@app.route(
    "/api/poses/<int:pose_id>",
    methods=["DELETE"]
)
def delete_pose(pose_id):

    pose = YogaPose.query.get(
        pose_id
    )

    if pose is None:

        return jsonify({
            "error": "Pose not found"
        }), 404


    db.session.delete(
        pose
    )

    db.session.commit()


    return jsonify({

        "message":
            "Yoga pose deleted successfully"

    }), 200


# ==========================================
# GET DASHBOARD STATISTICS
# ==========================================

@app.route(
    "/api/dashboard",
    methods=["GET"]
)
def dashboard_data():

    pose_count = YogaPose.query.count()

    analysis_count = \
        AnalysisResult.query.count()


    analyses = AnalysisResult.query.order_by(
        AnalysisResult.id.desc()
    ).limit(5).all()


    recent_analysis = []


    for item in analyses:

        recent_analysis.append({

            "id": item.id,

            "pose":
                item.pose_name,

            "confidence":
                item.confidence,

            "score":
                item.score,

            "feedback":
                item.feedback,

            "createdAt":
                item.created_at.isoformat()
                if item.created_at
                else None

        })


    average_score = 0


    if analysis_count > 0:

        total = db.session.query(
            db.func.avg(
                AnalysisResult.score
            )
        ).scalar()

        average_score = round(
            total,
            2
        )


    return jsonify({

        "poseCount":
            pose_count,

        "analysisCount":
            analysis_count,

        "averageScore":
            average_score,

        "recentAnalysis":
            recent_analysis

    }), 200


# ==========================================
# ANALYZER API
# ==========================================

@app.route("/api/analyze", methods=["POST"])
def analyze():

    if "image" not in request.files:
        return jsonify({
            "success": False,
            "error": "No image uploaded."
        }), 400

    image = request.files["image"]

    if image.filename == "":
        return jsonify({
            "success": False,
            "error": "No image selected."
        }), 400

    try:

        image_bytes = image.read()

        result = analyze_image(
            image_bytes
        )

        # Save successful analysis
        if result.get("success"):

            analysis = AnalysisResult(

                pose_name=result["pose"],

                confidence=result["confidence"],

                score=result["score"],

                feedback=result["correction"]
            )

            db.session.add(analysis)
            db.session.commit()

        return jsonify(result)

    except Exception as e:

        print("Analyzer error:", e)

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# ==========================================
# RUN APPLICATION
# ==========================================

if __name__ == "__main__":

    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )