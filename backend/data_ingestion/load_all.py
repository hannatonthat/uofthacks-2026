"""
Main script to load all datasets into MongoDB
Run this to populate the database
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from data_ingestion.db_loader import MongoDBLoader
from data_ingestion.load_csv_data import (
    load_green_spaces,
    load_environmental_areas,
    load_first_nations,
    load_land_vulnerability
)
from data_ingestion.load_xlsx_data import (
    load_indigenous_territories,
    load_indigenous_treaties,
    load_indigenous_languages
)


def main():
    """Load all data into MongoDB"""
    print("\n" + "=" * 60)
    print("MONGODB DATA INGESTION - Indigenous Land Perspectives")
    print("=" * 60)
    
    loader = MongoDBLoader()
    
    try:
        # Load CSV data
        print("\n### LOADING CSV DATASETS ###\n")
        load_green_spaces(loader)
        load_environmental_areas(loader)
        load_first_nations(loader)
        load_land_vulnerability(loader)
        
        # Load XLSX data
        print("\n### LOADING XLSX DATASETS ###\n")
        load_indigenous_territories(loader)
        load_indigenous_treaties(loader)
        load_indigenous_languages(loader)
        
        # Print summary
        print("\n" + "=" * 60)
        print("DATABASE SUMMARY")
        print("=" * 60)
        
        from config import COLLECTIONS
        total_docs = 0
        
        for name, collection in COLLECTIONS.items():
            if name not in ["user_events", "user_preferences", "agent_sessions"]:
                stats = loader.get_stats(collection)
                print(f"{name:30} {stats['count']:>6} documents  {len(stats['indexes'])} indexes")
                total_docs += stats['count']
        
        print("=" * 60)
        print(f"TOTAL: {total_docs} documents loaded")
        print("=" * 60)
        print("\n[SUCCESS] All data loaded into MongoDB!")
        print(f"Database: {loader.db.name}")
        print(f"Connection: {loader.client.address}")
        
    except Exception as e:
        print(f"\n[ERROR] Data loading failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        loader.close()


if __name__ == "__main__":
    main()
