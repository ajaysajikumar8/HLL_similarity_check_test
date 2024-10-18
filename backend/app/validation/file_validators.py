import pandas as pd
import logging


def get_required_columns(file_type: int):
    """
    
    Return a list of required columns based on the file type.

    Important: Change the header names as you update the sample price bid file. 
    
    """
    if file_type == 1:
        return [
            "sl_no",
            "brand_name",
            "composition",
            "name_of_manufacturer",
            "u_o_m",
            "dosage_form",
            "packing_unit",
            "gst",
            "mrp_incl_of_tax",
            "unit_rate_to_hll_excl_of_tax",
            "unit_rate_to_hll_incl_of_tax",
            "hsn_code",
            "margin",
        ]  # for Normal Price Bid
    elif file_type == 2:
        return [
            "sl_no",
            "item_code",
            "product_description_with_specification",
            "name_of_manufacturer",
            "gst",
            "variants",
            "mrp_incl_of_tax",
            "unit_rate_to_hll_excl_of_tax",
            "unit_rate_to_hll_incl_of_tax",
            "hsn_code",
            "margin",
        ]  # for Implant Price Bid
    else:
        return []  # Default case if file_type is unknown


def validate_headers(df, required_columns):
    """Check if the required headers are present in the DataFrame."""
    return all(col in df.columns for col in required_columns)


def validate_rows(df, required_columns):
    """Validate the contents of each row in the DataFrame."""
    row_errors = []

    for index, row in df.iterrows():
        # Example validation based on the required columns
        for col in required_columns:
            if pd.isnull(row[col]):
                row_errors.append(f"Row {index + 1} must have a value in '{col}'.")
                logging.getLogger(__name__).error(
                    f"Row {index + 1} missing value in '{col}'."
                )

        # Additional row validation checks can be added here

    return row_errors


def validate_file(file, file_type: int):
    errors = []

    try:
        df = pd.read_excel(file, engine="openpyxl")
    except Exception as e:
        errors.append("Uploaded file must be a valid Excel file.")
        logging.getLogger(__name__).error(f"File Format Issue: {e}")
        return None, errors
    

    required_columns = get_required_columns(file_type)
    if not validate_headers(df, required_columns):
        errors.append(
            f"Uploaded file must contain the required headers: {', '.join(required_columns)}."
        )
        logging.getLogger(__name__).error(
            "Missing required columns in the headers",
        )
        return None, errors
    
    return df, errors
