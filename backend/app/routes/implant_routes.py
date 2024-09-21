from flask import Blueprint, request, jsonify, Response
import pandas as pd
import logging
from ..services.implant_service import match_price_cap_implant
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
                jsonify(
                    {
                        "error": "Implant object and similar Implant Id required"
                    }
                ),
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