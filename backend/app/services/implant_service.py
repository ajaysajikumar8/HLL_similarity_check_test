import pandas as pd
from fuzzywuzzy import fuzz
import re
import logging
from sqlalchemy import func, text
from ..models import Implants, PriceCapImplants
from ..db import db
from ..constants import STATUS_APPROVED, STATUS_PENDING, STATUS_REJECTED

server_logger = logging.getLogger(__name__)
composition_match_logger = logging.getLogger("composition_match")
unmatched_compositions_logger = logging.getLogger("unmatched_compositions")
rough_compositions_logger = logging.getLogger("rough_compositions")
parse_composition_logger = logging.getLogger("parse_composition")
price_cap_logger = logging.getLogger("price_cap")
composition_crud_logger = logging.getLogger("composition_crud")


def calculate_similarity(product_implant, db_product_description):
    """
    Calculate the similarity between two implants.

    Args:
        product_implant (str): The user entered implant from the dataframe.
        db_product_description (str): The product description (or implant name) from the database.

    Returns:
        int: Similarity score.
    """
    return fuzz.token_sort_ratio(product_implant, db_product_description)


def find_best_match(similar_items, product_implant):
    """
    Find the best match from a list of similar items.

    Args:
        similar_items (List): List of similar implants from the database.
        product_implant (str): The product description (implant name) from the dataframe. 

    Returns:
        Tuple: Best match and maximum similarity score.
    """
    best_match = None
    max_similarity = 0

    for res in similar_items:
        similarity = calculate_similarity(product_implant, res.product_description)
        if similarity > max_similarity:
            max_similarity = similarity
            best_match = res

    return best_match, max_similarity


def fetch_similar_implants(product_implant):
    """
    Fetch similar implants from the database.

    Args:
        product_implant (str): The product description to be compared against the Database.

    Returns:
        List: A list of similar implant products from the database.
    """
    try:
        query = (
            db.session.query(Implants)
            .filter(Implants.status == STATUS_APPROVED)
            .order_by(func.levenshtein(Implants.product_description, product_implant))
            .limit(20)
        )
        return query.all()
    except Exception as e:
        server_logger.error(f"Error fetching similar implants: {e}")
        return []


def match_price_cap_implant(implant_id, implant):
    """
    Match the implant with the price cap data and calculate the price difference.

    Args:
        implant_id (int): The ID of the implant to match.
        implant (dict): The implant details from the input, including dosage and price.

    Returns:
        dict: Price comparison result, including price difference and status.
    """
    try:
        price_cap_query = db.session.query(PriceCapImplants).filter(
            PriceCapImplants.implant_id == implant_id
        )
        price_cap_results = price_cap_query.all()

        if price_cap_results:
            best_match = None
            for price_cap_result in price_cap_results:
                df_variant = implant["df_variant"].lower().strip()

                if df_variant == price_cap_result.variant.lower().strip():
                    best_match = price_cap_result
                    break  # Break on the first successful match

            if best_match:
                original_price = float(best_match.price_cap)
                price_diff = float(
                    original_price - float(implant["df_unit_rate_to_hll_excl_of_tax"])
                )
                status = "Below" if price_diff > 0 else "Above"

                return {"price_diff": price_diff, "status": status}
            else:
                return {
                    "price": original_price,
                    "price_diff": None,
                    "status": "No Match on Dosage or Packing Unit",
                }
        else:
            return {"price": None, "price_diff": None, "status": "No Price Found"}
    except Exception as e:
        price_cap_logger.error(f"Error while matching the price: {e}")
        return {"price": None, "price_diff": None, "status": "Error while fetching price"}


def match_single_implant(row):
    """
    Match a single implant from the dataframe with the database.

    Args:
        row (pd.Series): A row from the dataframe containing implant details.

    Returns:
        Tuple: A dictionary of matched implant data and a dictionary of unmatched compositions with similar items and their similarity scores.
    """
    implant = {
        "df_sl_no": row["sl_no"],
        "df_item_code": row["item_code"],
        "df_product_description_with_specification": row[
            "product_description_with_specification"
        ],
        "df_name_of_manufacturer": row["name_of_manufacturer"],
        "df_GST": row["gst"],
        "df_variant": row["variants"],
        "df_MRP_incl_tax": row["mrp_incl_of_tax"],
        "df_unit_rate_to_hll_excl_of_tax": row["unit_rate_to_hll_excl_of_tax"],
        "df_unit_rate_to_hll_incl_of_tax": row["unit_rate_to_hll_incl_of_tax"],
        "df_hsn_code": row["hsn_code"],
        "df_margin_percent_incl_of_tax": row["margin"],
    }

    product_implant = implant["df_product_description_with_specification"].lower()
    similar_items = fetch_similar_implants(product_implant)
    best_match, max_similarity = find_best_match(similar_items, product_implant)

    if best_match and max_similarity > 98:
        implant["df_product_description_with_specification"] = (
            best_match.product_description
        )
        implant_id = best_match.id
        implant["price_comparison"] = match_price_cap_implant(implant_id, implant)
        return implant, None
    else:
        similar_items_score = sorted(
            [
                {
                    "db_implant_id": res.id,
                    "db_implant": res.product_description,
                    "similarity_score": calculate_similarity(
                        product_implant, res.product_description
                    ),
                }
                for res in similar_items
            ],
            key=lambda x: x["similarity_score"],
            reverse=True,
        )
        return None, {
            "user_implant": implant,
            "similar_items": similar_items_score,
        }


