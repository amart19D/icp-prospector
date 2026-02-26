from __future__ import annotations

from prospector.models import Lead


class Scorer:
    def __init__(self, scoring_cfg: dict[str, int]) -> None:
        self.weights = scoring_cfg

    def score(self, lead: Lead) -> int:
        score = 0

        if lead.pain_quote.strip():
            score += int(self.weights["pain_signal_present"])

        b2b_weight = int(self.weights["b2b_saas_signals"])
        if lead.b2b_signal_count > 0:
            if lead.b2b_signal_count >= 4:
                score += b2b_weight
            elif lead.b2b_signal_count == 3:
                score += int(b2b_weight * 0.8)
            elif lead.b2b_signal_count == 2:
                score += int(b2b_weight * 0.6)
            else:
                score += int(b2b_weight * 0.4)

        if lead.small_team_signal_count > 0 or lead.team_size_signal:
            score += int(self.weights["small_team_signals"])

        if lead.support_stack != "unknown":
            score += int(self.weights["helpdesk_stack_detected"])

        if lead.docs_url:
            score += int(self.weights["docs_present"])

        if len(lead.keyword_variant_hits) >= 2:
            score += 5

        lead.fit_score = max(0, min(100, score))
        return lead.fit_score

    @staticmethod
    def band(score: int) -> str:
        if score >= 70:
            return "High"
        if score >= 40:
            return "Medium"
        return "Low"
