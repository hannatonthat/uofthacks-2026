'use client';

import { useEffect, useRef, useState } from 'react';
import Map, { MapRef, Layer, type MapMouseEvent } from 'react-map-gl/mapbox';
import { getRegionData, RegionData, generatePanorama } from '@/lib/api';
import AgentModal from './AgentModal';
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

export default function Map3D() {
  const mapRef = useRef<MapRef>(null);
  const [selectedPoint, setSelectedPoint] = useState<MapPoint | null>(null);
  const [regionData, setRegionData] = useState<RegionData | null>(null);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchSuggestions, setSearchSuggestions] = useState<any[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [panoramaPath, setPanoramaPath] = useState<string | null>(null);
  const [panoramaLoading, setPanoramaLoading] = useState(false);
  const [agentModalOpen, setAgentModalOpen] = useState(false);
  const [viewport, setViewport] = useState({
    latitude: GTA_CENTER[1],
    longitude: GTA_CENTER[0],
    zoom: 10,
    pitch: 45,  // Tilted view
    bearing: 0,
    minZoom: 9,   // Prevent zooming out too far
    maxZoom: 18,  // Max zoom level
  });

  // Initial fly-to animation
  useEffect(() => {
    const timer = setTimeout(() => {
      mapRef.current?.flyTo({
        center: GTA_CENTER,
        zoom: 10,
        pitch: 45,
        duration: 2000,
        essential: true,
      });
    }, 500);

    return () => clearTimeout(timer);
  }, []);

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
        `bbox=${GTA_BOUNDS[0][0]},${GTA_BOUNDS[0][1]},${GTA_BOUNDS[1][0]},${GTA_BOUNDS[1][1]}&` +
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
      const panoramaData = await generatePanorama(lat, lng);
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
    
    // Check if clicked within GTA bounds
    if (
      lngLat.lng < GTA_BOUNDS[0][0] ||
      lngLat.lng > GTA_BOUNDS[1][0] ||
      lngLat.lat < GTA_BOUNDS[0][1] ||
      lngLat.lat > GTA_BOUNDS[1][1]
    ) {
      console.log('Click outside GTA bounds');
      return;
    }

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
      const panoramaData = await generatePanorama(lngLat.lat, lngLat.lng);
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
      {/* Search Bar */}
      <div className="absolute top-4 left-4 z-[1000] w-80">
        <div className="relative">
          <input
            type="text"
            value={searchQuery}
            onChange={handleSearchChange}
            onFocus={() => searchSuggestions.length > 0 && setShowSuggestions(true)}
            placeholder="Search address in GTA..."
            className="w-full px-4 py-3 bg-black/90 text-white border border-gray-700 rounded-lg focus:outline-none focus:border-gray-500 placeholder-gray-500"
          />
          
          {/* Search Suggestions Dropdown */}
          {showSuggestions && searchSuggestions.length > 0 && (
            <div className="absolute top-full mt-2 w-full bg-black/95 border border-gray-700 rounded-lg overflow-hidden shadow-xl">
              {searchSuggestions.map((suggestion, index) => (
                <button
                  key={index}
                  onClick={() => handleSelectAddress(suggestion)}
                  className="w-full px-4 py-3 text-left text-white hover:bg-gray-800 border-b border-gray-800 last:border-b-0 transition-colors"
                >
                  <div className="font-medium text-sm">{suggestion.text}</div>
                  <div className="text-xs text-gray-400 mt-1">{suggestion.place_name}</div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      <Map
        ref={mapRef}
        {...viewport}
        onMove={(evt) => setViewport(evt.viewState)}
        onClick={handleMapClick}
        mapStyle="mapbox://styles/mapbox/dark-v11"
        mapboxAccessToken={process.env.NEXT_PUBLIC_MAPBOX_TOKEN}
        style={{ width: '100%', height: '100%' }}
        maxBounds={GTA_BOUNDS}
        maxBoundsViscosity={1.0}
        renderWorldCopies={false}
        antialias={true}
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
        <div className="absolute top-4 right-4 z-[1000] bg-black text-white px-4 py-2 rounded">
          Loading data...
        </div>
      )}

      {/* Info Panel */}
      {regionData && selectedPoint && (
        <div className="absolute top-4 right-4 bg-black text-white p-4 rounded-lg shadow-xl z-[1000] max-w-md max-h-[80vh] overflow-y-auto">
          <div className="flex justify-between items-start mb-4">
            <div>
              <h2 className="text-lg font-bold">{selectedPoint.address || 'Analysis Results'}</h2>
              <p className="text-sm text-gray-300">
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
              className="text-gray-300 hover:text-white text-xl"
            >
              ×
            </button>
          </div>

          {/* Panorama Preview */}
          {panoramaLoading ? (
            <div className="mb-4 bg-gray-800 border border-gray-700 rounded-lg p-4 flex items-center justify-center">
              <div className="flex items-center gap-3">
                <div className="animate-spin rounded-full h-5 w-5 border-2 border-white border-t-transparent"></div>
                <span className="text-sm text-gray-300">Generating panorama...</span>
              </div>
            </div>
          ) : panoramaPath ? (
            <div className="mb-4 border border-gray-700 rounded-lg overflow-hidden">
              <img 
                src={`http://localhost:8001/${panoramaPath}`}
                alt="Street View Panorama"
                className="w-full h-32 object-cover"
              />
            </div>
          ) : null}

          <div className="space-y-3 text-sm">
            {/* Nearest Green Space */}
            <div>
              <p className="text-gray-400">Nearest Green Space:</p>
              {regionData.nearby_data.green_spaces && regionData.nearby_data.green_spaces.length > 0 ? (
                <p className="font-medium text-white">
                  {regionData.nearby_data.green_spaces[0].name}
                  <span className="text-gray-400 text-xs ml-2">
                    ({(regionData.nearby_data.green_spaces[0].distance / 1000).toFixed(2)} km)
                  </span>
                </p>
              ) : (
                <p className="text-gray-500 text-xs">None nearby</p>
              )}
            </div>

            {/* Nearest Environmental Area */}
            <div>
              <p className="text-gray-400">Nearest Environmental Area:</p>
              {regionData.nearby_data.environmental_areas && regionData.nearby_data.environmental_areas.length > 0 ? (
                <p className="font-medium text-white">
                  {regionData.nearby_data.environmental_areas[0].name}
                  <span className="text-gray-400 text-xs ml-2">
                    ({(regionData.nearby_data.environmental_areas[0].distance / 1000).toFixed(2)} km)
                  </span>
                </p>
              ) : (
                <p className="text-gray-500 text-xs">None nearby</p>
              )}
            </div>

            {/* Nearest First Nation */}
            <div>
              <p className="text-gray-400">Nearest First Nation:</p>
              {regionData.nearest_first_nation ? (
                <p className="font-medium text-white">
                  {regionData.nearest_first_nation.name}
                  <span className="text-gray-400 text-xs ml-2">
                    ({(regionData.nearest_first_nation.distance / 1000).toFixed(2)} km)
                  </span>
                </p>
              ) : (
                <p className="text-gray-500 text-xs">None nearby</p>
              )}
            </div>

            <div className="border-t border-gray-700 pt-3 mt-3">
              {/* Indigenous Territory */}
              <div>
                <p className="text-gray-400">Indigenous Territory:</p>
                {regionData.indigenous_territory ? (
                  <p className="font-medium text-white">{regionData.indigenous_territory.name}</p>
                ) : (
                  <p className="text-gray-500 text-xs">Not in a territory</p>
                )}
              </div>

              {/* Treaties */}
              <div className="mt-3">
                <p className="text-gray-400">Treaties:</p>
                {regionData.nearby_data.indigenous_treaties && regionData.nearby_data.indigenous_treaties.length > 0 ? (
                  <p className="font-medium text-white">{regionData.nearby_data.indigenous_treaties[0].name}</p>
                ) : (
                  <p className="text-gray-500 text-xs">Not in a treaty area</p>
                )}
              </div>

              {/* Languages */}
              <div className="mt-3">
                <p className="text-gray-400">Indigenous Language:</p>
                {regionData.nearby_data.indigenous_languages && regionData.nearby_data.indigenous_languages.length > 0 ? (
                  <p className="font-medium text-white">{regionData.nearby_data.indigenous_languages[0].name}</p>
                ) : (
                  <p className="text-gray-500 text-xs">Not in a language region</p>
                )}
              </div>
            </div>

            {/* Ecological Sensitivity Score */}
            {regionData.ecological_score && (
              <div className="border-t border-gray-700 pt-3 mt-3">
                <div>
                  <p className="text-gray-400">Ecological Sensitivity Score:</p>
                  <div className="flex items-baseline gap-2">
                    <p className="text-2xl font-bold text-white">
                      {regionData.ecological_score.normalized_score?.toFixed(1) || '0.0'}
                    </p>
                    <p className="text-sm text-gray-400">/ 10</p>
                    <p className="text-xs text-gray-500">
                      ({regionData.ecological_score.total_score?.toFixed(1) || '0'} / 30 raw)
                    </p>
                  </div>
                </div>

                {/* 3-30-300 Rule Compliance */}
                {regionData.ecological_score.rule_compliance && (
                  <div className="mt-2 space-y-1">
                    <p className="text-xs text-gray-400">3-30-300 Rule Status:</p>
                    <div className="flex items-center gap-2 text-xs">
                      <span className={regionData.ecological_score.rule_compliance.has_3_trees ? 'text-green-400' : 'text-red-400'}>
                        {regionData.ecological_score.rule_compliance.has_3_trees ? '✓' : '✗'}
                      </span>
                      <span className="text-gray-300">
                        {regionData.ecological_score.metrics?.street_tree_count?.count || 0} trees visible
                      </span>
                    </div>
                    <div className="flex items-center gap-2 text-xs">
                      <span className={regionData.ecological_score.rule_compliance.within_300m_green_space ? 'text-green-400' : 'text-red-400'}>
                        {regionData.ecological_score.rule_compliance.within_300m_green_space ? '✓' : '✗'}
                      </span>
                      <span className="text-gray-300">Within 300m of green space</span>
                    </div>
                  </div>
                )}

                {/* Detailed Metrics */}
                <div className="mt-3 space-y-2 text-xs">
                  <div>
                    <p className="text-gray-500">Environmental Area Proximity:</p>
                    <p className="text-white">
                      {regionData.ecological_score.metrics?.environmental_area_proximity?.score?.toFixed(1) || '0.0'} / 10
                      {regionData.ecological_score.metrics?.environmental_area_proximity?.distance_meters && (
                        <span className="text-gray-400 ml-2">
                          ({(regionData.ecological_score.metrics.environmental_area_proximity.distance_meters).toFixed(0)}m away)
                        </span>
                      )}
                    </p>
                  </div>
                  
                  <div>
                    <p className="text-gray-500">Green Space Proximity:</p>
                    <p className="text-white">
                      {regionData.ecological_score.metrics?.green_space_proximity?.score?.toFixed(1) || '0.0'} / 10
                      {regionData.ecological_score.metrics?.green_space_proximity?.distance_meters && (
                        <span className="text-gray-400 ml-2">
                          ({(regionData.ecological_score.metrics.green_space_proximity.distance_meters).toFixed(0)}m away)
                        </span>
                      )}
                    </p>
                  </div>
                  
                  <div>
                    <p className="text-gray-500">Street Tree Count:</p>
                    <p className="text-white">
                      {regionData.ecological_score.metrics?.street_tree_count?.score?.toFixed(1) || '0.0'} / 10
                      <span className="text-gray-400 ml-2">
                        ({regionData.ecological_score.metrics?.street_tree_count?.count || 0} trees)
                      </span>
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* AI Agents Button */}
            <div className="border-t border-gray-700 pt-3 mt-3">
              <button
                onClick={() => setAgentModalOpen(true)}
                className="w-full bg-blue-600 hover:bg-blue-700 text-white py-3 px-4 rounded-lg font-medium transition-colors"
              >
                Open AI Agents
              </button>
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
    </div>
  );
}
