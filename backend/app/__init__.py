from flask import Flask
from .utils import setup_logging
from .db import db
from flask_migrate import Migrate
from dotenv import load_dotenv
from .services.composition_service import update_composition_id_in_price_cap
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
    setup_logging("critical.log", "critical", rotate_logs=False)
    setup_logging("composition_implant_match.log", "composition_implant_match")
    setup_logging(
        "unmatched_implants_compositions.log", "unmatched_implants_compositions"
    )
    setup_logging("rough_compositions_implants.log", "rough_compositions_implants")
    setup_logging("parse_composition.log", "parse_composition")
    setup_logging("price_cap.log", "price_cap")
    setup_logging("composition_implant_crud.log", "composition_implant_crud")

    # Register blueprints
    from .routes.composition_routes import composition_bp
    from .routes.common_routes import common_bp
    from .routes.implant_routes import implant_bp

    app.register_blueprint(common_bp)
    app.register_blueprint(composition_bp)
    app.register_blueprint(implant_bp)

    # Use this function when the composition id is null in the live DB ::: TEMP: WILL REMOVE LATER.
    # with app.app_context():
    #     update_composition_id_in_price_cap()

    with app.app_context():
        db.create_all()

    return app
