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
    var accept = banner.querySelector('[data-cookie-accept]');
    if (accept) accept.focus();
  }

  function createBanner() {
    var style = document.createElement('style');
    style.textContent = '.ott-cookie-banner{position:fixed;z-index:1000;right:1rem;bottom:1rem;width:min(100% - 2rem,32rem);padding:1.1rem;background:#101432;color:#FFF4DF;border:1px solid rgba(169,181,255,.45);border-radius:1rem;box-shadow:0 1rem 3rem rgba(0,0,0,.4);font:400 15px/1.5 Inter,system-ui,sans-serif}.ott-cookie-banner[hidden]{display:none}.ott-cookie-banner p{margin:.35rem 0 .9rem}.ott-cookie-banner a{color:#DCC8FF}.ott-cookie-actions{display:flex;flex-wrap:wrap;gap:.65rem}.ott-cookie-button{min-height:2.7rem;padding:.6rem .85rem;border-radius:.6rem;border:1px solid #A9B5FF;background:transparent;color:#FFF4DF;font:600 .9rem Inter,system-ui,sans-serif;cursor:pointer}.ott-cookie-button--accept{border-color:#FF6B72;background:#FF6B72;color:#090B24}.ott-cookie-button:focus-visible{outline:3px solid #DCC8FF;outline-offset:3px}';
    document.head.appendChild(style);

    banner = document.createElement('aside');
    banner.className = 'ott-cookie-banner';
    banner.setAttribute('aria-label', 'Cookie choices');
    banner.setAttribute('role', 'region');
    banner.innerHTML = '<strong>Optional marketing cookies</strong><p>With your permission, we use Meta Pixel to measure our ads and show relevant ads to people interested in Out There: Together. <a href="/cookies/">Cookie policy</a></p><div class="ott-cookie-actions"><button class="ott-cookie-button" type="button" data-cookie-reject>Reject</button><button class="ott-cookie-button ott-cookie-button--accept" type="button" data-cookie-accept>Accept marketing cookies</button></div>';
    document.body.appendChild(banner);

    banner.querySelector('[data-cookie-reject]').addEventListener('click', function () { setConsent('rejected'); });
    banner.querySelector('[data-cookie-accept]').addEventListener('click', function () { setConsent('accepted'); });
  }

  function initialise() {
    createBanner();
    var consent = getConsent();
    if (consent === 'accepted') loadMetaPixel();
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
