'use client';

import { useEffect, useRef, useState } from 'react';
import Map, { MapRef, Layer, type MapMouseEvent } from 'react-map-gl/mapbox';
import { getRegionData, RegionData, generatePanorama } from '@/lib/api';
import AgentModal from './AgentModal';
import PanoramaViewer from './PanoramaViewer';
import { trackMapRegionClicked, trackMapZoom } from '@/lib/amplitude';
import 'mapbox-gl/dist/mapbox-gl.css';

// GTA bounds
const GTA_CENTER: [number, number] = [-79.4, 43.7];
const GTA_BOUNDS: [[number, number], [number, number]] = [
  [-80.0, 43.4],  // Southwest
  [-78.8, 44.1]   // Northeast
];

interface MapPoint {
  lat: number;
  lon: number;
  name: string;
  address?: string;
}

interface Map3DProps {
  onGetStarted?: () => void;
}

// Helper function to convert ALL CAPS to Title Case
const toTitleCase = (str: string): string => {
  return str.toLowerCase().replace(/\b\w/g, (char) => char.toUpperCase());
};

export default function Map3D({ onGetStarted }: Map3DProps) {
  const mapRef = useRef<MapRef>(null);
  const [selectedPoint, setSelectedPoint] = useState<MapPoint | null>(null);
  
  // Custom scrollbar styles
  const scrollbarStyles = `
    .custom-scrollbar::-webkit-scrollbar {
      width: 8px;
    }
    .custom-scrollbar::-webkit-scrollbar-track {
      background: #000000;
    }
    .custom-scrollbar::-webkit-scrollbar-thumb {
      background: #292524;
      border-radius: 4px;
    }
    .custom-scrollbar::-webkit-scrollbar-thumb:hover {
      background: #44403c;
    }
  `;
  const [regionData, setRegionData] = useState<RegionData | null>(null);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchSuggestions, setSearchSuggestions] = useState<any[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [panoramaPath, setPanoramaPath] = useState<string | null>(null);
  const [panoramaLoading, setPanoramaLoading] = useState(false);
  const [agentModalOpen, setAgentModalOpen] = useState(false);
  const [panoramaViewerOpen, setPanoramaViewerOpen] = useState(false);
  const [showGettingStarted, setShowGettingStarted] = useState(true);
  const [animateMetrics, setAnimateMetrics] = useState(false);
  const [viewport, setViewport] = useState({
    latitude: 20,  // Start viewing from above the equator
    longitude: 0,   // Start centered on prime meridian
    zoom: 1.5,      // Zoomed out to see whole globe
    pitch: 0,       // Flat view initially
    bearing: -20,   // Slight rotation for dramatic effect
    minZoom: 0,     // Allow full zoom out to see globe
    maxZoom: 20,    // Max zoom level
  });


  // Toggle text labels based on getting started state
  useEffect(() => {
    if (!mapRef.current) return;
    
    const map = mapRef.current.getMap();
    if (!map.isStyleLoaded()) return;
    
    const style = map.getStyle();
    if (style && style.layers) {
      style.layers.forEach((layer) => {
        if (layer.type === 'symbol' && layer.id) {
          try {
            map.setLayoutProperty(
              layer.id, 
              'visibility', 
              showGettingStarted ? 'none' : 'visible'
            );
          } catch (e) {
            // Ignore errors for layers that don't support visibility
          }
        }
      });
    }
  }, [showGettingStarted]);

  // Slow globe rotation animation before getting started
  useEffect(() => {
    if (!showGettingStarted) return;

    let animationFrame: number;
    let currentLongitude = 0; // Start longitude

    const rotateGlobe = () => {
      currentLongitude += 0.1; // Slow rotation speed (degrees per frame)
      if (currentLongitude >= 180) currentLongitude = -180;

      setViewport(prev => ({
        ...prev,
        longitude: currentLongitude,
        bearing: -20  // Keep slight angle for visual interest
      }));
      
      animationFrame = requestAnimationFrame(rotateGlobe);
    };

    // Start rotation after a short delay to let map load
    const timer = setTimeout(() => {
      animationFrame = requestAnimationFrame(rotateGlobe);
    }, 1000);

    return () => {
      clearTimeout(timer);
      if (animationFrame) cancelAnimationFrame(animationFrame);
    };
  }, [showGettingStarted]);

  // Trigger zoom animation when Getting Started is clicked
  const handleGetStarted = () => {
    setShowGettingStarted(false);
    onGetStarted?.(); // Notify parent component
    
    setTimeout(() => {
      mapRef.current?.flyTo({
        center: GTA_CENTER,
        zoom: 11,
        pitch: 50,
        bearing: 0,
        duration: 4000,  // 4 second dramatic zoom
        essential: true,
      });
    }, 300);
  };

  // Animate metrics when regionData changes
  useEffect(() => {
    if (regionData) {
      setAnimateMetrics(false);
      // Slight delay before triggering animation
      const timer = setTimeout(() => {
        setAnimateMetrics(true);
      }, 100);
      return () => clearTimeout(timer);
    }
  }, [regionData]);

  // Search for addresses (forward geocoding)
  const searchAddress = async (query: string) => {
    if (!query || query.length < 3) {
      setSearchSuggestions([]);
      return;
    }

    try {
      const response = await fetch(
        `https://api.mapbox.com/geocoding/v5/mapbox.places/${encodeURIComponent(query)}.json?` +
        `access_token=${process.env.NEXT_PUBLIC_MAPBOX_TOKEN}&` +
        `limit=5`
      );

      if (!response.ok) {
        throw new Error('Search failed');
      }

      const data = await response.json();
      setSearchSuggestions(data.features || []);
      setShowSuggestions(true);
    } catch (error) {
      console.error('Error searching address:', error);
      setSearchSuggestions([]);
    }
  };

  // Handle search input change
  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setSearchQuery(value);
    searchAddress(value);
  };

  // Handle selecting a search result
  const handleSelectAddress = async (feature: any) => {
    const [lng, lat] = feature.center;
    const address = feature.place_name;

    setSearchQuery(address);
    setShowSuggestions(false);
    setLoading(true);

    setSelectedPoint({
      lat,
      lon: lng,
      name: address,
      address: address,
    });

    try {
      const data = await getRegionData(lat, lng, 500);
      setRegionData(data);

      // Fly to selected location
      mapRef.current?.flyTo({
        center: [lng, lat],
        zoom: 14,
        pitch: 60,
        duration: 1500,
        essential: true,
      });
    } catch (error) {
      console.error('Error fetching region data:', error);
      setRegionData(null);
    } finally {
      setLoading(false);
    }

    // Generate panorama in parallel
    setPanoramaLoading(true);
    try {
      const panoramaData = await generatePanorama(lat, lng, 4);
      setPanoramaPath(panoramaData.panorama_path);
      console.log('Panorama generated:', panoramaData);
    } catch (error) {
      console.error('Panorama generation failed:', error);
      setPanoramaPath(null);
    } finally {
      setPanoramaLoading(false);
    }
  };

  // Reverse geocode to get address from coordinates
  const getAddressFromCoords = async (lat: number, lng: number): Promise<string> => {
    try {
      const response = await fetch(
        `https://api.mapbox.com/geocoding/v5/mapbox.places/${lng},${lat}.json?access_token=${process.env.NEXT_PUBLIC_MAPBOX_TOKEN}`
      );
      
      if (!response.ok) {
        throw new Error('Geocoding failed');
      }
      
      const data = await response.json();
      
      if (data.features && data.features.length > 0) {
        // Get the most specific address (usually the first feature)
        return data.features[0].place_name;
      }
      
      return `${lat.toFixed(4)}, ${lng.toFixed(4)}`;
    } catch (error) {
      console.error('Error reverse geocoding:', error);
      return `${lat.toFixed(4)}, ${lng.toFixed(4)}`;
    }
  };

  // Handle map click - anywhere on the map
  const handleMapClick = async (event: MapMouseEvent) => {
    const { lngLat } = event;

    console.log('Map clicked at:', lngLat.lat, lngLat.lng);

    setLoading(true);
    
    // Get address first
    const address = await getAddressFromCoords(lngLat.lat, lngLat.lng);
    
    setSelectedPoint({
      lat: lngLat.lat,
      lon: lngLat.lng,
      name: address,
      address: address,
    });

    try {
      const data = await getRegionData(lngLat.lat, lngLat.lng, 500);
      setRegionData(data);
      
      // Track map region clicked with Amplitude
      trackMapRegionClicked(
        {
          lat: lngLat.lat,
          lon: lngLat.lng,
          address: address,
          territory: data.indigenous_territory?.Name,
        },
        data.ecological_score?.normalized_score
      );
      
      // Fly to clicked location
      mapRef.current?.flyTo({
        center: [lngLat.lng, lngLat.lat],
        zoom: 14,
        pitch: 60,
        duration: 1500,
        essential: true,
      });
    } catch (error) {
      console.error('Error fetching region data:', error);
      setRegionData(null);
    } finally {
      setLoading(false);
    }

    // Generate panorama in parallel (don't wait for region data)
    setPanoramaLoading(true);
    try {
      const panoramaData = await generatePanorama(lngLat.lat, lngLat.lng, 4);
      setPanoramaPath(panoramaData.panorama_path);
      console.log('Panorama generated:', panoramaData);
    } catch (error) {
      console.error('Panorama generation failed:', error);
      setPanoramaPath(null);
    } finally {
      setPanoramaLoading(false);
    }
  };

  return (
    <div className="relative w-full h-full">
      {/* Custom Scrollbar Styles */}
      <style dangerouslySetInnerHTML={{ __html: scrollbarStyles }} />
      
      {/* Getting Started Button Overlay */}
      {showGettingStarted && (
        <div className="absolute inset-0 z-[2000] flex items-center justify-center">
          <div className="text-center">
            <h1 className="text-6xl font-bold text-white mb-3 drop-shadow-2xl tracking-tight">REMAP</h1>
            <p className="text-2xl text-white mb-4 drop-shadow-lg font-light">Land before lines</p>
            <button
              onClick={handleGetStarted}
              className="text-white text-sm font-light cursor-pointer transition-all duration-200 flex items-center gap-1 mx-auto bg-black px-4 py-2 rounded-lg hover:scale-102 hover:shadow-[0_0_16px_rgba(255,255,255,0.5)]"
            >
              Explore <span>→</span>
            </button>
          </div>
        </div>
      )}

      {/* Profile Icon - Only show after getting started */}
      {!showGettingStarted && (
        <a
          href="/insights"
          className="absolute top-4 left-4 z-[1000] w-10 h-10 bg-black border border-white/20 rounded-full flex items-center justify-center text-white hover:shadow-[0_0_16px_rgba(255,255,255,0.5)] transition-all duration-300 cursor-pointer"
        >
          <svg
            className="w-5 h-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
            />
          </svg>
        </a>
      )}

      {/* Search Bar - Only show after getting started */}
      {!showGettingStarted && (
        <div className="absolute top-4 left-16 z-[1000] w-64">
          <div className="relative">
            <input
              type="text"
              value={searchQuery}
              onChange={handleSearchChange}
              onFocus={() => searchSuggestions.length > 0 && setShowSuggestions(true)}
              placeholder="Search..."
              className="w-full px-4 py-2 bg-black text-white border border-white/20 rounded-lg focus:outline-none focus:shadow-[0_0_16px_rgba(255,255,255,0.5)] placeholder-stone-400 transition-all duration-300"
            />
          
          {/* Search Suggestions Dropdown */}
          {showSuggestions && searchSuggestions.length > 0 && (
            <div className="absolute top-full mt-2 w-full bg-black border border-white/20 rounded-lg overflow-hidden shadow-[0_0_20px_rgba(0,0,0,0.8)]">
              {searchSuggestions.map((suggestion, index) => (
                <button
                  key={index}
                  onClick={() => handleSelectAddress(suggestion)}
                  className="w-full px-4 py-3 text-left text-white hover:bg-white/10 border-b border-white/10 last:border-b-0 transition-all duration-300 cursor-pointer"
                >
                  <div className="font-medium text-sm">{suggestion.text}</div>
                  <div className="text-xs text-stone-400 mt-1">{suggestion.place_name}</div>
                </button>
              ))}
            </div>
          )}
        </div>
        </div>
      )}

      <Map
        ref={mapRef}
        {...viewport}
        onMove={(evt) => setViewport({
          latitude: evt.viewState.latitude,
          longitude: evt.viewState.longitude,
          zoom: evt.viewState.zoom,
          pitch: evt.viewState.pitch,
          bearing: evt.viewState.bearing,
          minZoom: 0,
          maxZoom: 20
        })}
        onClick={handleMapClick}
        mapStyle="mapbox://styles/mapbox/dark-v11"
        onLoad={() => {
          // Hide labels on initial load
          if (showGettingStarted && mapRef.current) {
            const map = mapRef.current.getMap();
            const style = map.getStyle();
            if (style && style.layers) {
              style.layers.forEach((layer) => {
                if (layer.type === 'symbol' && layer.id) {
                  try {
                    map.setLayoutProperty(layer.id, 'visibility', 'none');
                  } catch (e) {
                    // Ignore errors for layers that don't support visibility
                  }
                }
              });
            }
          }
        }}
        mapboxAccessToken={process.env.NEXT_PUBLIC_MAPBOX_TOKEN}
        style={{ width: '100%', height: '100%' }}
        renderWorldCopies={true}
        antialias={true}
        projection={{ name: 'globe' }}
      >
        {/* 3D Buildings Layer */}
        <Layer
          id="3d-buildings"
          source="composite"
          source-layer="building"
          filter={['==', 'extrude', 'true']}
          type="fill-extrusion"
          minzoom={13}
          paint={{
            'fill-extrusion-color': '#3a3a3a',
            'fill-extrusion-height': [
              'interpolate',
              ['linear'],
              ['zoom'],
              13,
              0,
              13.05,
              ['get', 'height'],
            ],
            'fill-extrusion-base': [
              'interpolate',
              ['linear'],
              ['zoom'],
              13,
              0,
              13.05,
              ['get', 'min_height'],
            ],
            'fill-extrusion-opacity': 0.8,
          }}
        />
      </Map>

      {loading && (
        <div className="absolute top-4 right-4 z-[1000] h-10 w-10 bg-black border border-white/20 rounded-lg flex items-center justify-center">
          <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent"></div>
        </div>
      )}

      {/* Info Panel */}
      {regionData && selectedPoint && (
        <div className="absolute top-4 right-4 bg-black text-white p-4 rounded-lg shadow-xl z-[1000] max-w-md max-h-[80vh] overflow-y-auto custom-scrollbar">
          <div className="flex justify-between items-start mb-4">
            <div>
              <h2 className="text-lg font-bold">{selectedPoint.address || 'Analysis Results'}</h2>
              <p className="text-sm text-stone-300">
                {selectedPoint.lat.toFixed(4)}, {selectedPoint.lon.toFixed(4)}
              </p>
            </div>
            <button
              onClick={() => {
                setSelectedPoint(null);
                setRegionData(null);
                setSearchQuery('');
                mapRef.current?.flyTo({
                  center: GTA_CENTER,
                  zoom: 10,
                  pitch: 45,
                  duration: 1500,
                });
              }}
              className="text-stone-300 hover:text-white text-xl cursor-pointer"
            >
              ×
            </button>
          </div>

          {/* Content */}
          <div className="space-y-3">
              {/* Panorama Preview */}
              {panoramaLoading ? (
                <div className="bg-stone-800/50 border border-stone-700 rounded-lg p-4 flex items-center justify-center">
                  <div className="flex items-center gap-3">
                    <div className="animate-spin rounded-full h-5 w-5 border-2 border-white border-t-transparent"></div>
                    <span className="text-sm text-stone-300">Generating panorama...</span>
                  </div>
                </div>
              ) : panoramaPath ? (
                <div 
                  className="relative w-full border border-stone-700 rounded-lg overflow-hidden cursor-pointer group"
                  onClick={() => setPanoramaViewerOpen(true)}
                >
                  <img 
                    src={`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/${panoramaPath}`}
                    alt="Street View Panorama"
                    className="w-full h-32 object-cover"
                    onError={(e) => {
                      console.error('Failed to load panorama thumbnail:', e);
                    }}
                  />
                  <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex items-center justify-center">
                    <span className="text-white text-sm font-medium">Explore →</span>
                  </div>
                </div>
              ) : null}

              {/* Ecological Metrics */}
              {regionData.ecological_score && (
                <div className="bg-stone-800/50 rounded-lg p-3 space-y-3">
                  <h3 className="text-xs font-semibold text-stone-400 uppercase tracking-wider">Ecological Metrics</h3>
                
                {/* Circular Progress Indicators */}
                <div className="grid grid-cols-4 gap-3 mb-4">
                  {/* Green Space Quality */}
                  <div className="flex flex-col items-center">
                    <div className="relative w-16 h-16">
                      <svg className="transform -rotate-90 w-16 h-16">
                        <circle cx="32" cy="32" r="28" stroke="currentColor" strokeWidth="6" fill="none" className="text-stone-700" />
                        <circle 
                          cx="32" cy="32" r="28" 
                          stroke="currentColor" 
                          strokeWidth="6" 
                          fill="none" 
                          strokeDasharray={`${2 * Math.PI * 28}`}
                          strokeDashoffset={animateMetrics ? `${2 * Math.PI * 28 * (1 - (regionData.ecological_score.metrics?.green_space_proximity?.score || 0) / 10)}` : `${2 * Math.PI * 28}`}
                          className="text-emerald-400 transition-all duration-1000"
                          strokeLinecap="round"
                        />
                      </svg>
                      <div className="absolute inset-0 flex items-center justify-center">
                        <span className="text-sm font-bold text-white">
                          {Math.round(((regionData.ecological_score.metrics?.green_space_proximity?.score || 0) / 10) * 100)}%
                        </span>
                      </div>
                    </div>
                    <p className="text-xs text-stone-400 mt-2 text-center uppercase tracking-wide">Green Space</p>
                  </div>

                  {/* Environmental Quality */}
                  <div className="flex flex-col items-center">
                    <div className="relative w-16 h-16">
                      <svg className="transform -rotate-90 w-16 h-16">
                        <circle cx="32" cy="32" r="28" stroke="currentColor" strokeWidth="6" fill="none" className="text-stone-700" />
                        <circle 
                          cx="32" cy="32" r="28" 
                          stroke="currentColor" 
                          strokeWidth="6" 
                          fill="none" 
                          strokeDasharray={`${2 * Math.PI * 28}`}
                          strokeDashoffset={animateMetrics ? `${2 * Math.PI * 28 * (1 - (regionData.ecological_score.metrics?.environmental_area_proximity?.score || 0) / 10)}` : `${2 * Math.PI * 28}`}
                          className="text-amber-400 transition-all duration-1000"
                          strokeLinecap="round"
                        />
                      </svg>
                      <div className="absolute inset-0 flex items-center justify-center">
                        <span className="text-sm font-bold text-white">
                          {Math.round(((regionData.ecological_score.metrics?.environmental_area_proximity?.score || 0) / 10) * 100)}%
                        </span>
                      </div>
                    </div>
                    <p className="text-xs text-stone-400 mt-2 text-center uppercase tracking-wide">Environment</p>
                  </div>

                  {/* Tree Coverage */}
                  <div className="flex flex-col items-center">
                    <div className="relative w-16 h-16">
                      <svg className="transform -rotate-90 w-16 h-16">
                        <circle cx="32" cy="32" r="28" stroke="currentColor" strokeWidth="6" fill="none" className="text-stone-700" />
                        <circle 
                          cx="32" cy="32" r="28" 
                          stroke="currentColor" 
                          strokeWidth="6" 
                          fill="none" 
                          strokeDasharray={`${2 * Math.PI * 28}`}
                          strokeDashoffset={animateMetrics ? `${2 * Math.PI * 28 * (1 - (regionData.ecological_score.metrics?.street_tree_count?.score || 0) / 10)}` : `${2 * Math.PI * 28}`}
                          className="text-rose-400 transition-all duration-1000"
                          strokeLinecap="round"
                        />
                      </svg>
                      <div className="absolute inset-0 flex items-center justify-center">
                        <span className="text-sm font-bold text-white">
                          {Math.round(((regionData.ecological_score.metrics?.street_tree_count?.score || 0) / 10) * 100)}%
                        </span>
                      </div>
                    </div>
                    <p className="text-xs text-stone-400 mt-2 text-center uppercase tracking-wide">Tree Cover</p>
                  </div>

                  {/* Overall Score */}
                  <div className="flex flex-col items-center">
                    <div className="relative w-16 h-16">
                      <svg className="transform -rotate-90 w-16 h-16">
                        <circle cx="32" cy="32" r="28" stroke="currentColor" strokeWidth="6" fill="none" className="text-stone-700" />
                        <circle 
                          cx="32" cy="32" r="28" 
                          stroke="currentColor" 
                          strokeWidth="6" 
                          fill="none" 
                          strokeDasharray={`${2 * Math.PI * 28}`}
                          strokeDashoffset={animateMetrics ? `${2 * Math.PI * 28 * (1 - (regionData.ecological_score.normalized_score || 0) / 10)}` : `${2 * Math.PI * 28}`}
                          className="text-sky-400 transition-all duration-1000"
                          strokeLinecap="round"
                        />
                      </svg>
                      <div className="absolute inset-0 flex items-center justify-center">
                        <span className="text-sm font-bold text-white">
                          {Math.round(((regionData.ecological_score.normalized_score || 0) / 10) * 100)}%
                        </span>
                      </div>
                    </div>
                    <p className="text-xs text-stone-400 mt-2 text-center uppercase tracking-wide">Overall</p>
                  </div>
                </div>

                {/* Status Indicators */}
                <div className="grid grid-cols-2 gap-3 pt-3 border-t border-stone-700">
                  <div className="bg-stone-800/50 rounded p-2">
                    <p className="text-xs text-stone-400 uppercase tracking-wide mb-1">Status</p>
                    <p className="text-sm font-semibold text-white">
                      {regionData.ecological_score.normalized_score >= 7 ? 'Resilient' : 
                       regionData.ecological_score.normalized_score >= 4 ? 'Moderate' : 'Vulnerable'}
                    </p>
                  </div>
                  <div className="bg-stone-800/50 rounded p-2">
                    <p className="text-xs text-stone-400 uppercase tracking-wide mb-1">Priority</p>
                    <p className="text-sm font-semibold text-white">
                      {regionData.ecological_score.rule_compliance?.within_300m_green_space ? 'Priority B' : 'Priority A'}
                    </p>
                  </div>
                </div>
              </div>
            )}

              {/* Nearby Locations Card */}
              <div className="bg-stone-800/50 rounded-lg p-3 space-y-2">
                <h3 className="text-xs font-semibold text-stone-400 uppercase tracking-wider mb-2">Nearby Locations</h3>
                
                {/* Green Space */}
                <div>
                  <p className="text-xs text-stone-400 mb-0.5">Green Space</p>
                  {regionData.nearby_data.green_spaces && regionData.nearby_data.green_spaces.length > 0 ? (
                    <p className="text-sm font-medium text-white truncate">
                      {toTitleCase(regionData.nearby_data.green_spaces[0].name)}
                      <span className="text-stone-400 text-xs ml-1">
                        ({(regionData.nearby_data.green_spaces[0].distance / 1000).toFixed(2)} km)
                      </span>
                    </p>
                  ) : (
                    <p className="text-xs text-stone-500">None nearby</p>
                  )}
                </div>

                {/* Environmental Area */}
                <div>
                  <p className="text-xs text-stone-400 mb-0.5">Environmental Area</p>
                  {regionData.nearby_data.environmental_areas && regionData.nearby_data.environmental_areas.length > 0 ? (
                    <p className="text-sm font-medium text-white truncate">
                      {toTitleCase(regionData.nearby_data.environmental_areas[0].name)}
                      <span className="text-stone-400 text-xs ml-1">
                        ({(regionData.nearby_data.environmental_areas[0].distance / 1000).toFixed(2)} km)
                      </span>
                    </p>
                  ) : (
                    <p className="text-xs text-stone-500">None nearby</p>
                  )}
                </div>
              </div>

          {/* Indigenous Context Card */}
          <div className="bg-stone-800/50 rounded-lg p-3 space-y-2">
            <h3 className="text-xs font-semibold text-stone-400 uppercase tracking-wider mb-2">Indigenous Context</h3>
                
                {/* First Nation */}
                <div>
                  <p className="text-xs text-stone-400 mb-0.5">First Nation</p>
                  {regionData.nearest_first_nation ? (
                    <p className="text-sm font-medium text-white truncate">
                      {regionData.nearest_first_nation.name}
                      <span className="text-stone-400 text-xs ml-1">
                        ({(regionData.nearest_first_nation.distance / 1000).toFixed(2)} km)
                      </span>
                    </p>
                  ) : (
                    <p className="text-xs text-stone-500">None nearby</p>
                  )}
                </div>

                {/* Territory */}
                <div>
                  <p className="text-xs text-stone-400 mb-0.5">Territory</p>
                  {regionData.indigenous_territory ? (
                    <p className="text-sm font-medium text-white">{regionData.indigenous_territory.name}</p>
                  ) : (
                    <p className="text-xs text-stone-500">Not in a territory</p>
                  )}
                </div>

                {/* Treaties */}
                <div>
                  <p className="text-xs text-stone-400 mb-0.5">Treaty</p>
                  {regionData.nearby_data.indigenous_treaties && regionData.nearby_data.indigenous_treaties.length > 0 ? (
                    <p className="text-sm font-medium text-white">{regionData.nearby_data.indigenous_treaties[0].name}</p>
                  ) : (
                    <p className="text-xs text-stone-500">Not in a treaty area</p>
                  )}
                </div>

                {/* Languages */}
                <div>
                  <p className="text-xs text-stone-400 mb-0.5">Language</p>
                  {regionData.nearby_data.indigenous_languages && regionData.nearby_data.indigenous_languages.length > 0 ? (
                    <p className="text-sm font-medium text-white">{regionData.nearby_data.indigenous_languages[0].name}</p>
                  ) : (
                    <p className="text-xs text-stone-500">Not in a language region</p>
                  )}
                </div>
              </div>
          </div>
        </div>
      )}

      {/* Agent Modal */}
      <AgentModal
        isOpen={agentModalOpen}
        onClose={() => setAgentModalOpen(false)}
        panoramaPath={panoramaPath}
        locationData={selectedPoint ? {
          lat: selectedPoint.lat,
          lon: selectedPoint.lon,
          address: selectedPoint.address || selectedPoint.name,
          territory: regionData?.indigenous_territory?.name
        } : null}
      />

      {/* 360° Panorama Viewer */}
      <PanoramaViewer
        isOpen={panoramaViewerOpen}
        onClose={() => setPanoramaViewerOpen(false)}
        panoramaPath={panoramaPath}
        locationData={selectedPoint ? {
          lat: selectedPoint.lat,
          lon: selectedPoint.lon,
          address: selectedPoint.address || selectedPoint.name,
          territory: regionData?.indigenous_territory?.name
        } : null}
      />
    </div>
  );
}
