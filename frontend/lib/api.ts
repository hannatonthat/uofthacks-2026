/**
 * API client for Indigenous Land Perspectives backend
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';

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
