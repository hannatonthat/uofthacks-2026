/**
 * Amplitude Analytics Service
 * Provides typed event tracking with anonymous device ID management
 */

import * as amplitude from '@amplitude/analytics-browser';

// Initialize flag to prevent double initialization
let isInitialized = false;

// Device ID for anonymous tracking (persisted in localStorage)
const DEVICE_ID_KEY = 'amplitude_device_id';

/**
 * Generate or retrieve persistent device ID for anonymous tracking
 */
function getOrCreateDeviceId(): string {
  if (typeof window === 'undefined') return '';
  
  let deviceId = localStorage.getItem(DEVICE_ID_KEY);
  if (!deviceId) {
    // Generate UUID-like device ID
    deviceId = `device_${Date.now()}_${Math.random().toString(36).substring(2, 15)}`;
    localStorage.setItem(DEVICE_ID_KEY, deviceId);
  }
  return deviceId;
}

/**
 * Initialize Amplitude SDK (call once at app startup)
 */
export function initAmplitude() {
  if (isInitialized || typeof window === 'undefined') return;
  
  const apiKey = process.env.NEXT_PUBLIC_AMPLITUDE_API_KEY;
  
  if (!apiKey) {
    console.warn('Amplitude API key not found. Analytics disabled.');
    return;
  }
  
  const deviceId = getOrCreateDeviceId();
  
  amplitude.init(apiKey, deviceId, {
    defaultTracking: {
      sessions: true,
      pageViews: true,
      formInteractions: false,
      fileDownloads: false,
    },
    logLevel: amplitude.Types.LogLevel.Warn,
  });
  
  isInitialized = true;
  console.log('Amplitude initialized with device ID:', deviceId);
}

/**
 * Get current device ID
 */
export function getDeviceId(): string {
  return getOrCreateDeviceId();
}

/**
 * Get current session ID
 */
export function getSessionId(): string {
  return amplitude.getSessionId()?.toString() || '';
}

// ============================================================================
// TYPED EVENT TRACKING FUNCTIONS
// ============================================================================

export interface LocationData {
  lat: number;
  lon: number;
  territory?: string;
  address?: string;
}

/**
 * Track session start
 */
export function trackSessionStart() {
  amplitude.track('session_started', {
    device_id: getDeviceId(),
    timestamp: new Date().toISOString(),
  });
}

/**
 * Track session end
 */
export function trackSessionEnd(duration: number) {
  amplitude.track('session_ended', {
    device_id: getDeviceId(),
    duration_seconds: duration,
    timestamp: new Date().toISOString(),
  });
}

/**
 * Track map region click
 */
export function trackMapRegionClicked(location: LocationData, sustainabilityScore?: number) {
  amplitude.track('map_region_clicked', {
    device_id: getDeviceId(),
    lat: location.lat,
    lon: location.lon,
    territory: location.territory,
    address: location.address,
    sustainability_score: sustainabilityScore,
    timestamp: new Date().toISOString(),
  });
}

/**
 * Track agent chat started
 */
export function trackAgentChatStarted(
  agentType: 'sustainability' | 'indigenous' | 'proposal',
  threadId: string,
  location?: LocationData
) {
  amplitude.track('agent_chat_started', {
    device_id: getDeviceId(),
    agent_type: agentType,
    thread_id: threadId,
    location,
    timestamp: new Date().toISOString(),
  });
}

/**
 * Track agent message sent
 */
export function trackAgentMessageSent(
  agentType: 'sustainability' | 'indigenous' | 'proposal',
  threadId: string,
  message: string,
  messageIndex: number
) {
  amplitude.track('agent_message_sent', {
    device_id: getDeviceId(),
    agent_type: agentType,
    thread_id: threadId,
    message_length: message.length,
    message_index: messageIndex,
    timestamp: new Date().toISOString(),
  });
}

/**
 * Track agent response received
 */
