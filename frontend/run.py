from flask import Flask, render_template, request, jsonify
import requests
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)

backend_url = os.getenv("API_URL")  # Backend server URL
backend_url = "http://127.0.0.1:5000"  # overwrote because of env error :: CHECK LATER


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
    try:
        response = requests.post(f"{backend_url}/match-compositions", files=files)
        response = response.json()
        matched_compositions = response["matched_compositions"]
        unmatched_compositions = response["unmatched_compositions"]
        try:
            return render_template(
                "results.html",
                unmatched_compositions=unmatched_compositions,
                matched_compositions=matched_compositions,
            )
        except Exception as e:
            return jsonify({"error": "Some issues with the template rendering"})
    except Exception as e:
        return jsonify({"error": e})


@app.route("/get-all-compositions")
def get_all_compositions():
    try:
        response = requests.get(f"{backend_url}/get-all-compositions")
        return response.json()
    except Exception as e:
        print(f"{backend_url}/get-all-compositions")
        return jsonify({"error": ""})


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
