"""
FastAPI Backend for Indigenous Land Perspectives
UofTHacks 2026
"""
from fastapi import FastAPI, HTTPException, Query, UploadFile, File
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
    agent: str  # "sustainability", "indigenous", "proposal"
    message: Optional[str] = None  # Optional for create endpoints
    image_path: Optional[str] = None  # Optional image path for sustainability agent


class ChatResponse(BaseModel):
    """Response body for chat endpoints."""
    thread_id: str
    agent: str
    user_message: str
    assistant_response: str
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

@app.post("/create-chat")
def create_chat(request: ChatRequest) -> ChatResponse:
    """Create a new chat thread with the specified agent."""
    thread_id = str(uuid.uuid4())

    # Initialize the appropriate agent
    if request.agent.lower() == "sustainability":
        agent = SustainabilityAgent()
    elif request.agent.lower() == "indigenous":
        agent = IndigenousContextAgent()
    elif request.agent.lower() == "proposal":
        agent = ProposalWorkflowAgent()
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
def start_chat(threadid: str = Query(...), request: ChatRequest = None) -> ChatResponse:
    """Start a new message in an existing thread."""
    if threadid not in threads:
        raise HTTPException(status_code=404, detail=f"Thread {threadid} not found")

    if request is None:
        raise HTTPException(status_code=400, detail="Request body required")

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
def add_chat(threadid: str = Query(...), request: ChatRequest = None) -> ChatResponse:
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
            "message": "Panorama generated successfully. Use this path with /create-sustainability-chat"
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
    agent = SustainabilityAgent()
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

    # Debug: Log the paths being returned
    vision_path_return = thread_data.get("vision_path")
    original_path_return = request.image_path
    print(f"[RESPONSE] Returning paths:")
    print(f"  - Original image: {original_path_return}")
    print(f"  - Vision image: {vision_path_return}")

    return ChatResponse(
        thread_id=thread_id,
        agent="sustainability",
        user_message=user_message,
        assistant_response=response,
        vision_path=vision_path_return,
        original_image_path=original_path_return,
    )


@app.post("/add-sustainability-chat")
def add_sustainability_chat(threadid: str = Query(...), request: ChatRequest = None) -> ChatResponse:
    """Add a message to an existing sustainability thread and optionally regenerate vision using latest image."""
    if threadid not in threads:
        raise HTTPException(status_code=404, detail=f"Thread {threadid} not found")

    if request is None:
        raise HTTPException(status_code=400, detail="Request body required")

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

    # Debug: Log the paths being returned
    vision_path_return = thread_data.get("vision_path")
    original_path_return = thread_data.get("image_path")
    print(f"[RESPONSE] Returning paths for follow-up:")
    print(f"  - Original image: {original_path_return}")
    print(f"  - Vision image: {vision_path_return}")

    return ChatResponse(
        thread_id=threadid,
        agent="sustainability",
        user_message=request.message,
        assistant_response=response,
        vision_path=vision_path_return,
        original_image_path=original_path_return,
    )


# Helper functions removed - no AI recommendations yet


# Run server
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8001))
    host = os.getenv("HOST", "127.0.0.1")  # Use localhost instead of 0.0.0.0 for Windows compatibility
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=True
    )
