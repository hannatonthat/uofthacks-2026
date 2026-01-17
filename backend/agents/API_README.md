# Agents FastAPI Server

A FastAPI server for interacting with three specialized agents: Sustainability, Indigenous Context, and Proposal Workflow.

## Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export GOOGLE_API_KEY="your-google-api-key"
export BACKBOARD_API_KEY="your-backboard-api-key"

# Run the server
python api.py
```

The server will start on `http://localhost:8000`

## Endpoints

### POST /create-chat
Creates a new chat thread with the specified agent. **For Sustainability agent, automatically generates an initial vision image.**

**Request:**
```json
{
  "agent": "sustainability|indigenous|proposal",
  "message": "Your initial message"
}
```

**Response:**
```json
{
  "thread_id": "uuid-here",
  "agent": "sustainability",
  "user_message": "Your initial message",
  "assistant_response": "Sustainability agent initialized with initial vision image generated..."
}
```

**For Sustainability agent:** An initial image is generated and stored, ready for use in subsequent requests.

### POST /start-chat?threadid=<thread_id>
Start a conversation in an existing thread (same as /add-chat).

**Request:**
```json
{
  "agent": "sustainability",
  "message": "Continue the conversation"
}
```

**Response:**
```json
{
  "thread_id": "uuid-here",
  "agent": "SustainabilityAgent",
  "user_message": "Your message",
  "assistant_response": "Agent response"
}
```

### POST /add-chat?threadid=<thread_id>
Add a message to an existing thread (alias for /start-chat).

**Request:**
```json
{
  "agent": "sustainability",
  "message": "Your message"
}
```

### POST /upload-image?threadid=<thread_id>
Upload an image for the Sustainability agent to analyze and generate sustainable vision. **Only works with Sustainability agent threads.**

**Request:** (multipart/form-data)
- `file`: Image file (PNG, JPG, etc.)

**Response:**
```json
{
  "thread_id": "uuid-here",
  "status": "success",
  "original_image": "uploads/uuid_filename.png",
  "vision_image": "uploads/vision_uuid_filename.png",
  "message": "Image uploaded and sustainable vision generated!"
}
```

**Process:**
1. Upload image to thread
2. Sustainability agent analyzes the image
3. Generates a sustainable vision version
4. Both paths are stored and available for the thread

### GET /threads
List all active threads.

**Response:**
```json
{
  "total_threads": 5,
  "thread_ids": ["uuid1", "uuid2", "uuid3"]
}
```

### GET /thread/{threadid}
Get full conversation history and metadata for a thread.

**Response:**
```json
{
  "thread_id": "uuid-here",
  "agent": "SustainabilityAgent",
  "image_path": "uploads/vision_uuid_filename.png",
  "conversation_history": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ]
}
```

### DELETE /thread/{threadid}
Delete a thread and free up resources.

**Response:**
```json
{
  "message": "Thread uuid-here deleted",
  "agent": "SustainabilityAgent"
}
```

### GET /health
Health check endpoint.

**Response:**
```json
{
  "status": "ok"
}
```

## Agent Types

- **sustainability**: Analyzes land, proposes sustainable redesigns, generates future vision images
- **indigenous**: Adds indigenous context, builds proposal sections with community perspectives
- **proposal**: Manages workflow, generates outreach emails, tracks contacts

## Environment Variables

- `GOOGLE_API_KEY`: Google Generative AI API key (for Gemini)
- `BACKBOARD_API_KEY`: Backboard.io API key (for unified LLM access)
- `OPENAI_API_KEY`: (Optional) OpenAI API key

## Interactive API Docs

Once running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
