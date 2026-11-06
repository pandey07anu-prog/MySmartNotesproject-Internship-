/**
 * SMART NOTES ASSISTANT — SIMPLE & ELEGANT PRELOADER
 * Visual duration: exactly 4 seconds (4000ms).
 */

(function() {
  'use strict';

  function dismissPreloader() {
    const el = document.getElementById('cinematic-3d-preloader') || document.querySelector('.simple-preloader-root');
    if (!el || el.classList.contains('preloader-hidden')) return;

    el.classList.add('preloader-hidden');
    setTimeout(() => {
      if (el && el.parentNode) {
        el.style.display = 'none';
      }
    }, 450);
  }

  const timer = setTimeout(dismissPreloader, 4000);

  window.addEventListener('click', () => {
    clearTimeout(timer);
    dismissPreloader();
  });
  window.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ' || e.key === 'Escape') {
      clearTimeout(timer);
      dismissPreloader();
    }
  });
})();
