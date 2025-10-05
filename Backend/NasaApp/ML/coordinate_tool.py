import json
import os
from math import radians, cos, sin, asin, sqrt

COORD_FILE = "saved_coords.json"
MAX_DISTANCE_KM = 20  # max distance to consider "same location"

def haversine(lat1, lon1, lat2, lon2):
    """Calculate distance between two lat/lon points in kilometers."""
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1)*cos(lat2)*sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    return 6371 * c  # Earth radius in km

def find_existing(lat, lon):
    """Return (flag, coord) where flag=True if existing coord found, False otherwise."""
    
    # --- If file does not exist, no coordinate exists ---
    if not os.path.exists(COORD_FILE):
        return False, (lat, lon)

    # --- Load existing coordinates ---
    with open(COORD_FILE, 'r') as f:
        coords = json.load(f)

    # --- Check if close coordinate exists ---
    for c in coords:
        if haversine(lat, lon, c["lat"], c["lon"]) <= MAX_DISTANCE_KM:
            return True, (c["lat"], c["lon"])

    # --- No close coordinate found ---
    return False, (lat, lon)
