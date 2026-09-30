import json, os, uuid
from pathlib import Path
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    jsonify,
)
from dotenv import load_dotenv
import stripe
from services.research import research_trending_products, build_product
from services.cj import test_connection, create_order, CJError

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-change-me")
ROOT = Path(__file__).parent
PRODUCT = ROOT / "data" / "product.json"
CANDIDATES = ROOT / "data" / "candidates.json"
ORDERS = ROOT / "data" / "orders.json"


def read(path, default):
    try:
        return json.loads(path.read_text())
    except:
        return default


def write(path, data):
    path.write_text(json.dumps(data, indent=2))


def get_product():
    return read(PRODUCT, {})


def admin_ok():
    return session.get("admin") is True


def save_order(order):
    orders = read(ORDERS, [])
    orders.insert(0, order)
    write(ORDERS, orders[:500])


def fulfill_checkout(cs):
    # Convert Stripe Session object to normal Python dict
    if hasattr(cs, "to_dict"):
        cs = cs.to_dict()

    p = get_product()

    md = cs.get("metadata") or {}

    order_no = md.get("order_number") or "BA-" + uuid.uuid4().hex[:10].upper()

    details = cs.get("customer_details") or {}
    addr = details.get("address") or {}

    shipping = {
        "name": details.get("name", ""),
        "email": details.get("email", ""),
        "phone": details.get("phone", ""),
        "line1": addr.get("line1", ""),
        "line2": addr.get("line2", ""),
        "city": addr.get("city", ""),
        "state": addr.get("state", ""),
        "postal_code": addr.get("postal_code", ""),
        "country": addr.get("country", ""),
        "country_name": addr.get("country", ""),
    }

    record = {
        "order_number": order_no,
        "stripe_session": cs.get("id"),
        "payment_status": cs.get("payment_status"),
        "product": p.get("name"),
        "cj_status": "pending",
    }

    try:
        if not p.get("cj_vid"):
            raise CJError("Approved product has no CJ variant ID.")

        quantity = int(md.get("quantity", "1"))

        result = create_order(order_no, shipping, p["cj_vid"], quantity)

        record.update({"cj_status": "submitted", "cj_result": result})

    except Exception as e:
        record.update({"cj_status": "needs_attention", "cj_error": str(e)})

    save_order(record)

    return record


@app.route("/")
def home():
    return render_template("index.html", p=get_product())


@app.route("/product")
def product():
    return render_template("product.html", p=get_product())


@app.route("/purchase")
def purchase():
    try:
        quantity = max(1, min(int(request.args.get("quantity", "1")), 20))
    except (TypeError, ValueError):
        quantity = 1
    return render_template("purchase.html", p=get_product(), quantity=quantity)


@app.post("/create-checkout-session")
def checkout():
    p = get_product()
    stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
    try:
        quantity = max(1, min(int(request.form.get("quantity", "1")), 20))
    except (TypeError, ValueError):
        quantity = 1
    if not stripe.api_key:
        flash("Add STRIPE_SECRET_KEY to .env to enable checkout.")
        return redirect(url_for("purchase"))
    if not p.get("cj_vid"):
        flash("This product is not connected to CJdropshipping yet.")
        return redirect(url_for("purchase"))
    base = os.getenv("BASE_URL", request.host_url.rstrip("/"))
    order_no = "BA-" + uuid.uuid4().hex[:10].upper()
    s = stripe.checkout.Session.create(
        mode="payment",
        payment_method_types=["card"],
        billing_address_collection="auto",
        shipping_address_collection={
            "allowed_countries": ["US", "CA", "GB", "AU", "NZ"]
        },
        phone_number_collection={"enabled": True},
        customer_creation="always",
        metadata={
            "order_number": order_no,
            "cj_vid": p["cj_vid"],
            "quantity": str(quantity),
        },
        line_items=[
            {
                "price_data": {
                    "currency": p["currency"],
                    "product_data": {
                        "name": p["name"],
                        "description": p["tagline"],
                        "images": [p["image"]] if p.get("image") else [],
                    },
                    "unit_amount": int(round(float(p["price"]) * 100)),
                },
                "quantity": quantity,
            }
        ],
        success_url=base + "/success?session_id={CHECKOUT_SESSION_ID}",
        cancel_url=base + "/purchase",
    )
    return redirect(s.url, code=303)


@app.post("/stripe/webhook")
def stripe_webhook():
    payload = request.get_data()
    sig = request.headers.get("Stripe-Signature")
    secret = os.getenv("STRIPE_WEBHOOK_SECRET")
    if not secret:
        return "Webhook secret missing", 400
    try:
        event = stripe.Webhook.construct_event(payload, sig, secret)
    except Exception:
        return "Invalid webhook", 400
    if event["type"] == "checkout.session.completed":
        fulfill_checkout(event["data"]["object"])
    return "", 200


@app.route("/success")
def success():
    return render_template("success.html", p=get_product())


@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST" and not admin_ok():
        if request.form.get("password") == os.getenv("ADMIN_PASSWORD", "change-me"):
            session["admin"] = True
        else:
            flash("Incorrect admin password.")
        return redirect(url_for("admin"))
    return render_template(
        "admin.html",
        p=get_product(),
        candidates=read(CANDIDATES, []),
        orders=read(ORDERS, [])[:8],
        logged=admin_ok(),
    )


@app.post("/admin/research")
def research():
    if not admin_ok():
        return redirect(url_for("admin"))
    try:
        write(CANDIDATES, research_trending_products())
        flash("Research complete. Review the five candidates.")
    except Exception as e:
        flash("Research error: " + str(e))
    return redirect(url_for("admin"))


@app.post("/admin/approve/<int:i>")
def approve(i):
    if not admin_ok():
        return redirect(url_for("admin"))
    try:
        p = build_product(read(CANDIDATES, [])[i])
        write(PRODUCT, p)
        flash("Approved. CJ supplier data, storefront and checkout are updated.")
    except Exception as e:
        flash("Approval error: " + str(e))
    return redirect(url_for("admin"))


@app.post("/admin/test-cj")
def test_cj():
    if not admin_ok():
        return redirect(url_for("admin"))
    try:
        test_connection()
        flash("CJdropshipping API connection is working.")
    except Exception as e:
        flash("CJ connection error: " + str(e))
    return redirect(url_for("admin"))


@app.post("/admin/logout")
def logout():
    session.clear()
    return redirect(url_for("admin"))


@app.get("/health")
def health():
    return jsonify(
        ok=True,
        cj_configured=bool(os.getenv("CJ_ACCESS_TOKEN")),
        stripe_configured=bool(os.getenv("STRIPE_SECRET_KEY")),
    )


if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "0") == "1")
