"""
/api/stripe — Stripe integration for plan upgrades.

Plans:
  price_pro  → $9/mo  → 500 generations/day
  price_api  → $29/mo → 500 generations/day + API key

Webhook flow:
  checkout.session.completed → upgrade user plan in DB
  customer.subscription.deleted → downgrade back to free
"""
import os
import uuid

import stripe
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..db.session import get_db
from ..models.models import User
from ..services.auth import get_current_user

stripe.api_key = settings.stripe_secret_key
WEBHOOK_SECRET = settings.stripe_webhook_secret

PLAN_PRICES = {
    "pro": settings.stripe_price_pro,
    "api": settings.stripe_price_api,
}

PLAN_LIMITS = {
    "pro": 500,
    "api": 500,
}

router = APIRouter()


class CheckoutRequest(BaseModel):
    plan: str          # "pro" | "api"
    success_url: str
    cancel_url: str


class CheckoutResponse(BaseModel):
    checkout_url: str


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(
    body: CheckoutRequest,
    current_user: User = Depends(get_current_user),
):
    """Create a Stripe Checkout session for plan upgrade."""
    
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    if body.plan not in PLAN_PRICES:
        raise HTTPException(status_code=400, detail=f"Unknown plan: {body.plan}")

    session = stripe.checkout.Session.create(
        mode="subscription",
        payment_method_types=["card"],
        line_items=[{"price": PLAN_PRICES[body.plan], "quantity": 1}],
        success_url=body.success_url + "?upgraded=1",
        cancel_url=body.cancel_url,
        client_reference_id=current_user.id,
        customer_email=current_user.email,
        metadata={"user_id": current_user.id, "plan": body.plan},
    )
    return CheckoutResponse(checkout_url=session.url)


@router.post("/portal")
async def billing_portal(
    current_user: User = Depends(get_current_user),
    return_url: str = settings.frontend_url + "/dashboard",
):
    """Redirect to Stripe customer portal for subscription management."""
    
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Look up or create Stripe customer
    customers = stripe.Customer.list(email=current_user.email, limit=1)
    if not customers.data:
        raise HTTPException(status_code=404, detail="No billing account found")

    session = stripe.billing_portal.Session.create(
        customer=customers.data[0].id,
        return_url=return_url,
    )
    return {"portal_url": session.url}


@router.post("/webhook", include_in_schema=False)
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Handle Stripe webhook events.
    Verify signature before processing — never trust raw POST body alone.
    """
    body = await request.body()

    try:
        event = stripe.Webhook.construct_event(body, stripe_signature, WEBHOOK_SECRET)
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    # ── Handle events ─────────────────────────────────────────────────────────
    if event["type"] == "checkout.session.completed":
        session_data = event["data"]["object"]
        user_id = session_data.get("client_reference_id")
        plan = session_data.get("metadata", {}).get("plan", "pro")

        if user_id:
            new_limit = PLAN_LIMITS.get(plan, 500)
            api_key = f"mgpt_{uuid.uuid4().hex}" if plan == "api" else None

            updates: dict = {"plan": plan, "daily_limit": new_limit}
            if api_key:
                updates["api_key"] = api_key

            await db.execute(
                update(User).where(User.id == user_id).values(**updates)
            )
            await db.commit()

    elif event["type"] == "customer.subscription.deleted":
        # Subscription cancelled — downgrade to free
        subscription = event["data"]["object"]
        customer_id = subscription.get("customer")

        # Map Stripe customer → our user via email lookup
        try:
            customer = stripe.Customer.retrieve(customer_id)
            email = customer.get("email")
            if email:
                await db.execute(
                    update(User)
                    .where(User.email == email)
                    .values(plan="free", daily_limit=settings.rate_limit_free, api_key=None)
                )
                await db.commit()
        except Exception:
            pass  # Log in production

    return {"received": True}