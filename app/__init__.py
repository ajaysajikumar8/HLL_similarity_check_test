from flask import Flask
from .utils import setup_logging
from .db import db


def create_app():
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = (
        "postgresql://postgres:password@localhost/postgres"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    # Set up logging
    setup_logging("server.log", __name__)
    setup_logging("composition_match.log", "composition_match")
    setup_logging("unmatched_compositions.log", "unmatched_compositions")
    setup_logging("rough_compositions.log", "rough_compositions")
    setup_logging("parse_composition.log", "parse_composition")

    # Register blueprints
    from .routes.main_routes import main_bp
    from .routes.composition_routes import composition_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(composition_bp)

    with app.app_context():
        db.create_all()

    return app
