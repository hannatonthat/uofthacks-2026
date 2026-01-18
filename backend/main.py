"""
FastAPI Backend for Indigenous Land Perspectives
UofTHacks 2026
"""
from fastapi import FastAPI, HTTPException, Query, UploadFile, File, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
import os
import uuid
import shutil
import requests
import numpy as np
from PIL import Image
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor

from agents.specialized_agents import SustainabilityAgent, IndigenousContextAgent, ProposalWorkflowAgent
from agents.confirmation_service import ConfirmationService, ActionType

from database import get_database, close_database, get_collection
from utils.geo_queries import (
    find_near_point,
    find_all_near_point,
    find_containing_territory,
    find_in_bounds,
    calculate_ecological_sensitivity_score,
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


# Thread storage for agent chats
threads: Dict[str, Dict] = {}
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Mount static files directory to serve uploaded images
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


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


class ChatRequest(BaseModel):
    """Request body for chat endpoints."""
    agent: Optional[str] = None  # Required for create-chat, optional for start-chat
    message: Optional[str] = None  # Optional for create endpoints
    image_path: Optional[str] = None  # Optional image path for sustainability agent
    user_id: Optional[str] = None  # For personalization


class RatingRequest(BaseModel):
    """Request body for rating agent responses."""
    user_id: str
    thread_id: str
    agent_type: str
    message_index: int
    rating: int  # 1 for thumbs up, -1 for thumbs down
    context: Dict[str, Any]


class ChatResponse(BaseModel):
    """Response body for chat endpoints."""
    thread_id: str
    agent: str
    user_message: str
    assistant_response: str
    vision_path: Optional[str] = None
    original_image_path: Optional[str] = None
    vision_url: Optional[str] = None
    original_image_url: Optional[str] = None
    vision_path: Optional[str] = None
    original_image_path: Optional[str] = None


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
        
        # Calculate ecological sensitivity score with detailed metrics
        try:
            ecological_score = calculate_ecological_sensitivity_score(lon, lat, radius)
        except Exception as e:
            print(f"Error calculating ecological score: {e}")
            ecological_score = {
                "total_score": 0,
                "normalized_score": 0,
                "max_score": 30,
                "metrics": {},
                "rule_compliance": {}
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
            "ecological_score": ecological_score,
            "sustainability_score": ecological_score,  # Keep for backward compatibility
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


# Agent chat endpoints (merged from api.py)
# In-memory storage for agents and confirmations
workflow_agents = {}  # {thread_id: ProposalWorkflowAgent}
confirmation_service = ConfirmationService()  # Global confirmation service

@app.post("/create-chat")
def create_chat(request: ChatRequest) -> ChatResponse:
    """Create a new chat thread with the specified agent."""
    if not request.agent:
        raise HTTPException(status_code=400, detail="agent field is required for create-chat")
    
    thread_id = str(uuid.uuid4())

    # Initialize the appropriate agent with user_id for personalization
    user_id = request.user_id
    
    if request.agent.lower() == "sustainability":
        agent = SustainabilityAgent(user_id=user_id)
    elif request.agent.lower() == "indigenous":
        agent = IndigenousContextAgent(user_id=user_id)
    elif request.agent.lower() == "proposal":
        agent = ProposalWorkflowAgent(user_id=user_id)
    else:
        raise HTTPException(status_code=400, detail="Invalid agent. Use 'sustainability', 'indigenous', or 'proposal'")

    # Store agent in thread storage with image path if provided
    thread_data = {"agent": agent, "image_path": request.image_path}
    threads[thread_id] = thread_data

    # Use provided message or agent-specific default
    user_message = request.message
    if not user_message:
        if request.agent.lower() == "sustainability":
            user_message = "Generate initial redesign ideas"
        elif request.agent.lower() == "indigenous":
            user_message = "What are the key indigenous perspectives to consider?"
        elif request.agent.lower() == "proposal":
            user_message = "What are the steps in the proposal workflow?"
    
    # Send the first user message to the model immediately
    agent.add_message("user", user_message)

    vision_path = None
    try:
        # Call appropriate chat method based on agent type
        if request.agent.lower() == "sustainability":
            # If image provided, run full analysis with vision generation
            if request.image_path:
                vision_output_path = f"{UPLOAD_DIR}/vision_{thread_id}_initial.png"
                analysis_result = agent.run_full_analysis(
                    request.image_path,
                    context=user_message,
                    vision_output_path=vision_output_path
                )
                thread_data["vision_path"] = analysis_result.get("future_vision_path")
                vision_path = analysis_result.get("future_vision_path")
                
                # Build response from analysis
                response = f"Analysis complete.\n\nSuggestions:\n" + "\n".join(
                    analysis_result.get("redesign_suggestions", [])
                )
            else:
                response = agent.chat_with_context(user_message, context="")
        else:
            # Indigenous and Proposal agents don't accept context parameter
            response = agent.chat_with_context(user_message)
    except Exception as e:
        response = f"Agent initialized but model call failed: {str(e)}"

    agent.add_message("assistant", response)

    return ChatResponse(
        thread_id=thread_id,
        agent=request.agent,
        user_message=user_message,
        assistant_response=response,
        vision_path=vision_path,
    )


@app.post("/start-chat")
def start_chat(threadid: str = Query(...), request: ChatRequest = Body(...)) -> ChatResponse:
    """Start a new message in an existing thread."""
    if threadid not in threads:
        raise HTTPException(status_code=404, detail=f"Thread {threadid} not found")
    
    if not request or not request.message:
        raise HTTPException(status_code=400, detail="Request body with 'message' field required")

    thread_data = threads[threadid]
    agent = thread_data["agent"]
    image_path = thread_data.get("image_path")

    agent.add_message("user", request.message)
    agent_name = type(agent).__name__
    vision_path = None

    try:
        if agent_name == "SustainabilityAgent":
            # Run full analysis with image generation if image exists
            if image_path:
                import time
                vision_output_path = f"{UPLOAD_DIR}/vision_{threadid}_{int(time.time())}.png"
                analysis_result = agent.run_full_analysis(
                    image_path,
                    context=request.message,
                    vision_output_path=vision_output_path
                )
                thread_data["vision_path"] = analysis_result.get("future_vision_path")
                vision_path = analysis_result.get("future_vision_path")
                
                # Build response from analysis
                response = f"Analysis complete.\n\nSuggestions:\n" + "\n".join(
                    analysis_result.get("redesign_suggestions", [])
                )
            else:
                context = f"Image path: {image_path}" if image_path else ""
                response = agent.chat_with_context(request.message, context=context)
        elif agent_name == "IndigenousContextAgent":
            response = agent.chat_with_context(request.message)
        elif agent_name == "ProposalWorkflowAgent":
            response = agent.chat_with_context(request.message)
        else:
            response = f"Response from {agent_name}"
    except Exception as e:
        response = f"Error: {str(e)}"

    agent.add_message("assistant", response)

    return ChatResponse(
        thread_id=threadid,
        agent=agent_name,
        user_message=request.message,
        assistant_response=response,
        vision_path=vision_path,
    )


@app.post("/add-chat")
def add_chat(threadid: str = Query(...), request: ChatRequest = Body(...)) -> ChatResponse:
    """Add a message to an existing thread (alias for /start-chat)."""
    return start_chat(threadid=threadid, request=request)


@app.post("/upload-image")
def upload_image(threadid: str = Query(...), file: UploadFile = File(...)):
    """Upload an image to be used with a Sustainability agent thread."""
    if threadid not in threads:
        raise HTTPException(status_code=404, detail=f"Thread {threadid} not found")

    thread_data = threads[threadid]
    agent = thread_data["agent"]

    if type(agent).__name__ != "SustainabilityAgent":
        raise HTTPException(status_code=400, detail="Image upload only supported for Sustainability agent")

    try:
        file_path = f"{UPLOAD_DIR}/{threadid}_{file.filename}"
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        thread_data["image_path"] = file_path

        vision_path = f"{UPLOAD_DIR}/vision_{threadid}_{file.filename}"
        agent.generate_future_vision(file_path, vision_path)

        return {
            "thread_id": threadid,
            "status": "success",
            "original_image": file_path,
            "vision_image": vision_path,
            "message": "Image uploaded and sustainable vision generated!"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")


@app.get("/threads")
def list_threads():
    """List all active threads."""
    return {
        "total_threads": len(threads),
        "thread_ids": list(threads.keys()),
    }


@app.get("/thread/{threadid}")
def get_thread(threadid: str):
    """Get conversation history for a thread."""
    if threadid not in threads:
        raise HTTPException(status_code=404, detail=f"Thread {threadid} not found")

    thread_data = threads[threadid]
    agent = thread_data["agent"]
    image_path = thread_data.get("image_path")

    return {
        "thread_id": threadid,
        "agent": type(agent).__name__,
        "image_path": image_path,
        "conversation_history": getattr(agent, "_history", []),
    }


@app.delete("/thread/{threadid}")
def delete_thread(threadid: str):
    """Delete a thread."""
    if threadid not in threads:
        raise HTTPException(status_code=404, detail=f"Thread {threadid} not found")

    thread_data = threads[threadid]
    agent = thread_data["agent"]
    agent_name = type(agent).__name__
    image_path = thread_data.get("image_path")

    if image_path and os.path.exists(image_path):
        os.remove(image_path)

    del threads[threadid]

    return {
        "message": f"Thread {threadid} deleted",
        "agent": agent_name,
    }


# Sustainability-specific endpoints

@app.get("/generate-panorama")
def generate_panorama(
    lat: float = Query(..., ge=-90, le=90, description="Latitude"),
    lon: float = Query(..., ge=-180, le=180, description="Longitude"),
    num_directions: int = Query(4, ge=1, le=16, description="Number of Street View directions to stitch"),
    pitch: int = Query(0, ge=-90, le=90, description="Camera pitch (-90 to 90)"),
    size: str = Query("600x400", description="Image size (widthxheight)"),
) -> Dict[str, str]:
    """Generate a 360° panorama from Street View images at given lat/lon, optimized for sustainable vision generation."""
    try:
        api_key = os.getenv("GOOGLE_API_MAP_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="GOOGLE_API_MAP_KEY not set in environment")
        
        headings = np.linspace(0, 360, num_directions, endpoint=False)
        images_list = []
        
        def fetch_image(heading):
            try:
                url = f"https://maps.googleapis.com/maps/api/streetview?size={size}&location={lat},{lon}&heading={heading}&pitch={pitch}&radius=50&key={api_key}"
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    return int(heading), Image.open(BytesIO(response.content))
            except Exception as e:
                print(f"  Error loading {heading}°: {e}")
            return None, None
        
        print(f"Fetching {num_directions} Street View images for panorama at {lat},{lon}...")
        
        # Fetch all images in parallel
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(fetch_image, heading) for heading in headings]
            results = []
            for future in futures:
                try:
                    heading, img = future.result(timeout=15)
                    if img:
                        results.append((heading, img))
                        print(f"  Loaded {heading}°")
                except Exception as e:
                    print(f"  Failed to load image: {e}")
        
        if not results:
            raise HTTPException(status_code=500, detail="Failed to fetch Street View images for this location")
        
        # Sort by heading and extract images
        results.sort(key=lambda x: x[0])
        images_list = [img for _, img in results]
        
        # Stitch images horizontally into panorama
        total_width = sum(img.width for img in images_list)
        max_height = images_list[0].height
        
        panorama = Image.new('RGB', (total_width, max_height))
        x_offset = 0
        for img in images_list:
            panorama.paste(img, (x_offset, 0))
            x_offset += img.width
        
        # Save panorama
        panorama_id = str(uuid.uuid4())
        panorama_path = f"{UPLOAD_DIR}/panorama_{panorama_id}.png"
        panorama.save(panorama_path)
        
        print(f"[OK] Panorama generated: {panorama_path} ({total_width}x{max_height})")
        
        return {
            "panorama_path": panorama_path,
            "panorama_id": panorama_id,
            "dimensions": f"{total_width}x{max_height}",
            "location": f"{lat},{lon}",
            "message": "Panorama generated successfully. Use panorama_path to view or pass to /create-sustainability-chat"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating panorama: {str(e)}")
def generate_panorama(
    lat: float = Query(..., ge=-90, le=90, description="Latitude"),
    lon: float = Query(..., ge=-180, le=180, description="Longitude"),
    num_directions: int = Query(4, ge=1, le=16, description="Number of Street View directions to stitch"),
    pitch: int = Query(0, ge=-90, le=90, description="Camera pitch (-90 to 90)"),
    size: str = Query("600x400", description="Image size (widthxheight)"),
) -> Dict[str, str]:
    """Generate a 360° panorama from Street View images at given lat/lon, optimized for sustainable vision generation."""
    try:
        api_key = os.getenv("GOOGLE_API_MAP_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="GOOGLE_API_MAP_KEY not set in environment")
        
        headings = np.linspace(0, 360, num_directions, endpoint=False)
        images_list = []
        
        def fetch_image(heading):
            try:
                url = f"https://maps.googleapis.com/maps/api/streetview?size={size}&location={lat},{lon}&heading={heading}&pitch={pitch}&radius=50&key={api_key}"
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    return int(heading), Image.open(BytesIO(response.content))
            except Exception as e:
                print(f"  Error loading {heading}°: {e}")
            return None, None
        
        print(f"Fetching {num_directions} Street View images for panorama at {lat},{lon}...")
        
        # Fetch all images in parallel
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(fetch_image, heading) for heading in headings]
            results = []
            for future in futures:
                try:
                    heading, img = future.result(timeout=15)
                    if img:
                        results.append((heading, img))
                        print(f"  Loaded {heading}°")
                except Exception as e:
                    print(f"  Failed to load image: {e}")
        
        if not results:
            raise HTTPException(status_code=500, detail="Failed to fetch Street View images for this location")
        
        # Sort by heading and extract images
        results.sort(key=lambda x: x[0])
        images_list = [img for _, img in results]
        
        # Stitch images horizontally into panorama
        total_width = sum(img.width for img in images_list)
        max_height = images_list[0].height
        
        panorama = Image.new('RGB', (total_width, max_height))
        x_offset = 0
        for img in images_list:
            panorama.paste(img, (x_offset, 0))
            x_offset += img.width
        
        # Save panorama
        panorama_id = str(uuid.uuid4())
        panorama_path = f"{UPLOAD_DIR}/panorama_{panorama_id}.png"
        panorama.save(panorama_path)
        
        print(f"[OK] Panorama generated: {panorama_path} ({total_width}x{max_height})")
        
        return {
            "panorama_path": panorama_path,
            "panorama_id": panorama_id,
            "dimensions": f"{total_width}x{max_height}",
            "location": f"{lat},{lon}",
            "message": "Panorama generated successfully. Use this path with /create-sustainability-chat"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating panorama: {str(e)}")


@app.post("/create-sustainability-chat")
def create_sustainability_chat(request: ChatRequest) -> ChatResponse:
    """Create a new sustainability chat thread and run full analysis if image provided."""
    if request.agent.lower() != "sustainability":
        raise HTTPException(status_code=400, detail="This endpoint is for sustainability agent only")
    
    thread_id = str(uuid.uuid4())
    agent = SustainabilityAgent(user_id=request.user_id)
    thread_data = {"agent": agent, "image_path": request.image_path}
    threads[thread_id] = thread_data

    # Use provided message or default
    user_message = request.message or "Generate initial redesign ideas"
    
    # Send the first user message to the model immediately
    agent.add_message("user", user_message)
    
    try:
        # If image_path provided, run full analysis pipeline
        if request.image_path:
            vision_output_path = f"{UPLOAD_DIR}/vision_{thread_id}_generated.png"
            analysis_result = agent.run_full_analysis(
                request.image_path,
                context=user_message,
                vision_output_path=vision_output_path
            )
            thread_data["image_path"] = request.image_path
            
            # Only set vision_path if file actually exists
            future_vision = analysis_result.get("future_vision_path")
            if future_vision and os.path.exists(future_vision):
                thread_data["vision_path"] = future_vision
            else:
                thread_data["vision_path"] = None
                print(f"Vision generation failed or file not created: {future_vision}")
            
            # Build response from analysis
            suggestions = analysis_result.get("redesign_suggestions", [])
            if suggestions:
                response = f"Analysis complete.\n\nSuggestions:\n" + "\n".join(suggestions)
            else:
                response = "Analysis complete. I can provide suggestions for sustainable improvements. What aspects would you like me to focus on?"
        else:
            # No image, just chat
            context = f"Image path: {request.image_path}" if request.image_path else ""
            response = agent.chat_with_context(user_message, context=context)
    except Exception as e:
        response = f"Agent initialized but model call failed: {str(e)}"

    agent.add_message("assistant", response)

    # Return raw file paths - frontend constructs URLs as needed
    vision_path_return = thread_data.get("vision_path")
    original_path_return = thread_data.get("image_path")
    
    return ChatResponse(
        thread_id=thread_id,
        agent="sustainability",
        user_message=user_message,
        assistant_response=response,
        vision_path=vision_path_return,
        original_image_path=original_path_return,
        vision_url=vision_path_return,
        original_image_url=original_path_return,
    )


@app.post("/add-sustainability-chat")
def add_sustainability_chat(threadid: str = Query(...), request: ChatRequest = Body(...)) -> ChatResponse:
    """Add a message to an existing sustainability thread and optionally regenerate vision using latest image."""
    if threadid not in threads:
        raise HTTPException(status_code=404, detail=f"Thread {threadid} not found")

    if not request.message:
        raise HTTPException(status_code=400, detail="message field is required for add-sustainability-chat")

    thread_data = threads[threadid]
    agent = thread_data["agent"]

    if type(agent).__name__ != "SustainabilityAgent":
        raise HTTPException(status_code=400, detail="Thread is not a sustainability agent thread")

    # Override image_path if provided in request
    if request.image_path:
        thread_data["image_path"] = request.image_path
    
    # Use the latest vision image if available, otherwise use original image_path
    image_to_use = thread_data.get("vision_path") or thread_data.get("image_path")

    agent.add_message("user", request.message)

    try:
        # If image exists (original or latest vision), run full analysis pipeline
        if image_to_use:
            vision_output_path = f"{UPLOAD_DIR}/vision_{threadid}_{int(__import__('time').time())}.png"
            analysis_result = agent.run_full_analysis(
                image_to_use,
                context=request.message,
                vision_output_path=vision_output_path
            )
            
            # Only set vision_path if file actually exists
            future_vision = analysis_result.get("future_vision_path")
            if future_vision and os.path.exists(future_vision):
                thread_data["vision_path"] = future_vision
            else:
                thread_data["vision_path"] = None
                print(f"Vision generation failed or file not created: {future_vision}")
            
            # Build response from analysis
            suggestions = analysis_result.get("redesign_suggestions", [])
            if suggestions:
                response = f"Updated analysis.\n\nSuggestions:\n" + "\n".join(suggestions)
            else:
                response = "I can help improve this location. What specific changes would you like to see?"
        else:
            # No image, just chat
            response = agent.chat_with_context(request.message, context="")
    except Exception as e:
        response = f"Error: {str(e)}"

    agent.add_message("assistant", response)

    # Return raw file paths - frontend constructs URLs as needed
    vision_path_return = thread_data.get("vision_path")
    original_path_return = thread_data.get("image_path")

    return ChatResponse(
        thread_id=threadid,
        agent="sustainability",
        user_message=request.message,
        assistant_response=response,
        vision_path=vision_path_return,
        original_image_path=original_path_return,
        vision_url=vision_path_return,
        original_image_url=original_path_return,
    )


# ============================================================================
# WORKFLOW ENDPOINTS WITH CONFIRMATION SYSTEM
# ============================================================================

class ProposalGenerationRequest(BaseModel):
	"""Request body for generating a proposal from indigenous context."""
	location: str  # e.g., "Traditional Haudenosaunee Territory, Southern Ontario"
	land_use: str  # e.g., "Forest Management", "Water Conservation"
	objectives: Optional[str] = None  # e.g., "Sustainable harvesting practices"
	timeframe: Optional[str] = None  # e.g., "5-year plan"


@app.post("/workflow/generate-proposal")
def generate_indigenous_proposal(request: ProposalGenerationRequest):
	"""
	Generate a proposal from indigenous perspectives and land context.
	
	Uses IndigenousContextAgent to create a culturally-informed proposal
	that respects indigenous sovereignty and land stewardship principles.
	
	PARAMETERS:
	  location: Geographic location/territory
	  land_use: Type of land use or initiative
	  objectives: Specific goals for the proposal
	  timeframe: Duration or timeline for implementation
	
	RETURNS:
	  {
	    "status": "success",
	    "proposal_title": "Generated title respecting indigenous context",
	    "proposal_content": "Full proposal text",
	    "recommendations": ["List of", "indigenous-informed", "recommendations"]
	  }
	"""
	try:
		# Create indigenous context agent
		indigenous_agent = IndigenousContextAgent(
			base_prompt="Generate respectful, indigenous-informed proposals that prioritize tribal sovereignty and land stewardship."
		)
		
		# Build context-aware prompt
		context_prompt = (
			f"Generate a comprehensive proposal for {request.land_use} "
			f"in/at {request.location}. "
		)
		
		if request.objectives:
			context_prompt += f"Objectives: {request.objectives}. "
		
		if request.timeframe:
			context_prompt += f"Timeframe: {request.timeframe}. "
		
		context_prompt += (
			"The proposal should: "
			"1. Center indigenous sovereignty and traditional land management practices "
			"2. Include consultation with local indigenous communities "
			"3. Respect ecological systems and sacred sites "
			"4. Align with long-term stewardship principles "
			"5. Include measurable outcomes that benefit both land and community. "
			"Format as: TITLE, OVERVIEW, KEY OBJECTIVES, IMPLEMENTATION PLAN, COMMUNITY BENEFITS, MEASUREMENT & ACCOUNTABILITY"
		)
		
		# Generate proposal via indigenous agent
		proposal_content = indigenous_agent.chat_with_context(context_prompt)
		
		# Extract title from proposal (first line usually)
		lines = proposal_content.split('\n')
		proposal_title = lines[0] if lines else f"{request.land_use} Initiative - {request.location}"
		
		# Extract key recommendations
		recommendations = []
		if "COMMUNITY BENEFITS" in proposal_content:
			benefits_section = proposal_content.split("COMMUNITY BENEFITS")[1]
			benefit_lines = [line.strip() for line in benefits_section.split('\n') if line.strip() and line.strip().startswith('-')]
			recommendations = [line[1:].strip() for line in benefit_lines[:5]]
		
		return {
			"status": "success",
			"proposal_title": proposal_title,
			"proposal_content": proposal_content,
			"recommendations": recommendations if recommendations else [
				"Centered indigenous sovereignty",
				"Community-led decision making",
				"Ecological stewardship",
				"Long-term sustainability",
				"Cultural respect and protocols"
			],
			"metadata": {
				"location": request.location,
				"land_use": request.land_use,
				"objectives": request.objectives,
				"timeframe": request.timeframe
			}
		}
	
	except Exception as e:
		return {
			"status": "error",
			"message": f"Failed to generate proposal: {str(e)}",
			"error": str(e)
		}


@app.post("/workflow/generate-action-plan")
def generate_workflow_action_plan(request: ProposalGenerationRequest):
	"""
	Generate a complete workflow action plan with contacts, emails, meetings, and notifications.
	
	This endpoint:
	1. Generates an indigenous-informed proposal
	2. Identifies key stakeholders to contact
	3. Creates draft emails for outreach
	4. Suggests meetings to schedule
	5. Prepares Slack notifications for team coordination
	6. Provides a workflow summary
	
	PARAMETERS:
	  location: Geographic location/territory
	  land_use: Type of land use or initiative
	  objectives: Specific goals for the proposal
	  timeframe: Duration or timeline for implementation
	
	RETURNS:
	  Complete action plan with contacts, emails, meetings, and notifications
	"""
	try:
		# Step 1: Generate the proposal
		indigenous_agent = IndigenousContextAgent(
			base_prompt="Generate respectful, indigenous-informed proposals that prioritize tribal sovereignty and land stewardship."
		)
		
		context_prompt = (
			f"Generate a comprehensive proposal for {request.land_use} "
			f"in/at {request.location}. "
		)
		
		if request.objectives:
			context_prompt += f"Objectives: {request.objectives}. "
		
		if request.timeframe:
			context_prompt += f"Timeframe: {request.timeframe}. "
		
		context_prompt += (
			"The proposal should: "
			"1. Center indigenous sovereignty and traditional land management practices "
			"2. Include consultation with local indigenous communities "
			"3. Respect ecological systems and sacred sites "
			"4. Align with long-term stewardship principles "
			"5. Include measurable outcomes that benefit both land and community. "
			"Format as: TITLE, OVERVIEW, KEY OBJECTIVES, IMPLEMENTATION PLAN, COMMUNITY BENEFITS, MEASUREMENT & ACCOUNTABILITY"
		)
		
		proposal_content = indigenous_agent.chat_with_context(context_prompt)
		lines = proposal_content.split('\n')
		proposal_title = lines[0].strip().replace('#', '').strip() if lines else f"{request.land_use} Initiative - {request.location}"
		
		# Step 2: Generate stakeholder contacts WITH emails
		stakeholder_prompt = (
			f"For the proposal '{proposal_title}' at {request.location}, identify 3-5 key stakeholders "
			f"who should be consulted. For each person, provide: Role/Title, Reason for consultation, and a realistic email address. "
			f"Focus on: Indigenous leaders, Land council members, Environmental officers, Community elders. "
			f"Use realistic format like firstname.lastname@organization.ca or similar. "
			f"Format as: ROLE | REASON | EMAIL (one per line)"
		)
		
		stakeholder_response = indigenous_agent.chat_with_context(stakeholder_prompt)
		
		# Parse stakeholders with emails
		suggested_contacts = []
		for line in stakeholder_response.split('\n'):
			if '|' in line:
				parts = line.split('|')
				if len(parts) >= 3:
					email = parts[2].strip() if parts[2].strip() else "contact@example.com"
					suggested_contacts.append({
						"role": parts[0].strip(),
						"reason": parts[1].strip(),
						"email": email,
						"suggested_email": email
					})
				elif len(parts) >= 2:
					suggested_contacts.append({
						"role": parts[0].strip(),
						"reason": parts[1].strip(),
						"email": "contact@example.com",
						"suggested_email": "contact@example.com"
					})
		
		# Step 3: Generate email drafts to nuthanan06@gmail.com (demo only)
		workflow_agent = ProposalWorkflowAgent()
		email_drafts = []
		
		# Step 3a: Gather context from sustainability and indigenous agents
		sustainability_context = ""
		indigenous_context = ""
		
		# Create sustainability agent to get context
		try:
			sustainability_agent = SustainabilityAgent(
				base_prompt="Analyze this location for sustainable development opportunities."
			)
			sust_response = sustainability_agent.chat_with_context(
				f"Provide key sustainability insights for {request.land_use} at {request.location} in 2-3 sentences."
			)
			sustainability_context = sust_response[:300] if sust_response else ""
		except Exception as e:
			print(f"Could not get sustainability context: {e}")
		
		# Create indigenous context agent to get insights
		try:
			indg_agent = IndigenousContextAgent(
				base_prompt="Provide indigenous perspectives on sustainable development."
			)
			indg_response = indg_agent.chat_with_context(
				f"What are the key indigenous considerations for {request.land_use} at {request.location}? 2-3 sentences."
			)
			indigenous_context = indg_response[:300] if indg_response else ""
		except Exception as e:
			print(f"Could not get indigenous context: {e}")
		
		# Combine contexts for email enhancement
		combined_context = f"Sustainability insights: {sustainability_context}\nIndigenous perspectives: {indigenous_context}"
		
		for contact in suggested_contacts[:3]:  # Limit to 3 for demo
			try:
				email_content = workflow_agent.generate_outreach_email(
					contact_name=contact['role'],
					proposal_title=proposal_title,
					context=combined_context
				)
				email_drafts.append({
					"to": "nuthanan06@gmail.com",  # Demo: Send to your email only
					"subject": f"Consultation Request: {proposal_title} - {contact['role']}",
					"body": email_content,
					"reason": contact['reason'],
					"stakeholder_role": contact['role'],
					"stakeholder_email": contact['email'],  # Show what it would be
					"note": "DEMO: Sending to nuthanan06@gmail.com to avoid emailing random addresses"
				})
			except Exception as e:
				print(f"Email generation skipped: {e}")
		
		# Step 4: Generate at least 1 meeting
		meeting_suggestions = [
			{
				"title": f"Initial Consultation - {proposal_title}",
				"description": f"Kick-off meeting to discuss {request.land_use} initiative with indigenous leaders and community representatives",
				"attendees": [c['role'] for c in suggested_contacts[:2]],
				"duration_minutes": 60,
				"purpose": "Introduce proposal, gather initial feedback from key stakeholders, establish communication protocols and partnership agreements"
			}
		]
		
		# Add optional second meeting if multiple stakeholders
		if len(suggested_contacts) > 2:
			meeting_suggestions.append({
				"title": f"Community Feedback Session - {proposal_title}",
				"description": f"Open session for broader community input on {request.land_use} proposal",
				"attendees": ["Community Members", "Elders", "Youth Representatives"],
				"duration_minutes": 90,
				"purpose": "Collect community perspectives, address concerns, refine proposal based on traditional knowledge and feedback"
			})
		
		# Step 5: Generate Slack notifications (third component)
		slack_notifications = [
			{
				"channel": "#indigenous-initiatives",
				"message": f"📢 New Proposal Generated: {proposal_title}\n"
						  f"Location: {request.location}\n"
						  f"Focus: {request.land_use}\n"
						  f"Key Stakeholders: {', '.join([c['role'] for c in suggested_contacts[:3]])}\n"
						  f"Next Steps: Review proposal and schedule initial consultations",
				"priority": "high"
			},
			{
				"channel": "#team-planning",
				"message": f"🤝 Team Meeting Needed\n"
						  f"Topic: Planning outreach strategy for {proposal_title}\n"
						  f"Stakeholders identified: {len(suggested_contacts)}\n"
						  f"Action: Coordinate roles and timeline for community engagement",
				"priority": "medium"
			}
		]
		
		# Step 6: Generate workflow summary
		workflow_summary = {
			"proposal_title": proposal_title,
			"location": request.location,
			"land_use": request.land_use,
			"status": "Draft - Awaiting Community Consultation",
			"next_steps": [
				f"1. Review proposal content with internal team",
				f"2. Contact {len(suggested_contacts)} identified stakeholders",
				f"3. Schedule {len(meeting_suggestions)} consultation meetings",
				f"4. Send {len(email_drafts)} outreach emails",
				f"5. Post {len(slack_notifications)} team notifications",
				f"6. Gather community feedback and iterate on proposal"
			],
			"timeline": request.timeframe or "To be determined based on community input",
			"key_principles": [
				"Indigenous sovereignty",
				"Community-led decision making",
				"Ecological stewardship",
				"Cultural respect and protocols"
			]
		}
		
		return {
			"status": "success",
			"proposal": {
				"title": proposal_title,
				"content": proposal_content,
				"location": request.location,
				"land_use": request.land_use
			},
			"contacts": {
				"count": len(suggested_contacts),
				"suggested_stakeholders": suggested_contacts
			},
			"emails": {
				"count": len(email_drafts),
				"drafts": email_drafts
			},
			"meetings": {
				"count": len(meeting_suggestions),
				"suggested_meetings": meeting_suggestions
			},
			"notifications": {
				"count": len(slack_notifications),
				"slack_messages": slack_notifications
			},
			"workflow_summary": workflow_summary
		}
	
	except Exception as e:
		return {
			"status": "error",
			"message": f"Failed to generate action plan: {str(e)}",
			"error": str(e)
		}


class ContactRequest(BaseModel):
    """Request body for adding a contact."""
    name: str
    role: str
    email: str
    phone: Optional[str] = None


class WorkflowRequest(BaseModel):
    """Request body for workflow actions."""
    proposal_title: str
    event_type_name: Optional[str] = None  # For scheduling meetings


class ConfirmationRequest(BaseModel):
    """Request body for confirming/rejecting actions."""
    action_id: str
    approved: bool


@app.post("/workflow/add-contact")
def add_workflow_contact(
    threadid: str = Query(..., description="Thread ID for the workflow agent"),
    contact: ContactRequest = Body(...)
):
    """Add a contact to the workflow agent's contact list."""
    # Get or create workflow agent for this thread
    if threadid not in workflow_agents:
        workflow_agents[threadid] = ProposalWorkflowAgent()
    
    agent = workflow_agents[threadid]
    
    # Add contact
    result = agent.add_contact(
        name=contact.name,
        role=contact.role,
        email=contact.email,
        phone=contact.phone
    )
    
    return {
        "status": "success",
        "message": result,
        "thread_id": threadid,
        "contact": {
            "name": contact.name,
            "role": contact.role,
            "email": contact.email,
            "phone": contact.phone
        }
    }


@app.get("/workflow/contacts")
def get_workflow_contacts(threadid: str = Query(..., description="Thread ID for the workflow agent")):
    """Get all contacts for the specified workflow thread."""
    if threadid not in workflow_agents:
        return {
            "status": "success",
            "thread_id": threadid,
            "contacts": [],
            "count": 0
        }
    
    agent = workflow_agents[threadid]
    contacts = agent.get_contacts()
    
    return {
        "status": "success",
        "thread_id": threadid,
        "contacts": contacts,
        "count": len(contacts)
    }


@app.post("/workflow/send-emails")
def workflow_send_emails(
    threadid: str = Query(..., description="Thread ID for the workflow agent"),
    request: WorkflowRequest = Body(...)
):
    """
    Send outreach emails to all contacts.
    Requires confirmation before actual execution.
    """
    if threadid not in workflow_agents:
        raise HTTPException(status_code=404, detail="Workflow thread not found. Add contacts first.")
    
    agent = workflow_agents[threadid]
    contacts = agent.get_contacts()
    
    if not contacts:
        raise HTTPException(status_code=400, detail="No contacts found. Add contacts before sending emails.")
    
    # Request confirmation
    confirmation_req = confirmation_service.create_confirmation(
        action_type=ActionType.SEND_EMAILS,
        description=f"Send emails to {len(contacts)} contacts",
        details={
            "thread_id": threadid,
            "proposal_title": request.proposal_title,
            "contact_count": len(contacts),
            "contacts": contacts
        }
    )
    action_id = confirmation_req.action_id
    
    return {
        "status": "pending_confirmation",
        "action_id": action_id,
        "message": f"Confirmation required to send emails to {len(contacts)} contacts",
        "context": {
            "proposal_title": request.proposal_title,
            "contact_count": len(contacts),
            "contacts": contacts
        }
    }


@app.post("/workflow/schedule-meetings")
def workflow_schedule_meetings(
    threadid: str = Query(..., description="Thread ID for the workflow agent"),
    request: WorkflowRequest = Body(...)
):
    """
    Create Calendly scheduling links for all contacts.
    Requires confirmation before actual execution.
    """
    if threadid not in workflow_agents:
        raise HTTPException(status_code=404, detail="Workflow thread not found. Add contacts first.")
    
    agent = workflow_agents[threadid]
    contacts = agent.get_contacts()
    
    if not contacts:
        raise HTTPException(status_code=400, detail="No contacts found. Add contacts before scheduling meetings.")
    
    if not request.event_type_name:
        raise HTTPException(status_code=400, detail="event_type_name is required for scheduling meetings")
    
    # Request confirmation
    confirmation_req = confirmation_service.create_confirmation(
        action_type=ActionType.SCHEDULE_MEETINGS,
        description=f"Create scheduling links for {len(contacts)} contacts",
        details={
            "thread_id": threadid,
            "event_type_name": request.event_type_name,
            "contact_count": len(contacts),
            "contacts": contacts
        }
    )
    action_id = confirmation_req.action_id
    
    return {
        "status": "pending_confirmation",
        "action_id": action_id,
        "message": f"Confirmation required to create scheduling links for {len(contacts)} contacts",
        "context": {
            "event_type_name": request.event_type_name,
            "contact_count": len(contacts),
            "contacts": contacts
        }
    }


@app.post("/workflow/full-outreach")
def workflow_full_outreach(
    threadid: str = Query(..., description="Thread ID for the workflow agent"),
    request: WorkflowRequest = Body(...)
):
    """
    Execute full outreach workflow: send emails + create scheduling links + Slack notification.
    Requires confirmation before actual execution.
    """
    if threadid not in workflow_agents:
        raise HTTPException(status_code=404, detail="Workflow thread not found. Add contacts first.")
    
    agent = workflow_agents[threadid]
    contacts = agent.get_contacts()
    
    if not contacts:
        raise HTTPException(status_code=400, detail="No contacts found. Add contacts before executing outreach.")
    
    if not request.event_type_name:
        raise HTTPException(status_code=400, detail="event_type_name is required for full outreach")
    
    # Request confirmation
    confirmation_req = confirmation_service.create_confirmation(
        action_type=ActionType.FULL_OUTREACH,
        description=f"Execute full outreach to {len(contacts)} contacts",
        details={
            "thread_id": threadid,
            "proposal_title": request.proposal_title,
            "event_type_name": request.event_type_name,
            "contact_count": len(contacts),
            "contacts": contacts
        }
    )
    action_id = confirmation_req.action_id
    
    return {
        "status": "pending_confirmation",
        "action_id": action_id,
        "message": f"Confirmation required to execute full outreach to {len(contacts)} contacts",
        "context": {
            "proposal_title": request.proposal_title,
            "event_type_name": request.event_type_name,
            "contact_count": len(contacts),
            "contacts": contacts,
            "actions": ["Send emails", "Create scheduling links", "Send Slack notification"]
        }
    }


@app.post("/workflow/confirm")
def confirm_workflow_action(confirmation: ConfirmationRequest = Body(...)):
    """
    Confirm or reject a pending workflow action.
    If approved, executes the action. If rejected, cancels it.
    """
    action_id = confirmation.action_id
    approved = confirmation.approved
    
    # Get pending action
    confirmation_req = confirmation_service.get_confirmation(action_id)
    if not confirmation_req or confirmation_req.confirmed or confirmation_req.rejected:
        raise HTTPException(status_code=404, detail="Action not found or already processed")
    
    # Save context before approving/rejecting (approval/rejection removes from pending)
    action_type = confirmation_req.action_type
    context = confirmation_req.details
    thread_id = context["thread_id"]
    
    # Process confirmation
    if not approved:
        confirmation_service.reject_action(action_id)
        return {
            "status": "rejected",
            "action_id": action_id,
            "message": "Action cancelled by user"
        }
    
    # Approve and execute
    confirmation_service.approve_action(action_id)
    
    if thread_id not in workflow_agents:
        raise HTTPException(status_code=404, detail="Workflow thread not found")
    
    agent = workflow_agents[thread_id]
    
    try:
        if action_type == ActionType.SEND_EMAILS:
            result = agent.execute_send_emails(context["proposal_title"])
            return {
                "status": "success",
                "action_id": action_id,
                "action_type": "send_emails",
                "result": result
            }
        
        elif action_type == ActionType.SCHEDULE_MEETINGS:
            result = agent.execute_schedule_meetings(context["event_type_name"])
            return {
                "status": "success",
                "action_id": action_id,
                "action_type": "schedule_meetings",
                "result": result
            }
        
        elif action_type == ActionType.FULL_OUTREACH:
            result = agent.execute_full_outreach_workflow(
                context["proposal_title"],
                context["event_type_name"]
            )
            return {
                "status": "success",
                "action_id": action_id,
                "action_type": "full_outreach",
                "result": result
            }
        
        else:
            raise HTTPException(status_code=400, detail=f"Unknown action type: {action_type}")
    
    except Exception as e:
        return {
            "status": "error",
            "action_id": action_id,
            "message": f"Error executing action: {str(e)}"
        }


@app.get("/workflow/pending-actions")
def get_pending_actions():
    """Get all pending actions awaiting confirmation."""
    pending = confirmation_service.get_pending()
    return {
        "status": "success",
        "pending_count": len(pending),
        "actions": pending
    }


@app.get("/workflow/history")
def get_workflow_history(threadid: str = Query(..., description="Thread ID for the workflow agent")):
    """Get the workflow execution history for a specific thread."""
    if threadid not in workflow_agents:
        return {
            "status": "success",
            "thread_id": threadid,
            "history": [],
            "message": "No workflow history found for this thread"
        }
    
    agent = workflow_agents[threadid]
    history = agent.get_workflow_history()
    
    return {
        "status": "success",
        "thread_id": threadid,
        "history": history,
        "count": len(history)
    }


@app.get("/workflow/verification")
async def verify_integrations():
	"""
	CHECK THE STATUS OF ALL INTEGRATIONS.
	
	Returns configuration status for:
	- Calendly (API key configured, sample link creation)
	- Slack (webhook configured)
	- Gmail (credentials type check)
	
	Use this endpoint to verify that all integrations are properly configured.
	"""
	import os
	from pathlib import Path
	
	verification_status = {
		"timestamp": datetime.now().isoformat(),
		"integrations": {}
	}
	
	# Check Calendly
	try:
		from utils.calendly_utils import verify_calendly_setup
		calendly_setup = verify_calendly_setup()
		verification_status["integrations"]["calendly"] = {
			"configured": "CALENDLY_API_KEY" in os.environ,
			"api_key_set": bool(os.getenv("CALENDLY_API_KEY")),
			"status": "✓ Ready to use real API" if os.getenv("CALENDLY_API_KEY") else "Using mock links",
			"details": calendly_setup
		}
	except Exception as e:
		verification_status["integrations"]["calendly"] = {
			"configured": False,
			"error": str(e),
			"status": "⚠ Error checking Calendly"
		}
	
	# Check Slack
	slack_webhook = os.getenv("SLACK_WEBHOOK_URL")
	verification_status["integrations"]["slack"] = {
		"configured": bool(slack_webhook),
		"webhook_set": bool(slack_webhook),
		"status": "✓ Ready to send notifications" if slack_webhook else "[MOCK] Using mock notifications",
		"webhook_preview": slack_webhook[:50] + "..." if slack_webhook else None
	}
	
	# Check Gmail
	credentials_path = Path(__file__).parent / "credentials.json"
	gmail_configured = credentials_path.exists()
	gmail_credentials_type = None
	gmail_error = None
	
	if gmail_configured:
		try:
			import json
			with open(credentials_path, 'r') as f:
				creds = json.load(f)
				if 'web' in creds:
					gmail_credentials_type = "Web (⚠ NOT SUPPORTED - Need Desktop app type)"
					gmail_error = "You're using web credentials. Download Desktop app credentials from Google Console."
				elif 'installed' in creds:
					gmail_credentials_type = "Desktop (✓ CORRECT)"
				else:
					gmail_credentials_type = "Unknown format"
		except Exception as e:
			gmail_error = str(e)
	
	verification_status["integrations"]["gmail"] = {
		"configured": gmail_configured,
		"credentials_exist": gmail_configured,
		"credentials_path": str(credentials_path),
		"credentials_type": gmail_credentials_type,
		"status": "✓ Ready to send emails" if gmail_credentials_type == "Desktop (✓ CORRECT)" else "⚠ Configuration issue",
		"error": gmail_error
	}
	
	# Summary
	verification_status["summary"] = {
		"total_integrations": 3,
		"configured": sum(1 for i in verification_status["integrations"].values() if i.get("configured")),
		"ready": sum(1 for i in verification_status["integrations"].values() if "✓" in i.get("status", ""))
	}
	
	return verification_status


# Helper functions removed - no AI recommendations yet


# Rating endpoints for Amplitude integration

@app.post("/api/ratings")
def create_rating(request: RatingRequest):
    """Store a rating for an agent response."""
    try:
        ratings_collection = get_collection("agent_ratings")
        
        rating_doc = {
            "user_id": request.user_id,
            "thread_id": request.thread_id,
            "agent_type": request.agent_type,
            "message_index": request.message_index,
            "rating": request.rating,
            "context": request.context,
            "timestamp": datetime.utcnow(),
        }
        
        result = ratings_collection.insert_one(rating_doc)
        
        return {
            "status": "success",
            "rating_id": str(result.inserted_id),
            "message": "Rating saved successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save rating: {str(e)}")


@app.get("/api/ratings/stats")
def get_rating_stats(agent_type: Optional[str] = None):
    """Get aggregated rating statistics."""
    try:
        ratings_collection = get_collection("agent_ratings")
        
        match_filter = {}
        if agent_type:
            match_filter["agent_type"] = agent_type
        
        pipeline = [
            {"$match": match_filter} if match_filter else {"$match": {}},
            {
                "$group": {
                    "_id": "$agent_type",
                    "total_ratings": {"$sum": 1},
                    "positive_ratings": {
                        "$sum": {"$cond": [{"$eq": ["$rating", 1]}, 1, 0]}
                    },
                    "negative_ratings": {
                        "$sum": {"$cond": [{"$eq": ["$rating", -1]}, 1, 0]}
                    },
                    "avg_rating": {"$avg": "$rating"}
                }
            }
        ]
        
        stats = list(ratings_collection.aggregate(pipeline))
        
        return {
            "status": "success",
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get rating stats: {str(e)}")


@app.get("/api/ratings/agent/{agent_type}")
def get_agent_ratings(agent_type: str, limit: int = 50):
    """Get recent ratings for a specific agent."""
    try:
        ratings_collection = get_collection("agent_ratings")
        
        ratings = list(
            ratings_collection
            .find({"agent_type": agent_type})
            .sort("timestamp", -1)
            .limit(limit)
        )
        
        # Convert ObjectId to string for JSON serialization
        for rating in ratings:
            rating["_id"] = str(rating["_id"])
        
        return {
            "status": "success",
            "agent_type": agent_type,
            "count": len(ratings),
            "ratings": ratings
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get agent ratings: {str(e)}")


@app.get("/api/ratings/debug")
def debug_ratings():
    """Debug endpoint - see all ratings easily."""
    try:
        ratings_collection = get_collection("agent_ratings")
        
        all_ratings = list(ratings_collection.find().sort("timestamp", -1).limit(20))
        
        # Convert ObjectId to string
        for rating in all_ratings:
            rating["_id"] = str(rating["_id"])
        
        return {
            "status": "success",
            "total_count": ratings_collection.count_documents({}),
            "recent_ratings": all_ratings,
            "message": "Visit http://localhost:8000/api/ratings/debug to see your ratings!"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get ratings: {str(e)}")


@app.get("/api/analytics/summary")
def get_analytics_summary():
    """Get AI-powered analytics summary with insights."""
    try:
        from agents.analytics_agent import AnalyticsAgent
        
        analytics = AnalyticsAgent()
        summary = analytics.get_analytics_summary()
        
        return {
            "status": "success",
            "summary": summary
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get analytics summary: {str(e)}")


@app.get("/api/analytics/correlations/{user_id}")
def get_user_correlations(user_id: str):
    """Get AI-discovered behavioral correlations for a user."""
    try:
        from agents.analytics_agent import AnalyticsAgent
        
        analytics = AnalyticsAgent()
        correlations = analytics.analyze_event_correlations(user_id)
        
        return {
            "status": "success",
            "user_id": user_id,
            "correlations": correlations
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze correlations: {str(e)}")


@app.get("/api/analytics/user-insights/{user_id}")
def get_user_insights(user_id: str):
    """Get AI-generated personalized insights about the user's behavior."""
    try:
        from agents.analytics_agent import AnalyticsAgent
        
        analytics = AnalyticsAgent()
        insights = analytics.generate_user_insights(user_id)
        
        return {
            "status": "success",
            "user_id": user_id,
            "insights": insights
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate user insights: {str(e)}")


# Run server
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "127.0.0.1")  # Use localhost instead of 0.0.0.0 for Windows compatibility
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=True
    )
