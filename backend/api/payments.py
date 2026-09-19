import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
import stripe

from config import settings
from api.auth import get_current_user
from database import get_user, get_user_by_customer, set_premium

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/payments", tags=["payments"])

stripe.api_key = settings.stripe_secret_key


class CheckoutRequest(BaseModel):
    success_url: str
    cancel_url: str


@router.post("/create-checkout")
async def create_checkout(req: CheckoutRequest, user: dict = Depends(get_current_user)):
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=500, detail="Stripe not configured")
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="subscription",
            line_items=[{"price": settings.stripe_price_id, "quantity": 1}],
            success_url=req.success_url,
            cancel_url=req.cancel_url,
            customer_email=user["email"],
        )
        return {"url": session.url, "session_id": session.id}
    except stripe.error.StripeError as e:
        logger.error("Stripe error during checkout: %s", e, exc_info=True)
        raise HTTPException(status_code=400, detail="Payment processing error")


@router.post("/webhook")
async def webhook(request: Request):
    if not settings.stripe_webhook_secret:
        raise HTTPException(status_code=500, detail="Webhook secret not configured")
    payload = await request.body()
    sig = request.headers.get("stripe-signature")
    try:
        event = stripe.Webhook.construct_event(payload, sig, settings.stripe_webhook_secret)
    except (ValueError, stripe.error.SignatureVerificationError):
        raise HTTPException(status_code=400, detail="Invalid signature")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        email = session.get("customer_email") or session.get("customer_details", {}).get("email")
        if email and get_user(email):
            set_premium(email, True, session.get("customer"), datetime.utcnow().isoformat())
            logger.info("Premium activated for %s", email)
        elif email:
            logger.warning("Stripe checkout for unknown account: %s", email)

    elif event["type"] == "customer.subscription.deleted":
        subscription = event["data"]["object"]
        user = get_user_by_customer(subscription.get("customer"))
        if user:
            set_premium(user["email"], False)
            logger.info("Premium deactivated for %s", user["email"])

    elif event["type"] == "customer.subscription.updated":
        subscription = event["data"]["object"]
        user = get_user_by_customer(subscription.get("customer"))
        if user:
            is_active = subscription.get("status") == "active"
            set_premium(user["email"], is_active, since=datetime.utcnow().isoformat())
            logger.info("Premium %s for %s", "activated" if is_active else "deactivated", user["email"])

    return {"status": "ok"}


@router.get("/status")
async def payment_status(user: dict = Depends(get_current_user)):
    return {
        "premium": bool(user.get("premium")),
        "since": user.get("premium_since"),
    }


@router.get("/config")
async def payment_config():
    """Clé publique et tarif : informations publiques par nature, nécessaires avant toute
    connexion (la popup les lit pour préparer l'abonnement). Exiger un jeton ici cassait
    le parcours d'abonnement d'un visiteur non connecté."""
    return {
        "publishable_key": settings.stripe_publishable_key,
        "price_id": settings.stripe_price_id,
    }
