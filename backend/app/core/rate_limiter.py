from slowapi import Limiter
from slowapi.util import get_remote_address

# --- Limiter instance ---
# get_remote_address: uses the client's IP as the rate-limit key.
# This single instance is shared across all routes.
# Import it in main.py to attach to the FastAPI app.
limiter = Limiter(key_func=get_remote_address)


# --- Reusable limit strings ---
# Import these in route files instead of writing raw strings everywhere.
# Makes it easy to change limits in one place.

LIMIT_AUTH = "10/minute"        # login + register — brute-force protection
LIMIT_STANDARD = "60/minute"    # general page and data routes
LIMIT_PREDICTIONS = "30/minute" # prediction routes — slightly stricter
LIMIT_ADMIN = "20/minute"       # admin actions