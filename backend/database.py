"""
MongoDB database connection for FastAPI
"""
from pymongo import MongoClient
from config import MONGODB_URI, MONGODB_DB, COLLECTIONS

# Global MongoDB client
_client = None
_db = None


def get_database():
    """Get MongoDB database instance"""
    global _client, _db
    
    if _db is None:
        _client = MongoClient(MONGODB_URI)
        _db = _client[MONGODB_DB]
        print(f"Connected to MongoDB: {MONGODB_DB}")
    
    return _db


def get_collection(collection_name):
    """Get a collection from the database"""
    db = get_database()
    return db[COLLECTIONS.get(collection_name, collection_name)]


def close_database():
    """Close MongoDB connection"""
    global _client
    if _client:
        _client.close()
        print("MongoDB connection closed")
