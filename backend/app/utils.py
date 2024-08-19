import os
import logging
import numpy as np


def setup_logging(log_file_name, logger_name):
    """
    Setup Logging for different modules of the application. Each Log file serving its own purpose
    """
    logs_dir = "logs"
    os.makedirs(logs_dir, exist_ok=True)
    log_file_path = os.path.join(logs_dir, log_file_name)
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    file_handler = logging.FileHandler(log_file_path)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)


def replace_nan_with_none(data):
    """
    Replace 'nan' to just ''. Done to reduce the errors while decoding the json.
    """
    if isinstance(data, dict):
        return {k: replace_nan_with_none(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [replace_nan_with_none(v) for v in data]
    elif isinstance(data, float) and np.isnan(data):
        return ""
    else:
        return data
