import pandas as pd
from fuzzywuzzy import fuzz
import re
import logging
from sqlalchemy import func, text
from ..models import Compositions, PriceCapCompositions
from ..db import db

server_logger = logging.getLogger(__name__)
composition_match_logger = logging.getLogger("composition_match")
unmatched_compositions_logger = logging.getLogger("unmatched_compositions")
rough_compositions_logger = logging.getLogger("rough_compositions")
parse_composition_logger = logging.getLogger("parse_composition")
price_cap_logger = logging.getLogger("price_cap")
composition_crud_logger = logging.getLogger("composition_crud")


def get_all_compositions(search_keyword="", limit=10, offset=0):
    """
    Executes a raw SQL query to get all compositions with their status,
    aggregated and grouped by status, including search functionality.

    Args:
        search_keyword (str): Keyword to search in compositions and content_code.
        limit (int): The number of records to return per page.
        offset (int): The number of records to skip before starting to return results.

    Returns:
        dict: A dictionary containing the compositions grouped by status.
    """
    try:
        query = text(
            """
            WITH filtered_compositions AS (
                SELECT 
                    id,
                    status,
                    compositions,
                    compositions_striped,
                    content_code,
                    ROW_NUMBER() OVER (PARTITION BY status ORDER BY id) AS row_num
                FROM 
                    compositions
                WHERE
                    compositions ILIKE :search_keyword OR content_code ILIKE :search_keyword
            ),
            paginated_compositions AS (
                SELECT 
                    status,
                    json_agg(
                        json_build_object(
                            'id', id,
                            'compositions', compositions,
                            'compositions_striped', compositions_striped,
                            'content_code', content_code
                        )
                    ) AS compositions
                FROM 
                    filtered_compositions
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
                    filtered_compositions
                GROUP BY 
                    status
            )
            SELECT 
                p.status,
                json_build_object(
                    'compositions', COALESCE(p.compositions, '[]'::json),
                    'count', COALESCE(t.count, 0)
                ) AS result
            FROM 
                paginated_compositions p
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
        compositions_by_status = {row[0]: row[1] for row in result}

        return compositions_by_status

    except Exception as e:
        logging.getLogger(__name__).error(
            f"Error executing SQL query for compositions: {e}"
        )
        return None


def sort_and_strip_composition(composition):
    sorted_molecules = sorted(
        [molecule.strip().lower() for molecule in re.split(r"[+|]", composition)]
    )
    modified_composition = " + ".join(sorted_molecules)
    return modified_composition


def preprocess_data(data: list) -> list:
    """
    Split the composition and sort the molecule in ascending manner. The molecules are striped and converted to lower case.

    Args:
        data (list): compositions column from dataframe in excel

    Returns:
        Modified data (list): preprocessed compositions in excel
    """
    modified_data = []
    for composition in data:

        composition = sort_and_strip_composition(composition)
        modified_data.append(composition)

    return modified_data


def preprocess_compositions_in_db(table_name):
    """
    Preprocess compositions within the specified table and store the processed compositions
    in the compositions_striped column.
    :param table_name: Name of the table to be processed (e.g., 'Compositions' or 'PriceCap').
    """
    try:
        db.session.execute(
            text(
                f"UPDATE {table_name} SET compositions_striped = preprocess_composition(compositions);"
            )
        )
        db.session.commit()
        server_logger.info(
            f"Compositions in {table_name} preprocessed and stored in compositions_striped."
        )
    except Exception as e:
        db.session.rollback()
        server_logger.error(
            f"Error preprocessing compositions in the {table_name} table: {e}"
        )


def parse_composition(composition: str) -> list:
    """
    Split the composition from its name and amount.

    Args:
        composition (str) : Composition Inputed

    Returns:
        List: The parsed composition returned with name and unit separated
    """

    try:
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


def is_match(composition1: str, composition2: str) -> bool:
    """
    Compare the parsed versions of the composition with the ones stored in the DB.

    Args:
        composition1 (str):  User entered Composition.
        composition2 (str): DB Composition.

    Returns:
        True: if compostions match.
        False: if compositions doesnt match.
    """

    parsed1 = parse_composition(composition1)
    parsed2 = parse_composition(composition2)
    if parsed1 == parsed2:
        parse_composition_logger.info(f"Matched: User: {parsed1} with DB: {parsed2}")
    else:
        parse_composition_logger.error(
            f"Not a Match: User: {parsed1} with DB: {parsed2}"
        )
    return parsed1 == parsed2


def preprocess_dataframe(df):
    """
    Preprocess the composition data in the dataframe.

    Args:
        df (pd.DataFrame): Data from the Excel sheet.

    Returns:
        pd.DataFrame: Preprocessed dataframe.
    """

    try:
        df["composition"] = preprocess_data(df["composition"])

        return df
    except Exception as e:
        server_logger.error(
            f"Issues with file format, not able to identify the column header: {e}"
        )
        raise


def fetch_similar_compositions(striped_composition):
    """
    Fetch similar compositions from the database.

    Args:
        striped_composition (str): The stripped composition string from the dataframe.

    Returns:
        List: A list of similar compositions from the database.
    """
    try:
        query = (
            db.session.query(Compositions)
            .filter(Compositions.status == 1)
            .order_by(
                func.levenshtein(Compositions.compositions_striped, striped_composition)
            )
            .limit(20)
        )
        return query.all()
    except Exception as e:
        server_logger.error(f"Error fetching similar compositions: {e}")
        return []


def calculate_similarity(striped_composition, db_composition_striped):
    """
    Calculate the similarity between two compositions.

    Args:
        striped_composition (str): The stripped composition from the dataframe.
        db_composition_striped (str): The stripped composition from the database.

    Returns:
        int: Similarity score.
    """
    return fuzz.token_sort_ratio(striped_composition, db_composition_striped)


def find_best_match(similar_items, striped_composition):
    """
    Find the best match from a list of similar items.

    Args:
        similar_items (List): List of similar compositions from the database.
        striped_composition (str): The stripped composition string from the dataframe.

    Returns:
        Tuple: Best match and maximum similarity score.
    """
    best_match = None
    max_similarity = 0

    for res in similar_items:
        similarity = calculate_similarity(striped_composition, res.compositions_striped)
        if similarity > max_similarity and is_match(
            striped_composition, res.compositions_striped
        ):
            max_similarity = similarity
            best_match = res

    return best_match, max_similarity


def match_price_cap_composition(composition_id, composition):
    """
    Match the composition with the price cap data and calculate price difference.

    Args:
        composition_id (int): The ID of the composition to match.
        composition (dict): The composition details from the dataframe.
        striped_composition (str): The stripped composition string from the dataframe.

    Returns:
        dict: Price comparison result.
    """
    try:
        price_cap_query = db.session.query(PriceCapCompositions).filter(
            PriceCapCompositions.composition_id == composition_id
        )

        price_cap_results = price_cap_query.all()

        if price_cap_results:
            best_match = None
            for price_cap_result in price_cap_results:
                df_dosage_form = composition["df_dosage_form"].lower().strip()
                df_packing_unit = composition["df_packing_unit"].lower().strip()

                if (
                    df_dosage_form == price_cap_result.dosage_form.lower().strip()
                    and df_packing_unit == price_cap_result.packing_unit.lower().strip()
                ):
                    best_match = price_cap_result
                    break  # Break on the first successful match

            if best_match:
                original_price = float(best_match.price_cap)
                price_diff = float(
                    original_price - float(composition["df_unit_rate_to_hll_excl_of_tax"])
                )
                status = "Below" if price_diff > 0 else "Above"

                return {
                    "price": original_price,
                    "price_diff": price_diff,
                    "status": status,
                }
            else:
                return {
                    "price": None,
                    "price_diff": None,
                    "status": "No Match on Dosage or Packing Unit",
                }
        else:
            return {"price": None, "price_diff": None, "status": "No Price Found"}
    except Exception as e:
        price_cap_logger.error(f"Error while matching the price: {e}")
        return {
            "price": None,
            "price_diff": None,
            "status": "Error while fetching price",
        }


def match_single_composition(row):
    """
    Match a single composition from the dataframe with the database.

    Args:
        row (pd.Series): A row from the dataframe.

    Returns:
        Tuple: Matched composition data and list of unmatched compositions.
    """
    composition = {
        "df_sl_no": row["sl_no"],
        "df_brand_name": row["brand_name"],
        "df_compositions": row["composition"],
        "df_name_of_manufacturer": row["name_of_manufacturer"],
        "df_UoM": row["u_o_m"],
        "df_dosage_form": row["dosage_form"],
        "df_packing_unit": row["packing_unit"],
        "df_GST": row["gst"],
        "df_MRP_incl_tax": row["mrp_incl_of_tax"],
        "df_unit_rate_to_hll_excl_of_tax": row["unit_rate_to_hll_excl_of_tax"],
        "df_unit_rate_to_hll_incl_of_tax": row["unit_rate_to_hll_incl_of_tax"],
        "df_hsn_code": row["hsn_code"],
        "df_margin_percent_incl_of_tax": row["margin"],
    }

    striped_composition = composition["df_compositions"].replace(" ", "")
    similar_items = fetch_similar_compositions(striped_composition)
    best_match, max_similarity = find_best_match(similar_items, striped_composition)

    if best_match and max_similarity > 98:
        composition["df_compositions"] = best_match.compositions
        composition_id = best_match.id
        composition["price_comparison"] = match_price_cap_composition(
            composition_id, composition
        )
        return composition, None
    else:
        similar_items_score = sorted(
            [
                {
                    "db_composition_id": res.id,
                    "db_composition": res.compositions,
                    "similarity_score": calculate_similarity(
                        striped_composition, res.compositions_striped
                    ),
                }
                for res in similar_items
            ],
            key=lambda x: x["similarity_score"],
            reverse=True,
        )
        return None, {
            "user_composition": composition,
            "similar_items": similar_items_score,
        }


def match_compositions(df):
    """
    Checks the compositions in the dataframe and checks if they match with the DB.

    Args:
        df (pd.DataFrame): Data from the Excel sheet.

    Returns:
        dict: API response containing matched and unmatched compositions.
    """
    try:
        df = preprocess_dataframe(df)
    except Exception as e:
        return {"error": str(e)}

    # ::: REMOVE LATER  when CRUD implemented for the tables
    preprocess_compositions_in_db("Compositions")

    matched_compositions = []
    unmatched_compositions = []

    for _, row in df.iterrows():
        matched, unmatched = match_single_composition(row)
        if matched:
            matched_compositions.append(matched)
        else:
            unmatched_compositions.append(unmatched)

    return matched_compositions, unmatched_compositions


def add_composition(composition_name, content_code=None, dosage_form=None, status=0):
    try:
        new_composition = Compositions(
            content_code=content_code,
            compositions=composition_name,
            dosage_form=dosage_form,
            status=status,
        )
        db.session.add(new_composition)
        db.session.commit()
        return new_composition
    except Exception as e:
        db.session.rollback()
        composition_crud_logger.error(f"Error adding new composition: {e}")
        return None


def get_composition(composition_id):
    try:
        return Compositions.query.get(composition_id)
    except Exception as e:
        logging.getLogger(__name__).error(f"Error fetching composition by ID: {e}")
        return None


def update_composition_fields(composition_id, **fields):
    """
    Update the specified fields for a given composition.
    Args:
        composition_id (int): ID of the composition to update.
        fields (dict): A dictionary of fields to update.
    Returns:
        Compositions: Updated composition object or None if not found.
    """
    try:
        composition = Compositions.query.get(composition_id)
        if not composition:
            return None

        # Dynamically update fields
        for field, value in fields.items():
            if value is not None:  # Update only if the field is provided
                setattr(composition, field, value)

        db.session.commit()
        return composition
    except Exception as e:
        db.session.rollback()
        composition_crud_logger.error(f"Error updating composition fields: {e}")
        return None


def update_composition(composition_id, content_code=None, composition_name=None, dosage_form=None):
    """
    Update content_code, composition_name, and dosage_form for a given composition.
    """
    return update_composition_fields(
        composition_id,
        content_code=content_code,
        compositions=composition_name,
        dosage_form=dosage_form
    )


def update_composition_status(composition_id, status):
    """
    Update the status field for a given composition.
    """
    return update_composition_fields(composition_id, status=status)


# Soft delete or (rejected)
def delete_composition(composition_id):
    """
    Mark an composition as deleted by updating its status to 3.
    
    Args:
        composition_id (int): The ID of the composition to delete.

    Returns:
        Compositions: Updated Composition object or None if not found.
    """
    try:
        return update_composition_fields(composition_id, status=3)
    except Exception as e:
        composition_crud_logger.error(f"Error marking composition as deleted: {e}")
        return None


def update_composition_id_in_price_cap():
    try:
        # Update PriceCap with matching composition_id from Compositions
        db.session.query(PriceCapCompositions).filter(
            PriceCapCompositions.compositions_striped
            == Compositions.compositions_striped,
            PriceCapCompositions.composition_id.is_(
                None
            ),  # Only update if composition_id is NULL
        ).update(
            {PriceCapCompositions.composition_id: Compositions.id},
            synchronize_session="fetch",
        )  # Synchronize session to reflect changes
        db.session.commit()
        server_logger.info("Successfully updated composition_id in PriceCap.")
    except Exception as e:
        db.session.rollback()
        server_logger.error(f"Error updating composition_id in PriceCap: {e}")
