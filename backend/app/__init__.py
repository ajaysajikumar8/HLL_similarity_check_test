from flask import Flask
from .utils import setup_logging
from .db import db
from flask_migrate import Migrate
from dotenv import load_dotenv
import os

load_dotenv()


def create_app():
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("SQLALCHEMY_DATABASE_URI")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    migrate = Migrate(app, db)

    # Set up logging
    setup_logging("server.log", __name__)
    setup_logging("composition_match.log", "composition_match")
    setup_logging("unmatched_compositions.log", "unmatched_compositions")
    setup_logging("rough_compositions.log", "rough_compositions")
    setup_logging("parse_composition.log", "parse_composition")
    setup_logging("price_cap.log", "price_cap")

    # Register blueprints
    from .routes.composition_routes import composition_bp

    app.register_blueprint(composition_bp)

    with app.app_context():
        db.create_all()

    return app
