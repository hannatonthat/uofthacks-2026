"""FastAPI server for interacting with specialized agents."""

from fastapi import FastAPI, HTTPException, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
import uuid
import os
import shutil
from datetime import datetime
from database import get_collection

from agents import SustainabilityAgent, IndigenousContextAgent, ProposalWorkflowAgent

app = FastAPI(title="Agents API", version="1.0.0")

# Enable CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Thread storage: maps thread_id -> {"agent": agent_instance, "image_path": str}
threads: Dict[str, Dict] = {}
UPLOAD_DIR = "uploads"

# Create uploads directory if it doesn't exist
os.makedirs(UPLOAD_DIR, exist_ok=True)


class ChatRequest(BaseModel):
    """Request body for chat endpoints."""
    agent: str  # "sustainability", "indigenous", "proposal"
    message: str
    user_id: Optional[str] = None  # For personalization


class ChatResponse(BaseModel):
    """Response body for chat endpoints."""
    thread_id: str
    agent: str
    user_message: str
    assistant_response: str


@app.post("/create-chat")
def create_chat(request: ChatRequest) -> ChatResponse:
    """Create a new chat thread with the specified agent."""
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
    
    # Store agent in thread storage
    thread_data = {"agent": agent, "image_path": None}
    threads[thread_id] = thread_data
    
    # Generate initial response using base prompt
    agent.add_message("user", request.message)
    
    try:
        # Get contextual response from agent based on their base prompt
        if request.agent.lower() == "sustainability":
            response = f"Hi! I'm your sustainability agent. {agent._prompt}\n\nI can help you:\n• Analyze land images for ecological improvements\n• Suggest sustainable redesigns\n• Generate future vision images\n\nUpload an image to get started, or ask me anything about sustainable land development!"
        elif request.agent.lower() == "indigenous":
            response = f"Hi! I'm your indigenous context agent. {agent._prompt}\n\nI can help you:\n• Provide indigenous perspectives on land use\n• Build culturally respectful proposals\n• Ensure proper consultation processes\n\nWhat would you like to discuss?"
        elif request.agent.lower() == "proposal":
            response = f"Hi! I'm your proposal workflow agent. {agent._prompt}\n\nI can help you:\n• Manage proposal submission workflows\n• Generate respectful outreach emails\n• Track contacts and consultation steps\n\nWhat would you like help with?"
        else:
            response = f"{request.agent.capitalize()} agent ready. How can I assist you?"
    except Exception as e:
        response = f"Agent initialized. Error: {str(e)}"
    
    agent.add_message("assistant", response)
    
    return ChatResponse(
        thread_id=thread_id,
        agent=request.agent,
        user_message=request.message,
        assistant_response=response,
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
    
    # Add user message to conversation history
    agent.add_message("user", request.message)
    
    # Generate response based on agent type
    agent_name = type(agent).__name__
    
    try:
        if agent_name == "SustainabilityAgent":
            # For sustainability agent, include image context if available
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
    
    # Verify it's a Sustainability agent
    if type(agent).__name__ != "SustainabilityAgent":
        raise HTTPException(status_code=400, detail="Image upload only supported for Sustainability agent")
    
    try:
        # Save uploaded file
        file_path = f"{UPLOAD_DIR}/{threadid}_{file.filename}"
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        
        # Update thread data with image path
        thread_data["image_path"] = file_path
        
        # Generate sustainable vision based on uploaded image
        vision_path = f"{UPLOAD_DIR}/vision_{threadid}_{file.filename}"
        agent.generate_future_vision(file_path, vision_path)
        
        return {
            "thread_id": threadid,
            "status": "success",
            "original_image": file_path,
            "vision_image": vision_path,
            "message": f"Image uploaded and sustainable vision generated!"
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
        "conversation_history": agent._conversation_history,
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
    
    # Clean up image files if they exist
    if image_path and os.path.exists(image_path):
        os.remove(image_path)
    
    del threads[threadid]
    
    return {
        "message": f"Thread {threadid} deleted",
        "agent": agent_name,
    }


class RatingRequest(BaseModel):
    """Request body for rating agent responses."""
    user_id: str
    thread_id: str
    agent_type: str
    message_index: int
    rating: int  # 1 for thumbs up, -1 for thumbs down
    context: Dict[str, Any]


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


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
