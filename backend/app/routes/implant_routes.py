from flask import Blueprint, request, jsonify, Response
import pandas as pd
import logging
from ..services.implant_service import (
    match_price_cap_implant,
    get_all_implants,
    add_implant,
    update_implant,
    update_implant_status,
    get_implant,
    delete_implant
)
from ..utils import replace_nan_with_none
import json
from ..constants import STATUS_APPROVED, STATUS_PENDING, STATUS_REJECTED

implant_bp = Blueprint("implant", __name__)

composition_crud_logger = logging.getLogger("composition_crud")


@implant_bp.route("/similar-items-implants/compare-price", methods=["POST"])
def compare_price_similar_items_implants_route():
    """
    API route to compare the price of a similar implant.

    This route takes the details of an implant and a similar item, compares their prices,
    and returns the result.

    Parameters:
    - similar_implant_id (str): Required; the ID of the similar implant.
    - implant (dict): Required; the implant object containing product details.
    - similar_item (str): Required; the description of the similar item.

    Returns:
    - 200: JSON response containing the price comparison results.
    - 400: JSON response with an error message if both implant and similar item are missing.
    - 500: JSON response with an error message in case of any internal error.
    """

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
    """
    API route to fetch all implants with pagination and search functionality.

    This route retrieves a paginated list of implants based on an optional search keyword.

    Parameters:
    - page (int): Optional; the page number to retrieve, default is 1.
    - search_keyword (str): Optional; a keyword to filter implants by name or description.

    Returns:
    - 200: JSON response containing the list of implants, separated into approved and pending.
    - 500: JSON response with an error message if there is an issue processing or retrieving the implants.
    """

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
                    "approved": implants.get(STATUS_APPROVED, {"implants": [], "count": 0}),
                    "pending": implants.get(STATUS_PENDING, {"implants": [], "count": 0}),
                }
            }
            return jsonify(response)
        except Exception as e:
            logging.getLogger(__name__).error(
                f"Error processing Implants data: {e}"
            )
            return jsonify({"error": "Error processing implants data"}), 500
    else:
        return jsonify({"error": "Error retrieving implants"}), 500


@implant_bp.route("/add-new-implant", methods=["POST"])
def add_new_implant_as_approver_route():
    """
    API route to add a new implant as an approver.

    This route allows an approver to add a new implant with a product description and item code.

    Parameters:
    - item_code (str): Optional; the unique code for the implant.
    - product_description (str): Required; the name or description of the implant.

    Returns:
    - 200: JSON response indicating the implant was added successfully.
    - 400: JSON response with an error message if the product description is not provided.
    - 500: JSON response with an error message if there is an error during the addition process.
    """

    try:
        item_code = request.form.get("item_code", None)
        product_description = request.form.get("product_description")
        status = STATUS_APPROVED

        if not product_description:
            composition_crud_logger.error(f"Product (Implant) name is required")
            return jsonify({"error": "Product name (Implant) is required"}), 400

        try:
            new_composition = add_implant(
                item_code=item_code, product_description=product_description, status=status
            )
            if new_composition:
                return jsonify({"message": "Implant added successfully"})
            else:
                return jsonify({"error": "Error adding new Implant"}), 500
        except Exception as e:
            composition_crud_logger.error(f"Implant Add Error: {e}")
    except Exception as e:
        logging.getLogger(__name__).error(f"Error while adding implant: {e}")


@implant_bp.route("/get-implant/<int:implant_id>")
def get_implant_by_id(implant_id):
    """
    API route to fetch an implant by its ID.

    This route retrieves the details of a specific implant based on the provided implant ID.

    Parameters:
    - implant_id (int): Required; the ID of the implant to be fetched.

    Returns:
    - 200: JSON response containing the implant details if found.
    - 404: JSON response with an error message if the implant is not found.
    """

    implant = get_implant(implant_id)
    if implant:
        implant_data = {
            "id": implant.id,
            "item_code": implant.item_code,
            "product_description": implant.product_description,
            "status": implant.status,
        }
        return jsonify(implant_data)
    else:
        composition_crud_logger.info(
            f"Implant not found. Implant id: {implant_id}"
        )
        return jsonify({"error": "Implant not found"}), 404
    

