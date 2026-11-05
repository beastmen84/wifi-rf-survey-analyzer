"""Serializable analysis results shared by the UI and report exporters."""

from dataclasses import asdict, dataclass, field
from hashlib import sha256
import json
import math

ENGINE_VERSION = "3"


@dataclass(frozen=True)
class AnalysisProfile:
    coverage_dbm: float = -70.0
    minimum_confidence: float = 0.6
    minimum_points: int = 3
    channels_24: tuple[int, ...] = (1, 6, 11)
    channels_5: tuple[int, ...] = ()
    channels_6: tuple[int, ...] = ()

    def __post_init__(self):
        if not math.isfinite(self.coverage_dbm) or not -95 <= self.coverage_dbm <= -45:
            raise ValueError("Invalid coverage threshold")
        if not math.isfinite(self.minimum_confidence) or not 0.1 <= self.minimum_confidence <= 1:
            raise ValueError("Invalid confidence threshold")
        if not 2 <= self.minimum_points <= 20:
            raise ValueError("Invalid minimum point count")
        for band in ("2.4", "5", "6"):
            values = self.channels(band)
            if len(values) > 64 or any(not isinstance(v, int) or not valid_channel(v, band) for v in values):
                raise ValueError("Invalid candidate channel")

    def channels(self, band):
        return {"2.4": self.channels_24, "5": self.channels_5, "6": self.channels_6}.get(band, ())


def valid_channel(channel, band):
    if band == "2.4":
        return 1 <= channel <= 14
    if band == "5":
        return channel in (list(range(36, 65, 4)) + list(range(100, 145, 4)) + list(range(149, 178, 4)))
    return channel == 2 or channel in range(1, 234, 4) if band == "6" else False


@dataclass(frozen=True)
class EvidencePoint:
    point_id: str
    x: float
    y: float
    timestamp: str


@dataclass(frozen=True)
class EvidenceReading:
    point_id: str
    group_id: str
    ssid: str
    band: str
    signal_dbm: float
    channel: int | None
    width: int | None
    confidence: float
    backend: str = ""
    adapter_id: str = ""
    signal_kind: str = "unknown"
    freshness: str = "unknown"


@dataclass(frozen=True)
class Finding:
    finding_id: str
    rule: str
    category: str
    severity: str
    confidence: str
    group_ids: tuple[str, ...] = ()
    ssid: str = ""
    band: str = ""
    point_ids: tuple[str, ...] = ()
    metrics: dict = field(default_factory=dict)
    action: str = ""
    limitations: tuple[str, ...] = ()


@dataclass(frozen=True)
class AnalysisReport:
    fingerprint: str
    profile: AnalysisProfile
    findings: tuple[Finding, ...]
    points: tuple[EvidencePoint, ...]
    ap_labels: dict
    relevant_ssids: tuple[str, ...]
    row_count: int
    raw_count: int
    invalid_rows: int
    created_at: str
    survey_name: str
    readings: tuple[EvidenceReading, ...] = ()
    engine_version: str = ENGINE_VERSION
    measurements: dict = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)


def analysis_fingerprint(rows, raw_rows, groups, relevant, scale, profile, survey_name="", context_metadata=None):
    payload = dict(rows=rows, raw=raw_rows, groups=groups, relevant=sorted(relevant),
                   scale=scale, profile=asdict(profile), survey=survey_name, engine=ENGINE_VERSION,
                   context=context_metadata)
    return sha256(json.dumps(payload, sort_keys=True, ensure_ascii=True, default=str).encode()).hexdigest()
