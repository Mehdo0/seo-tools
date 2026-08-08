import logging
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
import stripe

from config import settings
from api.auth import get_current_user, USERS_DB

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
        if email and email in USERS_DB:
            USERS_DB[email]["premium"] = True
            USERS_DB[email]["stripe_customer_id"] = session.get("customer")
            logger.info("Premium activated for %s", email)

    elif event["type"] == "customer.subscription.deleted":
        subscription = event["data"]["object"]
        customer_id = subscription.get("customer")
        for email, user in USERS_DB.items():
            if user.get("stripe_customer_id") == customer_id:
                user["premium"] = False
                logger.info("Premium deactivated for %s", email)
                break

    elif event["type"] == "customer.subscription.updated":
        subscription = event["data"]["object"]
        customer_id = subscription.get("customer")
        is_active = subscription.get("status") == "active"
        for email, user in USERS_DB.items():
            if user.get("stripe_customer_id") == customer_id:
                user["premium"] = is_active
                logger.info("Premium %s for %s", "activated" if is_active else "deactivated", email)
                break

    return {"status": "ok"}


@router.get("/status")
async def payment_status(user: dict = Depends(get_current_user)):
    return {"premium": user.get("premium", False)}


@router.get("/config")
async def payment_config(user: dict = Depends(get_current_user)):
    return {
        "publishable_key": settings.stripe_publishable_key,
        "price_id": settings.stripe_price_id,
    }
