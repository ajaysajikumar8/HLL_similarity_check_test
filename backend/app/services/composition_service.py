import pandas as pd
from fuzzywuzzy import fuzz
import re
import logging
from sqlalchemy import func, text
from ..models import Compositions
from ..db import db

server_logger = logging.getLogger(__name__)
composition_match_logger = logging.getLogger("composition_match")
unmatched_compositions_logger = logging.getLogger("unmatched_compositions")
rough_compositions_logger = logging.getLogger("rough_compositions")
parse_composition_logger = logging.getLogger("parse_composition")


def get_all_compositions():
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


def preprocess_compositions_in_db():
    """Within the database, execute the preprocess function to process the compositions stored in the db."""
    try:
        db.session.execute(
            text(
                "UPDATE Compositions SET compositions_striped = preprocess_composition(compositions);"
            )
        )
        db.session.commit()
        server_logger.info(
            "Compositions preprocessed and stored in compositions_striped in the database"
        )
    except Exception as e:
        db.session.rollback()
        server_logger.error(f"Error preprocessing compositions in the database: {e}")


def parse_composition(composition: str) -> list:
    """
    Identify the amounts and the units from the compositions.

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
    try:
        print(df["Composition"])
    except Exception as e:
        print(f"File not read: {e}")
    try:
        df["Composition"] = preprocess_data(df["Composition"])
    except Exception as e:
        server_logger.error(
            f"Some error within the file, Issues with the file format, not able to identify the column header: {e}"
        )

    preprocess_compositions_in_db()

    matched_compositions = []
    unmatched_compositions = []
    modified_df = pd.DataFrame(columns=df.columns)

    for index, row in df.iterrows():
        print(row["Composition"])
        composition = row["Composition"]
        striped_composition = composition.replace(" ", "")
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
                rough_compositions_logger.info(
                    f"User-Inputted: {composition}; DB Composition: {db_composition}; with similarity score: {similarity}"
                )
                rough_compositions_logger.info(
                    f"Striped User-Input: {striped_composition}; DB Stripped Composition: {db_composition_striped}; with similarity score: {similarity} \n"
                )

                if similarity > max_similarity and is_match(
                    striped_composition, db_composition_striped
                ):
                    max_similarity = similarity
                    best_match = res.compositions

                similar_items_score.append(
                    {"db_composition": db_composition, "similarity_score": similarity}
                )

            similar_items_score = sorted(
                similar_items_score, key=lambda x: x["similarity_score"], reverse=True
            )
            if best_match and max_similarity > 98:
                matched_compositions.append(best_match)
                modified_df.loc[index] = row
                modified_df.at[index, "compositions"] = best_match

                composition_match_logger.info(
                    f"User-entered composition: {composition}, Matched composition: {best_match}, Match score: {max_similarity}"
                )
            else:
                unmatched_compositions.append(
                    {
                        "user_composition": composition,
                        "similar_items": similar_items_score,
                    }
                )
                unmatched_compositions_logger.info(
                    f"Unmatched composition: {composition}, Similarity percentage: {similarity}"
                )
        except Exception as e:
            server_logger.error(f"Error matching compositions: {e}")
            continue

    return matched_compositions, unmatched_compositions, modified_df


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
