from flask import Blueprint, render_template

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def upload():
    return render_template("index.html")


@main_bp.route("/add_composition")
def add_composition():
    return render_template("add_composition.html")
