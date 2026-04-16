import random

import requests
from sqlalchemy import func, select

from app.config import settings
from app.database import SessionLocal
from app.models import Rule, Source, account_sources
from app.services.phrase_generator import PhraseGenerator
from celery_app import celery_app

HINT_PROBABILITY = 0.8


@celery_app.task(name="tasks.generate_event.generate_random_event")
def generate_random_event():
    db = SessionLocal()
    try:
        row = db.execute(
            select(
                account_sources.c.account_id,
                account_sources.c.source_id,
            ).order_by(func.random()).limit(1)
        ).first()

        if row is None:
            return {"status": "skipped", "reason": "no linked account-source pairs found"}

        account_id, source_id = row

        source_name = None
        hint = None
        if random.random() < HINT_PROBABILITY:
            source = db.get(Source, source_id)
            rule = db.scalar(
                select(Rule).where(Rule.source_id == source_id).order_by(func.random()).limit(1)
            )
            if source and rule:
                source_name = source.name
                hint = rule.rule_text

        phrase = PhraseGenerator().generate(source_name=source_name, hint=hint)
        if not phrase:
            return {"status": "failed", "reason": "phrase generator returned empty text"}

        response = requests.post(
            f"{settings.app_base_url}/events/webhook",
            json={
                "account_id": account_id,
                "source_id": source_id,
                "payload": phrase,
            },
            timeout=30,
        )

        return {
            "status": "posted",
            "http_status": response.status_code,
            "account_id": account_id,
            "source_id": source_id,
        }
    finally:
        db.close()
