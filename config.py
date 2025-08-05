import os
from dotenv import load_dotenv
from urllib.parse import quote_plus

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Handle special characters in password by URL encoding
    db_password = os.getenv('DB_PASSWORD', '')
    if db_password:
        encoded_password = quote_plus(db_password)
        SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{os.getenv('DB_USER')}:{encoded_password}@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}"
    else:
        SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{os.getenv('DB_USER')}@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}"
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
class DevelopmentConfig(Config):
    DEBUG = True
    
class ProductionConfig(Config):
    DEBUG = False
    
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}