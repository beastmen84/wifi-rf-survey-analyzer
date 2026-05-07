from matplotlib.lines import Line2D

MAX_REFERENCE_ROWS = 10
MAX_LEGEND_ITEMS = 8
OTHER_AP_COLOR = "#6c757d"

AP_PALETTE = [
    "#0072B2",
    "#D55E00",
    "#009E73",
    "#CC79A7",
    "#56B4E9",
    "#E69F00",
    "#332288",
    "#88CCEE",
    "#882255",
    "#44AA99",
    "#117733",
    "#AA4499",
    "#999933",
    "#661100",
    "#6699CC",
]


def get_channel_color(channel, band):
    try:
        channel_number = int(float(channel))
    except (TypeError, ValueError):
        return "#7f8c8d"

    if band == "2.4":
        return {
            1: "#18bc9c",
            6: "#3498db",
            11: "#9b59b6"
        }.get(channel_number, "#f39c12")

    palette = [
        "#18bc9c",
        "#3498db",
        "#9b59b6",
        "#e74c3c",
        "#f39c12",
        "#2ecc71",
        "#34495e",
        "#d35400"
    ]
    return palette[channel_number % len(palette)]


def get_channel_band_prefix(channel):
    try:
        channel_number = int(float(channel))
    except (TypeError, ValueError):
        return ""

    if 1 <= channel_number <= 14:
        return "2.4G"

    if channel_number >= 36:
        return "5G"

    return ""


def get_bssid_suffix(bssid):
    parts = str(bssid or "").split(":")
    if len(parts) >= 2:
        return ":".join(parts[-2:])

    text = str(bssid or "")
    return text[-5:] if text else "-"


def get_ap_group_suffix(ap_group):
    parts = str(ap_group or "").split(":")
    if len(parts) >= 2:
        return ":".join(parts[-2:])

    text = str(ap_group or "")
    return text[-5:] if text else "-"


def get_bssid_color_map(bssids):
    return {
        bssid: AP_PALETTE[index % len(AP_PALETTE)]
        for index, bssid in enumerate(sorted(bssids))
    }


def get_limited_bssid_color_map(dominant_df, limit=MAX_LEGEND_ITEMS):
    counts = dominant_df["dominant_ap_group"].value_counts()
    primary_groups = list(counts.head(limit).index)
    color_map = {
        ap_group: AP_PALETTE[index % len(AP_PALETTE)]
        for index, ap_group in enumerate(primary_groups)
    }

    for ap_group in counts.index:
        color_map.setdefault(ap_group, OTHER_AP_COLOR)

    return color_map, primary_groups, max(0, len(counts) - len(primary_groups))


def create_marker_legend_handle(label, color):
    return Line2D(
        [0],
        [0],
        marker="o",
        color="w",
        label=label,
        markerfacecolor=color,
        markeredgecolor="black",
        markersize=6
    )


def build_channel_legend_handles(channel_df, band, intermediate_label, format_value, other_label="Altri"):
    if band == "2.4":
        handles = [
            create_marker_legend_handle("CH 1", "#18bc9c"),
            create_marker_legend_handle("CH 6", "#3498db"),
            create_marker_legend_handle("CH 11", "#9b59b6"),
        ]
        channels = {int(float(channel)) for channel in channel_df["channel"].dropna()}
        if channels - {1, 6, 11}:
            handles.append(create_marker_legend_handle(intermediate_label, "#f39c12"))
        return handles

    handles = []
    channels = sorted(channel_df["channel"].dropna().unique())
    visible_channels = channels[:MAX_LEGEND_ITEMS]
    for channel in visible_channels:
        channel_label = format_value(channel)
        band_prefix = get_channel_band_prefix(channel) if band == "all" else ""
        label_prefix = f"{band_prefix} " if band_prefix else ""
        handles.append(
            create_marker_legend_handle(
                f"{label_prefix}CH {channel_label}",
                get_channel_color(channel, band)
            )
        )
    if len(channels) > len(visible_channels):
        handles.append(create_marker_legend_handle(other_label, "#7f8c8d"))

    return handles


