from datetime import datetime
from database import db


class YogaPose(db.Model):

    __tablename__ = "yoga_poses"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(100),
        nullable=False
    )

    english_name = db.Column(
        db.String(100),
        nullable=False
    )

    difficulty = db.Column(
        db.String(30),
        nullable=False
    )

    duration = db.Column(
        db.String(50),
        nullable=False
    )

    benefits = db.Column(
        db.Text,
        nullable=False
    )

    description = db.Column(
        db.Text,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


class AnalysisResult(db.Model):

    __tablename__ = "analysis_results"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    pose_name = db.Column(
        db.String(100),
        nullable=False
    )

    confidence = db.Column(
        db.Float,
        nullable=False
    )

    score = db.Column(
        db.Float,
        nullable=False
    )

    feedback = db.Column(
        db.Text,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )