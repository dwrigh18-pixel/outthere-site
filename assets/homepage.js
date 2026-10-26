(() => {
  'use strict';

  // Sections fade and rise into view as they scroll in. With reduced motion
  // the stylesheet shows everything at once, so nothing is left hidden.
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
  const targets = document.querySelectorAll('.reveal');
  if (!targets.length) return;

  if (reduced.matches || !('IntersectionObserver' in window)) {
    targets.forEach((el) => el.classList.add('is-visible'));
    return;
  }

  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      entry.target.classList.add('is-visible');
      observer.unobserve(entry.target);
    });
  }, { rootMargin: '0px 0px -8% 0px', threshold: 0.12 });

  targets.forEach((el) => observer.observe(el));

  // Anything already on screen when the page loads shows straight away.
  window.requestAnimationFrame(() => {
    targets.forEach((el) => {
      const rect = el.getBoundingClientRect();
      if (rect.top < window.innerHeight && rect.bottom > 0) el.classList.add('is-visible');
    });
  });
})();
