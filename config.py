import os
from pathlib import Path

# Load .env file if available
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).resolve().parent / '.env'
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
except ImportError:
    pass

BASE_DIR = Path(__file__).resolve().parent

class Config:
    """Base application configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-medical-insurance-app-2026')
    DATABASE_PATH = os.environ.get('DATABASE_PATH', str(BASE_DIR / 'insurance_app.db'))
    MODEL_PATH = os.environ.get('MODEL_PATH', str(BASE_DIR / 'model.pkl'))
    
    # Session security settings
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = False  # Set to True if serving strictly over HTTPS
    PERMANENT_SESSION_LIFETIME = 86400  # 24 hours in seconds
    
    # App display settings
    CURRENCY_SYMBOL = "₹"
    CURRENCY_CODE = "INR"
