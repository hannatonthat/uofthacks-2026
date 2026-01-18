/**
 * API client for Indigenous Land Perspectives backend
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface RegionData {
  click_location: { lat: number; lon: number };
  indigenous_territory: any;
  nearest_first_nation: any;
  nearby_data: {
    green_spaces?: any[];
    environmental_areas?: any[];
    first_nations?: any[];
    indigenous_territories?: any[];
    indigenous_treaties?: any[];
    indigenous_languages?: any[];
  };
  ecological_score: {
    total_score: number;  // 0-30
    normalized_score: number;  // 0-10
    max_score: number;
    metrics: {
      environmental_area_proximity: any;
      green_space_proximity: any;
      street_tree_count: any;
    };
    rule_compliance: {
      has_3_trees: boolean;
      within_300m_green_space: boolean;
      rule_330_compliant: boolean;
    };
  };
  sustainability_score: any;  // Legacy field
  native_plants: any;
  recommendations: string[];
}

export interface MapBoundsData {
  bounds: {
    min_lon: number;
    min_lat: number;
    max_lon: number;
    max_lat: number;
  };
  layers: Record<string, any[]>;
  total_features: number;
}

export interface MapPoint {
  id: string;
  lat: number;
  lon: number;
  name: string;
  type: string;
}

export interface PanoramaData {
  panorama_path: string;
  panorama_id: string;
  dimensions: string;
  location: string;
  message: string;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface ChatResponse {
  thread_id: string;
  agent: string;
  user_message: string;
  assistant_response: string;
  vision_path?: any;
  original_image_path?: any;
  vision_url?: any;
  original_image_url?: any;
}

export interface ThreadHistory {
  thread_id: string;
  agent: string;
  image_path?: string;
  conversation_history: ChatMessage[];
}

/**
 * Get sample of interesting locations to display on map
 * NOTE: Not used in 3D map - kept for legacy 2D map compatibility
 */
export async function getMapPoints(limit: number = 100): Promise<MapPoint[]> {
  const response = await fetch(
    `${API_BASE_URL}/api/map/points?limit=${limit}`
  );
  
  if (!response.ok) {
    throw new Error(`API error: ${response.statusText}`);
  }
  
  const data = await response.json();
  return data.points;
}

/**
 * Get all data near a clicked point
 */
export async function getRegionData(
  lat: number,
  lon: number,
  radius: number = 500
): Promise<RegionData> {
  const response = await fetch(
    `${API_BASE_URL}/api/map/region/${lat}/${lon}?radius=${radius}`
  );
  
  if (!response.ok) {
    throw new Error(`API error: ${response.statusText}`);
  }
  
  return response.json();
}

/**
 * Get data within map viewport bounds
 */
export async function getMapBounds(
  minLon: number,
  minLat: number,
  maxLon: number,
  maxLat: number,
  layers?: string[]
): Promise<MapBoundsData> {
  const layersParam = layers ? `&layers=${layers.join(',')}` : '';
  const response = await fetch(
    `${API_BASE_URL}/api/map/bounds?min_lon=${minLon}&min_lat=${minLat}&max_lon=${maxLon}&max_lat=${maxLat}${layersParam}`
  );
  
  if (!response.ok) {
    throw new Error(`API error: ${response.statusText}`);
  }
  
  return response.json();
}

/**
 * Get sustainability analysis for a location
 */
export async function getSustainabilityAnalysis(
  lat: number,
  lon: number,
  radius: number = 1000
) {
  const response = await fetch(
    `${API_BASE_URL}/api/sustainability/analyze/${lat}/${lon}?radius=${radius}`
  );
  
  if (!response.ok) {
    throw new Error(`API error: ${response.statusText}`);
  }
  
  return response.json();
}

/**
 * Log user event (for Amplitude tracking)
 */
