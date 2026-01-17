'use client';

import { useEffect, useState } from 'react';
import { MapContainer, TileLayer, CircleMarker, Popup } from 'react-leaflet';
import type { LatLngExpression } from 'leaflet';
import { getMapPoints, getRegionData, MapPoint, RegionData } from '@/lib/api';
import 'leaflet/dist/leaflet.css';
import type { ReactElement } from 'react';

// GTA center coordinates and bounds
const GTA_CENTER: LatLngExpression = [43.7, -79.4];
const GTA_BOUNDS: [[number, number], [number, number]] = [
  [43.4, -80.0],  // Southwest corner (min_lat, min_lon)
  [44.1, -78.8]   // Northeast corner (max_lat, max_lon)
];

// Color based on data type
function getTypeColor(type: string): string {
  switch (type) {
    case 'green_space':
      return '#22c55e'; // green-500
    case 'environmental':
      return '#84cc16'; // lime-500
    case 'first_nation':
      return '#f59e0b'; // amber-500
    case 'grid_point':
      return '#6b7280'; // gray-500 - neutral for grid
    default:
      return '#3b82f6'; // blue-500
  }
}

interface GridMarkersProps {
  points: MapPoint[];
  onPointClick: (point: MapPoint) => void;
}

function GridMarkers({ points, onPointClick }: GridMarkersProps): ReactElement {
  return (
    <>
      {points.map((point) => {
        const color = getTypeColor(point.type);
        const isGridPoint = point.type === 'grid_point';
        
        return (
          <CircleMarker
            key={point.id}
            center={[point.lat, point.lon]}
            radius={isGridPoint ? 4 : 6}
            pathOptions={{ 
              color: color, 
              fillColor: color, 
              fillOpacity: isGridPoint ? 0.4 : 0.7,
              weight: isGridPoint ? 1 : 2
            }}
            eventHandlers={{
              click: () => onPointClick(point)
            }}
          >
            <Popup>
              <div className="p-2">
                <p className="text-xs font-semibold">{point.name}</p>
                <p className="text-xs text-gray-600">
                  {isGridPoint ? 'Click to explore this area' : point.type.replace(/_/g, ' ')}
                </p>
              </div>
            </Popup>
          </CircleMarker>
        );
      })}
    </>
  );
}

export default function Map() {
  const [points, setPoints] = useState<MapPoint[]>([]);
  const [selectedPoint, setSelectedPoint] = useState<MapPoint | null>(null);
  const [regionData, setRegionData] = useState<RegionData | null>(null);
  const [loading, setLoading] = useState(true);
  
  // Load points on mount - now FAST (just sampling, no complex queries)
  useEffect(() => {
    async function loadPoints() {
      try {
        const data = await getMapPoints(100); // 100 points from actual locations
        setPoints(data);
        console.log(`Loaded ${data.length} points on map`);
      } catch (error) {
        console.error('Error loading map points:', error);
        alert('Error loading data. Make sure backend is running on port 8001.');
      } finally {
        setLoading(false);
      }
    }
    
    loadPoints();
  }, []);
  
  // When a point is clicked, fetch all nearby data
  async function handlePointClick(point: MapPoint) {
    setSelectedPoint(point);
    setLoading(true);
    
    try {
      const data = await getRegionData(point.lat, point.lon, 500);
      setRegionData(data);
    } catch (error) {
      console.error('Error fetching region data:', error);
      setRegionData(null);
    } finally {
      setLoading(false);
    }
  }
  
  return (
    <div className="relative w-full h-full">
      {loading && (
        <div className="absolute top-4 right-4 z-[1000] bg-black text-white px-4 py-2 rounded">
          Loading grid...
        </div>
      )}
      
      <MapContainer
        center={GTA_CENTER}
        zoom={10}
        maxBounds={GTA_BOUNDS}
        maxBoundsViscosity={1.0}
        minZoom={9}
        style={{ width: '100%', height: '100%' }}
        className="z-0"
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        
        <GridMarkers points={points} onPointClick={handlePointClick} />
      </MapContainer>
      
      {/* Simple Dark Info Panel */}
      {regionData && selectedPoint && (
        <div className="absolute top-4 right-4 bg-black text-white p-4 rounded-lg shadow-xl z-[1000] max-w-md max-h-96 overflow-y-auto">
          <div className="flex justify-between items-start mb-4">
            <div>
              <h2 className="text-lg font-bold">{selectedPoint.name}</h2>
              <p className="text-sm text-gray-300">
                {selectedPoint.lat.toFixed(4)}, {selectedPoint.lon.toFixed(4)}
              </p>
            </div>
            <button
              onClick={() => {
                setSelectedPoint(null);
                setRegionData(null);
              }}
              className="text-gray-300 hover:text-white text-xl"
            >
              ×
            </button>
          </div>
          
          <div className="space-y-3 text-sm">
            {/* Nearest from EACH Collection */}
            
            {/* 1. Nearest Green Space */}
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
                <p className="text-gray-500 text-xs">Loading...</p>
              )}
            </div>
            
            {/* 2. Nearest Environmental Area */}
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
                <p className="text-gray-500 text-xs">Loading...</p>
              )}
            </div>
            
            {/* 3. Nearest First Nation */}
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
                <p className="text-gray-500 text-xs">Loading...</p>
              )}
            </div>
            
            <div className="border-t border-gray-700 pt-3 mt-3">
              {/* 4. Indigenous Territory (contains this point) */}
              <div>
                <p className="text-gray-400">Indigenous Territory:</p>
                {regionData.indigenous_territory ? (
                  <p className="font-medium text-white">{regionData.indigenous_territory.name}</p>
                ) : (
                  <p className="text-gray-500 text-xs">Not in a territory</p>
                )}
              </div>
              
              {/* 5. Treaties */}
              <div className="mt-3">
                <p className="text-gray-400">Treaties:</p>
                {regionData.nearby_data.indigenous_treaties && regionData.nearby_data.indigenous_treaties.length > 0 ? (
                  <p className="font-medium text-white">{regionData.nearby_data.indigenous_treaties[0].name}</p>
                ) : (
                  <p className="text-gray-500 text-xs">Not in a treaty area</p>
                )}
              </div>
              
              {/* 6. Languages */}
              <div className="mt-3">
                <p className="text-gray-400">Indigenous Language:</p>
                {regionData.nearby_data.indigenous_languages && regionData.nearby_data.indigenous_languages.length > 0 ? (
                  <p className="font-medium text-white">{regionData.nearby_data.indigenous_languages[0].name}</p>
                ) : (
                  <p className="text-gray-500 text-xs">Not in a language region</p>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
