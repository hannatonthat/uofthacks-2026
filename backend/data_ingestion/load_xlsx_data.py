"""
Load XLSX datasets into MongoDB
Handles: indigenous_territories, indigenous_treaties, indigenous_languages
"""
import pandas as pd
import sys
from pathlib import Path
from datetime import datetime

sys.path.append(str(Path(__file__).parent.parent))
from config import DATA_FILES, COLLECTIONS
from data_ingestion.db_loader import MongoDBLoader
from data_ingestion.geo_utils import parse_geometry, create_point, validate_geojson, get_centroid, parse_native_land_coordinates


def load_indigenous_territories(loader):
    """Load Indigenous territories data"""
    print("\n" + "=" * 60)
    print("Loading Indigenous Territories (Canada)")
    print("=" * 60)
    
    file_path = DATA_FILES["indigenous_territories"]
    if not file_path.exists():
        print(f"[ERROR] File not found: {file_path}")
        return
    
    df = pd.read_excel(file_path)
    print(f"Read {len(df)} rows from {file_path.name}")
    
    documents = []
    skipped = 0
    
    for idx, row in df.iterrows():
        # Try to parse coordinates column (Native Land format)
        geometry = None
        if "coordinates" in df.columns and "geometry_type" in df.columns:
            coords_str = row.get("coordinates")
            geom_type = row.get("geometry_type")
            if pd.notna(coords_str) and pd.notna(geom_type):
                geometry = parse_native_land_coordinates(coords_str, geom_type)
        
        # Try to parse geometry column if it exists
        if not geometry and "geometry" in df.columns:
            geometry = parse_geometry(row.get("geometry"))
        
        # If no geometry, try to create point from lat/lon
        if not geometry:
            lat_cols = [c for c in df.columns if 'lat' in c.lower()]
            lon_cols = [c for c in df.columns if 'lon' in c.lower() or 'lng' in c.lower()]
            
            if lat_cols and lon_cols:
                lat = row.get(lat_cols[0])
                lon = row.get(lon_cols[0])
                
                if pd.notna(lat) and pd.notna(lon):
                    geometry = create_point(float(lon), float(lat))
        
        if not geometry:
            skipped += 1
            continue
        
        # Get name from first text column or ID
        name_cols = [c for c in df.columns if 'name' in c.lower() or c.lower() in ['territory', 'nation']]
        name = str(row.get(name_cols[0])) if name_cols else f"Territory {idx}"
        
        # Get all other properties
        properties = {}
        for col in df.columns:
            if col not in ['geometry'] and pd.notna(row.get(col)):
                properties[col.lower().replace(' ', '_')] = str(row.get(col))
        
        # Get centroid
        centroid_lon, centroid_lat = get_centroid(geometry)
        
        doc = {
            "name": name,
            "type": "indigenous_territory",
            "properties": properties,
            "geometry": geometry,
            "centroid": {
                "type": "Point",
                "coordinates": [centroid_lon, centroid_lat]
            } if centroid_lon and centroid_lat else None,
            "metadata": {
                "source": "native_land_territories_canada_coords.xlsx",
                "loaded_at": datetime.utcnow(),
            }
        }
        
        documents.append(doc)
    
    print(f"Processed {len(documents)} valid documents ({skipped} skipped)")
    loader.bulk_insert(COLLECTIONS["indigenous_territories"], documents)
    loader.create_geospatial_index(COLLECTIONS["indigenous_territories"])


