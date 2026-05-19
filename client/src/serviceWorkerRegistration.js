/**
 * Регистрация service worker в production-сборке.
 *
 * В dev-режиме (`npm start`) SW не регистрируется, чтобы не мешать HMR.
 * Файл /service-worker.js лежит в public/ и копируется в build/ как есть.
 */

export function register() {
  if (process.env.NODE_ENV !== 'production') return;
  if (!('serviceWorker' in navigator)) return;

  window.addEventListener('load', () => {
    navigator.serviceWorker
      .register('/service-worker.js')
      .then((reg) => {
        // eslint-disable-next-line no-console
        console.log('SW registered:', reg.scope);
      })
      .catch((err) => {
        // eslint-disable-next-line no-console
        console.warn('SW registration failed:', err);
      });
  });
}

export function unregister() {
  if (!('serviceWorker' in navigator)) return;
  navigator.serviceWorker.ready.then((reg) => reg.unregister()).catch(() => {});
}
