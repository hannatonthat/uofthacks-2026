'use client';

import dynamic from 'next/dynamic';

// Dynamic import to avoid SSR issues with Leaflet
const Map = dynamic(() => import('@/components/Map'), {
  ssr: false,
  loading: () => (
    <div className="w-full h-screen flex items-center justify-center">
      <p>Loading map...</p>
    </div>
  ),
});

export default function Home() {
  return (
    <main className="h-screen">
      <Map />
    </main>
  );
}
