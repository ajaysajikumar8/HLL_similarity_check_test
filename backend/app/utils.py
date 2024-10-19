import os
import logging
import numpy as np
from logging.handlers import TimedRotatingFileHandler


def setup_logging(log_file_name, logger_name, rotate_logs=True):
    """
    Setup Logging for different modules of the application. Each Log file serving its own purpose.
    Rotates logs weekly unless disabled (e.g., for critical logs).
    
    Args:
        log_file_name (str): The log file name.
        logger_name (str): The name of the logger.
        rotate_logs (bool): Whether to enable log rotation. Defaults to True for all logs except 'critical'.
    """
    logs_dir = "logs"
    archive_dir = os.path.join(logs_dir, "archive")
    os.makedirs(logs_dir, exist_ok=True)

    log_file_path = os.path.join(logs_dir, log_file_name)
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)

    ### FIX THIS CODE: LOGGER ISSUE

    # if logger.hasHandlers():
    #     for handler in logger.handlers:
    #         handler.close()  # Ensure files are closed
    #         logger.removeHandler(handler)
    
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d %(message)s")

    # if rotate_logs:
    #     os.makedirs(archive_dir, exist_ok=True)
        
    #     # Log rotation setup: Rotate weekly (on Monday), keeping up to 3 backups
    #     handler = TimedRotatingFileHandler(log_file_path, when="W0", interval=1, backupCount=3)
    #     handler.suffix = "%Y-%m-%d"  # Logs will be named with the year and week number
    # else:
    #     handler = logging.FileHandler(log_file_path)

    handler = logging.FileHandler(log_file_path)
    
    handler.setFormatter(formatter)
    logger.addHandler(handler)


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
