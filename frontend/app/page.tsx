'use client';

import dynamic from 'next/dynamic';

// Dynamic import for Mapbox GL 3D map
const Map3D = dynamic(() => import('@/components/Map3D'), {
  ssr: false,
  loading: () => (
    <div className="w-full h-screen flex items-center justify-center bg-gray-900 text-white">
      <p>Loading 3D map...</p>
    </div>
  ),
});

export default function Home() {
  return (
    <main className="h-screen relative">
      {/* Navigation Bar */}
      <div className="absolute top-0 left-0 right-0 z-20 bg-gradient-to-b from-black/80 to-transparent p-4">
        <div className="flex justify-between items-center max-w-7xl mx-auto">
          <div>
            <h1 className="text-xl font-bold text-white">Indigenous Land Perspectives</h1>
            <p className="text-gray-300 text-xs">Explore territories and sustainable practices</p>
          </div>
          <div className="flex gap-3">
            <a 
              href="/insights"
              className="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-lg transition-colors flex items-center gap-2 text-sm font-semibold"
            >
              <span>🎯</span>
              <span className="hidden sm:inline">Your Insights</span>
            </a>
            <a 
              href="/analytics"
              className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg transition-colors flex items-center gap-2 text-sm font-semibold"
            >
              <span>📊</span>
              <span className="hidden sm:inline">Analytics</span>
            </a>
          </div>
        </div>
      </div>
      
      <Map3D />
    </main>
  );
}
