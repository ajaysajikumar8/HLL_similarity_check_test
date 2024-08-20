import pandas as pd
from fuzzywuzzy import fuzz
import re
import logging
from sqlalchemy import func, text
from ..models import Compositions, PriceCap
from ..db import db

server_logger = logging.getLogger(__name__)
composition_match_logger = logging.getLogger("composition_match")
unmatched_compositions_logger = logging.getLogger("unmatched_compositions")
rough_compositions_logger = logging.getLogger("rough_compositions")
parse_composition_logger = logging.getLogger("parse_composition")
price_cap_logger = logging.getLogger("price_cap")


def get_all_compositions():
    """
    Returns:
        List: All the compositions from the DB.
    """
    try:
        compositions = Compositions.query.all()
        return compositions
    except Exception as e:
        logging.getLogger(__name__).error(f"Error retrieving all compositions: {e}")
        return None


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
        sorted_molecules = sorted(
            [molecule.strip().lower() for molecule in re.split(r"[+|]", composition)]
        )
        modified_composition = " + ".join(sorted_molecules)
        modified_data.append(modified_composition)
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


def match_compositions(df):
    """
    Checks the compositions in the dataframe and checks if they match with the DB.

    Args:
        df (dataframe): Data from the excel sheet.

    Returns:
        dict: API response containing matched and unmatched compositions.
    """
    try:
        df["Composition"] = preprocess_data(df["Composition"])
    except Exception as e:
        server_logger.error(
            f"Some error within the file, Issues with the file format, not able to identify the column header: {e}"
        )

    preprocess_compositions_in_db("Compositions")
    preprocess_compositions_in_db("Price_Cap")

    matched_compositions = []
    unmatched_compositions = []

    for index, row in df.iterrows():
        composition = {
            "df_sl_no": row["Sl No"],
            "df_brand_name": row["Brand Name"],
            "df_compositions": row["Composition"],
            "df_name_of_manufacturer": row["Name of manufacturer"],
            "df_UoM": row["UoM"],
            "df_dosage_form": row["Dosage  Form"],
            "df_packing_unit": row["Packing Unit"],
            "df_GST": row["GST %  "],
            "df_MRP_incl_tax": row["MRP(incl of tax)"],
            "df_unit_rate_to_hll_excl_of_tax": row["Unit Rate to HLL (excl of tax)"],
            "df_unit_rate_to_hll_incl_of_tax": row[
                "Unit Rate incl of tax  to HLL                                                     (Rate excl of tax*GST%)+Rate excl of tax"
            ],
            "df_hsn_code": row["HSN Code"],
            "df_margin_percent_incl_of_tax": row[
                "Margin %                             (MRP-Unit Rate incl of tax)/MRP*100"
            ],
        }

        striped_composition = composition["df_compositions"].replace(" ", "")
        try:
            query = (
                db.session.query(Compositions)
                .order_by(
                    func.levenshtein(
                        Compositions.compositions_striped, striped_composition
                    )
                )
                .limit(20)
            )
            result = query.all()

            best_match = None
            max_similarity = 0
            similar_items_score = []

            for res in result:
                db_composition = res.compositions
                db_composition_striped = res.compositions_striped
                similarity = fuzz.token_sort_ratio(
                    striped_composition, db_composition_striped
                )
                # rough_compositions_logger.info(
                #     f"User-Inputted: {df_compositions}; DB Composition: {db_composition}; with similarity score: {similarity}"
                # )
                # rough_compositions_logger.info(
                #     f"Striped User-Input: {striped_composition}; DB Stripped Composition: {db_composition_striped}; with similarity score: {similarity} \n"
                # )

                if similarity > max_similarity and is_match(
                    striped_composition, db_composition_striped
                ):
                    max_similarity = similarity
                    best_match = res

                similar_items_score.append(
                    {"db_composition": db_composition, "similarity_score": similarity}
                )

            similar_items_score = sorted(
                similar_items_score, key=lambda x: x["similarity_score"], reverse=True
            )

            if best_match and max_similarity > 98:
                composition["df_compositions"] = best_match.compositions

                # Implement the price cap
                try:
                    price_cap_query = (
                        db.session.query(PriceCap)
                        .filter(
                            PriceCap.compositions_striped
                            == best_match.compositions_striped
                        )
                        .limit(1)
                    )
                    price_cap_result = price_cap_query.first()

                    if price_cap_result:
                        df_dosage_form = composition["df_dosage_form"].lower().strip()
                        df_packing_unit = composition["df_packing_unit"].lower().strip()

                        if (
                            df_dosage_form
                            == price_cap_result.dosage_form.lower().strip()
                            and df_packing_unit
                            == price_cap_result.packing_unit.lower().strip()
                        ):
                            price_diff = (
                                price_cap_result.price_cap
                                - composition["df_unit_rate_to_hll_excl_of_tax"]
                            )

                            price_diff = float(price_diff)
                            status = "Below" if price_diff > 0 else "Above"

                            composition["price_comparison"] = {
                                "price_diff": price_diff,
                                "status": status,
                            }
                        else:
                            composition["price_comparison"] = {
                                "price_diff": None,
                                "status": "No Match on Dosage or Packing Unit",
                            }
                    else:
                        composition["price_comparison"] = {
                            "price_diff": None,
                            "status": "No Price Found",
                        }

                except Exception as e:
                    price_cap_logger.error(f"Error while matching the price: {e}")
                    composition["price_comparison"] = {
                        "price_diff": None,
                        "status": "Error while fetching price",
                    }

                matched_compositions.append(composition)
                # composition_match_logger.info(
                #     f"User-entered composition: {df_compositions}, Matched composition: {best_match}, Match score: {max_similarity}"
                # )
            else:
                unmatched_compositions.append(
                    {
                        "user_composition": composition,
                        "similar_items": similar_items_score,
                    }
                )
            # unmatched_compositions_logger.info(
            #         f"Unmatched composition: {df_compositions}, Similarity percentage: {similarity}"
            #     )
        except Exception as e:
            server_logger.error(f"Error matching compositions: {e}")
            continue

    return matched_compositions, unmatched_compositions


def add_composition(content_code, composition_name, dosage_form):
    try:
        new_composition = Compositions(
            content_code=content_code,
            compositions=composition_name,
            compositions_striped="".join(composition_name.split()).lower(),
            dosage_form=dosage_form,
        )
        db.session.add(new_composition)
        db.session.commit()
        return new_composition
    except Exception as e:
        db.session.rollback()
        logging.getLogger(__name__).error(f"Error adding new composition: {e}")
        return None
