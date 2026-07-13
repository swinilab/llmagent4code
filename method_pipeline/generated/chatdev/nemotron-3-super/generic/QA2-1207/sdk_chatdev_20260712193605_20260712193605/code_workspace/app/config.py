import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")
DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")