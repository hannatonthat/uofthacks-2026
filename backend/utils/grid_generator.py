"""
Generate grid points for map visualization
Creates evenly-spaced grid across the GTA
"""
from typing import List, Dict, Any
import math
from config import GTA_BOUNDS
from utils.geo_queries import find_near_point, find_containing_polygon
from database import get_collection

def generate_gta_grid(spacing_km: float = 1.0) -> List[Dict[str, float]]:
    """
    Generate evenly-spaced grid points across the GTA
    
    Args:
        spacing_km: Distance between points in kilometers
    
    Returns:
        List of {lat, lon, id} grid points
    """
    # Get bounds from config
    min_lat = GTA_BOUNDS["min_lat"]
    max_lat = GTA_BOUNDS["max_lat"]
    min_lon = GTA_BOUNDS["min_lon"]
    max_lon = GTA_BOUNDS["max_lon"]
    
    # Calculate spacing in degrees
    # 1 degree latitude ≈ 111 km
    lat_spacing = spacing_km / 111.0
    
    # 1 degree longitude ≈ 111 km * cos(latitude)
    # Use center latitude for calculation
    center_lat = (min_lat + max_lat) / 2
    lon_spacing = spacing_km / (111.0 * math.cos(math.radians(center_lat)))
    
    # Generate grid points
    grid_points = []
    point_id = 0
    
    lat = min_lat
    while lat <= max_lat:
        lon = min_lon
        while lon <= max_lon:
            grid_points.append({
                "id": f"grid_{point_id}",
                "lat": round(lat, 6),
                "lon": round(lon, 6)
            })
            point_id += 1
            lon += lon_spacing
        lat += lat_spacing
    
    return grid_points


def get_all_data_for_point(lat: float, lon: float) -> Dict[str, Any]:
    """
    Query all collections to find nearest/containing data for a grid point
    
    Args:
        lat: Latitude
        lon: Longitude
    
    Returns:
        Dictionary with nearest and containing data from all collections
    """
    result = {
        "lat": lat,
        "lon": lon,
        "nearest_green_space": None,
        "nearest_environmental_area": None,
        "nearest_first_nation": None,
        "containing_territory": None,
        "containing_treaty": None,
        "containing_language": None
    }
    
    # Find nearest green space
    try:
        nearest = find_near_point("green_spaces", lon, lat, limit=1)
        if nearest:
            doc = nearest[0]
            result["nearest_green_space"] = {
                "name": doc.get("name", "Unknown"),
                "distance": doc.get("distance", 0)
            }
    except Exception as e:
        print(f"Error finding nearest green space: {e}")
    
    # Find nearest environmental area
    try:
        nearest = find_near_point("environmental_areas", lon, lat, limit=1)
        if nearest:
            doc = nearest[0]
            result["nearest_environmental_area"] = {
                "name": doc.get("name", "Unknown"),
                "distance": doc.get("distance", 0)
            }
    except Exception as e:
        print(f"Error finding nearest environmental area: {e}")
    
    # Find nearest first nation
    try:
        nearest = find_near_point("first_nations", lon, lat, limit=1)
        if nearest:
            doc = nearest[0]
            result["nearest_first_nation"] = {
                "name": doc.get("name", "Unknown"),
                "distance": doc.get("distance", 0)
            }
    except Exception as e:
        print(f"Error finding nearest first nation: {e}")
    
    # Find containing territory
    try:
        territory = find_containing_polygon("indigenous_territories", lon, lat)
        if territory:
            result["containing_territory"] = {
                "name": territory.get("name", "Unknown")
            }
    except Exception as e:
        print(f"Error finding containing territory: {e}")
    
    # Find containing treaty
    try:
        treaty = find_containing_polygon("indigenous_treaties", lon, lat)
        if treaty:
            result["containing_treaty"] = {
                "name": treaty.get("name", "Unknown")
            }
    except Exception as e:
        print(f"Error finding containing treaty: {e}")
    
    # Find containing language region
    try:
        language = find_containing_polygon("indigenous_languages", lon, lat)
        if language:
            result["containing_language"] = {
                "name": language.get("name", "Unknown")
            }
    except Exception as e:
        print(f"Error finding containing language: {e}")
    
    return result


