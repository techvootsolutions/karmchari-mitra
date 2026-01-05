import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'techvoot-hr-secret-key-2024')
    DATABASE_PATH = os.getenv('DATABASE_PATH', 'database/hr_candidates.db')
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    
    # Company Information
    COMPANY_NAME = "Techvoot Solution"
    AGENT_NAME = "Techvootbot"
    
    # Omnidimension Settings
    OMNIDIMENSION_API_KEY = os.getenv('OMNIDIMENSION_API_KEY', 'a0dtyD6zF6mGoPICMrNO8B71yuMRORhtmajn7bd8X5I')
    OMNIDIMENSION_AGENT_ID = os.getenv('OMNIDIMENSION_AGENT_ID', '74835')
    
    # Call Settings
    CALL_TIMEOUT = 300  # seconds
    MAX_CALLS_PER_DAY = 50
    
    # Paths
    TEMPLATE_DIR = "templates"
    STATIC_DIR = "static"
    LOG_DIR = "logs"