export function trackAgentResponseReceived(
  agentType: 'sustainability' | 'indigenous' | 'proposal',
  threadId: string,
  responseLength: number,
  messageIndex: number,
  responseTime?: number
) {
  amplitude.track('agent_response_received', {
    device_id: getDeviceId(),
    agent_type: agentType,
    thread_id: threadId,
    response_length: responseLength,
    message_index: messageIndex,
    response_time_ms: responseTime,
    timestamp: new Date().toISOString(),
  });
}

/**
 * Track agent response rating (thumbs up/down)
 */
export function trackAgentResponseRated(
  agentType: 'sustainability' | 'indigenous' | 'proposal',
  threadId: string,
  messageIndex: number,
  rating: 1 | -1,
  userMessage: string,
  agentResponse: string,
  location?: LocationData
) {
  amplitude.track('agent_response_rated', {
    device_id: getDeviceId(),
    agent_type: agentType,
    thread_id: threadId,
    message_index: messageIndex,
    rating,
    user_message_length: userMessage.length,
    agent_response_length: agentResponse.length,
    location,
    timestamp: new Date().toISOString(),
  });
}

/**
 * Track workflow step viewed
 */
export function trackWorkflowStepViewed(
  stepNumber: number,
  stepName: string,
  region?: string
) {
  amplitude.track('workflow_step_viewed', {
    device_id: getDeviceId(),
    step_number: stepNumber,
    step_name: stepName,
    region,
    timestamp: new Date().toISOString(),
  });
}

/**
 * Track workflow step completed
 */
export function trackWorkflowStepCompleted(
  stepNumber: number,
  stepName: string,
  timeSpent: number,
  skipped: boolean = false
) {
  amplitude.track('workflow_step_completed', {
    device_id: getDeviceId(),
    step_number: stepNumber,
    step_name: stepName,
    time_spent_seconds: timeSpent,
    skipped,
    timestamp: new Date().toISOString(),
  });
}

/**
 * Track native plant viewed
 */
export function trackNativePlantViewed(
  plantId: string,
  plantName: string,
  location?: LocationData
) {
  amplitude.track('native_plant_viewed', {
    device_id: getDeviceId(),
    plant_id: plantId,
    plant_name: plantName,
    location,
    timestamp: new Date().toISOString(),
  });
}

/**
 * Track indigenous leader contact clicked
 */
export function trackIndigenousLeaderContactClicked(
  leaderId: string,
  leaderName: string,
  organization: string,
  location?: LocationData
) {
  amplitude.track('indigenous_leader_contact_clicked', {
    device_id: getDeviceId(),
    leader_id: leaderId,
    leader_name: leaderName,
    organization,
    location,
    timestamp: new Date().toISOString(),
  });
}

/**
 * Track map zoom event
 */
export function trackMapZoom(
  zoomLevel: number,
  centerLat: number,
  centerLon: number,
  regionsVisible: number
) {
  amplitude.track('map_zoom', {
    device_id: getDeviceId(),
    zoom_level: zoomLevel,
    center_lat: centerLat,
    center_lon: centerLon,
    regions_visible: regionsVisible,
    timestamp: new Date().toISOString(),
  });
}

/**
 * Track custom event with flexible properties
 */
export function trackCustomEvent(eventName: string, properties: Record<string, any> = {}) {
  amplitude.track(eventName, {
    device_id: getDeviceId(),
    ...properties,
    timestamp: new Date().toISOString(),
  });
}

// ============================================================================
// USER PROPERTIES (for personalization)
// ============================================================================

/**
 * Set user properties for personalization
 */
export function setUserProperties(properties: Record<string, any>) {
  const identify = new amplitude.Identify();
  
  Object.entries(properties).forEach(([key, value]) => {
    identify.set(key, value);
  });
  
  amplitude.identify(identify);
}

/**
 * Increment user property (e.g., message count)
 */
export function incrementUserProperty(property: string, value: number = 1) {
  const identify = new amplitude.Identify();
  identify.add(property, value);
  amplitude.identify(identify);
}

/**
 * Track user preference
 */
export function trackUserPreference(preferenceName: string, value: any) {
  const identify = new amplitude.Identify();
  identify.set(preferenceName, value);
  amplitude.identify(identify);
}

// Export amplitude instance for advanced usage
export { amplitude };
