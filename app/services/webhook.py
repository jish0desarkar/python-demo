import hashlib
import hmac
import json
import logging

import requests

from app.config import settings

logger = logging.getLogger(__name__)


class WebhookSender:
    def send_filter_pass(self, payload: dict) -> None:
        body = json.dumps(payload).encode()
        signature = "sha256=" + hmac.new(
            settings.webhook_secret.encode(), body, hashlib.sha256
        ).hexdigest()

        event_id = payload.get("event_id")
        rule_name = payload.get("filter_name")

        try:
            response = requests.post(
                settings.webhook_url,
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Signature-256": signature,
                },
                timeout=30,
            )
            logger.info(
                "Webhook sent: status=%s, event_id=%s, rule=%s",
                response.status_code,
                event_id,
                rule_name,
            )
        except Exception:
            logger.exception(
                "Failed to send webhook for event_id=%s, rule=%s", event_id, rule_name
            )
