"""
MongoDB database loader utilities
"""
from pymongo import MongoClient, GEOSPHERE
from pymongo.errors import BulkWriteError
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))
from config import MONGODB_URI, MONGODB_DB, COLLECTIONS


class MongoDBLoader:
    """MongoDB connection and loading utilities"""
    
    def __init__(self):
        self.client = MongoClient(MONGODB_URI)
        self.db = self.client[MONGODB_DB]
        print(f"Connected to MongoDB: {MONGODB_DB}")
    
    def get_collection(self, collection_name):
        """Get a collection by name"""
        return self.db[collection_name]
    
    def create_geospatial_index(self, collection_name):
        """Create 2dsphere index on geometry field"""
        collection = self.get_collection(collection_name)
        try:
            collection.create_index([("geometry", GEOSPHERE)])
            print(f"[OK] Created 2dsphere index on {collection_name}")
        except Exception as e:
            print(f"[WARN] Index may already exist on {collection_name}: {e}")
    
    def bulk_insert(self, collection_name, documents, ordered=False):
        """Bulk insert documents with error handling"""
        if not documents:
            print(f"[SKIP] No documents to insert for {collection_name}")
            return 0
        
        collection = self.get_collection(collection_name)
        
        try:
            result = collection.insert_many(documents, ordered=ordered)
            count = len(result.inserted_ids)
            print(f"[OK] Inserted {count} documents into {collection_name}")
            return count
        except BulkWriteError as e:
            # Some documents inserted, some failed
            count = e.details.get('nInserted', 0)
            print(f"[PARTIAL] Inserted {count} documents into {collection_name}")
            print(f"[ERROR] {len(e.details.get('writeErrors', []))} documents failed")
            return count
        except Exception as e:
            print(f"[ERROR] Failed to insert into {collection_name}: {e}")
            return 0
    
    def upsert_documents(self, collection_name, documents, key_field="_id"):
        """Upsert documents (insert or update if exists)"""
        if not documents:
            print(f"[SKIP] No documents to upsert for {collection_name}")
            return 0
        
        collection = self.get_collection(collection_name)
        
        updated = 0
        inserted = 0
        
        for doc in documents:
            if key_field in doc:
                result = collection.replace_one(
                    {key_field: doc[key_field]},
                    doc,
                    upsert=True
                )
                if result.upserted_id:
                    inserted += 1
                else:
                    updated += 1
        
        print(f"[OK] {collection_name}: {inserted} inserted, {updated} updated")
        return inserted + updated
    
    def clear_collection(self, collection_name):
        """Clear all documents from a collection"""
        collection = self.get_collection(collection_name)
        result = collection.delete_many({})
        print(f"[OK] Cleared {result.deleted_count} documents from {collection_name}")
        return result.deleted_count
    
    def get_stats(self, collection_name):
        """Get collection statistics"""
        collection = self.get_collection(collection_name)
        count = collection.count_documents({})
        indexes = collection.index_information()
        return {"count": count, "indexes": list(indexes.keys())}
    
    def close(self):
        """Close MongoDB connection"""
        self.client.close()
        print("MongoDB connection closed")
