from .db import db


class Compositions(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content_code = db.Column(db.String(10), nullable=True)
    compositions = db.Column(db.String(255), nullable=False)
    compositions_striped = db.Column(db.String(255), nullable=True)
    dosage_form = db.Column(db.String(50), default="", nullable=True)
    status = db.Column(db.Integer, nullable=False, default=0)


class PriceCapCompositions(db.Model):
    __tablename__ = 'price_cap_compositions'

    id = db.Column(db.Integer, primary_key=True)
    compositions = db.Column(db.String(255), nullable=False)
    strength = db.Column(db.String, nullable=True)
    dosage_form = db.Column(db.String, nullable=True)
    packing_unit = db.Column(db.String, nullable=True)
    price_cap = db.Column(db.Numeric, nullable=True)
    compositions_striped = db.Column(db.String, nullable=True)
    composition_id = db.Column(db.Integer, db.ForeignKey('compositions.id'), nullable=True)


class Implants(db.Model):
    __tablename__ = 'implants'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    item_code = db.Column(db.String(255), nullable=True)
    product_description = db.Column(db.String(255), nullable=True)
    status = db.Column(db.Integer, nullable=True, default=0)


class PriceCapImplants(db.Model):
    __tablename__ = 'price_cap_implants'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    implant_id = db.Column(db.Integer, db.ForeignKey('implants.id'), nullable=True)
    variant = db.Column(db.String(255), nullable=True)
    price_cap = db.Column(db.Numeric, nullable=True)