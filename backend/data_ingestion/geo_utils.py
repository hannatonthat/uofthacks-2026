"""
Geospatial utility functions for converting data to GeoJSON format
"""
import json
from shapely.geometry import shape, Point, Polygon, MultiPolygon, mapping
from shapely import wkt


def parse_geometry(geom_value):
    """
    Parse geometry from various formats to GeoJSON
    Handles: WKT strings, GeoJSON strings, dict objects
    """
    if geom_value is None or (isinstance(geom_value, float) and geom_value != geom_value):  # NaN check
        return None
    
    # If it's already a dict (GeoJSON)
    if isinstance(geom_value, dict):
        if "type" in geom_value and "coordinates" in geom_value:
            return geom_value
        # Might be nested JSON string
        return geom_value
    
    # If it's a string
    if isinstance(geom_value, str):
        # Try parsing as JSON first
        try:
            geom_dict = json.loads(geom_value)
            if "type" in geom_dict and "coordinates" in geom_dict:
                return geom_dict
        except (json.JSONDecodeError, ValueError):
            pass
        
        # Try parsing as WKT
        try:
            geom = wkt.loads(geom_value)
            return mapping(geom)  # Convert shapely to GeoJSON
        except Exception:
            pass
    
    return None


def create_point(lon, lat):
    """Create a GeoJSON Point from lon/lat"""
    if lon is None or lat is None:
        return None
    
    try:
        lon = float(lon)
        lat = float(lat)
        
        # Validate coordinates
        if -180 <= lon <= 180 and -90 <= lat <= 90:
            return {
                "type": "Point",
                "coordinates": [lon, lat]
            }
    except (ValueError, TypeError):
        pass
    
    return None


def validate_geojson(geojson_geom):
    """Validate that geometry is valid GeoJSON"""
    if not geojson_geom or not isinstance(geojson_geom, dict):
        return False
    
    if "type" not in geojson_geom or "coordinates" not in geojson_geom:
        return False
    
    valid_types = ["Point", "LineString", "Polygon", "MultiPoint", "MultiLineString", "MultiPolygon"]
    return geojson_geom["type"] in valid_types


def get_centroid(geojson_geom):
    """Get centroid coordinates from any GeoJSON geometry"""
    if not geojson_geom:
        return None, None
    
    try:
        geom = shape(geojson_geom)
        centroid = geom.centroid
        return centroid.x, centroid.y  # lon, lat
    except Exception:
        return None, None


def coords_in_gta(lon, lat):
    """Check if coordinates are in Greater Toronto Area bounds"""
    GTA_BOUNDS = {
        "min_lat": 43.4,
        "max_lat": 44.1,
        "min_lon": -80.0,
        "max_lon": -78.8,
    }
    
    try:
        lon = float(lon)
        lat = float(lat)
        return (
            GTA_BOUNDS["min_lat"] <= lat <= GTA_BOUNDS["max_lat"] and
            GTA_BOUNDS["min_lon"] <= lon <= GTA_BOUNDS["max_lon"]
        )
    except (ValueError, TypeError):
        return False


def parse_native_land_coordinates(coords_str, geom_type):
    """
    Parse coordinates from Native Land XLSX format
    Format: "lon,lat;lon,lat;lon,lat"
    
    Args:
        coords_str: Semicolon-separated coordinate pairs
        geom_type: "Polygon" or "MultiPolygon"
    
    Returns:
        GeoJSON geometry dict
    """
    if not coords_str or not geom_type:
        return None
    
    try:
        # Parse coordinate pairs
        pairs = coords_str.strip().split(';')
        coords = []
        for pair in pairs:
            lon, lat = pair.split(',')
            coords.append([float(lon), float(lat)])
        
        if len(coords) < 3:  # Need at least 3 points for a polygon
            return None
        
        # Close the polygon if not already closed
        if coords[0] != coords[-1]:
            coords.append(coords[0])
        
        # Create GeoJSON based on type
        if geom_type == "Polygon":
            return {
                "type": "Polygon",
                "coordinates": [coords]  # Polygon needs array of rings
            }
        elif geom_type == "MultiPolygon":
            return {
                "type": "MultiPolygon",
                "coordinates": [[coords]]  # MultiPolygon needs array of polygons
            }
        else:
            return None
            
    except Exception as e:
        print(f"Error parsing coordinates: {e}")
        return None
