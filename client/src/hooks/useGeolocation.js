import { useCallback, useEffect, useRef, useState } from 'react';

const STATUS = {
  UNSUPPORTED: 'unsupported',
  IDLE: 'idle',         // не запрашивали permission
  PROMPT: 'prompt',     // система знает что нужно спросить
  ASKING: 'asking',     // ждём ответа пользователя
  GRANTED: 'granted',   // permission получен, watcher работает
  DENIED: 'denied',     // пользователь отказал
  ERROR: 'error',
};

/**
 * Хук для постоянного отслеживания геолокации через navigator.geolocation.watchPosition.
 *
 * Без таймаутов и без перезапросов permission — один раз спросили, дальше
 * координаты текут в state. coords всегда отражает самое свежее обновление.
 */
export function useGeolocation({ enableHighAccuracy = true, maximumAge = 30000 } = {}) {
  const supported =
    typeof navigator !== 'undefined' && !!navigator.geolocation && typeof window !== 'undefined';

  const [coords, setCoords] = useState(null); // {lat, lon, accuracy, ts}
  const [status, setStatus] = useState(supported ? STATUS.IDLE : STATUS.UNSUPPORTED);
  const [error, setError] = useState(null);
  const watchIdRef = useRef(null);

  const stopWatch = useCallback(() => {
    if (watchIdRef.current != null && navigator.geolocation) {
      navigator.geolocation.clearWatch(watchIdRef.current);
      watchIdRef.current = null;
    }
  }, []);

  const startWatch = useCallback(() => {
    if (!supported || watchIdRef.current != null) return;
    setStatus(STATUS.ASKING);
    watchIdRef.current = navigator.geolocation.watchPosition(
      (pos) => {
        setError(null);
        setStatus(STATUS.GRANTED);
        setCoords({
          lat: pos.coords.latitude,
          lon: pos.coords.longitude,
          accuracy: pos.coords.accuracy,
          ts: pos.timestamp,
        });
      },
      (err) => {
        if (err && err.code === 1) {
          setStatus(STATUS.DENIED);
          setError('Доступ к геолокации запрещён. Можно разрешить в настройках браузера.');
        } else {
          setStatus(STATUS.ERROR);
          setError(err?.message || 'Не удалось получить геолокацию.');
        }
      },
      {
        enableHighAccuracy,
        maximumAge,
        // НЕТ таймаута — ждём столько сколько нужно. Watcher всё равно крутится.
      }
    );
  }, [supported, enableHighAccuracy, maximumAge]);

  // Если permission уже granted при загрузке — стартуем сами.
  useEffect(() => {
    if (!supported) return undefined;
    let cancelled = false;
    if (navigator.permissions?.query) {
      navigator.permissions
        .query({ name: 'geolocation' })
        .then((result) => {
          if (cancelled) return;
          if (result.state === 'granted') {
            startWatch();
          } else if (result.state === 'prompt') {
            setStatus(STATUS.PROMPT);
          } else if (result.state === 'denied') {
            setStatus(STATUS.DENIED);
          }
          // дальше — слушаем смену permission
          result.onchange = () => {
            if (result.state === 'granted' && watchIdRef.current == null) startWatch();
            if (result.state === 'denied') {
              stopWatch();
              setStatus(STATUS.DENIED);
            }
          };
        })
        .catch(() => {
          // permissions API нет — поставим prompt
          setStatus(STATUS.PROMPT);
        });
    } else {
      setStatus(STATUS.PROMPT);
    }
    return () => {
      cancelled = true;
      stopWatch();
    };
  }, [supported, startWatch, stopWatch]);

  const request = useCallback(() => {
    if (!supported) return;
    if (status === STATUS.GRANTED) return;
    startWatch();
  }, [supported, status, startWatch]);

  return {
    coords,
    status,
    error,
    request,
    isSupported: supported,
  };
}

useGeolocation.STATUS = STATUS;
