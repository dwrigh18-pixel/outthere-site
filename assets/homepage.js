(() => {
  'use strict';
  const endpoint = 'https://dpfadeuxbniufdonzkvy.supabase.co/functions/v1/waitlist-signup';
  const form = document.querySelector('.signup');
  if (!form) return;
  const button = form.querySelector('button[type="submit"]');
  const status = document.getElementById('signup-status');
  let submitting = false;

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (submitting || !form.reportValidity()) return;
    const email = form.elements.namedItem('email').value.trim();
    const company = form.elements.namedItem('company').value;
    if (!email) return;
    submitting = true;
    button.disabled = true;
    button.textContent = 'Joining…';
    form.setAttribute('aria-busy', 'true');
    status.textContent = 'Adding you to the waitlist…';
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 15000);
    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, company }),
        signal: controller.signal,
      });
      const result = await response.json().catch(() => ({}));
      if (response.ok && result.joined === true) {
        form.reset();
        status.textContent = "You're on the waitlist. We'll email you as beta access opens.";
      } else if (response.status === 429) {
        status.textContent = 'Too many attempts. Please wait a little before trying again.';
      } else {
        status.textContent = typeof result.error === 'string'
          ? result.error
          : 'We could not add you just now. Please try again shortly.';
      }
    } catch (error) {
      status.textContent = error.name === 'AbortError'
        ? 'This is taking longer than expected. Please try again shortly.'
        : 'We could not reach the waitlist. Please check your connection and try again.';
    } finally {
      clearTimeout(timeout);
      submitting = false;
      button.disabled = false;
      button.textContent = 'Join the beta waitlist';
      form.removeAttribute('aria-busy');
    }
  });
})();
