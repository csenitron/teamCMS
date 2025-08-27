(function(){
  function initStaticRating(root){
    const containers = (root || document).querySelectorAll('.rating[data-rating]');
    containers.forEach(container => {
      const ratingValue = parseFloat(container.getAttribute('data-rating')) || 0;
      const stars = container.querySelectorAll('.star');
      stars.forEach((star, index) => {
        const fillSvg = star.querySelector('.star-fill');
        if (!fillSvg) return;
        // Ensure the fill SVG is fully sized so clipping works even if inline width="0%" was present
        fillSvg.style.width = '100%';
        fillSvg.style.height = '100%';
        const portion = Math.max(0, Math.min(1, ratingValue - index)); // 0..1
        const fillPercent = Math.round(portion * 100);
        // clip from right side so left part stays filled
        fillSvg.style.clipPath = `inset(0 ${100 - fillPercent}% 0 0)`;
      });
    });
  }
  function initStars(scope){
    const starsWrap = scope.querySelector('.stars');
    if (!starsWrap) return;
    const inputId = starsWrap.getAttribute('data-input');
    const input = document.getElementById(inputId);
    if (!input) return;
    let current = Number(input.value || 0);
    const paint = (val)=>{
      starsWrap.querySelectorAll('.star').forEach(s=>{
        s.classList.toggle('active', Number(s.dataset.value) <= val);
      });
    };
    starsWrap.querySelectorAll('.star').forEach(star => {
      star.addEventListener('mouseenter', ()=> paint(Number(star.dataset.value)));
      star.addEventListener('mouseleave', ()=> paint(current || 0));
      star.addEventListener('click', ()=> { current = Number(star.dataset.value); input.value = String(current); paint(current); });
    });
    paint(current || 0);
  }

  function initFitScale(scale){
    const hiddenId = scale.getAttribute('data-input');
    const hidden = document.getElementById(hiddenId);
    if (!hidden) return;
    const left = scale.querySelector('.fit-scale__progress-left');
    const right = scale.querySelector('.fit-scale__progress-right');
    const handle = scale.querySelector('.fit-scale__handle');
    const dots = scale.querySelectorAll('[data-value]');
    const setVal = (v)=>{
      hidden.value = String(v);
      const total = (v - 1) / 4 * 100; // 0..100 across
      const leftWidth = Math.max(0, 50 - total);
      const rightWidth = Math.max(0, total - 50);
      if (left) left.style.width = leftWidth + '%';
      if (right) right.style.width = rightWidth + '%';
      if (handle) handle.style.left = total + '%';
    };
    dots.forEach(d => d.addEventListener('click', ()=> setVal(Number(d.dataset.value))));
    setVal(Number(hidden.value || 3));
  }

  function initAll(root){
    initStaticRating(root);
    initStars(root);
    root.querySelectorAll('.fit-scale').forEach(initFitScale);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function(){ initAll(document); });
  } else {
    initAll(document);
  }

  // Re-init on modal show in case of dynamic DOM updates
  const reviewModal = document.getElementById('reviewModal');
  if (reviewModal && window.bootstrap && typeof window.bootstrap.Modal !== 'undefined'){
    reviewModal.addEventListener('show.bs.modal', function(){ initAll(reviewModal); });
  }

  // AJAX submit
  document.addEventListener('submit', function(e){
    const form = e.target;
    if (form && form.getAttribute('action') && /\/product\/.+\/review$/.test(form.getAttribute('action'))){
      e.preventDefault();
      const url = form.getAttribute('action');
      const data = new FormData(form);
      fetch(url, { method: 'POST', body: data, headers: { 'X-Requested-With': 'XMLHttpRequest' }})
        .then(r => r.json()).then(json => {
          if (json && json.ok){
            // show thank you
            const body = form.closest('.modal-content').querySelector('.modal-body');
            if (body){ body.innerHTML = '<div class="py-4 text-center">Спасибо за отзыв! Он появится после модерации.</div>'; }
            const btns = form.closest('.modal-content').querySelector('.modal-footer');
            if (btns){ btns.innerHTML = '<button type="button" class="btn btn-sm btn-dark" data-bs-dismiss="modal">Ок</button>'; }
          } else {
            alert('Ошибка отправки отзыва');
          }
        }).catch(()=> alert('Ошибка отправки отзыва'));
    }
  }, true);

  // Like/Dislike voting
  document.addEventListener('click', function(e){
    const likeBtn = e.target.closest('.like-icon');
    const dislikeBtn = e.target.closest('.dislike-icon');
    if (!likeBtn && !dislikeBtn) return;
    const card = (likeBtn || dislikeBtn).closest('[data-review-id]');
    if (!card) return;
    const reviewId = card.getAttribute('data-review-id');
    const action = likeBtn ? 'like' : 'dislike';
    fetch(`/reviews/${reviewId}/vote`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action })
    }).then(async r => {
      let json = null;
      try { json = await r.json(); } catch(_) {}
      if (r.status === 409) {
        // duplicate vote – просто покажем сообщение и синхронизируем счетчики
        if (json && typeof json.likes === 'number' && typeof json.dislikes === 'number') {
          const likeSpan = card.querySelector('.like-icon ~ span');
          const dislikeSpan = card.querySelector('.dislike-icon ~ span');
          if (likeSpan) likeSpan.textContent = String(json.likes);
          if (dislikeSpan) dislikeSpan.textContent = String(json.dislikes);
        }
        alert('Вы уже голосовали за этот отзыв');
        return;
      }
      if (!json || !json.ok) return;
      const likeSpan = card.querySelector('.like-icon ~ span');
      const dislikeSpan = card.querySelector('.dislike-icon ~ span');
      if (likeSpan && typeof json.likes === 'number') likeSpan.textContent = String(json.likes);
      if (dislikeSpan && typeof json.dislikes === 'number') dislikeSpan.textContent = String(json.dislikes);
    }).catch(()=>{});
  });

  // Load more reviews
  document.addEventListener('click', function(e){
    const btn = e.target.closest('#reviews-load-more');
    if (!btn) return;
    e.preventDefault();
    const productId = btn.getAttribute('data-product-id');
    let offset = parseInt(btn.getAttribute('data-offset') || '0', 10);
    const limit = parseInt(btn.getAttribute('data-limit') || '2', 10);
    fetch(`/product/${productId}/reviews?offset=${offset}&limit=${limit}`)
      .then(r => r.json())
      .then(json => {
        if (!json || !json.ok) return;
        const parent = btn.parentNode; // вставляем соседями кнопки
        const temp = document.createElement('div');
        temp.innerHTML = json.html || '';
        const cards = Array.from(temp.children);
        cards.forEach(card => parent.insertBefore(card, btn));
        btn.setAttribute('data-offset', String(json.next_offset || (offset + cards.length)));
        if (!json.has_more) {
          btn.remove();
        }
      }).catch(()=>{});
  });
})();
