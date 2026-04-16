"""
Configuration file for Solar System Small Bodies Explorer
"""

# Server Configuration
HOST = '0.0.0.0'
PORT = 5050
DEBUG = True

# Cache Configuration
CACHE_DIR = 'cache'
CACHE_EXPIRY_HOURS = 24

# API Configuration
JPL_SBDB_BASE_URL = "https://ssd-api.jpl.nasa.gov/sbdb_query.api"
JPL_SBDB_DETAIL_URL = "https://ssd-api.jpl.nasa.gov/sbdb.api"
JPL_CAD_URL = "https://ssd-api.jpl.nasa.gov/cad.api"

SSODNET_BASE_URL = "https://ssp.imcce.fr/webservices"
SSODNET_CARD_URL = f"{SSODNET_BASE_URL}/ssodnet/api/ssocard.php"
SSODNET_DATACLOUD_URL = f"{SSODNET_BASE_URL}/ssodnet/api/datacloud.php"

# API Timeouts (seconds)
API_TIMEOUT = 30

# Data Analysis Configuration
CRITICAL_PROPERTIES = [
    'diameter',    # Object size (km)
    'albedo',      # Surface reflectivity
    'rot_per',     # Rotation period (hours)
    'H',           # Absolute magnitude
    'spec_B',      # Bus spectral classification
    'spec_T',      # Tholen spectral classification
    'GM',          # Gravitational parameter (mass)
    'BV',          # B-V color index
    'UB',          # U-B color index
]

# Priority Calculation Weights
PRIORITY_WEIGHTS = {
    'neo': 2.0,        # Near-Earth Objects get higher priority
    'pha': 3.0,        # Potentially Hazardous Asteroids highest priority
    'diameter': 1.5,   # Size is important
    'albedo': 1.5,     # Albedo is important
    'spectral': 2.0,   # Spectral type is very important
}

# Query Limits
DEFAULT_QUERY_LIMIT = 100
MAX_QUERY_LIMIT = 1000

# Export Configuration
EXPORT_FORMATS = ['csv', 'json', 'xlsx']

# Logging
LOG_LEVEL = 'INFO'
LOG_FILE = 'app.log'

# Feature Flags
ENABLE_SSODNET = True
ENABLE_EXOPLANET_ARCHIVE = False  # Future feature
ENABLE_MPC = False  # Future feature
ENABLE_WISE = False  # Future feature

# UI Configuration
ITEMS_PER_PAGE = 50
CHART_COLORS = {
    'primary': '#4a9eff',
    'secondary': '#5fd3ff',
    'high_priority': '#ff5252',
    'medium_priority': '#ffc107',
    'low_priority': '#4caf50',
}

