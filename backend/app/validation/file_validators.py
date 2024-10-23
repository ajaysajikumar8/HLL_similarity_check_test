import pandas as pd
import logging
from cerberus import Validator

file_validator_logger = logging.getLogger("file_validation")

def check_for_nan(df, schema):
    """Check for NaN values in required columns and return their row numbers."""
    errors = []
    for col in schema.keys():
        if schema[col].get('required', False):
            nan_rows = df.index[df[col].isnull()].tolist()
            for row in nan_rows:
                errors.append(f"Row {row + 2}: Column '{col}' contains empty value.")
    return errors

def get_required_columns(file_type: int):
    """
    Return a schema with validation rules based on the file type.
    """
    if file_type == 1:
        return {
            "sl_no": {"nullable": False, "required": True, "empty": False},
            "brand_name": {"type": "string", "nullable": False, "required": True, "empty": False},
            "composition": {"type": "string", "nullable": False, "required": True, "empty": False},
            "name_of_manufacturer": {"type": "string", "nullable": False, "required": True, "empty": False},
            "u_o_m": {"type": "string", "nullable": False, "required": True, "empty": False},
            "dosage_form": {"type": "string", "nullable": False, "required": True, "empty": False},
            "packing_unit": {"type": "string", "nullable": False, "required": True, "empty": False},
            "gst": {"type": "integer", "min": 0, "max": 100, "nullable": False, "required": True, "empty": False},
            "mrp_incl_of_tax": {"type": "float", "min": 0, "nullable": False, "required": True, "empty": False},
            "unit_rate_to_hll_excl_of_tax": {"type": "float", "min": 0, "nullable": False, "required": True, "empty": False},
            "unit_rate_to_hll_incl_of_tax": {"type": "float", "min": 0, "nullable": False, "required": True, "empty": False},
            "hsn_code": {"type": "integer", "nullable": False, "required": True, "empty": False},
        }

    elif file_type == 2:
        return {
            "sl_no": { "nullable": False, "required": True, "empty": False},
            "item_code": {"nullable": False, "required": True, "empty": False},
            "product_description_with_specification": {"type": "string", "nullable": False, "required": True, "empty": False},
            "name_of_manufacturer": {"type": "string", "nullable": False, "required": True, "empty": False},
            "gst": {"min": 0, "max": 100, "nullable": False, "required": True, "empty": False},
            "variants": {"type": "string", "nullable": False, "required": True, "empty": False},
            "mrp_incl_of_tax": {"type": "float", "min": 0, "nullable": False, "required": True, "empty": False},
            "unit_rate_to_hll_excl_of_tax": {"type": "float", "min": 0, "nullable": False, "required": True, "empty": False},
            "unit_rate_to_hll_incl_of_tax": {"type": "float", "min": 0, "nullable": False, "required": True, "empty": False},
            "hsn_code": {"type": "integer", "nullable": False, "required": True, "empty": False},
        }
    else:
        return {}

def validate_headers(df, schema):
    """Validate if the required headers match the schema keys."""
    missing_columns = [col for col in schema if col not in df.columns]
    return missing_columns if missing_columns else None

def validate_rows(df, schema):
    """Validate each row of the DataFrame using Cerberus."""
    validator = Validator(schema)
    row_errors = []

    for index, row in df.iterrows():
        row_dict = row.to_dict()
        
        # Perform Cerberus validation
        if not validator.validate(row_dict):
            row_errors.append(f"Row {index + 2}: {validator.errors}")
            file_validator_logger.error(f"Row {index + 2}: {validator.errors}")

    return row_errors

def validate_file(file, file_type: int):
    """Validate the uploaded Excel file based on the file type."""
    errors = []

    try:
        df = pd.read_excel(file, engine="openpyxl")
    except Exception as e:
        errors.append("Uploaded file must be a valid Excel file.")
        file_validator_logger.error(f"File Format Issue: {e}")
        return None, errors

    schema = get_required_columns(file_type)

    df = df.where(pd.notnull(df), None)

    # Validate headers
    missing_columns = validate_headers(df, schema)
    if missing_columns:
        errors.append(f"Missing required headers: {', '.join(missing_columns)}.")
        file_validator_logger.error("Missing required columns in the headers")
        return None, errors

    # Pre-check for NaN values
    nan_errors = check_for_nan(df, schema)
    if nan_errors:
        errors.extend(nan_errors)
        file_validator_logger.error("NaN value issues: " + ', '.join(nan_errors))
        return None, errors

    # Validate rows
    row_errors = validate_rows(df, schema)
    if row_errors:
        errors.extend(row_errors)

    return df, errors
