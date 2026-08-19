import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

DATABASE_PATH = BASE_DIR / "instance" / "inventory.db"

PRE_DISTRIBUTION_TEMPLATE = BASE_DIR / "Templates" / "Pre-Distribution-Template.xlsx"

# existing excel by Post-Distribution
SP_DISTRIBUTION_FILE = BASE_DIR / "Templates" / "SP Distribution.xlsx"
SP_DISTRIBUTION_SHEET = "SP Distribution-beneficiaries"

PRE_DISTRIBUTION_OUTPUT_DIR = BASE_DIR / "Pre-Distribution Files"

# upload file rules
MAX_CONTENT_LENGTH = 16 * 1024 * 1024
ALLOWED_CSV_EXTENSIONS = {".csv"}