def load_indigenous_treaties(loader):
    """Load Indigenous treaties data"""
    print("\n" + "=" * 60)
    print("Loading Indigenous Treaties (Canada)")
    print("=" * 60)
    
    file_path = DATA_FILES["indigenous_treaties"]
    if not file_path.exists():
        print(f"[ERROR] File not found: {file_path}")
        return
    
    df = pd.read_excel(file_path)
    print(f"Read {len(df)} rows from {file_path.name}")
    
    documents = []
    skipped = 0
    
    for idx, row in df.iterrows():
        # Try to parse Native Land coordinates format FIRST
        geometry = None
        if "coordinates" in df.columns and "geometry_type" in df.columns:
            coords_str = row.get("coordinates")
            geom_type = row.get("geometry_type")
            if pd.notna(coords_str) and pd.notna(geom_type):
                geometry = parse_native_land_coordinates(coords_str, geom_type)
        
        # Try to parse geometry column if it exists
        if not geometry and "geometry" in df.columns:
            geometry = parse_geometry(row.get("geometry"))
        
        # If no geometry, try point from lat/lon
        if not geometry:
            lat_cols = [c for c in df.columns if 'lat' in c.lower()]
            lon_cols = [c for c in df.columns if 'lon' in c.lower() or 'lng' in c.lower()]
            
            if lat_cols and lon_cols:
                lat = row.get(lat_cols[0])
                lon = row.get(lon_cols[0])
                
                if pd.notna(lat) and pd.notna(lon):
                    geometry = create_point(float(lon), float(lat))
        
        if not geometry:
            skipped += 1
            continue
        
        # Get name
        name_cols = [c for c in df.columns if 'name' in c.lower() or 'treaty' in c.lower()]
        name = str(row.get(name_cols[0])) if name_cols else f"Treaty {idx}"
        
        # Get all properties
        properties = {}
        for col in df.columns:
            if col not in ['geometry'] and pd.notna(row.get(col)):
                properties[col.lower().replace(' ', '_')] = str(row.get(col))
        
        # Get centroid
        centroid_lon, centroid_lat = get_centroid(geometry)
        
        doc = {
            "name": name,
            "type": "indigenous_treaty",
            "properties": properties,
            "geometry": geometry,
            "centroid": {
                "type": "Point",
                "coordinates": [centroid_lon, centroid_lat]
            } if centroid_lon and centroid_lat else None,
            "metadata": {
                "source": "native_land_treaties_canada_coords.xlsx",
                "loaded_at": datetime.utcnow(),
            }
        }
        
        documents.append(doc)
    
    print(f"Processed {len(documents)} valid documents ({skipped} skipped)")
    loader.bulk_insert(COLLECTIONS["indigenous_treaties"], documents)
    loader.create_geospatial_index(COLLECTIONS["indigenous_treaties"])


def load_indigenous_languages(loader):
    """Load Indigenous languages data"""
    print("\n" + "=" * 60)
    print("Loading Indigenous Languages (Canada)")
    print("=" * 60)
    
    file_path = DATA_FILES["indigenous_languages"]
    if not file_path.exists():
        print(f"[ERROR] File not found: {file_path}")
        return
    
    df = pd.read_excel(file_path)
    print(f"Read {len(df)} rows from {file_path.name}")
    
    documents = []
    skipped = 0
    
    for idx, row in df.iterrows():
        # Try to parse coordinates column (Native Land format)
        geometry = None
        if "coordinates" in df.columns and "geometry_type" in df.columns:
            coords_str = row.get("coordinates")
            geom_type = row.get("geometry_type")
            if pd.notna(coords_str) and pd.notna(geom_type):
                geometry = parse_native_land_coordinates(coords_str, geom_type)
        
        # Try to parse geometry
        if not geometry and "geometry" in df.columns:
            geometry = parse_geometry(row.get("geometry"))
        
        # If no geometry, try point from lat/lon
        if not geometry:
            lat_cols = [c for c in df.columns if 'lat' in c.lower()]
            lon_cols = [c for c in df.columns if 'lon' in c.lower() or 'lng' in c.lower()]
            
            if lat_cols and lon_cols:
                lat = row.get(lat_cols[0])
                lon = row.get(lon_cols[0])
                
                if pd.notna(lat) and pd.notna(lon):
                    geometry = create_point(float(lon), float(lat))
        
        if not geometry:
            skipped += 1
            continue
        
        # Get name
        name_cols = [c for c in df.columns if 'name' in c.lower() or 'language' in c.lower()]
        name = str(row.get(name_cols[0])) if name_cols else f"Language {idx}"
        
        # Get all properties
        properties = {}
        for col in df.columns:
            if col not in ['geometry'] and pd.notna(row.get(col)):
                properties[col.lower().replace(' ', '_')] = str(row.get(col))
        
        # Get centroid
        centroid_lon, centroid_lat = get_centroid(geometry)
        
        doc = {
            "name": name,
            "type": "indigenous_language",
            "properties": properties,
            "geometry": geometry,
            "centroid": {
                "type": "Point",
                "coordinates": [centroid_lon, centroid_lat]
            } if centroid_lon and centroid_lat else None,
            "metadata": {
                "source": "native_land_languages_canada_coords.xlsx",
                "loaded_at": datetime.utcnow(),
            }
        }
        
        documents.append(doc)
    
    print(f"Processed {len(documents)} valid documents ({skipped} skipped)")
    loader.bulk_insert(COLLECTIONS["indigenous_languages"], documents)
    loader.create_geospatial_index(COLLECTIONS["indigenous_languages"])


if __name__ == "__main__":
    loader = MongoDBLoader()
    
    try:
        load_indigenous_territories(loader)
        load_indigenous_treaties(loader)
        load_indigenous_languages(loader)
        
        print("\n" + "=" * 60)
        print("XLSX Data Loading Complete!")
        print("=" * 60)
        
    finally:
        loader.close()
