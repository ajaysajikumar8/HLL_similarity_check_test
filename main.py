from flask import Flask, request, jsonify, render_template, send_file
import pandas as pd
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, text
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

setup_logging("parsing_composition.log", "parse_composition")
parse_composition_logger = logging.getLogger("parse_composition")


# Define Composition model
class Compositions(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content_code = db.Column(db.String(10), nullable=True)
    compositions = db.Column(db.String(255), nullable=False)
    compositions_striped = db.Column(db.String(255), nullable=True)
    dosage_form = db.Column(db.String(50), default="", nullable=True)


with app.app_context():
    db.create_all()


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
                "UPDATE Compositions SET compositions_striped = preprocess_composition(compositions);"
            )
        )
        db.session.commit()
        server_logger.info(
            "Compositions preprocessed and stored in compositions_striped in the database"
        )
    except Exception as e:
        db.session.rollback()
        server_logger.error(f"Error preprocessing compositions in the database: {e}")


def parse_composition(composition):
    """
    Parse the composition into a list of tuples (molecule, unit).
    If the molecule does not have a unit, use None as the unit.
    """
    try:
        # Match molecule and unit pairs
        pattern = r"([\w\s]+)(?:\(([\d.\/%\w]+)\))?"
        molecules = re.findall(pattern, composition)
        parsed_molecules = []

        for name, unit in molecules:
            name = name.strip()
            unit = unit if unit else None
            parsed_molecules.append((name, unit))

        return sorted(parsed_molecules)
    except Exception as e:
        parse_composition_logger.error(
            f"Error parsing composition: {composition}. Error: {e}"
        )
        return []


def is_match(composition1, composition2):
    """
    Custom comparison function to ensure both molecule names and units match.
    """

    # Parsed 1 =  User entered composition
    parsed1 = parse_composition(composition1)

    # Parsed 2 = DB Composition
    parsed2 = parse_composition(composition2)

    if parsed1 == parsed2:
        parse_composition_logger.info(f"Matched: User: {parsed1} with DB: {parsed2}")
    else:
        parse_composition_logger.error(
            f"Not a Match: User: {parsed1} with DB: {parsed2}"
        )

    return parsed1 == parsed2


def match_compositions(df):
    try:
        df["compositions"] = preprocess_data(df["compositions"])
    except Exception as e:
        server_logger.error(f"Some error within the file", e)

    # Later have to remove this code, only preprocess in the db if we add new compositions
    preprocess_compositions_in_db()

    matched_compositions = []
    unmatched_compositions = []
    modified_df = pd.DataFrame(columns=df.columns)

    for index, row in df.iterrows():
        composition = row["compositions"]
        striped_composition = composition.replace(
            " ", ""
        )  # Strip spaces for comparison

        try:
            query = (
                db.session.query(Compositions)
                .order_by(
                    func.levenshtein(
                        Compositions.compositions_striped, striped_composition
                    )
                )
                .limit(20)
            )
            result = query.all()

            best_match = None
            max_similarity = 0
            similar_items_score = []
            # array for storing similar composition and its score
            for res in result:
                db_composition_striped = res.compositions_striped
                similarity = fuzz.token_sort_ratio(
                    striped_composition, db_composition_striped
                )
                rough_compositions_logger.info(
                    f"User-Inputted: {composition};  DB Composition: {res.compositions};  with similarity score: {similarity}"
                )
                rough_compositions_logger.info(
                    f"Striped User-Input: {striped_composition}; DB Stripped Composition: {db_composition_striped}; with similarity score: {similarity} \n"
                )

                if similarity > max_similarity and is_match(
                    striped_composition, db_composition_striped
                ):
                    max_similarity = similarity
                    best_match = res.compositions

                similar_items_score.append((composition, similarity))
                

            if best_match and max_similarity > 98:
                matched_compositions.append(best_match)
                modified_df.loc[index] = row
                modified_df.at[index, "compositions"] = best_match

                composition_match_logger.info(
                    f"User-entered composition: {composition}, Matched composition: {best_match}, Match score: {max_similarity}"
                )
            else:
                unmatched_compositions.append(composition)
                unmatched_compositions_logger.info(
                    f"Unmatched composition: {composition}, Similarity percentage: {similarity}"
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
        "results.html",
        unmatched_compositions=unmatched_compositions,
        matched_compositions=matched_compositions,
    )


@app.route("/download-modified-file")
def download_modified_file():
    modified_file_path = "matched_compositions.xlsx"
    return send_file(modified_file_path, as_attachment=True)


# Run Flask app
if __name__ == "__main__":
    server_logger.info("Starting Flask app...")
    app.run(debug=True)
