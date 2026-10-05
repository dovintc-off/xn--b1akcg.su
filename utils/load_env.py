# load_env.py created by DOV1NTC powered by XWARED TEAM(C)
import os
from dotenv import load_dotenv, dotenv_values
from utils.log import log

_last_mtime = 0
_config_cache = {}
_env_path = ""

def load(path: str):
    global _env_path, _last_mtime, _config_cache
    full_path = os.path.join(path, ".env")
    if not os.path.exists(full_path): log("path is not exists", "error"); return
    _env_path = full_path
    load_dotenv(full_path)
    try:
        _last_mtime = os.path.getmtime(full_path)
        _config_cache = dotenv_values(full_path)
        log(".env loaded successfully", "info")
    except Exception as e:
        log(f"Error initializing env cache: {e}", "error")

def _refresh_config_if_needed():
    global _last_mtime, _config_cache
    if not _env_path or not os.path.exists(_env_path): return
    try:
        current_mtime = os.path.getmtime(_env_path)
        if current_mtime != _last_mtime:
            _config_cache = dotenv_values(_env_path)
            _last_mtime = current_mtime
            load_dotenv(_env_path, override=True) 
    except Exception as e:
        log(f"Error refreshing .env: {e}", "error")

def get_secret_key():
    _refresh_config_if_needed()
    value = os.getenv('FLASK_SECRET_KEY')
    if not value: log("FLASK_SECRET_KEY not found", "error"); return
    return value

def get_smtp_data():
    _refresh_config_if_needed()
    SMTP_MAIL_CODE = os.getenv('SMTP_PASSWORD')
    MAIL_SENDER = os.getenv('SMTP_MAIL')
    if not MAIL_SENDER: log("SMTP_MAIL not found", "error"); return
    if not SMTP_MAIL_CODE: log("SMTP_MAIL_CODE not found", "error"); return
    return (SMTP_MAIL_CODE, MAIL_SENDER)

def get_password():
    _refresh_config_if_needed()
    value = os.getenv('ADMIN_PASSWORD')
    if not value: log("ADMIN_PASSWORD not found", "error"); return
    return value

def get_path_to_db():
    _refresh_config_if_needed()
    value = os.getenv('DB_PATH')
    if not value: log("DB_PATH not found", "error"); return
    return value
    
def get_path_to_quizes():
    _refresh_config_if_needed()
    value = os.getenv('QUIZES_PATH')
    if not value: log("QUIZES_PATH not found", "error"); return
    return value

def is_technical_break():
    _refresh_config_if_needed()
    value = os.getenv('TECHNICAL_BREAK', 'False')
    return value.lower() == 'true'