"""
Load CSV datasets into MongoDB
Handles: green_spaces, environmental_areas, first_nations, land_vulnerability
"""
import pandas as pd
import sys
from pathlib import Path
from datetime import datetime

sys.path.append(str(Path(__file__).parent.parent))
from config import DATA_FILES, COLLECTIONS
from data_ingestion.db_loader import MongoDBLoader
from data_ingestion.geo_utils import parse_geometry, create_point, validate_geojson, get_centroid


def load_green_spaces(loader):
    """Load green spaces data"""
    print("\n" + "=" * 60)
    print("Loading Green Spaces (Toronto)")
    print("=" * 60)
    
    file_path = DATA_FILES["green_spaces"]
    if not file_path.exists():
        print(f"[ERROR] File not found: {file_path}")
        return
    
    df = pd.read_csv(file_path)
    print(f"Read {len(df)} rows from {file_path.name}")
    
    documents = []
    skipped = 0
    
    for idx, row in df.iterrows():
        # Parse geometry
        geometry = parse_geometry(row.get("geometry"))
        
        if not geometry or not validate_geojson(geometry):
            skipped += 1
            continue
        
        # Get centroid for point queries
        centroid_lon, centroid_lat = get_centroid(geometry)
        
        doc = {
            "name": str(row.get("AREA_NAME", "Unknown")),
            "type": "green_space",
            "properties": {
                "area_id": int(row.get("AREA_ID")) if pd.notna(row.get("AREA_ID")) else None,
                "area_class": str(row.get("AREA_CLASS", "")),
                "area_desc": str(row.get("AREA_DESC", "")),
                "area_code": str(row.get("AREA_LONG_CODE", "")),
                "objectid": int(row.get("OBJECTID")) if pd.notna(row.get("OBJECTID")) else None,
            },
            "geometry": geometry,
            "centroid": {
                "type": "Point",
                "coordinates": [centroid_lon, centroid_lat]
            } if centroid_lon and centroid_lat else None,
            "metadata": {
                "source": "green_spaces_toronto.csv",
                "loaded_at": datetime.utcnow(),
            }
        }
        
        documents.append(doc)
    
    print(f"Processed {len(documents)} valid documents ({skipped} skipped)")
    loader.bulk_insert(COLLECTIONS["green_spaces"], documents)
    loader.create_geospatial_index(COLLECTIONS["green_spaces"])


def load_environmental_areas(loader):
    """Load environmentally significant areas"""
    print("\n" + "=" * 60)
    print("Loading Environmentally Significant Areas (Toronto)")
    print("=" * 60)
    
    file_path = DATA_FILES["environmental_areas"]
    if not file_path.exists():
        print(f"[ERROR] File not found: {file_path}")
        return
    
    df = pd.read_csv(file_path)
    print(f"Read {len(df)} rows from {file_path.name}")
    
    documents = []
    skipped = 0
    
    for idx, row in df.iterrows():
        # Parse geometry
        geometry = parse_geometry(row.get("geometry"))
        
        if not geometry or not validate_geojson(geometry):
            skipped += 1
            continue
        
        # Get centroid
        centroid_lon, centroid_lat = get_centroid(geometry)
        
        doc = {
            "name": str(row.get("ESA_NAME", "Unknown")),
            "type": "environmental_area",
            "properties": {
                "esa_number": int(row.get("ESA_NUM")) if pd.notna(row.get("ESA_NUM")) else None,
                "link": str(row.get("LINK", "")),
                "x": float(row.get("X")) if pd.notna(row.get("X")) else None,
                "y": float(row.get("Y")) if pd.notna(row.get("Y")) else None,
                "latitude": float(row.get("LATITUDE")) if pd.notna(row.get("LATITUDE")) else None,
                "longitude": float(row.get("LONGITUDE")) if pd.notna(row.get("LONGITUDE")) else None,
                "shape_area": float(row.get("Shape__Area")) if pd.notna(row.get("Shape__Area")) else None,
                "shape_length": float(row.get("Shape__Length")) if pd.notna(row.get("Shape__Length")) else None,
            },
            "geometry": geometry,
            "centroid": {
                "type": "Point",
                "coordinates": [centroid_lon, centroid_lat]
            } if centroid_lon and centroid_lat else None,
            "metadata": {
                "source": "environmentally_significant_areas_toronto.csv",
                "loaded_at": datetime.utcnow(),
            }
        }
        
        documents.append(doc)
    
    print(f"Processed {len(documents)} valid documents ({skipped} skipped)")
    loader.bulk_insert(COLLECTIONS["environmental_areas"], documents)
    loader.create_geospatial_index(COLLECTIONS["environmental_areas"])