@implant_bp.route("/update-implant/<int:implant_id>", methods=["PUT"])
def update_implant_route(implant_id):
    """
    API route to update an implant's details by its ID.

    This route allows for updating the details of a specific implant, including
    its item code and product description.

    Parameters:
    - implant_id (int): Required; the ID of the implant to be updated.
    - item_code (str): Optional; the new item code for the implant.
    - product_description (str): Optional; the new product description for the implant.

    Returns:
    - 200: JSON response indicating the implant has been updated successfully.
    - 404: JSON response with an error message if no implant is found with the provided ID.
    - 500: JSON response with an error message if a server error occurs during the update process.
    """

    try:
        item_code = request.form.get("item_code", None)
        product_description = request.form.get("product_description", None)

        try:
            updated_implant = update_implant(
                implant_id=implant_id, item_code=item_code, product_description=product_description
            )
            if updated_implant:
                return jsonify({"message": "Implant updated successfully"}), 200
            else:
                composition_crud_logger.error(
                    f"Cannot Update, No Implant found with id: {implant_id}"
                )
                return jsonify({"error": "No Implant found to update"}), 404
        except Exception as e:
            composition_crud_logger.error(f"Error updating the implant: {e}")
    except Exception as e:
        composition_crud_logger.error(f"Error while updating implant: {e}")
        return jsonify({"error": "Server error"}), 500



# Delete a implant (CRUD delete)
@implant_bp.route("/delete-implant/<int:implant_id>", methods=["DELETE"])
def delete_implant_route(implant_id):
    """
    API route to delete an implant by its ID.

    This route allows for the deletion of a specific implant based on the provided
    implant ID.

    Parameters:
    - implant_id (int): Required; the ID of the implant to be deleted.

    Returns:
    - 200: JSON response confirming that the implant has been deleted successfully.
    - 404: JSON response with an error message if no implant is found with the provided ID.
    - 500: JSON response with an error message if a server error occurs during the deletion process.
    """

    try:
        deleted_implant = delete_implant(implant_id)
        if deleted_implant:
            return jsonify({"message": "Implant deleted successfully"})
        else:
            return jsonify({"error" : "No implant found with the provided id"})
    except Exception as e:
        composition_crud_logger.error(f"Error while deleting implant: {e}")
        return jsonify({"error": "Error deleting implant"}), 500


# Request a implant (status 0)
@implant_bp.route("/request-implant", methods=["POST"])
def request_to_add_implant_route():
    """
    API route to request the addition of a new implant.

    This route allows users to request the addition of a new implant with a specified 
    item code and product description. The request will be recorded with a status of 
    'pending' (status 0).

    Parameters:
    - item_code (str): Optional; the code associated with the implant.
    - product_description (str): Required; the name of the product (implant).

    Returns:
    - 200: JSON response confirming the implant request was successful, including status.
    - 400: JSON response with an error message if the product description is missing.
    - 500: JSON response with an error message if an error occurs during the request process.
    """

    try:
        item_code = request.form.get("item_code", None)
        product_description = request.form.get("product_description")
        status = STATUS_PENDING

        if not product_description:
            composition_crud_logger.error(f"Product (Implant) name is required")
            return jsonify({"error": "Product name (Implant) is required"}), 400

        try:
            new_implant = add_implant(
                item_code=item_code, product_description=product_description, status=status
            )
            if new_implant:
                return jsonify(
                    {"message": "Implant requested successfully", "status": 0}
                )
            else:
                return jsonify({"error": "Error requesting implant"}), 500
        except Exception as e:
            composition_crud_logger.error(f"Error while requesting implant: {e}")
    except Exception as e:
        composition_crud_logger.error(f"Error while requesting implant: {e}")
        return jsonify({"error": "Server error"}), 500


# Approve a implant (status 1)
@implant_bp.route("/approve-implant", methods=["PUT"])
def approve_requested_implant_route():
    """
    API route to approve a requested implant.

    This route allows an approver to change the status of a requested implant to 'approved' (status 1) 
    based on the provided implant ID.

    Parameters:
    - implant_id (int): Required; the ID of the implant to be approved.

    Returns:
    - 200: JSON response confirming the implant approval with status 1.
    - 400: JSON response with an error message if the implant ID is missing.
    - 500: JSON response with an error message if an error occurs during the approval process or if no implant is found with the provided ID.
    """

    try:
        implant_id = request.json.get("implant_id")

        if not implant_id:
            return jsonify({"error": "Implant ID is required"}), 400

        try:
            updated_implant = update_implant_status(implant_id=implant_id, status=STATUS_APPROVED)

            if updated_implant:
                return jsonify({"message": "Implant approved", "status": 1})
            else:
                return jsonify({"error": "Error approving implant, No Implant found with the provided id"}), 500
        except Exception as e:
            composition_crud_logger.error(f"Error approving implant: {e}")

    except Exception as e:
        composition_crud_logger.error(f"Error approving implant: {e}")
        return jsonify({"error": str(e)}), 500