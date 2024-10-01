from flask import Blueprint, request, jsonify, Response
from ..services.composition_service import (
    sort_and_strip_composition,
    match_price_cap_composition,
    get_all_compositions,
    add_composition,
    update_composition_status,
    delete_composition,
    get_composition,
    update_composition,
)
import logging
from ..utils import replace_nan_with_none
import json
from ..constants import STATUS_REJECTED, STATUS_PENDING, STATUS_APPROVED

composition_bp = Blueprint("composition", __name__)

composition_crud_logger = logging.getLogger("composition_crud")


@composition_bp.route("/similar-items/compare-price", methods=["POST"])
def compare_price_similar_items_compositions_route():
    """
    API route to compare prices of similar items against a specified composition.

    This route accepts a JSON payload containing a similar composition ID,
    a composition object, and a similar item name. It compares the price
    of the specified composition against the price cap for the similar item.

    Request JSON Payload:
    - similar_composition_id: str, required, the ID of the similar composition to compare against.
    - composition: dict, required, the composition object containing relevant pricing details.
    - similar_item: str, required, the name of the similar item to compare.

    Returns:
    - 200: JSON response containing the composition object with the price comparison result.
    - 400: If the required fields are missing in the request payload.
    - 500: If an error occurs during processing, including reading the composition or performing the price comparison.
    """

    try:
        similar_composition_id = request.json.get("similar_composition_id")
        composition = request.json.get("composition")
        similar_item = request.json.get("similar_item")

        if not composition or not similar_item or not similar_composition_id:
            return (
                jsonify(
                    {
                        "error": "composition object and similar composition name and its id is required"
                    }
                ),
                400,
            )
        try:
            composition["df_compositions"] = similar_item
            composition["df_unit_rate_to_hll_excl_of_tax"] = float(
                composition["df_unit_rate_to_hll_excl_of_tax"]
            )
            composition["price_comparison"] = match_price_cap_composition(
                similar_composition_id, composition
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
    except Exception as e:
        logging.getLogger(__name__).error(f"Error : {e}")
        error_data = {"error": str(e)}
        json_error_data = json.dumps(error_data)
        return Response(json_error_data, mimetype="application/json")


@composition_bp.route("/get-all-compositions/")
def get_all_compositions_route():
    """
    API route to retrieve a paginated list of all compositions.

    This route accepts optional query parameters for pagination and searching.
    
    Query Parameters:
    - page: int, optional, the page number for pagination (default is 1).
    - search_keyword: str, optional, a keyword to filter compositions by name (default is an empty string).

    Returns:
    - 200: JSON response containing a paginated list of compositions, including both approved and pending statuses.
    - 500: If an error occurs while processing the request or retrieving data.
    """

    # Retrieve query parameters from the request
    page = request.args.get("page", default=1, type=int)
    search_keyword = request.args.get("search_keyword", default="", type=str)

    limit = 10  # Define the number of records per page
    offset = (page - 1) * limit  # Calculate the offset based on the current page

    compositions = get_all_compositions(search_keyword, limit=limit, offset=offset)

    if compositions is not None:
        try:
            response = {
                "compositions": {
                    "approved": compositions.get(STATUS_APPROVED, {"compositions": [], "count": 0}),
                    "pending": compositions.get(STATUS_PENDING, {"compositions": [], "count": 0}),
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


@composition_bp.route("/add-new-composition", methods=["POST"])
def add_new_composition_as_approver_route():
    """
    API route to add a new composition as an approver.

    This route allows an approver to submit a new composition, including its name, content code, 
    and dosage form.

    Request Body:
    - content_code: str, optional, the code associated with the composition (default is None).
    - composition_name: str, required, the name of the new composition.
    - dosage_form: str, optional, the form in which the composition is available (default is None).

    Returns:
    - 200: JSON response with a success message when the composition is added successfully.
    - 400: JSON response with an error message if the composition name is missing.
    - 500: JSON response with an error message if there was an error adding the composition.
    """

    try:
        content_code = request.form.get("content_code", None)
        composition_name = request.form.get("composition_name")
        dosage_form = request.form.get("dosage_form", None)
        status = STATUS_APPROVED

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
def get_composition_by_id(composition_id):
    """
    API route to fetch a composition by its ID.

    This route retrieves the details of a specific composition based on the provided composition ID.

    Parameters:
    - composition_id: int, required, the ID of the composition to be fetched.

    Returns:
    - 200: JSON response containing the composition details if found.
    - 404: JSON response with an error message if the composition is not found.
    """

    composition = get_composition(composition_id)
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
    """
    API route to retrieve a composition by its ID.

    This route fetches the details of a specific composition based on the provided composition ID.

    Parameters:
    - composition_id: int, required, the unique identifier of the composition to retrieve.

    Returns:
    - 200: JSON response containing the composition details if found.
    - 404: JSON response with an error message if the composition is not found.
    """

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
    """
    API route to delete a composition by its ID.

    This route allows the user to delete a specific composition from the database using its unique identifier.

    Parameters:
    - composition_id: int, required, the unique identifier of the composition to delete.

    Returns:
    - 200: JSON response with a success message if the composition is deleted successfully.
    - 404: JSON response with an error message if no composition is found with the provided ID.
    - 500: JSON response with an error message in case of an internal server error.
    """

    try:
        deleted_composition = delete_composition(composition_id)
        if deleted_composition:
            return jsonify({"message": "Composition deleted successfully"})
        else:
            return jsonify({"error" : "No composition found with the provided id"})
    except Exception as e:
        composition_crud_logger.error(f"Error while deleting composition: {e}")
        return jsonify({"error": "Error deleting composition"}), 500


# Request a composition (status 0)
@composition_bp.route("/request-composition", methods=["POST"])
def request_composition():
    """
    API route to request a new composition.

    This route allows users to submit a request for a new composition by providing the necessary details.
    The new composition would have a status of 0

    Parameters:
    - content_code: str, optional, the content code associated with the composition.
    - composition_name: str, required, the name of the composition being requested.
    - dosage_form: str, optional, the dosage form of the composition.

    Returns:
    - 200: JSON response with a success message if the composition is requested successfully.
    - 400: JSON response with an error message if the composition name is not provided.
    - 500: JSON response with an error message in case of an internal server error.
    """

    try:
        content_code = request.form.get("content_code", None)
        composition_name = request.form.get("composition_name")
        dosage_form = request.form.get("dosage_form", None)
        if not composition_name:
            return jsonify(
                {"error": "Composition name is required"}
            )

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


# Approve a composition (status 1)
@composition_bp.route("/approve-composition", methods=["PUT"]) 
def approve_composition():
    """
    API route to approve a composition.

    This route allows an approver to change the status of a composition to approved (status 1).

    Parameters:
    - composition_id: int, required, the ID of the composition to be approved.

    Returns:
    - 200: JSON response with a success message if the composition is approved successfully.
    - 400: JSON response with an error message if the composition ID is not provided.
    - 500: JSON response with an error message if there is an issue approving the composition or if no composition is found.
    """

    try:
        composition_id = request.json.get("composition_id")

        if not composition_id:
            return jsonify({"error": "Composition ID is required"}), 400

        try:
            updated_composition = update_composition_status(composition_id=composition_id, status=STATUS_APPROVED)

            if updated_composition:
                return jsonify({"message": "Composition approved", "status": 1})
            else:
                return jsonify({"error": "Error approving composition, no composition found"}), 500
        except Exception as e:
            composition_crud_logger.error(f"Error approving composition: {e}")

    except Exception as e:
        composition_crud_logger.error(f"Error approving composition: {e}")
        return jsonify({"error": str(e)}), 500
