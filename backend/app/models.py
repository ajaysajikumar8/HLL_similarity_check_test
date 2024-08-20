from .db import db


class Compositions(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content_code = db.Column(db.String(10), nullable=True)
    compositions = db.Column(db.String(255), nullable=False)
    compositions_striped = db.Column(db.String(255), nullable=True)
    dosage_form = db.Column(db.String(50), default="", nullable=True)


class PriceCap(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    compositions = db.Column(db.String(255), nullable=False)
    strength = db.Column(db.String, nullable=True)
    dosage_form = db.Column(db.String, nullable=True)
    packing_unit = db.Column(db.String, nullable=True)
    price_cap = db.Column(db.Numeric, nullable=True)
    compositions_striped = db.Column(db.String, nullable=True)
