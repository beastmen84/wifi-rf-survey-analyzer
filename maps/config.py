"""Serializable configuration object for live and exported maps."""

from dataclasses import dataclass

from app_core.constants import HEATMAP_MAX_DISTANCE_PX, HEATMAP_SMOOTHING_SIGMA


@dataclass(frozen=True)
class MapConfig:
    ssid: str = ""
    band: str = "all"
    map_type: str = "signal"
    interference_mode: str = "intra_ssid"
    interpolation: str = "rbf"
    aggregation: str = "max"
    color_scale: str = "fixed"
    point_label_mode: str = "auto"
    ap_group_filter: str = ""
    ap_group_map: tuple = ()
    ap_group_roles: tuple = ()
    usable_only: bool = False
    smoothing_sigma: float = HEATMAP_SMOOTHING_SIGMA
    max_distance_px: int = HEATMAP_MAX_DISTANCE_PX

    def normalized(self):
        band = self.band
        point_label_mode = self.point_label_mode

        if self.map_type == "interference":
            if band == "all":
                band = "2.4"
            if point_label_mode in {"auto", "all"}:
                point_label_mode = "critical"

        return MapConfig(
            ssid=self.ssid,
            band=band,
            map_type=self.map_type,
            interference_mode=self.interference_mode,
            interpolation=self.interpolation,
            aggregation=self.aggregation,
            color_scale=self.color_scale,
            point_label_mode=point_label_mode,
            ap_group_filter=self.ap_group_filter,
            ap_group_map=self.ap_group_map,
            ap_group_roles=self.ap_group_roles,
            usable_only=self.usable_only,
            smoothing_sigma=self.smoothing_sigma,
            max_distance_px=self.max_distance_px,
        )

    @property
    def is_signal(self):
        return self.map_type == "signal"

    @property
    def is_interference(self):
        return self.map_type == "interference"

    @property
    def is_channel(self):
        return self.map_type == "channel"

    @property
    def is_dominant(self):
        return self.map_type == "dominant"

    @property
    def is_continuous(self):
        return not (self.is_channel or self.is_dominant)
