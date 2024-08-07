from flask import Blueprint, request, jsonify, send_file
import pandas as pd
from ..services.composition_service import (
    match_compositions,
    get_all_compositions,
    add_composition,
)
import logging
from ..utils import CustomJSONEncoder, replace_nan_with_none
import json

composition_bp = Blueprint("composition", __name__)


@composition_bp.route("/match-compositions", methods=["POST"])
def match_compositions_api():
    file = request.files.get("file")
    if not file:
        logging.getLogger(__name__).error(f"File not uploaded")
        return jsonify({"error": "No file uploaded"})

    try:
        df = pd.read_excel(file, engine="openpyxl")
    except Exception as e:
        logging.getLogger(__name__).error(f"Error reading Excel file: {e}")
        return jsonify({"error": "Error reading Excel file"})

    try:
        matched_compositions, unmatched_compositions, modified_df = match_compositions(
            df
        )
    except Exception as e:
        logging.getLogger(__name__).error(f"Error performing string matching: {e}")
        return jsonify({"error": "Error performing string matching"})

    modified_file_path = "matched_compositions.xlsx"
    modified_df.to_excel(modified_file_path, index=False)

    data = {
        "matched_compositions": matched_compositions,
        "unmatched_compositions": unmatched_compositions,
        "file_path": modified_file_path,
    }

    clean_data = replace_nan_with_none(data)

    logging.getLogger(__name__).info(clean_data)

    return jsonify(clean_data)


@composition_bp.route("/get-all-compositions")
def get_all_compositions_route():
    compositions = get_all_compositions()
    if compositions is not None:
        try:
            compositions_data = [
                {
                    "id": composition.id,
                    "content_code": composition.content_code,
                    "compositions": composition.compositions,
                    "compositions_striped": composition.compositions_striped,
                    "dosage_form": composition.dosage_form,
                }
                for composition in compositions
            ]
            return jsonify({"compositions": compositions_data})
        except Exception as e:
            logging.getLogger(__name__).error(
                f"Error retrieving compositions from DB: {e}"
            )
            return jsonify({"error": "Error processing compositions data"})
    else:
        return jsonify({"error": "Error retrieving compositions"})


@composition_bp.route("/add-new-composition", methods=["POST"])
def add_new_composition():
    content_code = request.form.get("content_code", None)
    composition_name = request.form.get("composition_name")
    dosage_form = request.form.get("dosage_form", None)

    if not composition_name:
        return jsonify({"error": "Composition name is required"}), 400

    new_composition = add_composition(content_code, composition_name, dosage_form)
    if new_composition:
        return jsonify({"message": "Composition added successfully"})
    else:
        return jsonify({"error": "Error adding new composition"}), 500


@composition_bp.route("/download-modified-file")
def download_modified_file():
    modified_file_path = "matched_compositions.xlsx"
    return send_file(modified_file_path, as_attachment=True)
