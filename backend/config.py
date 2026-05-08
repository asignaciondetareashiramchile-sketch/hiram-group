import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "hiram-group-dev-key-2024")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "Hiram Group <noreply@hiramgroup.cl>")
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() == "true"

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "HiramGroup2024!")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "administracion@poffice.cl")

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
PORT = int(os.getenv("PORT", "8000"))

# Chile holidays (2024-2026)
CHILE_HOLIDAYS = [
    "2025-01-01", "2025-04-18", "2025-04-19", "2025-05-01",
    "2025-05-21", "2025-06-20", "2025-07-16", "2025-08-15",
    "2025-09-18", "2025-09-19", "2025-10-12", "2025-10-31",
    "2025-11-01", "2025-12-08", "2025-12-25",
    "2026-01-01", "2026-04-03", "2026-04-04", "2026-05-01",
    "2026-05-21", "2026-06-19", "2026-07-16", "2026-08-15",
    "2026-09-18", "2026-09-19", "2026-10-12", "2026-10-31",
    "2026-11-01", "2026-12-08", "2026-12-25",
]