def match_implants(df):
    """
    Checks the implants in the dataframe and checks if they match with the DB.

    Args:
        df (pd.DataFrame): Data from the Excel sheet.

    Returns:
        dict: API response containing matched and unmatched implants.
    """

    matched_implants = []
    unmatched_implants = []

    for _, row in df.iterrows():
        matched, unmatched = match_single_implant(row)
        if matched:
            matched_implants.append(matched)
        else:
            unmatched_implants.append(unmatched)

    return matched_implants, unmatched_implants


def get_all_implants(search_keyword="", limit=10, offset=0):
    """
    Executes a raw SQL query to get all implants with their status,
    aggregated and grouped by status, including search functionality.

    Args:
        search_keyword (str): Keyword to search in product_description and item_code.
        limit (int): The number of records to return per page.
        offset (int): The number of records to skip before starting to return results.

    Returns:
        dict: A dictionary containing the implants grouped by status.
    """
    try:
        query = text(
            """
            WITH filtered_implants AS (
                SELECT 
                    id,
                    item_code,
                    product_description,
                    status,
                    ROW_NUMBER() OVER (PARTITION BY status ORDER BY id) AS row_num
                FROM 
                    implants
                WHERE
                    product_description ILIKE :search_keyword OR item_code ILIKE :search_keyword
            ),
            paginated_implants AS (
                SELECT 
                    status,
                    json_agg(
                        json_build_object(
                            'id', id,
                            'product_description', product_description,
                            'item_code', item_code
                        )
                    ) AS implants_data
                FROM 
                    filtered_implants
                WHERE 
                    row_num > :offset AND row_num <= :limit + :offset
                GROUP BY 
                    status
            ),
            total_counts AS (
                SELECT 
                    status,
                    COUNT(*) AS count
                FROM 
                    filtered_implants
                GROUP BY 
                    status
            )
            SELECT 
                p.status,
                json_build_object(
                    'implants', COALESCE(p.implants_data, '[]'::json),
                    'count', COALESCE(t.count, 0)
                ) AS result
            FROM 
                paginated_implants p
            LEFT JOIN 
                total_counts t
            ON 
                p.status = t.status
            ORDER BY 
                p.status;
            """
        ).params(search_keyword=f"%{search_keyword}%", limit=limit, offset=offset)

        # Execute the query and get the results
        result = db.session.execute(query).all()
    
        # Construct the dictionary based on the fetched results
        implants_by_status = {row[0]: row[1] for row in result}

        return implants_by_status

    except Exception as e:
        logging.getLogger(__name__).error(
            f"Error executing SQL query for implants: {e}"
        )
        return None


def add_implant(product_description, item_code=None, status=STATUS_PENDING):
    """
    Adds a new implant to the database.

    Args:
        product_description (str): Description of the implant.
        item_code (str, optional): Unique item code for the implant. Defaults to None.
        status (int, optional): Status of the implant. Defaults to STATUS_PENDING.

    Returns:
        Implants: The newly created implant object, or None if an error occurs.
    """
    try:
        new_implant = Implants(
            item_code=item_code,
            product_description=product_description,
            status=status,
        )
        db.session.add(new_implant)
        db.session.commit()
        return new_implant
    except Exception as e:
        db.session.rollback()
        composition_crud_logger.error(f"Error adding new Implant: {e}")
        return None
    

def get_implant(implant_id):
    """
    Fetches an implant by its ID.

    Args:
        implant_id (int): The ID of the implant to retrieve.

    Returns:
        Implants: The implant object if found, or None if an error occurs.
    """
    try:
        return Implants.query.get(implant_id)
    except Exception as e:
        logging.getLogger(__name__).error(f"Error fetching Implant by ID: {e}")
        return None

    

def update_implant_fields(implant_id: int, **fields: dict) -> Implants | None:
    """
    Updates specified fields for a given implant.

    Args:
        implant_id (int): ID of the implant to update.
        fields (dict): Key-value pairs of fields to update.

    Returns:
        Implants: The updated implant object, or None if not found or on error.
    """
    try:
        implant = Implants.query.get(implant_id)
        if not implant:
            return None

        # Update only provided fields
        for field, value in fields.items():
            if value is not None:
                setattr(implant, field, value)

        db.session.commit()
        return implant
    except Exception as e:
        db.session.rollback()
        composition_crud_logger.error(f"Error updating implant fields: {e}")
        return None



def update_implant(implant_id: int, item_code: str = None, product_description: str = None) -> Implants | None:
    """
    Updates the item_code and product_description for a given implant.

    Args:
        implant_id (int): ID of the implant to update.
        item_code (str, optional): New item code for the implant.
        product_description (str, optional): New product description for the implant.

    Returns:
        Implants: The updated implant object, or None if not found or on error.
    """
    return update_implant_fields(
        implant_id,
        item_code=item_code,
        product_description=product_description,
    )


def update_implant_status(implant_id: int, status: int) -> Implants | None:
    """
    Updates the status field for a given implant.

    Args:
        implant_id (int): ID of the implant to update.
        status (int): New status value for the implant.

    Returns:
        Implants: The updated implant object, or None if not found or on error.
    """
    return update_implant_fields(implant_id, status=status)



def delete_implant(implant_id: int) -> Implants | None:
    """
    Mark an implant as deleted by updating its status to STATUS_REJECTED.

    Args:
        implant_id (int): The ID of the implant to delete.

    Returns:
        Implants: The updated implant object, or None if not found or on error.
    """
    try:
        return update_implant_fields(implant_id, status=STATUS_REJECTED)
    except Exception as e:
        composition_crud_logger.error(f"Error marking implant as deleted: {e}")
        return None

