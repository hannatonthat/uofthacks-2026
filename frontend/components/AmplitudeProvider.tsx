'use client';

import { useEffect } from 'react';
import { initAmplitude, trackSessionStart, trackSessionEnd } from '@/lib/amplitude';

/**
 * Amplitude Provider Component
 * Initializes Amplitude analytics and tracks session lifecycle
 */
export default function AmplitudeProvider({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    // Initialize Amplitude on client-side mount
    initAmplitude();
    
    // Track session start
    trackSessionStart();
    
    // Track session duration on unmount
    const sessionStartTime = Date.now();
    
    return () => {
      const duration = Math.floor((Date.now() - sessionStartTime) / 1000);
      trackSessionEnd(duration);
    };
  }, []);
  
  return <>{children}</>;
}
