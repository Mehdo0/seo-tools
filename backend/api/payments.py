from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
import stripe

from config import settings
from api.auth import get_current_user

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
        raise HTTPException(status_code=400, detail=str(e))


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
        email = session.get("customer_email", session.get("customer_details", {}).get("email"))
    elif event["type"] == "customer.subscription.updated":
        subscription = event["data"]["object"]
    elif event["type"] == "customer.subscription.deleted":
        subscription = event["data"]["object"]
    return {"status": "ok"}
