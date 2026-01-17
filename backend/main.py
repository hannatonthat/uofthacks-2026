"""
FastAPI Backend for Indigenous Land Perspectives
UofTHacks 2026
"""
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
import os

from database import get_database, close_database, get_collection
from utils.geo_queries import (
    find_near_point,
    find_all_near_point,
    find_containing_territory,
    find_in_bounds,
    calculate_sustainability_score,
    get_native_plants_for_territory,
    get_nearest_first_nation
)
from utils.grid_generator import get_data_points_for_map
from config import DEFAULT_RADIUS_METERS, GTA_BOUNDS

# Initialize FastAPI app
app = FastAPI(
    title="Indigenous Land Perspectives API",
    description="Backend API for UofTHacks 2026 - Interactive mapping with Indigenous perspectives",
    version="1.0.0"
)

# CORS middleware for frontend
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:3001").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models for request/response
class MapClickRequest(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    radius: Optional[int] = Field(DEFAULT_RADIUS_METERS, ge=100, le=5000)


class EventLog(BaseModel):
    event_type: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    data: Dict[str, Any]
    timestamp: Optional[datetime] = None


class UserPreferences(BaseModel):
    user_id: str
    interests: List[str] = []
    visited_regions: List[Dict[str, float]] = []
    favorite_territories: List[str] = []
    preferences: Dict[str, Any] = {}


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize database connection on startup"""
    get_database()
    print("FastAPI server started - MongoDB connected")


@app.on_event("shutdown")
async def shutdown_event():
    """Close database connection on shutdown"""
    close_database()
    print("FastAPI server shutdown - MongoDB disconnected")


# Health check
@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "ok",
        "message": "Indigenous Land Perspectives API",
        "version": "1.0.0",
        "database": "connected"
    }


# Map data endpoints
@app.get("/api/map/region/{lat}/{lon}")
async def get_region_data(
    lat: float,
    lon: float,
    radius: int = Query(DEFAULT_RADIUS_METERS, ge=100, le=5000)
):
    """
    Get all data near a clicked point on the map
    This is the main endpoint for map interactions
    """
    try:
        # Find all nearby data
        nearby_data = find_all_near_point(lon, lat, radius)
        
        # Find containing indigenous territory
        territory = find_containing_territory(lon, lat)
        
        # Calculate sustainability score (with error handling)
        try:
            sustainability = calculate_sustainability_score(lon, lat, radius)
        except Exception as e:
            print(f"Error calculating sustainability: {e}")
            sustainability = {
                "score": 5.0,
                "raw_score": 0,
                "max_score": 10,
                "breakdown": {}
            }
        
        # Get nearest First Nation community (with error handling)
        try:
            nearest_community = get_nearest_first_nation(lon, lat)
        except Exception as e:
            print(f"Error finding nearest First Nation: {e}")
            nearest_community = None
        
        return {
            "click_location": {"lat": lat, "lon": lon},
            "radius_meters": radius,
            "indigenous_territory": territory,
            "nearest_first_nation": nearest_community,
            "nearby_data": nearby_data,
            "sustainability_score": sustainability,
        }
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error querying region data: {str(e)}")


@app.get("/api/map/bounds")
async def get_map_bounds(
    min_lon: float = Query(...),
    min_lat: float = Query(...),
    max_lon: float = Query(...),
    max_lat: float = Query(...),
    layers: Optional[str] = Query(None, description="Comma-separated list of layers")
):
    """
    Get data within map viewport bounds
    Used for rendering visible map data
    """
    try:
        # Parse layers
        if layers:
            layer_list = layers.split(",")
        else:
            layer_list = ["green_spaces", "environmental_areas", "first_nations"]
        
        results = {}
        for layer in layer_list:
            try:
                data = find_in_bounds(layer, min_lon, min_lat, max_lon, max_lat, limit=500)
                results[layer] = data
            except Exception as e:
                print(f"Error loading layer {layer}: {e}")
                results[layer] = []
        
        return {
            "bounds": {
                "min_lon": min_lon,
                "min_lat": min_lat,
                "max_lon": max_lon,
                "max_lat": max_lat
            },
            "layers": results,
            "total_features": sum(len(v) for v in results.values())
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error querying bounds: {str(e)}")


@app.get("/api/map/layers")
async def get_available_layers():
    """Get list of available data layers"""
    return {
        "layers": [
            {"id": "green_spaces", "name": "Green Spaces", "type": "polygon"},
            {"id": "environmental_areas", "name": "Environmental Areas", "type": "polygon"},
            {"id": "first_nations", "name": "First Nations", "type": "point"},
            {"id": "indigenous_territories", "name": "Indigenous Territories", "type": "polygon"},
            {"id": "indigenous_treaties", "name": "Treaties", "type": "polygon"},
            {"id": "indigenous_languages", "name": "Languages", "type": "polygon"},
        ]
    }


@app.get("/api/map/points")
async def get_map_points(limit: int = Query(100, ge=10, le=200)):
    """
    Get interesting locations from actual data (fast!)
    Returns points from green spaces, environmental areas, and First Nations
    Detailed nearby data is fetched when user clicks a point
    
    Args:
        limit: Number of points to return (10-200)
    
    Returns:
        Sample of actual data locations
    """
    try:
        # Sample from actual data locations - FAST!
        points = get_data_points_for_map(limit=limit)
        
        return {
            "points": points,
            "total": len(points)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating map points: {str(e)}")


# Indigenous data endpoints (for AI agents)
@app.get("/api/indigenous/territory/{lat}/{lon}")
async def get_territory_at_point(lat: float, lon: float):
    """Get Indigenous territory at a specific point"""
    try:
        territory = find_containing_territory(lon, lat)
        if not territory:
            return {"found": False, "message": "No Indigenous territory found at this location"}
        
        return {
            "found": True,
            "territory": territory
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sustainability/analyze/{lat}/{lon}")
async def analyze_sustainability(
    lat: float,
    lon: float,
    radius: int = Query(1000, ge=100, le=5000)
):
    """Get sustainability analysis for a location"""
    try:
        score = calculate_sustainability_score(lon, lat, radius)
        territory = find_containing_territory(lon, lat)
        
        return {
            "sustainability": score,
            "territory": territory,
            "location": {"lat": lat, "lon": lon}
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/plants/native/{lat}/{lon}")
async def get_native_plants(lat: float, lon: float):
    """Get native plants for location's Indigenous territory"""
    try:
        territory = find_containing_territory(lon, lat)
        if not territory:
            # Return generic Ontario native plants
            plants = get_native_plants_for_territory("Ontario")
        else:
            plants = get_native_plants_for_territory(territory.get("name"))
        
        return {
            "territory": territory.get("name") if territory else "Ontario (general)",
            "native_plants": plants
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Event tracking endpoints (for Amplitude prize)
@app.post("/api/events")
async def log_event(event: EventLog):
    """Log a user interaction event (for Amplitude analytics)"""
    try:
        collection = get_collection("user_events")
        
        event_doc = {
            "event_type": event.event_type,
            "user_id": event.user_id,
            "session_id": event.session_id,
            "data": event.data,
            "timestamp": event.timestamp or datetime.utcnow()
        }
        
        result = collection.insert_one(event_doc)
        
        return {
            "success": True,
            "event_id": str(result.inserted_id)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error logging event: {str(e)}")


@app.get("/api/events/{user_id}")
async def get_user_events(
    user_id: str,
    limit: int = Query(100, ge=1, le=1000),
    event_type: Optional[str] = None
):
    """Get events for a user (for AI personalization)"""
    try:
        collection = get_collection("user_events")
        
        query = {"user_id": user_id}
        if event_type:
            query["event_type"] = event_type
        
        events = list(collection.find(query).sort("timestamp", -1).limit(limit))
        
        # Convert ObjectId to string
        for event in events:
            event["_id"] = str(event["_id"])
        
        return {
            "user_id": user_id,
            "events": events,
            "count": len(events)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# User preferences endpoints (for Backboard memory)
@app.post("/api/user/{user_id}/preferences")
async def save_user_preferences(user_id: str, preferences: UserPreferences):
    """Save user preferences (for AI memory/personalization)"""
    try:
        collection = get_collection("user_preferences")
        
        pref_doc = {
            "user_id": user_id,
            "interests": preferences.interests,
            "visited_regions": preferences.visited_regions,
            "favorite_territories": preferences.favorite_territories,
            "preferences": preferences.preferences,
            "updated_at": datetime.utcnow()
        }
        
        # Upsert (update or insert)
        result = collection.replace_one(
            {"user_id": user_id},
            pref_doc,
            upsert=True
        )
        
        return {
            "success": True,
            "user_id": user_id,
            "updated": result.modified_count > 0,
            "inserted": result.upserted_id is not None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/user/{user_id}/preferences")
async def get_user_preferences(user_id: str):
    """Get user preferences"""
    try:
        collection = get_collection("user_preferences")
        
        prefs = collection.find_one({"user_id": user_id})
        
        if not prefs:
            return {
                "found": False,
                "user_id": user_id,
                "preferences": {}
            }
        
        prefs["_id"] = str(prefs["_id"])
        
        return {
            "found": True,
            "user_id": user_id,
            "preferences": prefs
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Helper functions removed - no AI recommendations yet


# Run server
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=True
    )
