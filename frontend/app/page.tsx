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
    <main className="h-screen">
      <Map3D />
    </main>
  );
}
