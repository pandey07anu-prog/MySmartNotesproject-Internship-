/**
 * SMART NOTES ASSISTANT — SIMPLE & ELEGANT PRELOADER
 * Minimalist, ultra-lightweight brand entrance.
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

  // Exactly 4.0 seconds visual duration
  const timer = setTimeout(dismissPreloader, 4000);

  // Optional fast exit if user clicks or presses key
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
