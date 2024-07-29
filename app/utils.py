import os
import logging

def setup_logging(log_file_name, logger_name):
    logs_dir = 'logs'
    os.makedirs(logs_dir, exist_ok=True)
    log_file_path = os.path.join(logs_dir, log_file_name)
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    file_handler = logging.FileHandler(log_file_path)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)