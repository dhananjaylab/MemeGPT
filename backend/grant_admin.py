"""
Grant or revoke the is_admin flag on a user, by email.

The Phase 1 security remediation locks /api/storage/*, /api/jobs/queue/cleanup,
and /api/memes/seed-templates behind get_current_admin_user. There is
intentionally no API endpoint that can grant admin (that would just move the
privilege-escalation hole rather than close it) — this CLI script, run with
direct database access, is the bootstrap mechanism.

Usage:
    python grant_admin.py user@example.com           # grant
    python grant_admin.py user@example.com --revoke   # revoke
"""
import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import select, update

from db.session import _init_engine, AsyncSessionLocal
from models.models import User


async def set_admin(email: str, is_admin: bool) -> None:
    _init_engine()
    from db.session import AsyncSessionLocal as SessionLocal

    async with SessionLocal() as db:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user:
            print(f"❌ No user found with email: {email}")
            return

        await db.execute(
            update(User).where(User.id == user.id).values(is_admin=is_admin)
        )
        await db.commit()

        verb = "granted to" if is_admin else "revoked from"
        print(f"✅ Admin privileges {verb} {email} (user id: {user.id})")


def main() -> None:
    parser = argparse.ArgumentParser(description="Grant or revoke admin privileges for a MemeGPT user")
    parser.add_argument("email", help="Email address of the user")
    parser.add_argument("--revoke", action="store_true", help="Revoke instead of grant admin privileges")
    args = parser.parse_args()

    asyncio.run(set_admin(args.email, is_admin=not args.revoke))


if __name__ == "__main__":
    main()
