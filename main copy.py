from flask import Flask, request, jsonify, render_template, send_file
import pandas as pd
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from fuzzywuzzy import fuzz
from utils import setup_logging
import logging
import re

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = (
    "postgresql://postgres:password@localhost/postgres"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# Set up logging
loggers = {
    "server": "server.log",
    "composition_match": "composition_match.log",
    "unmatched_compositions": "unmatched_compositions.log",
    "rough_compositions": "rough_compositions.log",
}

for logger_name, log_file in loggers.items():
    setup_logging(log_file, logger_name)

server_logger = logging.getLogger("server")
composition_match_logger = logging.getLogger("composition_match")
unmatched_compositions_logger = logging.getLogger("unmatched_compositions")
rough_compositions_logger = logging.getLogger("rough_compositions")


# Define Composition model
class Composition(db.Model):
    __tablename__ = "compositions_copy"
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


unit_conversion = {
    "mcg": 1e-6,
    "mg": 1e-3,
    "g": 1,
    "kg": 1e3,
    "ml": 1e-3,
    "l": 1,
    "iu": 1,
    "meq": 1,
    "ppm": 1,
    "ppb": 1e-3,
    "mg/m²": 1e-3,
}


def parse_composition(composition):
    pattern = re.compile(
        r"(\b[\w\s]+\b)\s*(?:\(?(\d+\.?\d*%?)\s*([a-zA-Z\/]+)\)?|(\d+\.?\d*%?)\s*([a-zA-Z\/]+)?)?\s*(tablet|capsule|caplet|syrup|injection|cream|ointment|gel|solution|suspension)?"
    )
    matches = pattern.findall(composition)
    parsed_composition = []

    # TODO: have to add error handling here
    for match in matches:
        molecule = match[0].strip().lower()
        amount = float(match[1])
        unit = match[2].lower()
        parsed_composition.append((molecule, amount, unit))

    return parsed_composition


# Can skip this part for now, after we decide on the units. 
def normalize_units(parsed_composition):
    normalized_composition = []

    # TODO: study the loop here, might be a bug here: 
    for molecule, amount, unit in parsed_composition:
        normalized_amount = amount * unit_conversion.get(unit, 1)
        normalized_unit = "g" if unit in unit_conversion else unit
        normalized_composition.append((molecule, normalized_amount, normalized_unit))

    return normalized_composition


def preprocess_data(data):
    modified_data = []

    for composition in data:
        parsed_composition = parse_composition(composition)
        normalized_composition = normalize_units(parsed_composition)
        sorted_composition = sorted(normalized_composition, key=lambda x: x[0])
        formatted_composition = " + ".join(
            [
                f"{molecule} {amount}{unit}"
                for molecule, amount, unit in sorted_composition
            ]
        )
        modified_data.append(formatted_composition)

    return modified_data


def preprocess_compositions_in_db():
    #TODO:  use the preprocess function in the db (postgres) instead of modifying the code as whole. 
    try:
        compositions = Composition.query.all()
        for comp in compositions:
            parsed_composition = parse_composition(comp.compositions)
            normalized_composition = normalize_units(parsed_composition)
            normalized_composition.sort(key=lambda x: (x[0], x[1]))
            comp.compositions = " + ".join(
                [f"{mol} {amt}{unit}" for mol, amt, unit in normalized_composition]
            )
        db.session.commit()
        server_logger.info("Compositions preprocessed in the database")
    except Exception as e:
        db.session.rollback()
        server_logger.error(f"Error preprocessing compositions in the database: {e}")


def match_compositions(df):
    preprocess_compositions_in_db()
    matched_compositions = []
    unmatched_compositions = []
    modified_df = pd.DataFrame(columns=df.columns)

    for index, row in df.iterrows():
        composition = row["compositions"]
        parsed_composition = parse_composition(composition)
        normalized_composition = normalize_units(parsed_composition)
        normalized_composition.sort(key=lambda x: (x[0], x[1]))
        normalized_composition_str = " + ".join(
            [f"{mol} {amt}{unit}" for mol, amt, unit in normalized_composition]
        )

        try:
            # Fetch top 20 closest matches using Levenshtein distance
            query = (
                db.session.query(Composition)
                .order_by(
                    func.levenshtein(
                        Composition.compositions, normalized_composition_str
                    )
                )
                .limit(20)
            )
            result = query.all()

            best_match = None
            max_similarity = 0
            #TODO:  is there any redundancy here, because we are doing the same function here. 
            for res in result:
                db_parsed_composition = parse_composition(res.compositions)
                db_normalized_composition = normalize_units(db_parsed_composition)
                db_normalized_composition.sort(key=lambda x: (x[0], x[1]))
                db_normalized_composition_str = " + ".join(
                    [
                        f"{mol} {amt}{unit}"
                        for mol, amt, unit in db_normalized_composition
                    ]
                )

                # Direct comparison of sorted and normalized components
                if normalized_composition == db_normalized_composition:
                    best_match = res.compositions
                    max_similarity = 100  # Exact match
                    break
                else:
                    # Perform fuzzy matching as a fallback
                    similarity = fuzz.token_sort_ratio(
                        normalized_composition_str, db_normalized_composition_str
                    )
                    rough_compositions_logger.info(
                        f"User-Inputted: {normalized_composition_str}; DB Composition: {db_normalized_composition_str} with similarity score: {similarity}"
                    )
                    if similarity > max_similarity:
                        max_similarity = similarity
                        best_match = db_normalized_composition_str

            rough_compositions_logger.info(" ")

            if (
                best_match and max_similarity >= 98
            ):  # Adjust similarity threshold as needed
                matched_compositions.append(best_match)
                modified_df.loc[index] = row
                modified_df.at[index, "compositions"] = best_match
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
