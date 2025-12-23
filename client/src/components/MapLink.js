import React from 'react';
import './MapLink.css';

function MapLink() {
  return (
    <div className="map-link-container">
      <div className="map-link-card">
        <div className="map-link-icon">🗺️</div>
        <div className="map-link-content">
          <h3>Интерактивная карта затоплений</h3>
          <p>Актуальная информация о паводковой ситуации в Тюменской области</p>
          <a 
            href="https://gis.72to.ru/orbismap/public_map/geoportal72/map29/#/map/65.507851,57.028528/7/31354,31356,31352,31363,31366,31372,31376,31373,31381,31501,31500,31351,31349"
            target="_blank"
            rel="noopener noreferrer"
            className="map-link-button"
          >
            <span>Открыть карту</span>
            <span className="arrow">→</span>
          </a>
        </div>
      </div>
    </div>
  );
}

export default MapLink;

