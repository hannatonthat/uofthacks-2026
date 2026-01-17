"""
Geospatial query utilities for MongoDB
"""
from typing import List, Dict, Any, Optional, Tuple
from database import get_collection
from config import DEFAULT_RADIUS_METERS, COLLECTIONS


def find_near_point(
    collection_name: str,
    lon: float,
    lat: float,
    radius_meters: int = DEFAULT_RADIUS_METERS,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Find documents near a point using $geoNear
    
    Args:
        collection_name: Name of collection to query
        lon: Longitude
        lat: Latitude
        radius_meters: Search radius in meters
        limit: Maximum results to return
    
    Returns:
        List of documents with distance information
    """
    collection = get_collection(collection_name)
    
    pipeline = [
        {
            "$geoNear": {
                "near": {
                    "type": "Point",
                    "coordinates": [lon, lat]
                },
                "distanceField": "distance",
                "maxDistance": radius_meters,
                "spherical": True
            }
        },
        {"$limit": limit}
    ]
    
    results = list(collection.aggregate(pipeline))
    
    # Convert ObjectId to string for JSON serialization
    for doc in results:
        if "_id" in doc:
            doc["_id"] = str(doc["_id"])
    
    return results


def find_all_near_point(
    lon: float,
    lat: float,
    radius_meters: int = DEFAULT_RADIUS_METERS
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Find all data near a point across all geospatial collections
    
    Args:
        lon: Longitude
        lat: Latitude
        radius_meters: Search radius in meters
    
    Returns:
        Dictionary with collection names as keys and nearby documents as values
    """
    # Point collections - use $geoNear
    point_collections = [
        "green_spaces",
        "environmental_areas",
        "first_nations",
    ]
    
    # Polygon collections - use $geoIntersects or $geoWithin
    polygon_collections = [
        "indigenous_territories",
        "indigenous_treaties",
        "indigenous_languages",
    ]
    
    results = {}
    
    # Query point-based collections
    for coll_name in point_collections:
        try:
            nearby = find_near_point(coll_name, lon, lat, radius_meters, limit=50)
            # If nothing within radius, find the absolute nearest (no radius limit)
            if not nearby:
                nearby = find_near_point(coll_name, lon, lat, radius_meters=10000000, limit=1)  # 10,000 km
            results[coll_name] = nearby if nearby else []
        except Exception as e:
            print(f"Error querying {coll_name}: {e}")
            results[coll_name] = []
    
    # Query polygon-based collections (find containing polygons)
    point = {
        "type": "Point",
        "coordinates": [lon, lat]
    }
    
    for coll_name in polygon_collections:
        try:
            collection = get_collection(coll_name)
            # Find polygons that contain this point
            docs = list(collection.find({
                "geometry": {
                    "$geoIntersects": {
                        "$geometry": point
                    }
                }
            }).limit(10))
            
            # Format results
            formatted_docs = []
            for doc in docs:
                doc["_id"] = str(doc["_id"])
                formatted_docs.append(doc)
            
            results[coll_name] = formatted_docs
        except Exception as e:
            print(f"Error querying {coll_name}: {e}")
            results[coll_name] = []
    
    return results


def find_containing_polygon(collection_name: str, lon: float, lat: float) -> Optional[Dict[str, Any]]:
    """
    Find which polygon (territory, treaty, language) contains this point
    
    Args:
        collection_name: Name of the collection to search
        lon: Longitude
        lat: Latitude
    
    Returns:
        Document or None
    """
    collection = get_collection(collection_name)
    
    point = {
        "type": "Point",
        "coordinates": [lon, lat]
    }
    
    # Query for polygon that contains this point
    result = collection.find_one({
        "geometry": {
            "$geoIntersects": {
                "$geometry": point
            }
        }
    })
    
    # Convert ObjectId to string for JSON serialization
    if result and "_id" in result:
        result["_id"] = str(result["_id"])
    
    return result


def find_containing_territory(lon: float, lat: float) -> Optional[Dict[str, Any]]:
    """
    Find which Indigenous territory contains this point
    
    Args:
        lon: Longitude
        lat: Latitude
    
    Returns:
        Territory document or None
    """
    return find_containing_polygon("indigenous_territories", lon, lat)
    
    # Find territory that contains this point
    territory = collection.find_one({
        "geometry": {
            "$geoIntersects": {
                "$geometry": point
            }
        }
    })
    
    if territory and "_id" in territory:
        territory["_id"] = str(territory["_id"])
    
    return territory


def find_in_bounds(
    collection_name: str,
    min_lon: float,
    min_lat: float,
    max_lon: float,
    max_lat: float,
    limit: int = 1000
) -> List[Dict[str, Any]]:
    """
    Find documents within a bounding box (for map viewport)
    
    Args:
        collection_name: Name of collection
        min_lon: Minimum longitude (west)
        min_lat: Minimum latitude (south)
        max_lon: Maximum longitude (east)
        max_lat: Maximum latitude (north)
        limit: Maximum results
    
    Returns:
        List of documents
    """
    collection = get_collection(collection_name)
    
    # Use $geoWithin with $box for bounding box query
    query = {
        "geometry": {
            "$geoWithin": {
                "$box": [
                    [min_lon, min_lat],  # Southwest corner
                    [max_lon, max_lat]   # Northeast corner
                ]
            }
        }
    }
    
    results = list(collection.find(query).limit(limit))
    
    # Convert ObjectId to string
    for doc in results:
        if "_id" in doc:
            doc["_id"] = str(doc["_id"])
    
    return results


def calculate_ecological_sensitivity_score(
    lon: float, 
    lat: float, 
    search_radius_meters: int = 1000
) -> Dict[str, Any]:
    """
    Calculate ecological sensitivity score based on 3-30-300 rule
    
    Metrics (30 points total):
    1. Proximity to Environmentally Significant Area (10 pts)
    2. Proximity to Green Space (10 pts) 
    3. Number of Street Trees within radius (10 pts)
    
    Returns:
        {
            "total_score": float,  # 0-30
            "normalized_score": float,  # 0-10 for display
            "metrics": {
                "environmental_area_proximity": {...},
                "green_space_proximity": {...},
                "street_tree_count": {...}
            },
            "rule_compliance": {
                "has_3_trees": bool,
                "within_300m_green_space": bool
            }
        }
    """
    score = 0
    metrics = {}
    
    # Metric 1: Environmental Area Proximity (10 points)
    # Score = 10 - 10 * (1 - d/d_min), d_min = 1km
    env_areas = find_near_point("environmental_areas", lon, lat, 1000, limit=1)
    if env_areas and len(env_areas) > 0:
        distance = env_areas[0].get("distance", 1001)
        if distance <= 1000:
            env_score = 10 - 10 * (1 - distance / 1000)
        else:
            env_score = 0
    else:
        env_score = 0
        distance = None
    
    metrics["environmental_area_proximity"] = {
        "score": round(env_score, 2),
        "max": 10,
        "distance_meters": round(distance, 2) if distance else None,
        "nearest_area": env_areas[0].get("name") if env_areas else None
    }
    score += env_score
    
    # Metric 2: Green Space Proximity (10 points)
    # Score = 10 - 10 * (1 - d/d_min), d_min = 0.3km (300m)
    green_spaces = find_near_point("green_spaces", lon, lat, 300, limit=1)
    if green_spaces and len(green_spaces) > 0:
        distance = green_spaces[0].get("distance", 301)
        if distance <= 300:
            green_score = 10 - 10 * (1 - distance / 300)
        else:
            green_score = 0
    else:
        green_score = 0
        distance = None
    
    metrics["green_space_proximity"] = {
        "score": round(green_score, 2),
        "max": 10,
        "distance_meters": round(distance, 2) if distance else None,
        "nearest_space": green_spaces[0].get("name") if green_spaces else None,
        "within_300m": distance <= 300 if distance else False
    }
    score += green_score
    
    # Metric 3: Street Trees Count (10 points)
    # Score = 10 - 10 * (1 - n/n_min), n_min = 3 trees
    # Using smaller radius and limit for performance with 689K tree dataset
    try:
        # Use smaller radius (300m max) for tree queries to improve speed
        tree_radius = min(search_radius_meters, 300)
        street_trees = find_near_point("street_trees", lon, lat, tree_radius, limit=5)
        tree_count = len(street_trees)
        if tree_count >= 3:
            tree_score = 10
        else:
            tree_score = 10 - 10 * (1 - tree_count / 3)
    except Exception as e:
        print(f"Street trees not available: {e}")
        tree_count = 0
        tree_score = 0
    
    metrics["street_tree_count"] = {
        "score": round(tree_score, 2),
        "max": 10,
        "count": tree_count,
        "search_radius_meters": search_radius_meters,
        "has_minimum_3": tree_count >= 3
    }
    score += tree_score
    
    # Rule compliance check
    rule_compliance = {
        "has_3_trees": tree_count >= 3,
        "within_300m_green_space": metrics["green_space_proximity"]["within_300m"],
        "rule_330_compliant": tree_count >= 3 and metrics["green_space_proximity"]["within_300m"]
    }
    
    return {
        "total_score": round(score, 2),
        "normalized_score": round((score / 30) * 10, 2),  # 0-10 scale
        "max_score": 30,
        "metrics": metrics,
        "rule_compliance": rule_compliance,
        "location": {"lon": lon, "lat": lat}
    }


def calculate_sustainability_score(lon: float, lat: float, radius_meters: int = 1000) -> Dict[str, Any]:
    """Legacy function - calls new ecological sensitivity score"""
    return calculate_ecological_sensitivity_score(lon, lat, radius_meters)


def get_native_plants_for_territory(territory_name: str) -> List[str]:
    """
    Get native plants for an indigenous territory
    TODO: Integrate with tree data once we process street_trees
    
    For now, returns common native plants for Ontario/Toronto region
    """
    # Common native plants for Southern Ontario
    native_plants = {
        "trees": [
            "White Pine (Pinus strobus)",
            "Sugar Maple (Acer saccharum)",
            "Red Oak (Quercus rubra)",
            "Eastern White Cedar (Thuja occidentalis)",
            "Black Cherry (Prunus serotina)",
            "Paper Birch (Betula papyrifera)",
            "Eastern Hemlock (Tsuga canadensis)",
        ],
        "shrubs": [
            "Serviceberry (Amelanchier)",
            "Elderberry (Sambucus canadensis)",
            "Nannyberry (Viburnum lentago)",
            "Red-osier Dogwood (Cornus sericea)",
        ],
        "plants": [
            "Wild Bergamot (Monarda fistulosa)",
            "Black-eyed Susan (Rudbeckia hirta)",
            "New England Aster (Symphyotrichum novae-angliae)",
            "Canada Goldenrod (Solidago canadensis)",
        ]
    }
    
    return native_plants


def get_nearest_first_nation(lon: float, lat: float) -> Optional[Dict[str, Any]]:
    """Get nearest First Nation community"""
    results = find_near_point("first_nations", lon, lat, radius_meters=100000, limit=1)
    return results[0] if results else None
