from flask import Blueprint, request, jsonify, Response
import pandas as pd
import logging
from app.services.composition_service import match_compositions
from app.services.implant_service import match_implants
from ..utils import replace_nan_with_none
import json

common_bp = Blueprint("common", __name__)


@common_bp.route("/match-file", methods=["POST"])
def match_file_api():
    file = request.files.get("file")
    file_type = request.args.get("file_type", default=1, type=int)

    if not file:
        logging.getLogger(__name__).error("File not uploaded")
        return jsonify({"error": "No file uploaded"}), 400

    try:
        df = pd.read_excel(file, engine="openpyxl")
    except Exception as e:
        logging.getLogger(__name__).error(f"Error reading Excel file: {e}")
        return jsonify({"error": "Error reading Excel file"}), 500

    file_type_to_function = {
        1: match_compositions,  # Normal Price Bid File
        2: match_implants,  # Implant Price Bid File
    }

    try:
        # Retrieve the function based on the file_type
        match_function = file_type_to_function.get(file_type)

        if match_function:
            matched, unmatched = match_function(df)
        else:
            logging.getLogger(__name__).error("Invalid file type")
            return jsonify({"error": "Invalid file type"}), 400
    except Exception as e:
        logging.getLogger(__name__).error(f"Error performing string matching: {e}")
        return jsonify({"error": "Error performing string matching"}), 500

    data = {
        "matched": matched,
        "unmatched": unmatched,
    }

    try:
        clean_data = replace_nan_with_none(data)
        json_data = json.dumps(clean_data, indent=4)

        return Response(json_data, mimetype="application/json")
    except Exception as e:
        logging.getLogger(__name__).error(f"Error processing response data: {e}")
        error_data = {"error": str(e)}
        json_error_data = json.dumps(error_data)
        return Response(json_error_data, mimetype="application/json"), 500
