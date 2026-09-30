document.addEventListener('DOMContentLoaded',()=>{document.querySelectorAll('.thumb').forEach(t=>t.addEventListener('click',()=>{document.querySelector('.gallery-main img').src=t.dataset.image;document.querySelectorAll('.thumb').forEach(x=>x.classList.remove('active'));t.classList.add('active')}));document.querySelectorAll('form button').forEach(b=>b.addEventListener('click',()=>{if(b.form&&b.form.checkValidity()){setTimeout(()=>{b.disabled=true;b.dataset.old=b.textContent;b.textContent='Working…'},30)}}))});

// Checkout quantity selector
(() => {
  const input = document.getElementById('quantity');
  if (!input) return;
  const unit = Number(window.BUYANYTHING_UNIT_PRICE || 0);
  const clamp = n => Math.max(1, Math.min(20, Number.isFinite(n) ? Math.trunc(n) : 1));
  const update = () => {
    const q = clamp(Number(input.value)); input.value = q;
    const amount = (unit * q).toFixed(2);
    const qtyLabel = document.getElementById('qty-label');
    const lineTotal = document.getElementById('line-total');
    const total = document.getElementById('checkout-total');
    if (qtyLabel) qtyLabel.textContent = `Qty ${q}`;
    if (lineTotal) lineTotal.textContent = `$${amount}`;
    if (total) total.textContent = `$${amount}`;
  };
  document.querySelectorAll('.qty-btn').forEach(btn => btn.addEventListener('click', () => { input.value = clamp(Number(input.value) + Number(btn.dataset.step)); update(); }));
  input.addEventListener('input', update); input.addEventListener('change', update); update();
})();
