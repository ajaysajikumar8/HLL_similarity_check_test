from flask import Blueprint, request, jsonify, render_template, send_file
import pandas as pd
from ..services.composition_service import match_compositions
import logging

composition_bp = Blueprint("composition", __name__)


@composition_bp.route("/match-compositions", methods=["POST"])
def match_compositions_api():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No file uploaded"})

    try:
        df = pd.read_excel(file, engine="openpyxl")
        print("Test: ", __name__)
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
    return render_template(
        "results.html",
        unmatched_compositions=unmatched_compositions,
        matched_compositions=matched_compositions,
    )


@composition_bp.route("/download-modified-file")
def download_modified_file():
    modified_file_path = "matched_compositions.xlsx"
    return send_file(modified_file_path, as_attachment=True)
