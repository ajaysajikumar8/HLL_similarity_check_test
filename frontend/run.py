from flask import Flask, render_template, request, jsonify
import requests
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)

backend_url = os.getenv("API_URL")  # Backend server URL


@app.route("/")
def upload():
    return render_template("index.html")


@app.route("/add_composition")
def add_composition():
    return render_template("add_composition.html")


@app.route("/match-compositions", methods=["POST"])
def match_compositions():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No file uploaded"})

    files = {"file": (file.filename, file.stream, file.mimetype)}
    response = requests.post(f"{backend_url}/match-compositions", files=files)
    response = response.json()
    matched_compositions = response["matched_compositions"]
    unmatched_compositions = response["unmatched_compositions"]

    return render_template(
        "results.html",
        unmatched_compositions=unmatched_compositions,
        matched_compositions=matched_compositions,
    )


@app.route("/get-all-compositions")
def get_all_compositions():
    response = requests.get(f"{backend_url}/get-all-compositions")
    return response.json()


@app.route("/add-new-composition", methods=["POST"])
def add_new_composition():
    data = {
        "content_code": request.form.get("content_code"),
        "composition_name": request.form.get("composition_name"),
        "dosage_form": request.form.get("dosage_form"),
    }
    response = requests.post(f"{backend_url}/add-new-composition", data=data)
    return response.json()


if __name__ == "__main__":
    app.run(debug=True, port=5001)
