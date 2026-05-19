import { useCallback, useState } from 'react';
import type { GeoLocation } from '@/types';

export function useGeo() {
  const [location, setLocation] = useState<GeoLocation | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const request = useCallback((): Promise<GeoLocation | null> => {
    return new Promise((resolve) => {
      if (!('geolocation' in navigator)) {
        setError('Геолокация не поддерживается');
        resolve(null);
        return;
      }
      setLoading(true);
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          const loc: GeoLocation = {
            lat: pos.coords.latitude,
            lon: pos.coords.longitude,
            accuracy: pos.coords.accuracy,
            source: 'browser',
          };
          setLocation(loc);
          setError(null);
          setLoading(false);
          resolve(loc);
        },
        (err) => {
          setError(err.message || 'Не удалось получить геопозицию');
          setLoading(false);
          resolve(null);
        },
        { enableHighAccuracy: false, timeout: 10000, maximumAge: 60000 },
      );
    });
  }, []);

  const clear = useCallback(() => {
    setLocation(null);
    setError(null);
  }, []);

  return { location, error, loading, request, clear };
}
