from db import db  # Importing db from db.py

class StudyMaterial(db.Model):
    __bind_key__ = 'second'  # This model uses the second database
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    course = db.Column(db.String(100), nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    semester = db.Column(db.String(10), nullable=False)
    material_type = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=True)
    file_path = db.Column(db.String(200), nullable=True)
    youtube_link = db.Column(db.String(200), nullable=True)