def build_interference_legend_handles(low_label, medium_label, high_label):
    return [
        create_marker_legend_handle(f"0-30 {low_label}", "#1a9850"),
        create_marker_legend_handle(f"30-60 {medium_label}", "#fee08b"),
        create_marker_legend_handle(f"60-100 {high_label}", "#d73027"),
    ]


def build_dominant_ap_legend_handles(dominant_df, color_map, roaming_label, other_label="Altri"):
    handles = []
    visible_groups = [
        ap_group
        for ap_group, color in color_map.items()
        if color != OTHER_AP_COLOR
    ]
    for ap_group in visible_groups[:MAX_LEGEND_ITEMS]:
        handles.append(
            create_marker_legend_handle(
                get_ap_group_suffix(ap_group),
                color_map.get(ap_group, "#7f8c8d")
            )
        )

    if any(color == OTHER_AP_COLOR for color in color_map.values()):
        handles.append(create_marker_legend_handle(other_label, OTHER_AP_COLOR))

    if dominant_df.get("roaming_overlap", []).any():
        handles.append(
            Line2D(
                [0],
                [0],
                marker="o",
                color="w",
                label=roaming_label,
                markerfacecolor="#ffffff",
                markeredgecolor="#f1c40f",
                markeredgewidth=2,
                markersize=6
            )
        )

    return handles


def add_reference_table(ax, rows, title, overflow_label=None, max_rows=MAX_REFERENCE_ROWS):
    if not rows:
        return

    total_rows = len(rows)
    visible_rows = rows[:max_rows]

    if total_rows > max_rows:
        visible_rows.append({
            "ref": "+",
            "label": overflow_label or f"{total_rows - max_rows} more in CSV report"
        })

    table_rows = []
    for row in visible_rows:
        table_rows.append([str(row["ref"]), str(row["label"])])

    table_height = min(0.22, max(0.11, 0.038 * (len(table_rows) + 1)))
    table = ax.table(
        cellText=table_rows,
        colLabels=["#", title],
        cellLoc="left",
        colLoc="left",
        loc="bottom",
        colWidths=[0.08, 0.92],
        bbox=[0.02, -0.12 - table_height, 0.96, table_height]
    )
    table.auto_set_font_size(False)
    table.set_fontsize(6.2)
    table.scale(1, 1.15)

    for cell in table.get_celld().values():
        cell.set_edgecolor("#d0d0d0")
        cell.set_linewidth(0.5)

    ax.figure.subplots_adjust(bottom=0.16 + table_height)


def annotate_channel_references(ax, channel_df, format_value, mode="auto", band="all", labels=None):
    labels = labels or {}
    references = []
    previous_channel = None

    for _index, row in channel_df.iterrows():
        channel_value = row.get("channel", "")
        if not should_label_channel_point(row, previous_channel, mode, band):
            previous_channel = channel_value
            continue

        channel = format_value(row.get("channel", ""))
        width = format_value(row.get("channel_width_mhz", ""))
        band_prefix = get_channel_band_prefix(row.get("channel", "")) if band == "all" else ""
        label_prefix = f"{band_prefix} " if band_prefix else ""
        channel_word = labels.get("channel", "CH")
        width_word = labels.get("width", "width")
        label = f"{label_prefix}{channel_word} {channel}"
        if width != "-":
            label = f"{label}, {width_word} {width} MHz"

        ref = len(references) + 1
        if ref <= MAX_REFERENCE_ROWS:
            annotate_reference_number(ax, row["x"], row["y"], ref)
        references.append({"ref": ref, "label": label})
        previous_channel = channel_value

    return references


def should_label_channel_point(row, previous_channel, mode, band):
    if mode == "none":
        return False
    if mode == "all":
        return True

    try:
        channel = int(float(row.get("channel", "")))
    except (TypeError, ValueError):
        return mode in {"auto", "critical"}

    is_intermediate_24 = band == "2.4" and channel not in {1, 6, 11}
    try:
        previous_channel_number = int(float(previous_channel))
    except (TypeError, ValueError):
        previous_channel_number = None

    changed_channel = previous_channel_number is None or channel != previous_channel_number

    if mode == "critical":
        return is_intermediate_24 and changed_channel

    return changed_channel


