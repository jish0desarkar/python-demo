from rapidfuzz import fuzz

from app.models import Rule

FUZZY_THRESHOLD = 0.75


class EventFilter:
    def __init__(self, threshold: float = FUZZY_THRESHOLD):
        self.threshold = threshold

    def match(self, rules: list[Rule], payload: str) -> tuple[Rule | None, int]:
        payload_lower = payload.lower()
        for rule in rules:
            score = fuzz.partial_token_set_ratio(rule.rule_text.lower(), payload_lower)
            if score / 100 >= self.threshold:
                return rule, int(score)
        return None, 0
