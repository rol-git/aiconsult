import React, { createContext, useContext, useMemo } from 'react';

import { useGeolocation } from '../hooks/useGeolocation';

const GeoContext = createContext(null);

export function GeoProvider({ children }) {
  const geo = useGeolocation();

  const value = useMemo(
    () => ({
      coords: geo.coords,
      status: geo.status,
      error: geo.error,
      request: geo.request,
      isSupported: geo.isSupported,
      /** Готовый payload для отправки на сервер (или null). */
      locationPayload: geo.coords
        ? {
            lat: geo.coords.lat,
            lon: geo.coords.lon,
            accuracy: geo.coords.accuracy,
            source: 'browser',
          }
        : null,
    }),
    [geo.coords, geo.status, geo.error, geo.request, geo.isSupported]
  );

  return <GeoContext.Provider value={value}>{children}</GeoContext.Provider>;
}

export function useGeo() {
  const ctx = useContext(GeoContext);
  if (!ctx) {
    throw new Error('useGeo must be used within <GeoProvider>');
  }
  return ctx;
}
