# buyanything

A responsive Flask single-product advertising storefront. AI researches recent demand signals, the admin approves a candidate, CJdropshipping supplies the actual product/variant, Stripe collects customer payment, and a successful Stripe webhook submits the paid order to CJ.

## Launch

1. `python -m venv .venv`
2. Activate it by `source .venv/Scripts/activate` and run `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and fill every required secret.
4. Run `python app.py` locally or `gunicorn app:app` in production.
5. Visit `/admin`, test CJ, run research, then approve a candidate.
6. In Stripe, create a webhook pointing to `https://YOUR-DOMAIN/stripe/webhook` and subscribe to `checkout.session.completed`; copy its signing secret into `STRIPE_WEBHOOK_SECRET`.

## CJdropshipping

Set `CJ_ACCESS_TOKEN` to your CJ API 2.0 access token. It is used only by the Flask backend. Approval searches CJ's Product List V2, loads product details/variants, selects an orderable variant, and stores `cj_pid`/`cj_vid`/SKU values in the live product record.

`CJ_PAY_TYPE=2` means that after the shopper has paid you through Stripe, buyanything submits the supplier order to CJ using your CJ balance. Keep enough CJ balance available. If you prefer manual supplier payment, use `CJ_PAY_TYPE=3`; the CJ order is created without automatic payment.

`CJ_LOGISTIC_NAME` must be a logistics method valid for the destination/product. CJ can reject an order if the configured method is unavailable; those orders appear as `needs attention` in the admin panel. For a larger production store, add CJ freight-calculation/logistics selection before order submission rather than relying on one configured default.

## Important production checklist

- Use HTTPS and a strong `FLASK_SECRET_KEY` + `ADMIN_PASSWORD`.
- Never commit `.env` or API keys.
- Use live Stripe keys only after test checkout succeeds.
- Verify your CJ logistics method, CJ balance, target countries, returns/refunds policy, taxes, privacy policy, and customer-support information before buying ads.
- Stripe is the source of truth for customer payment. Fulfillment is initiated only from the signed Stripe webhook, not from the browser success page.
- The current JSON storage is deliberately simple. For meaningful order volume, move products/orders to PostgreSQL and add webhook idempotency so repeated Stripe events cannot create duplicate CJ orders.