def load_first_nations(loader):
    """Load First Nations communities"""
    print("\n" + "=" * 60)
    print("Loading First Nations Communities (Canada)")
    print("=" * 60)
    
    file_path = DATA_FILES["first_nations"]
    if not file_path.exists():
        print(f"[ERROR] File not found: {file_path}")
        return
    
    # This CSV doesn't have headers, so we define them
    column_names = [
        "name", "id", "province", "code", "electoral_system", "chief",
        "address", "city", "postal_code", "website", "profile", "longitude", "latitude"
    ]
    
    df = pd.read_csv(file_path, names=column_names, header=None)
    print(f"Read {len(df)} rows from {file_path.name}")
    
    documents = []
    skipped = 0
    
    for idx, row in df.iterrows():
        # Get coordinates (last two columns)
        lon = row.get("longitude")
        lat = row.get("latitude")
        
        if pd.isna(lat) or pd.isna(lon):
            skipped += 1
            continue
        
        try:
            geometry = create_point(float(lon), float(lat))
            if not geometry:
                skipped += 1
                continue
        except (ValueError, TypeError):
            skipped += 1
            continue
        
        doc = {
            "name": str(row.get("name", "Unknown")),
            "type": "first_nation",
            "properties": {
                "fn_id": str(row.get("id", "")),
                "province": str(row.get("province", "")),
                "code": str(row.get("code", "")),
                "electoral_system": str(row.get("electoral_system", "")),
                "chief": str(row.get("chief", "")),
                "address": str(row.get("address", "")),
                "city": str(row.get("city", "")),
                "postal_code": str(row.get("postal_code", "")),
                "website": str(row.get("website", "")),
                "profile": str(row.get("profile", "")),
            },
            "geometry": geometry,
            "metadata": {
                "source": "first_nations_canada.csv",
                "loaded_at": datetime.utcnow(),
            }
        }
        
        documents.append(doc)
    
    print(f"Processed {len(documents)} valid documents ({skipped} skipped)")
    loader.bulk_insert(COLLECTIONS["first_nations"], documents)
    loader.create_geospatial_index(COLLECTIONS["first_nations"])


def load_land_vulnerability(loader):
    """Load land cover vulnerability 2050 data"""
    print("\n" + "=" * 60)
    print("Loading Land Cover Vulnerability 2050")
    print("=" * 60)
    
    file_path = DATA_FILES["land_vulnerability"]
    if not file_path.exists():
        print(f"[ERROR] File not found: {file_path}")
        return
    
    df = pd.read_csv(file_path)
    print(f"Read {len(df)} rows from {file_path.name}")
    
    documents = []
    
    for idx, row in df.iterrows():
        # These are raster/tile metadata, not points
        # Store as documents with center coordinates
        center_x = row.get("CenterX")
        center_y = row.get("CenterY")
        
        if pd.notna(center_x) and pd.notna(center_y):
            geometry = create_point(float(center_x), float(center_y))
        else:
            geometry = None
        
        doc = {
            "name": str(row.get("Name", "Unknown")),
            "type": "land_vulnerability",
            "properties": {
                "objectid": int(row.get("OBJECTID")) if pd.notna(row.get("OBJECTID")) else None,
                "min_ps": float(row.get("MinPS")) if pd.notna(row.get("MinPS")) else None,
                "max_ps": float(row.get("MaxPS")) if pd.notna(row.get("MaxPS")) else None,
                "low_ps": float(row.get("LowPS")) if pd.notna(row.get("LowPS")) else None,
                "high_ps": float(row.get("HighPS")) if pd.notna(row.get("HighPS")) else None,
                "category": int(row.get("Category")) if pd.notna(row.get("Category")) else None,
                "product_name": str(row.get("ProductName", "")),
                "shape_area": float(row.get("Shape_Area")) if pd.notna(row.get("Shape_Area")) else None,
            },
            "geometry": geometry,
            "metadata": {
                "source": "land_cover_vulnerability_2050.csv",
                "loaded_at": datetime.utcnow(),
            }
        }
        
        documents.append(doc)
    
    print(f"Processed {len(documents)} documents")
    loader.bulk_insert(COLLECTIONS["land_vulnerability"], documents)
    if any(doc.get("geometry") for doc in documents):
        loader.create_geospatial_index(COLLECTIONS["land_vulnerability"])


if __name__ == "__main__":
    loader = MongoDBLoader()
    
    try:
        load_green_spaces(loader)
        load_environmental_areas(loader)
        load_first_nations(loader)
        load_land_vulnerability(loader)
        
        print("\n" + "=" * 60)
        print("CSV Data Loading Complete!")
        print("=" * 60)
        
    finally:
        loader.close()
