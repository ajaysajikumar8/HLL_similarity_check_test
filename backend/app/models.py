from .db import db


class Compositions(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content_code = db.Column(db.String(10), nullable=True)
    compositions = db.Column(db.String(255), nullable=False)
    compositions_striped = db.Column(db.String(255), nullable=True)
    dosage_form = db.Column(db.String(50), default="", nullable=True)
