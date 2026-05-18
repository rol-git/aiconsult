import React from 'react';

import { useGeo } from '../context/GeoContext';
import './GeoBanner.css';

const STATUS = {
  GRANTED: 'granted',
  ASKING: 'asking',
  PROMPT: 'prompt',
  IDLE: 'idle',
  DENIED: 'denied',
  ERROR: 'error',
  UNSUPPORTED: 'unsupported',
};

/**
 * Тонкий баннер над чатом: показывает состояние геолокации и предлагает
 * включить её. Не блокирует чат — пользователь может писать без гео,
 * тогда сервер попросит адрес текстом.
 */
function GeoBanner() {
  const { coords, status, error, request, isSupported } = useGeo();

  if (status === STATUS.GRANTED && coords) {
    return (
      <div className="geo-banner geo-banner--ok" role="status">
        <span className="geo-banner__dot" aria-hidden="true" />
        <span className="geo-banner__text">
          Местоположение определено (точность ~{Math.round(coords.accuracy || 0)} м).
          Бот учитывает его в ответах.
        </span>
      </div>
    );
  }

  if (status === STATUS.DENIED) {
    return (
      <div className="geo-banner geo-banner--warn" role="status">
        <span className="geo-banner__text">
          🛑 Доступ к геолокации запрещён.{' '}
          Чтобы я подсказывал ближайший ПВР и проверял зону подтопления — разрешите
          геолокацию в адресной строке браузера (значок замка) или напишите ваш адрес
          в чате (например, «Тюмень, ул. Республики, 1»).
        </span>
      </div>
    );
  }

  if (status === STATUS.UNSUPPORTED) {
    return (
      <div className="geo-banner geo-banner--warn" role="status">
        <span className="geo-banner__text">
          Браузер не поддерживает геолокацию. Напишите ваш адрес в чате —
          и я подскажу по нему ближайший ПВР.
        </span>
      </div>
    );
  }

  if (status === STATUS.ERROR) {
    return (
      <div className="geo-banner geo-banner--warn" role="status">
        <span className="geo-banner__text">
          Не удалось определить геолокацию: {error}. Напишите ваш адрес в чате.
        </span>
      </div>
    );
  }

  // PROMPT / IDLE / ASKING — приглашение разрешить
  return (
    <div className="geo-banner geo-banner--cta" role="status">
      <span className="geo-banner__text">
        📍 Разрешите доступ к геолокации, чтобы я подсказывал ближайший ПВР,
        предупреждал о зонах подтопления и строил маршруты.
      </span>
      <button
        type="button"
        className="geo-banner__btn"
        onClick={request}
        disabled={!isSupported || status === STATUS.ASKING}
      >
        {status === STATUS.ASKING ? 'Запрашиваю…' : 'Разрешить'}
      </button>
    </div>
  );
}

export default GeoBanner;
