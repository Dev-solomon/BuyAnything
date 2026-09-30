document.addEventListener('DOMContentLoaded', () => {

  // =========================
  // PRODUCT GALLERY
  // =========================
  const mainImage = document.querySelector('.gallery-main img');

  document.querySelectorAll('.thumb').forEach(thumb => {
    thumb.addEventListener('click', () => {
      if (!mainImage || !thumb.dataset.image) return;

      mainImage.src = thumb.dataset.image;

      document.querySelectorAll('.thumb').forEach(item => {
        item.classList.remove('active');
      });

      thumb.classList.add('active');
    });
  });


  // =========================
  // QUANTITY SELECTOR
  // =========================
  const quantityInput = document.getElementById('quantity');

  if (quantityInput) {

    const unitPrice = Number(window.BUYANYTHING_UNIT_PRICE || 0);

    const clampQuantity = value => {
      const number = parseInt(value, 10);

      if (Number.isNaN(number)) {
        return 1;
      }

      return Math.max(1, Math.min(20, number));
    };


    const updateCheckout = () => {

      const quantity = clampQuantity(quantityInput.value);

      quantityInput.value = quantity;

      const amount = unitPrice * quantity;

      const formattedAmount = amount.toLocaleString('en-US', {
        style: 'currency',
        currency: 'USD'
      });

      const qtyLabel = document.getElementById('qty-label');
      const lineTotal = document.getElementById('line-total');
      const checkoutTotal = document.getElementById('checkout-total');

      if (qtyLabel) {
        qtyLabel.textContent = `Qty ${quantity}`;
      }

      if (lineTotal) {
        lineTotal.textContent = formattedAmount;
      }

      if (checkoutTotal) {
        checkoutTotal.textContent = formattedAmount;
      }
    };


    // Plus / Minus buttons
    document.querySelectorAll('.qty-btn').forEach(button => {

      // Prevent quantity buttons from submitting the checkout form
      button.type = 'button';

      button.addEventListener('click', event => {

        event.preventDefault();

        const step = parseInt(button.dataset.step || '0', 10);

        const currentQuantity = clampQuantity(quantityInput.value);

        quantityInput.value = clampQuantity(
          currentQuantity + step
        );

        updateCheckout();
      });

    });


    // Manual quantity entry
    quantityInput.addEventListener('input', () => {

      // Don't aggressively change the value while the user is typing
      const value = parseInt(quantityInput.value, 10);

      if (!Number.isNaN(value) && value > 20) {
        quantityInput.value = 20;
      }

      updateCheckout();
    });


    quantityInput.addEventListener('change', updateCheckout);

    quantityInput.addEventListener('blur', updateCheckout);

    updateCheckout();
  }


  // =========================
  // FORM SUBMISSION
  // =========================
  document.querySelectorAll('form').forEach(form => {

    form.addEventListener('submit', event => {

      if (!form.checkValidity()) {
        return;
      }

      const submitButton = form.querySelector(
        'button[type="submit"], input[type="submit"]'
      );

      if (!submitButton) return;

      // Prevent accidental double checkout
      submitButton.disabled = true;

      if (submitButton.tagName === 'BUTTON') {

        submitButton.dataset.oldText = submitButton.textContent;

        submitButton.textContent = 'Working…';
      }
    });

  });

});