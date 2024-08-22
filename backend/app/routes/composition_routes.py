from flask import Blueprint, request, jsonify, Response
import pandas as pd
from ..services.composition_service import (
    sort_and_strip_composition,
    match_price_cap,
    match_compositions,
    get_all_compositions,
    add_composition,
    update_composition_status,
    delete_composition,
    get_composition_by_id,
    update_composition,
)
import logging
from ..utils import replace_nan_with_none
import json

composition_bp = Blueprint("composition", __name__)

composition_crud_logger = logging.getLogger("composition_crud")


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
        matched_compositions, unmatched_compositions = match_compositions(df)
    except Exception as e:
        logging.getLogger(__name__).error(f"Error performing string matching: {e}")
        return jsonify({"error": "Error performing string matching"})

    data = {
        "matched_compositions": matched_compositions,
        "unmatched_compositions": unmatched_compositions,
    }

    try:
        clean_data = replace_nan_with_none(data)

        json_data = json.dumps(clean_data, indent=4)

        return Response(json_data, mimetype="application/json")

    except Exception as e:
        error_data = {"error": str(e)}
        json_error_data = json.dumps(error_data)
        return Response(json_error_data, mimetype="application/json")


@composition_bp.route("/similar-items/compare-price", methods=["POST"])
def compare_price_similar_items_route():
    composition = request.json.get("composition")
    similar_item = request.json.get("similar_item")

    if not composition and not similar_item:
        return (
            jsonify(
                {"error": "composition object and similar composition name required"}
            ),
            400,
        )
    try:
        composition["df_compositions"] = similar_item
        striped_composition = sort_and_strip_composition(similar_item)
        composition["price_comparison"] = match_price_cap(
            composition, striped_composition
        )

        clean_data = replace_nan_with_none(composition)
        json_data = json.dumps(clean_data, indent=4)
        return Response(json_data, mimetype="application/json")

    except Exception as e:
        logging.getLogger("price_cap").error(
            f"Error comparing price for similar item: {e}"
        )
        error_data = {"error": str(e)}
        json_error_data = json.dumps(error_data)
        return Response(json_error_data, mimetype="application/json")


@composition_bp.route("/get-all-compositions")
def get_all_compositions_route():
    compositions = get_all_compositions()
    if compositions is not None:
        try:
            approved_compositions = []
            pending_compositions = []

            for composition in compositions:
                composition_data = {
                    "id": composition.id,
                    "content_code": composition.content_code,
                    "compositions": composition.compositions,
                    "compositions_striped": composition.compositions_striped,
                    "dosage_form": composition.dosage_form,
                    "status": composition.status,
                }

                if composition.status == 1:
                    approved_compositions.append(composition_data)
                else:
                    pending_compositions.append(composition_data)

            return jsonify(
                {
                    "compositions": {
                        "approved": approved_compositions,
                        "pending": pending_compositions,
                    }
                }
            )
        except Exception as e:
            logging.getLogger(__name__).error(
                f"Error processing compositions data: {e}"
            )
            return jsonify({"error": "Error processing compositions data"}), 500
    else:
        return jsonify({"error": "Error retrieving compositions"}), 500


@composition_bp.route("/add-new-composition", methods=["POST"])
def add_new_composition_as_approver_route():
    try:
        content_code = request.form.get("content_code", None)
        composition_name = request.form.get("composition_name")
        dosage_form = request.form.get("dosage_form", None)
        status = 1

        if not composition_name:
            composition_crud_logger.error(f"Composition name is required")
            return jsonify({"error": "Composition name is required"}), 400

        try:
            new_composition = add_composition(
                composition_name, content_code, dosage_form, status
            )
            if new_composition:
                return jsonify({"message": "Composition added successfully"})
            else:
                return jsonify({"error": "Error adding new composition"}), 500
        except Exception as e:
            composition_crud_logger.error(f"Composition Add Error: {e}")
    except Exception as e:
        logging.getLogger(__name__).error(f"Error while adding composition: {e}")


# Fetch a composition by ID
@composition_bp.route("/get-composition/<int:composition_id>")
def get_composition(composition_id):
    composition = get_composition_by_id(composition_id)
    if composition:
        composition_data = {
            "id": composition.id,
            "content_code": composition.content_code,
            "compositions": composition.compositions,
            "compositions_striped": composition.compositions_striped,
            "dosage_form": composition.dosage_form,
            "status": composition.status,
        }
        return jsonify(composition_data)
    else:
        composition_crud_logger.info(
            f"Composition not found. Composition id: {composition_id}"
        )
        return jsonify({"error": "Composition not found"}), 404


@composition_bp.route("/update-composition/<int:composition_id>", methods=["PUT"])
def update_composition_route(composition_id):
    try:
        content_code = request.form.get("content_code", None)
        composition_name = request.form.get("composition_name", None)
        dosage_form = request.form.get("dosage_form", None)

        try:
            updated_composition = update_composition(
                composition_id, content_code, composition_name, dosage_form
            )
            if updated_composition:
                return jsonify({"message": "Composition updated successfully"}), 200
            else:
                composition_crud_logger.error(
                    f"Cannot Update, No Composition found with id: {composition_id}"
                )
                return jsonify({"error": "No Composition found to update"}), 404
        except Exception as e:
            composition_crud_logger.error(f"Error updating the composition: {e}")
    except Exception as e:
        composition_crud_logger.error(f"Error while updating composition: {e}")
        return jsonify({"error": "Server error"}), 500


# Delete a composition (CRUD delete)
@composition_bp.route("/delete-composition/<int:composition_id>", methods=["DELETE"])
def delete_composition_route(composition_id):
    try:
        delete_composition(composition_id)
        return jsonify({"message": "Composition deleted successfully"})
    except Exception as e:
        composition_crud_logger.error(f"Error while deleting composition: {e}")
        return jsonify({"error": "Error deleting composition"}), 500


# Request a composition (status 0)
@composition_bp.route("/request-composition", methods=["POST"])
def request_composition():
    try:
        content_code = request.form.get("content_code", None)
        composition_name = request.form.get("composition_name")
        dosage_form = request.form.get("dosage_form", None)
        try:
            new_composition = add_composition(
                composition_name, content_code, dosage_form
            )
            if new_composition:
                return jsonify(
                    {"message": "Composition requested successfully", "status": 0}
                )
            else:
                return jsonify({"error": "Error requesting composition"}), 500
        except Exception as e:
            composition_crud_logger.error(f"Error while requesting composition: {e}")
    except Exception as e:
        composition_crud_logger.error(f"Error while requesting composition: {e}")
        return jsonify({"error": "Server error"}), 500


@composition_bp.route("/approve-composition", methods=["POST"])
def approve_composition():
    try:
        composition_id = request.json.get("composition_id")

        if not composition_id:
            return jsonify({"error": "Composition ID is required"}), 400

        try:
            updated_composition = update_composition_status(composition_id, 1)

            if updated_composition:
                return jsonify({"message": "Composition approved", "status": 1})
            else:
                return jsonify({"error": "Error approving composition"}), 500
        except Exception as e:
            composition_crud_logger.error(f"Error approving composition: {e}")

    except Exception as e:
        composition_crud_logger.error(f"Error approving composition: {e}")
        return jsonify({"error": str(e)}), 500
