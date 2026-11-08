"""Read-only organization of findings; RF decisions remain in the engine."""
from dataclasses import dataclass


RECOMMENDATION_RULES = frozenset({"channel_change", "channel_width", "weak_coverage", "dominance", "roaming"})
PREREQUISITE_RULES = frozenset({"channel_unstable", "model_override", "missing_position",
                              "missing_network", "empty_measurement"})


@dataclass(frozen=True)
class RecommendationSections:
    recommendations: tuple
    prerequisites: tuple
    observations: tuple

    @property
    def affected_points(self):
        return len({pid for finding in self.prerequisites for pid in finding.point_ids})


def recommendation_kind(finding):
    if finding.rule == "channel_change":
        return "proposal"
    if finding.action == "power_trial" or finding.rule == "channel_width":
        return "trial"
    return "review"


def recommendation_order(finding):
    # A joint channel plan must retain its engine step order. This is a reading
    # order by concreteness, not a computed business-impact or urgency score.
    if finding.rule == "channel_change":
        return (0, finding.metrics.get("step", 0), 0, 0, finding.finding_id)
    kind = 1 if recommendation_kind(finding) == "trial" else 2
    rule = {"weak_coverage": 0, "dominance": 1, "channel_width": 2, "roaming": 3}.get(finding.rule, 4)
    severity = {"warning": 0, "notice": 1}.get(finding.severity, 2)
    return (kind, rule, severity, -len(finding.point_ids), finding.finding_id)


def sections(report):
    recommendations, prerequisites, observations = [], [], []
    for finding in report.findings:
        if finding.category == "data" or finding.rule in PREREQUISITE_RULES:
            prerequisites.append(finding)
        elif finding.rule in RECOMMENDATION_RULES:
            recommendations.append(finding)
        else:
            observations.append(finding)
    return RecommendationSections(tuple(sorted(recommendations, key=recommendation_order)),
                                  tuple(prerequisites), tuple(observations))


def empty_recommendation_key(grouped):
    if grouped.prerequisites:
        return "none_limited"
    return "none_observations" if grouped.observations else "none"
