window.GalleryView = (function () {
  let el;
  let uid = null;
  let currentMedia = [];
  let currentIndex = -1;

  const TEMPLATE = `
    <div id="gallery-error-banner"></div>
    <div class="panel">
      <div class="gallery-controls">
        <label>Rover
          <select id="gallery-rover"></select>
        </label>
        <button id="gallery-refresh">Refresh</button>
      </div>
    </div>
    <div class="panel">
      <div class="panel-title">Media Gallery</div>
      <div id="media-gallery" class="media-gallery"></div>
    </div>
    <div id="media-lightbox" class="media-lightbox" hidden>
      <div class="media-lightbox-backdrop"></div>
      <div class="media-lightbox-content">
        <button id="media-lightbox-close" class="media-lightbox-close" aria-label="Close">✕</button>
        <div id="media-lightbox-body"></div>
        <div class="media-lightbox-actions">
          <a id="media-lightbox-download" class="media-lightbox-download" download>Download</a>
        </div>
      </div>
    </div>
  `;

  function showError(message) {
    document.getElementById('gallery-error-banner').innerHTML = message ? `<div class="error-banner">${message}</div>` : '';
  }

  function populateRoverSelect(rovers) {
    const select = document.getElementById('gallery-rover');
    select.innerHTML = rovers.map((r) => `<option value="${Api.escapeHtml(r.device_uid)}">${Api.escapeHtml(r.device_uid)}</option>`).join('');
    if (!uid) {
      const shared = RoverSelection.get();
      const stillPresent = shared && rovers.some((r) => r.device_uid === shared);
      uid = stillPresent ? shared : (rovers.length > 0 ? rovers[0].device_uid : null);
    }
    select.value = uid;
  }

  function openLightbox(index) {
    currentIndex = index;
    const m = currentMedia[index];
    const url = Api.mediaUrl(uid, m.id);
    const body = document.getElementById('media-lightbox-body');
    body.innerHTML = m.media_type === 'photo'
      ? `<img src="${url}" alt="media ${m.id}">`
      : `<video src="${url}" controls autoplay></video>`;
    document.getElementById('media-lightbox-download').href = url;
    document.getElementById('media-lightbox').hidden = false;
  }

  function showAdjacent(step) {
    if (currentIndex === -1 || currentMedia.length === 0) return;
    const next = (currentIndex + step + currentMedia.length) % currentMedia.length;
    openLightbox(next);
  }

  function closeLightbox() {
    currentIndex = -1;
    document.getElementById('media-lightbox').hidden = true;
    document.getElementById('media-lightbox-body').innerHTML = '';
  }

  document.addEventListener('keydown', (evt) => {
    if (document.getElementById('media-lightbox') && document.getElementById('media-lightbox').hidden) return;
    if (evt.key === 'ArrowLeft') showAdjacent(-1);
    else if (evt.key === 'ArrowRight') showAdjacent(1);
    else if (evt.key === 'Escape') closeLightbox();
  });

  function loadMediaGallery() {
    if (!uid) return;
    Api.media(uid, { limit: 50 }).then((data) => {
      showError(null);
      currentMedia = data.media || [];
      const gallery = document.getElementById('media-gallery');
      if (currentMedia.length === 0) {
        gallery.innerHTML = '<p style="color: var(--text-dim);">No media files yet.</p>';
        return;
      }
      gallery.innerHTML = data.media.map((m) => {
        const url = Api.mediaUrl(uid, m.id);
        const preview = m.media_type === 'photo'
          ? `<img src="${url}" alt="media ${m.id}" loading="lazy">`
          : `<video src="${url}" muted></video>`;
        return `
          <div class="media-item" data-id="${m.id}">
            <div class="media-preview">${preview}</div>
            <div class="media-info">
              <div class="media-type">${m.media_type}</div>
              <div class="media-time">${TimeUtil.dateTime(m.captured_at)}</div>
              <div class="media-size">${(m.file_size_bytes / 1024).toFixed(0)} KB</div>
            </div>
            <a class="media-download-btn" href="${url}" download aria-label="Download media">⬇</a>
            <button class="media-delete-btn" data-id="${m.id}" aria-label="Delete media">✕</button>
          </div>
        `;
      }).join('');

      gallery.querySelectorAll('.media-item').forEach((item) => {
        const id = Number(item.dataset.id);
        const index = currentMedia.findIndex((x) => x.id === id);
        item.querySelector('.media-preview').addEventListener('click', () => openLightbox(index));
      });

      gallery.querySelectorAll('.media-download-btn').forEach((link) => {
        link.addEventListener('click', (e) => e.stopPropagation());
      });

      gallery.querySelectorAll('.media-delete-btn').forEach((btn) => {
        btn.addEventListener('click', (e) => {
          e.stopPropagation();
          const id = btn.dataset.id;
          if (confirm('Delete this media file?')) {
            Api.deleteMedia(uid, id).then(() => {
              loadMediaGallery();
            }).catch((err) => {
              showError(`Failed to delete media: ${err.message || err.code}`);
            });
          }
        });
      });
    }).catch((err) => {
      showError(`Media gallery unavailable: ${err.message || err.code}`);
      document.getElementById('media-gallery').innerHTML = '<p style="color: var(--text-dim);">Media unavailable.</p>';
    });
  }

  function mount(rootEl) {
    el = rootEl;
    el.innerHTML = TEMPLATE;

    Api.rovers().then((rovers) => { populateRoverSelect(rovers); loadMediaGallery(); })
      .catch((err) => showError(`Rover list unavailable: ${err.message || err.code}`));

    document.getElementById('gallery-rover').addEventListener('change', (evt) => {
      uid = evt.target.value;
      RoverSelection.set(uid);
      loadMediaGallery();
    });
    document.getElementById('gallery-refresh').addEventListener('click', () => loadMediaGallery());
    document.getElementById('media-lightbox-close').addEventListener('click', closeLightbox);
    document.querySelector('.media-lightbox-backdrop').addEventListener('click', closeLightbox);
    RoverSelection.subscribe((newUid) => {
      if (newUid === uid) return;
      uid = newUid;
      const select = document.getElementById('gallery-rover');
      if (select) select.value = uid;
      loadMediaGallery();
    });
  }

  function start() {}
  function stop() {}

  return { mount, start, stop };
})();
