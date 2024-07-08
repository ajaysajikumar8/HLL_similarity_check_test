from flask import Flask, request, jsonify, render_template, send_file
import pandas as pd
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, text
from fuzzywuzzy import fuzz
from utils import setup_logging
import logging
import re

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://root:@localhost/test"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# Set up logging for server logs
setup_logging("server.log", __name__)
server_logger = logging.getLogger(__name__)

# Set up logging for composition matches
setup_logging("composition_match.log", "composition_match")
composition_match_logger = logging.getLogger("composition_match")

# Set up logging for unmatched compositions
setup_logging("unmatched_compositions.log", "unmatched_compositions")
unmatched_compositions_logger = logging.getLogger("unmatched_compositions")

setup_logging("rough_compositions.log", "rough_compositions")
rough_compositions_logger = logging.getLogger("rough_compositions")


# Define Composition model
class Compositions(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content_code = db.Column(db.String(10), nullable=True)
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
    modified_data = []

    for composition in data:
        # Split compositions by '+' or '|', strip extra spaces, and sort molecules alphabetically
        sorted_molecules = sorted(
            [molecule.strip().lower() for molecule in re.split(r"[+|]", composition)]
        )

        # Join sorted molecules back into a composition string
        modified_composition = " + ".join(sorted_molecules)

        modified_data.append(modified_composition)

    return modified_data


def preprocess_compositions_in_db():
    try:
        # Execute SQL command to preprocess compositions using the SQL function
        db.session.execute(
            text(
                "UPDATE Compositions SET compositions = preprocess_composition(compositions)"
            )
        )
        print("Hey")
        db.session.commit()
        server_logger.info("Compositions preprocessed in the database")
    except Exception as e:
        db.session.rollback()
        server_logger.error(f"Error preprocessing compositions in the database: {e}")


def match_compositions(df):
    # Preprocess compositions in the database, #essential to ensure proper matching of compositions
    print("check 1")
    preprocess_compositions_in_db()
    print("check 2")

    matched_compositions = []
    unmatched_compositions = []
    modified_df = pd.DataFrame(columns=df.columns)

    for index, row in df.iterrows():
        composition = row["compositions"]

        try:
            # Fetch compositions from the database ordered by Levenshtein distance
            query = (
                db.session.query(Compositions)
                .order_by(func.levenshtein(Compositions.compositions, composition))
                .limit(20)
            )
            result = query.all()

            # Compare fetched compositions with composition from Excel file
            best_match = None
            max_similarity = 0
            for res in result:
                similarity = fuzz.token_sort_ratio(composition, res.compositions)
                rough_compositions_logger.info(
                    f"User-Inputted: {composition}; DB Composition: {res.compositions} with similarity score: {similarity}"
                )
                if similarity > max_similarity:
                    max_similarity = similarity
                    best_match = res.compositions
            rough_compositions_logger.info(" ")

            if (
                best_match and max_similarity > 98
            ):  # Adjust similarity threshold as needed
                matched_compositions.append(best_match)
                modified_df.loc[index] = row
                modified_df.at[index, "compositions"] = best_match

                # Log the match including both user-entered and matched compositions
                composition_match_logger.info(
                    f"User-entered composition: {composition}, Matched composition: {best_match}, Match score: {max_similarity}"
                )
            else:
                unmatched_compositions.append(composition)
                unmatched_compositions_logger.info(
                    f"Unmatched composition: {composition}, Similarity percentage: {max_similarity if max_similarity is not None else 0}"
                )
        except Exception as e:
            server_logger.error(f"Error matching compositions: {e}")
            continue

    return matched_compositions, unmatched_compositions, modified_df


# User Interface - API endpoints
@app.route("/")
def upload():
    return render_template("index.html")


@app.route("/match-compositions", methods=["POST"])
def match_compositions_api():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No file uploaded"})

    try:
        df = pd.read_excel(file, engine="openpyxl")
    except Exception as e:
        server_logger.error(f"Error reading Excel file: {e}")
        return jsonify({"error": "Error reading Excel file"})

    # Preprocess compositions directly from DataFrame
    df["compositions"] = preprocess_data(df["compositions"])

    try:
        matched_compositions, unmatched_compositions, modified_df = match_compositions(
            df
        )
    except Exception as e:
        server_logger.error(f"Error performing string matching: {e}")
        return jsonify({"error": "Error performing string matching"})

    modified_file_path = "matched_compositions.xlsx"
    modified_df.to_excel(modified_file_path, index=False)

    return render_template(
        "results.html", unmatched_compositions=unmatched_compositions
    )


@app.route("/download-modified-file")
def download_modified_file():
    modified_file_path = "matched_compositions.xlsx"
    return send_file(modified_file_path, as_attachment=True)


# Run Flask app
if __name__ == "__main__":
    server_logger.info("Starting Flask app...")
    app.run(debug=True)