def get_data_points_for_map(limit: int = 100) -> List[Dict[str, Any]]:
    """
    Returns BOTH actual data locations AND evenly-spaced grid points
    No pre-querying - just coordinates
    Detailed data is fetched when user clicks a point
    
    Args:
        limit: Total number of points to return
    
    Returns:
        Mix of actual data locations + grid points
    """
    points = []
    
    # 1. Get actual data points (60% of limit)
    data_point_count = int(limit * 0.6)
    collections_config = [
        ("green_spaces", int(data_point_count * 0.4), "green_space"),
        ("environmental_areas", int(data_point_count * 0.2), "environmental"),
        ("first_nations", int(data_point_count * 0.4), "first_nation"),
    ]
    
    for collection_name, count, point_type in collections_config:
        if count == 0:
            continue
            
        collection = get_collection(collection_name)
        
        # Sample random documents - FAST, filter to GTA bounds
        pipeline = [
            # Only get GTA points using centroid or geometry coordinates
            {"$match": {
                "geometry": {"$exists": True},
                "$or": [
                    {
                        "centroid.coordinates.0": {"$gte": GTA_BOUNDS["min_lon"], "$lte": GTA_BOUNDS["max_lon"]},
                        "centroid.coordinates.1": {"$gte": GTA_BOUNDS["min_lat"], "$lte": GTA_BOUNDS["max_lat"]}
                    },
                    {
                        "geometry.coordinates.0": {"$gte": GTA_BOUNDS["min_lon"], "$lte": GTA_BOUNDS["max_lon"]},
                        "geometry.coordinates.1": {"$gte": GTA_BOUNDS["min_lat"], "$lte": GTA_BOUNDS["max_lat"]}
                    }
                ]
            }},
            {"$sample": {"size": count}},
            {"$project": {
                "_id": 1,
                "name": 1,
                "geometry": 1,
                "centroid": 1
            }}
        ]
        
        docs = list(collection.aggregate(pipeline))
        
        for doc in docs:
            # Get coordinates
            if doc.get("centroid") and doc["centroid"].get("coordinates"):
                lon, lat = doc["centroid"]["coordinates"]
            elif doc.get("geometry") and doc["geometry"].get("coordinates"):
                coords = doc["geometry"]["coordinates"]
                if doc["geometry"]["type"] == "Point":
                    lon, lat = coords
                else:
                    # For polygons, use first coordinate
                    lon, lat = coords[0][0] if isinstance(coords[0], list) else coords[0], coords[0][1] if isinstance(coords[0], list) else coords[1]
            else:
                continue
            
            # Double-check point is within GTA bounds
            if not (GTA_BOUNDS["min_lat"] <= lat <= GTA_BOUNDS["max_lat"] and 
                    GTA_BOUNDS["min_lon"] <= lon <= GTA_BOUNDS["max_lon"]):
                continue
            
            points.append({
                "id": str(doc["_id"]),
                "lat": lat,
                "lon": lon,
                "name": doc.get("name", "Unknown"),
                "type": point_type
            })
    
    # 2. Add strategic grid points in Toronto core (40% of limit)
    # Focus on main Toronto area where people actually live/work
    grid_count = limit - len(points)
    if grid_count > 0:
        # Toronto downtown and major areas - avoid Lake Ontario
        # These are strategic points at major intersections/neighborhoods
        toronto_strategic_points = [
            (43.6532, -79.3832, "Downtown Toronto"),
            (43.6426, -79.3871, "CN Tower / Harbourfront"),
            (43.6629, -79.3957, "Trinity Bellwoods"),
            (43.6708, -79.4163, "High Park"),
            (43.6465, -79.4637, "High Park West"),
            (43.6591, -79.4500, "The Junction"),
            (43.6789, -79.3469, "Greektown"),
            (43.6545, -79.3626, "Corktown"),
            (43.6650, -79.3197, "Leslieville"),
            (43.6850, -79.2950, "The Beaches"),
            (43.7101, -79.4163, "York / Eglinton West"),
            (43.7070, -79.3975, "Yorkville"),
            (43.6800, -79.4100, "Little Italy"),
            (43.7280, -79.4100, "Forest Hill"),
            (43.7000, -79.3000, "East York"),
            (43.7700, -79.4100, "North York Centre"),
            (43.7800, -79.4700, "Downsview"),
            (43.7500, -79.5300, "Etobicoke North"),
            (43.6300, -79.4300, "Liberty Village"),
            (43.6200, -79.3800, "Toronto Islands"),
            (43.7400, -79.5000, "Weston"),
            (43.7600, -79.3000, "Don Mills"),
            (43.7900, -79.3500, "Willowdale"),
            (43.6900, -79.5400, "Etobicoke"),
            (43.7200, -79.2800, "Scarborough West"),
            (43.7700, -79.2300, "Scarborough East"),
            (43.8100, -79.5100, "Jane & Finch"),
            (43.7300, -79.5800, "Humber Bay"),
            (43.6100, -79.5400, "Mimico"),
            (43.6500, -79.5200, "Long Branch"),
            (43.7400, -79.3400, "Midtown"),
            (43.6700, -79.2900, "Riverside"),
        ]
        
        # Take as many as we need
        for i, (lat, lon, name) in enumerate(toronto_strategic_points[:grid_count]):
            points.append({
                "id": f"strategic_{i}",
                "lat": lat,
                "lon": lon,
                "name": name,
                "type": "grid_point"
            })
    
    print(f"Generated {len(points)} points: {len([p for p in points if p['type'] != 'grid_point'])} data + {len([p for p in points if p['type'] == 'grid_point'])} grid")
    return points