export async function logEvent(
  eventType: string,
  userId: string,
  sessionId: string,
  data: Record<string, any>
) {
  const response = await fetch(`${API_BASE_URL}/api/events`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      event_type: eventType,
      user_id: userId,
      session_id: sessionId,
      data,
    }),
  });
  
  if (!response.ok) {
    console.error('Failed to log event:', response.statusText);
  }
  
  return response.json();
}

/**
 * Generate panorama image from Street View at location
 */
export async function generatePanorama(
  lat: number,
  lon: number,
  numDirections: number = 4
): Promise<PanoramaData> {
  const response = await fetch(
    `${API_BASE_URL}/generate-panorama?lat=${lat}&lon=${lon}&num_directions=${numDirections}`
  );
  
  if (!response.ok) {
    throw new Error(`Failed to generate panorama: ${response.statusText}`);
  }
  
  return response.json();
}

/**
 * Create a new agent chat thread
 */
export async function createAgentChat(
  agent: 'sustainability' | 'indigenous' | 'proposal',
  message?: string,
  imagePath?: string,
  lat?: number,
  lon?: number
): Promise<ChatResponse> {
  // Import getDeviceId dynamically
  const { getDeviceId } = await import('./amplitude');
  
  const response = await fetch(`${API_BASE_URL}/create-chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      agent,
      message,
      image_path: imagePath,
      user_id: getDeviceId(),
      lat,
      lon,
    }),
  });
  
  if (!response.ok) {
    throw new Error(`Failed to create agent chat: ${response.statusText}`);
  }
  
  return response.json();
}

/**
 * Create sustainability chat with full analysis (returns both original and vision paths)
 */
export async function createSustainabilityChat(
  message: string,
  imagePath: string
): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE_URL}/create-sustainability-chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      agent: 'sustainability',
      message,
      image_path: imagePath,
    }),
  });
  
  if (!response.ok) {
    throw new Error(`Failed to create sustainability chat: ${response.statusText}`);
  }
  
  return response.json();
}

/**
 * Add message to sustainability chat (generates new vision)
 */
export async function addSustainabilityMessage(
  threadId: string,
  message: string
): Promise<ChatResponse> {
  const response = await fetch(
    `${API_BASE_URL}/add-sustainability-chat?threadid=${threadId}`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        agent: 'sustainability',
        message,
      }),
    }
  );

  if (!response.ok) {
    throw new Error(`Failed to send message: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Send message to existing agent chat thread (generic)
 */
export async function sendAgentMessage(
  threadId: string,
  message: string
): Promise<ChatResponse> {
  const response = await fetch(
    `${API_BASE_URL}/start-chat?threadid=${threadId}`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message,
      }),
    }
  );

  if (!response.ok) {
    throw new Error(`Failed to send message: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Get conversation history for a thread
 */
export async function getThreadHistory(threadId: string): Promise<ThreadHistory> {
  const response = await fetch(`${API_BASE_URL}/thread/${threadId}`);
  
  if (!response.ok) {
    throw new Error(`Failed to get thread history: ${response.statusText}`);
  }
  
  return response.json();
}

/**
 * Delete a thread and its chat history
 */
export async function deleteThread(threadId: string): Promise<any> {
  const response = await fetch(`${API_BASE_URL}/thread/${threadId}`, {
    method: 'DELETE',
  });
  
  if (!response.ok) {
    throw new Error(`Failed to delete thread: ${response.statusText}`);
  }
  
  return response.json();
}

/**
 * Generate summary PDF with all conversations and images
 */
export async function generateSummaryPDF(
  threadIds: {
    sustainability?: string;
    indigenous?: string;
    workflow?: string;
  },
  projectName: string
): Promise<{ pdf_url: string; pdf_path: string }> {
  const response = await fetch(`${API_BASE_URL}/api/generate-summary-pdf`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      thread_ids: threadIds,
      project_name: projectName,
    }),
  });
  
  if (!response.ok) {
    throw new Error(`Failed to generate PDF: ${response.statusText}`);
  }
  
  return response.json();
}
