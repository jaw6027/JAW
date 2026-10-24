'use strict';
const lightbox = document.querySelector('#lightbox');
document.querySelectorAll('[data-image]').forEach(button => {
  button.addEventListener('click', () => {
    const image = lightbox.querySelector('img');
    image.src = button.dataset.image;
    image.alt = button.dataset.alt;
    lightbox.querySelector('p').textContent = button.dataset.alt;
    lightbox.showModal();
  });
});
lightbox?.querySelector('button').addEventListener('click', () => lightbox.close());
lightbox?.addEventListener('click', event => { if (event.target === lightbox) lightbox.close(); });
document.querySelectorAll('.share-button').forEach(button => {
  button.addEventListener('click', async () => {
    const status = button.nextElementSibling;
    try {
      await navigator.clipboard.writeText(button.dataset.url);
      status.textContent = 'Design link copied. Share a little inspiration.';
    } catch {
      status.textContent = `Copy this address: ${button.dataset.url}`;
    }
  });
});
