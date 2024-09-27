from flask import Blueprint, request, jsonify, Response
import pandas as pd
import logging
from ..services.implant_service import (
    match_price_cap_implant,
    get_all_implants,
    add_implant,
)
from ..utils import replace_nan_with_none
import json

implant_bp = Blueprint("implant", __name__)

composition_crud_logger = logging.getLogger("composition_crud")


@implant_bp.route("/similar-items-implants/compare-price", methods=["POST"])
def compare_price_similar_items_implants_route():
    try:
        similar_implant_id = request.json.get("similar_implant_id")
        product_implant = request.json.get("implant")
        similar_item = request.json.get("similar_item")

        if not product_implant and not similar_item:
            return (
                jsonify({"error": "Implant object and similar Implant Id required"}),
                400,
            )
        try:
            logging.getLogger("price_cap").info(product_implant)
            product_implant["df_product_description_with_specification"] = similar_item
            product_implant["df_unit_rate_to_hll_excl_of_tax"] = float(
                product_implant["df_unit_rate_to_hll_excl_of_tax"]
            )

            product_implant["price_comparison"] = match_price_cap_implant(
                similar_implant_id, product_implant
            )

            clean_data = replace_nan_with_none(product_implant)
            json_data = json.dumps(clean_data, indent=4)
            return Response(json_data, mimetype="application/json")

        except Exception as e:
            logging.getLogger("price_cap").error(
                f"Error comparing price for similar item: {e}"
            )
            error_data = {"error": str(e)}
            json_error_data = json.dumps(error_data)
            return Response(json_error_data, mimetype="application/json")
    except Exception as e:
        logging.getLogger(__name__).error(f"Error : {e}")
        error_data = {"error": str(e)}
        json_error_data = json.dumps(error_data)
        return Response(json_error_data, mimetype="application/json")


@implant_bp.route("/get-all-implants/")
def get_all_implants_route():
    # Retrieve query parameters from the request
    page = request.args.get("page", default=1, type=int)
    search_keyword = request.args.get("search_keyword", default="", type=str)

    limit = 10  # Define the number of records per page
    offset = (page - 1) * limit  # Calculate the offset based on the current page

    implants = get_all_implants(search_keyword, limit=limit, offset=offset)

    if implants is not None:
        try:
            response = {
                "implants": {
                    "approved": implants.get(1, {"implants": [], "count": 0}),
                    "pending": implants.get(0, {"implants": [], "count": 0}),
                }
            }
            return jsonify(response)
        except Exception as e:
            logging.getLogger(__name__).error(
                f"Error processing compositions data: {e}"
            )
            return jsonify({"error": "Error processing compositions data"}), 500
    else:
        return jsonify({"error": "Error retrieving compositions"}), 500


@implant_bp.route("/add-new-implant", methods=["POST"])
def add_new_implant_as_approver_route():
    try:
        item_code = request.form.get("item_code", None)
        implant_name = request.form.get("implant_name")
        status = 1

        if not implant_name:
            composition_crud_logger.error(f"Product (Implant) name is required")
            return jsonify({"error": "Product name (Implant) is required"}), 400

        try:
            new_composition = add_implant(
                item_code=item_code, implant_name=implant_name, status=status
            )
            if new_composition:
                return jsonify({"message": "Implant added successfully"})
            else:
                return jsonify({"error": "Error adding new Implant"}), 500
        except Exception as e:
            composition_crud_logger.error(f"Implant Add Error: {e}")
    except Exception as e:
        logging.getLogger(__name__).error(f"Error while adding implant: {e}")