def annotate_dominant_ap_references(ax, dominant_df, format_value, mode="auto", labels=None):
    labels = labels or {}
    references = []
    previous_bssid = None
    previous_roaming_overlap = False

    for _index, row in dominant_df.iterrows():
        ap_group = row.get("dominant_ap_group", "")
        roaming_overlap = bool(row.get("roaming_overlap"))
        if not should_label_dominant_point(row, previous_bssid, previous_roaming_overlap, mode):
            previous_bssid = ap_group
            previous_roaming_overlap = roaming_overlap
            continue

        ap_word = labels.get("ap", "AP")
        label = f"{ap_word} {get_ap_group_suffix(row.get('dominant_ap_group', ''))}"

        if row.get("roaming_overlap"):
            delta = format_value(row.get("delta_db", ""))
            delta_word = labels.get("delta", "delta")
            label = f"{label}, {delta_word} {delta} dB"

        ref = len(references) + 1
        if ref <= MAX_REFERENCE_ROWS:
            annotate_reference_number(ax, row["x"], row["y"], ref)
        references.append({"ref": ref, "label": label})
        previous_bssid = ap_group
        previous_roaming_overlap = roaming_overlap

    return references


def should_label_dominant_point(row, previous_bssid, previous_roaming_overlap=False, mode="auto"):
    if mode == "none":
        return False
    if mode == "all":
        return True

    is_roaming_overlap = bool(row.get("roaming_overlap"))
    changed_bssid = previous_bssid is None or row.get("dominant_ap_group", "") != previous_bssid
    starts_roaming_overlap = is_roaming_overlap and not previous_roaming_overlap

    if mode == "critical":
        return starts_roaming_overlap

    return changed_bssid or starts_roaming_overlap


def annotate_interference_references(ax, risk_df, format_value, mode="critical", limit=3, labels=None):
    if mode == "none":
        return []

    labels = labels or {}
    references = []
    sorted_points = risk_df.sort_values("risk", ascending=False)
    top_points = sorted_points if mode == "all" else sorted_points.head(limit)

    for _index, row in top_points.iterrows():
        risk_value = float(row.get("risk", 0) or 0)
        if risk_value < 30:
            continue

        risk_word = labels.get("risk", "Risk")
        channel_word = labels.get("channel_short", "CH")
        serving_ssid = str(row.get("ssid", "") or "-")
        interferer_ssid = str(row.get("strongest_interferer_ssid", "") or "-")
        serving_channel = format_value(row.get("serving_channel", ""))
        interferer_channel = format_value(row.get("strongest_interferer_channel", ""))
        label = f"{risk_word} {risk_value:.0f}%"

        interferer_label = interferer_ssid
        if interferer_channel != "-":
            interferer_label = f"{interferer_label} {channel_word} {interferer_channel}"

        serving_label = serving_ssid
        if serving_channel != "-":
            serving_label = f"{serving_label} {channel_word} {serving_channel}"

        if interferer_label != "-" or serving_label != "-":
            label = f"{label}, {interferer_label} -> {serving_label}"

        ref = len(references) + 1
        if ref <= MAX_REFERENCE_ROWS:
            annotate_reference_number(ax, row["x"], row["y"], ref)
        references.append({"ref": ref, "label": label})

    return references


def annotate_point(ax, x, y, label):
    ax.annotate(
        label,
        xy=(x, y),
        xytext=(6, -8),
        textcoords="offset points",
        fontsize=6,
        fontweight="bold",
        color="#111111",
        bbox={
            "boxstyle": "round,pad=0.18",
            "facecolor": "white",
            "edgecolor": "#333333",
            "alpha": 0.74,
            "linewidth": 0.7
        },
        zorder=4
    )


def annotate_reference_number(ax, x, y, number):
    ax.annotate(
        str(number),
        xy=(x, y),
        xytext=(4, -4),
        textcoords="offset points",
        ha="center",
        va="center",
        fontsize=4.3,
        fontweight="bold",
        color="#111111",
        bbox={
            "boxstyle": "circle,pad=0.06",
            "facecolor": "white",
            "edgecolor": "#333333",
            "alpha": 0.92,
            "linewidth": 0.55
        },
        zorder=5
    )
