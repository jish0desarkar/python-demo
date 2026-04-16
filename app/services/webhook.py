import hashlib
import hmac
import json
import logging

import requests

from app.config import settings

logger = logging.getLogger(__name__)


class WebhookSender:
    def send_filter_pass(self, event_payload: str, rule_name: str, rule_text: str) -> None:
        body = json.dumps(
            {
                "event_text": event_payload,
                "filter_name": rule_name,
                "filter_text": rule_text,
            }
        ).encode()
        signature = "sha256=" + hmac.new(
            settings.webhook_secret.encode(), body, hashlib.sha256
        ).hexdigest()

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
            logger.info("Webhook sent: status=%s, rule=%s", response.status_code, rule_name)
        except Exception:
            logger.exception("Failed to send webhook for rule=%s", rule_name)
