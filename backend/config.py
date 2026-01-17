"""
Configuration for MongoDB connection and data ingestion
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MongoDB Configuration
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
MONGODB_DB = "indigenous_lands"

# Collection names
COLLECTIONS = {
    "green_spaces": "green_spaces",
    "environmental_areas": "environmental_areas",
    "street_trees": "street_trees",
    "indigenous_territories": "indigenous_territories",
    "indigenous_treaties": "indigenous_treaties",
    "indigenous_languages": "indigenous_languages",
    "first_nations": "first_nations",
    "land_vulnerability": "land_vulnerability",
    "user_events": "user_events",
    "user_preferences": "user_preferences",
    "agent_sessions": "agent_sessions",
}

# Data file paths
DATA_DIR = Path(__file__).parent.parent / "Data"
DATA_FILES = {
    "green_spaces": DATA_DIR / "green_spaces_toronto.csv",
    "environmental_areas": DATA_DIR / "environmentally_significant_areas_toronto.csv",
    "street_trees": DATA_DIR / "street_trees_toronto.7z",  # Will need extraction
    "indigenous_territories": DATA_DIR / "native_land_territories_canada_coords.xlsx",
    "indigenous_treaties": DATA_DIR / "native_land_treaties_canada_coords.xlsx",
    "indigenous_languages": DATA_DIR / "native_land_languages_canada_coords.xlsx",
    "first_nations": DATA_DIR / "first_nations_canada.csv",
    "land_vulnerability": DATA_DIR / "land_cover_vulnerability_2050.csv",
}

# GTA (Greater Toronto Area) bounds for filtering
GTA_BOUNDS = {
    "min_lat": 43.4,
    "max_lat": 44.1,
    "min_lon": -80.0,
    "max_lon": -78.8,
}

# Default query radius (meters)
DEFAULT_RADIUS_METERS = 500

# Coordinate reference system
CRS = "EPSG:4326"  # WGS84 (standard lat/lon)
