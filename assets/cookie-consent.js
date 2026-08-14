(function () {
  'use strict';

  var STORAGE_KEY = 'ott_marketing_cookie_consent';
  var banner;

  function getConsent() {
    try { return window.localStorage.getItem(STORAGE_KEY); } catch (error) { return null; }
  }

  function saveConsent(value) {
    try { window.localStorage.setItem(STORAGE_KEY, value); } catch (error) { /* The banner will be shown again if storage is unavailable. */ }
  }

  function loadMetaPixel() {
    if (window.__ottMetaPixelLoaded) return;
    window.__ottMetaPixelLoaded = true;

    var pixelCode = document.getElementById('ott-meta-pixel-code');
    if (!pixelCode) return;

    var script = document.createElement('script');
    script.text = pixelCode.textContent;
    document.head.appendChild(script);
  }

  function hideBanner() {
    if (banner) banner.hidden = true;
  }

  function setConsent(value) {
    saveConsent(value);
    hideBanner();
    if (value === 'accepted') loadMetaPixel();
  }

  function showBanner() {
    if (!banner) return;
    banner.hidden = false;
    var reject = banner.querySelector('[data-cookie-reject]');
    if (reject) reject.focus();
  }

  function createBanner() {
    var style = document.createElement('style');
    style.textContent = '.ott-cookie-banner{position:fixed;z-index:1000;left:50%;bottom:.75rem;transform:translateX(-50%);display:flex;align-items:center;justify-content:space-between;gap:1rem;width:min(calc(100% - 1.5rem),72rem);padding:.75rem .85rem;background:#101432;color:#FFF4DF;border:1px solid rgba(169,181,255,.45);border-radius:.8rem;box-shadow:0 .75rem 2.5rem rgba(0,0,0,.4);font:400 13px/1.4 Inter,system-ui,sans-serif}.ott-cookie-banner[hidden]{display:none}.ott-cookie-banner p{margin:0}.ott-cookie-banner strong{display:block;margin-bottom:.1rem;font-size:.86rem}.ott-cookie-banner a{color:#DCC8FF}.ott-cookie-actions{display:flex;flex:0 0 auto;gap:.5rem}.ott-cookie-button{min-height:2.4rem;padding:.5rem .75rem;border-radius:.55rem;border:1px solid #A9B5FF;background:transparent;color:#FFF4DF;font:600 .82rem Inter,system-ui,sans-serif;white-space:nowrap;cursor:pointer}.ott-cookie-button--accept{border-color:#FF6B72;background:#FF6B72;color:#090B24}.ott-cookie-button:focus-visible{outline:3px solid #DCC8FF;outline-offset:3px}@media(max-width:42rem){.ott-cookie-banner{align-items:stretch;flex-direction:column;gap:.65rem}.ott-cookie-actions{display:grid;grid-template-columns:1fr 1fr}.ott-cookie-button{width:100%}}';
    document.head.appendChild(style);

    banner = document.createElement('aside');
    banner.className = 'ott-cookie-banner';
    banner.setAttribute('aria-label', 'Cookie choices');
    banner.setAttribute('role', 'region');
    banner.innerHTML = '<div class="ott-cookie-copy"><strong>Optional marketing cookies</strong><p>Allow Meta Pixel to measure our ads? The site works without it. <a href="/cookies/">Cookie policy</a></p></div><div class="ott-cookie-actions"><button class="ott-cookie-button" type="button" data-cookie-reject>No thanks</button><button class="ott-cookie-button ott-cookie-button--accept" type="button" data-cookie-accept>Allow</button></div>';
    document.body.appendChild(banner);

    banner.querySelector('[data-cookie-reject]').addEventListener('click', function () { setConsent('rejected'); });
    banner.querySelector('[data-cookie-accept]').addEventListener('click', function () { setConsent('accepted'); });
  }

  function initialise() {
    createBanner();
    var consent = getConsent();
    if (consent === 'accepted') {
      hideBanner();
      loadMetaPixel();
    }
    else if (consent === 'rejected') hideBanner();

    document.addEventListener('click', function (event) {
      var target = event.target.closest('[data-cookie-settings]');
      if (!target) return;
      event.preventDefault();
      showBanner();
    });
  }

  window.outThereCookieSettings = showBanner;
  document.addEventListener('DOMContentLoaded', initialise);
}());
