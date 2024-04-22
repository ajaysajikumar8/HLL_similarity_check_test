from flask import Flask, request, jsonify, render_template
import pandas as pd
from flask_sqlalchemy import SQLAlchemy
from fuzzywuzzy import fuzz

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://root:@localhost/test"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# Define Composition model
class Compositions(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content_code = db.Column(db.String(10))
    compositions = db.Column(db.String(255), nullable=False)
    dosage_form = db.Column(db.String(50), default="")
    strength = db.Column(db.String(50), default="")
    packing_unit = db.Column(db.String(10), default="")
    rate_cap = db.Column(db.Numeric(10, 2), default=0.00)
    remarks = db.Column(db.String(255), default="")
    total_suppliers = db.Column(db.Integer, default=0)
    above_price_cap = db.Column(db.Integer, default=0)

# Data Preprocessing
def preprocess_data(data):
    # Add any necessary preprocessing steps here
    return data

# String Matching and Similarity Check
def match_compositions(vendor_data):
    matched_compositions = []
    for composition in vendor_data:
        max_similarity = 0
        matched_composition = None
        # Fetch compositions from the database
        master_data = Compositions.query.filter(
            Compositions.compositions.ilike("%" + composition + "%")
        ).all()
        for master_composition in master_data:
            similarity = fuzz.token_set_ratio(
                composition, master_composition.compositions
            )
            if similarity > max_similarity:
                max_similarity = similarity
                matched_composition = master_composition
        if max_similarity > 80:  # Adjust similarity threshold as needed
            matched_compositions.append(matched_composition.compositions)
    return matched_compositions

# User Interface - API endpoints
@app.route("/")
def upload():
    return render_template("index.html")

@app.route("/match-compositions", methods=["POST"])
def match_compositions_api():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"})

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"})

    # Read the uploaded Excel file
    try:
        df = pd.read_excel(file, engine="openpyxl")
    except Exception as e:
        return jsonify({"error": f"Error reading Excel file: {str(e)}"})

    # Extract compositions from the Excel file
    vendor_data = df["compositions"].tolist()

    # Preprocess vendor data
    vendor_data = preprocess_data(vendor_data)

    # Perform string matching
    matched_compositions = match_compositions(vendor_data)

    return jsonify({"matched_compositions": matched_compositions})

# Run Flask app
if __name__ == "__main__":
    app.run(debug=True)
