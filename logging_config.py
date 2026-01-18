# Logging configuration module for ocpp2mqtt
# Supports console and file logging with rotation

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv

load_dotenv(verbose=True)

# Logging configuration from environment
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
LOG_FILE = os.getenv('LOG_FILE', None)
LOG_MAX_SIZE = int(os.getenv('LOG_MAX_SIZE', 10 * 1024 * 1024))  # 10MB default
LOG_BACKUP_COUNT = int(os.getenv('LOG_BACKUP_COUNT', 5))
LOG_FORMAT = os.getenv('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
LOG_DATE_FORMAT = os.getenv('LOG_DATE_FORMAT', '%Y-%m-%d %H:%M:%S')


def setup_logging(name: str = None) -> logging.Logger:
    """
    Configure and return a logger instance.
    
    Args:
        name: Logger name. If None, configures the root logger.
        
    Returns:
        Configured logger instance.
    """
    # Get the logger
    logger = logging.getLogger(name)
    
    # Only configure if not already configured
    if logger.handlers:
        return logger
    
    # Set log level
    numeric_level = getattr(logging, LOG_LEVEL, logging.INFO)
    logger.setLevel(numeric_level)
    
    # Create formatter
    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
    
    # Console handler (always enabled)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (if LOG_FILE is set)
    if LOG_FILE:
        try:
            # Create directory if it doesn't exist
            log_dir = os.path.dirname(LOG_FILE)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)
            
            # Create rotating file handler
            file_handler = RotatingFileHandler(
                LOG_FILE,
                maxBytes=LOG_MAX_SIZE,
                backupCount=LOG_BACKUP_COUNT,
                encoding='utf-8'
            )
            file_handler.setLevel(numeric_level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            
            logger.info(f"File logging enabled: {LOG_FILE}")
        except Exception as e:
            logger.error(f"Failed to setup file logging: {e}")
    
    return logger


def configure_root_logging():
    """
    Configure the root logger with both console and optional file output.
    Call this once at application startup.
    """
    # Clear any existing handlers on root logger
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    
    # Set log level
    numeric_level = getattr(logging, LOG_LEVEL, logging.INFO)
    root_logger.setLevel(numeric_level)
    
    # Create formatter
    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler (if LOG_FILE is set)
    if LOG_FILE:
        try:
            # Create directory if it doesn't exist
            log_dir = os.path.dirname(LOG_FILE)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)
            
            file_handler = RotatingFileHandler(
                LOG_FILE,
                maxBytes=LOG_MAX_SIZE,
                backupCount=LOG_BACKUP_COUNT,
                encoding='utf-8'
            )
            file_handler.setLevel(numeric_level)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
            
            root_logger.info(f"File logging enabled: {LOG_FILE}")
            root_logger.info(f"Log rotation: max {LOG_MAX_SIZE} bytes, {LOG_BACKUP_COUNT} backups")
        except Exception as e:
            root_logger.error(f"Failed to setup file logging: {e}")
    
    return root_logger
