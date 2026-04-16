from rapidfuzz import fuzz
import logging
from app.models import Rule

FUZZY_THRESHOLD = 0.75

logger = logging.getLogger(__name__)



class EventFilter:
    def __init__(self, threshold: float = FUZZY_THRESHOLD):
        self.threshold = threshold

    def match(self, rules: list[Rule], payload: str) -> tuple[Rule | None, int]:
        for rule in rules:
            score = fuzz.partial_token_set_ratio(rule.rule_text.lower(), payload.lower())
            logger.info("Rule used: %s, Score: %s, Payload: %s", rule.rule_text, score, payload)

            if score / 100 >= self.threshold:
                return rule, int(score)
        return None, int(score)
