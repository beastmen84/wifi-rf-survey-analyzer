import os
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import tkinter as tk
from tkinter import font as tkfont
from tkinter import filedialog, messagebox, simpledialog
from datetime import datetime

import ttkbootstrap as ttk
from ttkbootstrap.constants import DANGER, INFO, PRIMARY, SECONDARY, SUCCESS, WARNING
import fitz  # pymupdf
from PIL import Image, ImageTk
import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg", force=True)
import matplotlib.pyplot as plt

from ap_groups import (
    build_detected_ap_groups,
    build_dominant_ap_group_labels as build_ap_group_labels,
    build_default_manual_groups,
    format_ap_label as format_ap_group_label,
    format_short_bssid,
    get_ap_group_key,
    merge_new_bssids_into_manual_groups,
)
from constants import (
    HEATMAP_GRID_SIZE,
    HEATMAP_SMOOTHING_SIGMA,
    HEATMAP_MAX_DISTANCE_PX,
    MIN_GOOD_SCAN_NETWORKS,
    SUSPICIOUS_SCAN_RATIO,
)
from heatmap_tools import (
    apply_distance_mask,
    apply_signal_threshold,
    calculate_interference_points,
    collapse_heatmap_points,
    filter_by_band,
    format_band_label,
    get_channel_map_points,
    get_distance_alpha,
    get_dominant_ap_points,
    get_interference_data_quality,
    interpolate_signal_grid,
    smooth_heatmap_grid,
)
from i18n import SUPPORTED_LANGUAGES, normalize_language, translate
from live_renderer import render_live_continuous_map
from map_config import MapConfig
from map_rendering import (
    add_reference_table,
    annotate_channel_references,
    annotate_dominant_ap_references,
    annotate_interference_references,
    build_channel_legend_handles,
    build_dominant_ap_legend_handles,
    build_interference_legend_handles,
    get_channel_color,
    get_channel_sort_key,
    get_limited_bssid_color_map,
)
from mouse_icons import create_shortcut_icon
from quality_engine import (
    QUALITY_GOOD,
    QUALITY_LOW_CONFIDENCE,
    QUALITY_MISSING_RELEVANT,
    QUALITY_SPARSE_DATA,
    QUALITY_UNSTABLE_SIGNAL,
    evaluate_point_quality,
)
from survey_store import (
    format_point_id,
    SurveySession,
    SurveyFormatError,
)
from ui_dialogs import open_existing_survey_file, save_survey_file_as
from utils import sanitize_filename, signal_to_color
from wifi_scanner import get_connected_ssid, scan_wifi

RELEVANT_SSIDS_METADATA_KEY = "relevant_ssids"
KNOWN_SSIDS_METADATA_KEY = "known_ssids"
AVAILABLE_THEMES = ("flatly", "cosmo", "darkly", "superhero")
DARK_THEMES = {"darkly", "superhero"}


class WifiHeatmapApp:
    def __init__(self, root, csv_file, language="it"):
        self.root = root
        self.language = normalize_language(language)
        self.language_var = tk.StringVar(value=self.language.upper())
        self.root.title(self.tr("app_title"))
        self.configure_app_styles()
        self.session = SurveySession(csv_file)
        self.csv_file = self.session.csv_file

        self.image_path = None
        self.bg_image = None
        self.tk_image = None
        self.canvas_image = None
        self.point_markers = []
        self.zoom_level = 1.0
        self.last_good_scan = []
        self.last_scan_backend_used = "-"
        self.relevant_ssids = self.load_relevant_ssids()
        self.known_ssids = self.load_known_ssids()
        self.selected_point_id = None
        self.highlight_item_id = None
        self.tooltip_window = None
        self.modal_dialogs = []
        self.live_preview_image = None
        self.live_preview_tk_image = None
        self.live_update_after_id = None
        self.live_quality_after_id = None
        self.live_preview_dirty = False
        self.live_preview_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="live-preview")
        self.live_preview_task_id = 0
        self.live_preview_busy = False
        self.live_point_infos = []
        self.live_image_transform = None
        self.live_tooltip_window = None
        self.live_tooltip_point = None
        self.live_hover_legend_label = None
        self.live_zoom_level = 1.0
        self.live_scale_payload = None
        self.points_table_resize_after_id = None
        self.point_quality_by_item = {}
        self.alias_table_resize_after_id = None

        self.status_var = tk.StringVar(value=self.tr("active_survey", name=self.session_display_name()))
        self.csv_var = tk.StringVar(value=self.session_display_name())
        self.map_var = tk.StringVar(value=self.tr("no_map"))
        self.points_var = tk.StringVar(value="0")
        self.last_point_var = tk.StringVar(value="-")
        self.footer_info_var = tk.StringVar(value="")
        self.last_scan_var = tk.StringVar(value=self.tr("no_scan"))
        self.best_scan_var = tk.StringVar(value="-")
        self.scan_filter_var = tk.StringVar(value="-")
        self.scan_quality_var = tk.StringVar(value=self.tr("scan_quality_empty"))
        self.scan_backend_used_var = tk.StringVar(value=self.tr("backend_used_empty"))
        self.saved_network_var = tk.StringVar(value="")
        self.scan_backend_var = tk.StringVar(value="auto")
        self.theme_var = tk.StringVar(value="flatly")
        self.ssid_var = tk.StringVar(value="")
        self.band_var = tk.StringVar(value="all")
        self.map_type_var = tk.StringVar(value="signal")
        self.live_map_type_choice_var = tk.StringVar()
        self.interference_mode_var = tk.StringVar(value="intra_ssid")
        self.interpolation_var = tk.StringVar(value="rbf")
        self.aggregation_var = tk.StringVar(value="max")
        self.color_scale_var = tk.StringVar(value="fixed")
        self.point_label_mode_var = tk.StringVar(value="auto")
        self.ap_group_filter_var = tk.StringVar(value="")
        self.usable_only_var = tk.BooleanVar(value=False)
        self.smoothing_var = tk.DoubleVar(value=HEATMAP_SMOOTHING_SIGMA)
        self.distance_var = tk.DoubleVar(value=self.distance_display_from_px(HEATMAP_MAX_DISTANCE_PX))
        self.scale_calibration_points = []
        self.scale_calibration_items = []

        toolbar = ttk.Frame(root, padding=(8, 6))
        toolbar.pack(side=tk.TOP, fill=tk.X)

        self.toolbar_title = ttk.Label(toolbar, text="Wi-Fi Heatmap", font=("Segoe UI", 11, "bold"), bootstyle=PRIMARY)
        self.toolbar_title.pack(side=tk.LEFT, padx=(0, 12))
        self.new_survey_button = ttk.Button(toolbar, command=self.new_survey, bootstyle=SECONDARY)
        self.new_survey_button.pack(side=tk.LEFT, padx=(0, 6))
        self.open_survey_button = ttk.Button(toolbar, command=self.open_survey, bootstyle=SECONDARY)
        self.open_survey_button.pack(side=tk.LEFT, padx=(0, 6))
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=(0, 6))
        self.load_plan_button = ttk.Button(toolbar, command=self.load_plan, bootstyle=PRIMARY)
        self.load_plan_button.pack(side=tk.LEFT, padx=(0, 6))
        self.save_button = ttk.Button(toolbar, command=self.save_survey, bootstyle=PRIMARY)
        self.save_button.pack(side=tk.LEFT, padx=(0, 6))
        self.open_csv_button = ttk.Button(toolbar, command=self.open_csv, bootstyle=SECONDARY)
        self.open_csv_button.pack(side=tk.LEFT, padx=(0, 6))
        self.alias_button = ttk.Button(toolbar, command=self.open_ap_alias_dialog, bootstyle=SECONDARY)
        self.alias_button.pack(side=tk.LEFT, padx=(0, 6))
        self.calibrate_button = ttk.Button(toolbar, command=self.start_scale_calibration, bootstyle=SECONDARY)
        self.calibrate_button.pack(side=tk.LEFT, padx=(0, 6))
        self.help_button = ttk.Button(toolbar, command=self.open_help_dialog, bootstyle=SECONDARY)
        self.help_button.pack(side=tk.LEFT)
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=(0, 6))
        self.generate_button = ttk.Button(toolbar, command=self.open_heatmap_dialog, bootstyle=SUCCESS)
        self.generate_button.pack(side=tk.LEFT)
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=(0, 6))
        ttk.Button(toolbar, text="-", width=3, command=self.zoom_out, bootstyle=SECONDARY).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(toolbar, text="+", width=3, command=self.zoom_in, bootstyle=SECONDARY).pack(side=tk.LEFT, padx=(0, 4))
        self.fit_button = ttk.Button(toolbar, width=5, command=self.fit_to_window, bootstyle=SECONDARY)
        self.fit_button.pack(side=tk.LEFT)

        language_frame = ttk.Frame(toolbar)
        language_frame.pack(side=tk.RIGHT)
        self.language_label = ttk.Label(language_frame)
        self.language_label.pack(side=tk.LEFT, padx=(0, 6))
        self.language_combo = ttk.Combobox(
            language_frame,
            textvariable=self.language_var,
            state="readonly",
            values=SUPPORTED_LANGUAGES,
            width=5
        )
        self.language_combo.pack(side=tk.LEFT)
        self.language_combo.bind("<<ComboboxSelected>>", self.on_language_selected)

        theme_frame = ttk.Frame(toolbar)
        theme_frame.pack(side=tk.RIGHT, padx=(0, 14))
        self.theme_label = ttk.Label(theme_frame)
        self.theme_label.pack(side=tk.LEFT, padx=(0, 6))
        self.theme_combo = ttk.Combobox(
            theme_frame,
            textvariable=self.theme_var,
            state="readonly",
            values=self.get_available_themes(),
            width=14
        )
        self.theme_combo.pack(side=tk.LEFT)
        self.theme_combo.bind("<<ComboboxSelected>>", lambda _event: self.apply_selected_theme())

        main_notebook = ttk.Notebook(root, style="Main.TNotebook")
        main_notebook.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=8, pady=(4, 0))

        survey_tab = ttk.Frame(main_notebook)
        live_tab = ttk.Frame(main_notebook)
        main_notebook.add(survey_tab, text=self.tr("survey_tab"))
        main_notebook.add(live_tab, text=self.tr("live_map_tab"))
        main_notebook.bind("<<NotebookTabChanged>>", self.on_main_tab_changed)
        self.main_notebook = main_notebook

        content = ttk.Frame(survey_tab, padding=(0, 0, 0, 0))
        content.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        sidebar = ttk.Frame(content, width=260)
        sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8))
        sidebar.pack_propagate(False)
        self.build_sidebar(sidebar)

        viewer = ttk.Frame(content)
        viewer.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(viewer, bg="#6f6f6f", highlightthickness=0)
        self.v_scroll = ttk.Scrollbar(viewer, orient=tk.VERTICAL, command=self.canvas.yview)
        self.h_scroll = ttk.Scrollbar(viewer, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.canvas.configure(xscrollcommand=self.h_scroll.set, yscrollcommand=self.v_scroll.set)

        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.v_scroll.grid(row=0, column=1, sticky="ns")
        self.h_scroll.grid(row=1, column=0, sticky="ew")
        viewer.grid_rowconfigure(0, weight=1)
        viewer.grid_columnconfigure(0, weight=1)

        footer = ttk.Frame(root, padding=(8, 4))
        footer.pack(side=tk.BOTTOM, fill=tk.X)
        self.status = ttk.Label(footer, textvariable=self.status_var, anchor="w")
        self.status.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.copyright_label = ttk.Label(footer, anchor="e", style="ReadableMuted.TLabel")
        self.copyright_label.pack(side=tk.RIGHT, padx=(12, 0))
        self.footer_info = ttk.Label(footer, textvariable=self.footer_info_var, anchor="e", style="ReadableMuted.TLabel")
        self.footer_info.pack(side=tk.RIGHT, padx=(12, 0))

        self.canvas.bind("<ButtonPress-1>", self.start_map_drag)
        self.canvas.bind("<B1-Motion>", self.drag_map)
        self.canvas.bind("<ButtonRelease-1>", self.end_map_drag)
        self.canvas.bind("<Button-3>", self.create_point_from_event)
        self.canvas.bind("<MouseWheel>", self.on_mousewheel)
        self.canvas.bind("<Shift-MouseWheel>", self.on_shift_mousewheel)
        self.canvas.bind("<Control-MouseWheel>", self.on_ctrl_mousewheel)
        self.build_points_table(viewer)
        self.build_live_tab(live_tab)
        self.load_saved_plan()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.bind("<FocusIn>", self.restore_active_modal_dialog, add="+")
        self.root.bind("<Map>", self.restore_active_modal_dialog, add="+")
        self.apply_language()
        self.refresh_session_labels()

    def tr(self, key, **kwargs):
        return translate(self.language, key, **kwargs)

    def get_px_per_meter(self):
        try:
            value = float(self.session.metadata.get("px_per_meter", ""))
        except (TypeError, ValueError):
            return None

        return value if value > 0 else None

    def has_scale_calibration(self):
        return self.get_px_per_meter() is not None

    def distance_display_from_px(self, px_value):
        px_per_meter = self.get_px_per_meter()
        if px_per_meter:
            return round(float(px_value) / px_per_meter, 1)

        return int(round(float(px_value)))

    def distance_px_from_display(self, display_value):
        px_per_meter = self.get_px_per_meter()
        value = max(0.1, float(display_value))
        if px_per_meter:
            return max(1, int(round(value * px_per_meter)))

        return max(1, int(round(value)))

    def get_max_distance_label(self):
        return self.tr("max_distance_m") if self.has_scale_calibration() else self.tr("max_distance_px")

    def get_distance_control_range(self):
        if self.has_scale_calibration():
            return 1, 50, 0.5

        return 40, 600, 20

    def update_distance_labels(self):
        if hasattr(self, "live_distance_label"):
            self.live_distance_label.configure(text=self.get_max_distance_label())

        if hasattr(self, "live_distance_spinbox"):
            from_value, to_value, increment = self.get_distance_control_range()
            self.live_distance_spinbox.configure(from_=from_value, to=to_value, increment=increment)

    def session_display_name(self):
        if self.session.csv_file:
            return self.session.display_name

        return self.tr("unsaved_survey")

    def load_relevant_ssids(self):
        value = self.session.metadata.get(RELEVANT_SSIDS_METADATA_KEY)
        if value:
            try:
                ssids = json.loads(value)
            except json.JSONDecodeError:
                ssids = []

            if isinstance(ssids, list):
                return {
                    str(ssid)
                    for ssid in ssids
                    if str(ssid).strip()
                }

        return set()

    def load_known_ssids(self):
        value = self.session.metadata.get(KNOWN_SSIDS_METADATA_KEY)
        if value:
            try:
                ssids = json.loads(value)
            except json.JSONDecodeError:
                ssids = []

            if isinstance(ssids, list):
                return {
                    str(ssid)
                    for ssid in ssids
                    if str(ssid).strip()
                }

        return set(self.relevant_ssids)

    def save_known_ssids(self):
        serialized = json.dumps(sorted(self.known_ssids), ensure_ascii=False)
        self.session.update_metadata({KNOWN_SSIDS_METADATA_KEY: serialized})

    def update_saved_network_label(self):
        if not self.relevant_ssids:
            self.saved_network_var.set(self.tr("relevant_networks_none"))
            if hasattr(self, "forget_saved_network_button"):
                button_state = tk.NORMAL if self.known_ssids else tk.DISABLED
                self.forget_saved_network_button.configure(state=button_state, bootstyle=SECONDARY)
            return

        if hasattr(self, "forget_saved_network_button"):
            self.forget_saved_network_button.configure(state=tk.NORMAL, bootstyle=DANGER)

        self.saved_network_var.set(", ".join(sorted(self.relevant_ssids)))

    def refresh_session_labels(self):
        suffix = " *" if self.session.dirty else ""
        display_name = self.session_display_name()
        self.csv_var.set(f"{display_name}{suffix}")
        if hasattr(self, "save_button"):
            self.save_button.configure(bootstyle=WARNING if self.session.dirty else PRIMARY)
        self.update_footer_info()

    def configure_app_styles(self):
        style = ttk.Style()
        colors = style.colors
        is_dark_theme = str(style.theme_use()).lower() in DARK_THEMES
        self.is_dark_theme = is_dark_theme
        self.readable_text_color = "#d7dde3" if is_dark_theme else "#2f3640"
        self.readable_muted_color = "#d7dde3" if is_dark_theme else "#495057"
        self.live_overlay_bg = "#2f3640" if is_dark_theme else "#ffffff"
        self.live_overlay_border = "#d7dde3" if is_dark_theme else "#2c3e50"
        self.live_overlay_highlight = "#415161" if is_dark_theme else "#e8f4ff"
        self.live_overlay_separator = "#6c757d" if is_dark_theme else "#d7dde3"
        muted_foreground = "#d7dde3" if is_dark_theme else "#495057"
        style.configure(
            "Main.TNotebook",
            background=colors.bg,
            borderwidth=0,
            tabmargins=(6, 4, 6, 0)
        )
        style.configure(
            "Main.TNotebook.Tab",
            font=("Segoe UI", 10, "bold"),
            padding=(18, 9),
            background=colors.light,
            foreground=colors.secondary,
            borderwidth=1
        )
        style.map(
            "Main.TNotebook.Tab",
            background=[
                ("selected", colors.primary),
                ("active", colors.info),
            ],
            foreground=[
                ("selected", "#ffffff"),
                ("active", "#ffffff"),
            ],
            padding=[
                ("selected", (20, 10)),
                ("!selected", (18, 9)),
            ]
        )
        style.configure(
            "ReadableMuted.TLabel",
            foreground=muted_foreground,
            background=colors.bg
        )
        if hasattr(self, "live_scale_canvas"):
            self.live_scale_canvas.configure(background=colors.bg)
            self.redraw_live_scale_bar()

    def update_footer_info(self):
        self.footer_info_var.set(
            self.tr(
                "footer_survey_info",
                csv=self.csv_var.get(),
                map=self.map_var.get(),
                points=self.points_var.get(),
                last=self.last_point_var.get()
            )
        )

    def on_language_selected(self, _event=None):
        self.language = normalize_language(self.language_var.get())
        self.apply_language()
        self.refresh_session_labels()
        self.refresh_points_table()

    def apply_language(self):
        self.root.title(self.tr("app_title"))
        self.new_survey_button.configure(text=self.tr("new_survey"))
        self.open_survey_button.configure(text=self.tr("open_existing_survey"))
        self.load_plan_button.configure(text=self.tr("load_plan"))
        self.generate_button.configure(text=self.tr("generate_heatmap"))
        self.open_csv_button.configure(text=self.tr("open_csv"))
        self.save_button.configure(text=self.tr("save"))
        self.alias_button.configure(text=self.tr("ap_aliases"))
        self.calibrate_button.configure(text=self.tr("calibrate_scale"))
        self.help_button.configure(text=self.tr("help"))
        self.fit_button.configure(text=self.tr("fit"))
        self.language_label.configure(text=self.tr("language"))
        self.theme_label.configure(text=self.tr("theme"))
        self.copyright_label.configure(text=self.tr("copyright"))
        if hasattr(self, "main_notebook"):
            self.main_notebook.tab(0, text=self.tr("survey_tab"))
            self.main_notebook.tab(1, text=self.tr("live_map_tab"))
        if hasattr(self, "live_band_label"):
            self.live_band_label.configure(text=self.tr("band"))
            self.live_ap_filter_label.configure(text=self.tr("ap_filter"))
            self.live_map_type_label.configure(text=self.tr("map_type"))
            self.live_auto_update_check.configure(text=self.tr("live_auto_update"))
            self.live_update_button.configure(text=self.tr("live_update_now"))
            self.refresh_live_map_type_options()
            self.live_interference_mode_label.configure(text=self.tr("interference_mode"))
            self.update_distance_labels()
            self.live_usable_check.configure(text=self.tr("usable_only"))
            self.live_color_scale_label.configure(text=self.tr("color_scale"))
            self.live_interpolation_label.configure(text=self.tr("interpolation"))
            self.live_aggregation_label.configure(text=self.tr("aggregation"))
            self.live_fit_button.configure(text=self.tr("fit"))
            self.refresh_live_ap_filter_options()
            self.update_live_scale_bar()

        if self.image_path is None:
            self.map_var.set(self.tr("no_map"))
        if self.last_scan_backend_used == "-":
            self.last_scan_var.set(self.tr("no_scan"))
            self.scan_quality_var.set(self.tr("scan_quality_empty"))
            self.scan_backend_used_var.set(self.tr("backend_used_empty"))

        self.update_footer_info()
        self.update_saved_network_label()

        if hasattr(self, "scan_group"):
            self.scan_group.configure(text=self.tr("last_scan"))
            self.saved_network_group.configure(text=self.tr("saved_network"))
            self.forget_saved_network_button.configure(text=self.tr("forget_saved_network"))
            self.legend_group.configure(text=self.tr("points_legend"))
            self.points_table_group.configure(text=self.tr("detected_points"))
            self.points_table.heading("best", text=self.tr("best_dbm"))
            self.points_table.heading("quality", text=self.tr("quality"))
            self.points_table.heading("rows", text=self.tr("rows"))
            self.schedule_points_table_resize()
            self.focus_point_button.configure(text=self.tr("go_to_point"))
            self.delete_selected_button.configure(text=self.tr("delete_selected"))
            self.delete_last_button.configure(text=self.tr("delete_last"))

    def build_sidebar(self, parent):
        self.scan_group = ttk.LabelFrame(parent)
        self.scan_group.pack(fill=tk.X)
        scan_frame = ttk.Frame(self.scan_group, padding=8)
        scan_frame.pack(fill=tk.X)

        ttk.Label(scan_frame, textvariable=self.last_scan_var, wraplength=220).pack(anchor="w")
        self.scan_quality_label = ttk.Label(scan_frame, textvariable=self.scan_quality_var, wraplength=220, style="ReadableMuted.TLabel")
        self.scan_quality_label.pack(anchor="w", pady=(6, 0))
        ttk.Label(scan_frame, textvariable=self.best_scan_var, wraplength=220).pack(anchor="w", pady=(6, 0))
        ttk.Label(scan_frame, textvariable=self.scan_filter_var, wraplength=220).pack(anchor="w", pady=(6, 0))
        ttk.Label(scan_frame, textvariable=self.scan_backend_used_var, wraplength=220, bootstyle=INFO).pack(anchor="w", pady=(6, 0))

        self.saved_network_group = ttk.LabelFrame(parent)
        self.saved_network_group.pack(fill=tk.X, pady=(8, 0))
        saved_network_frame = ttk.Frame(self.saved_network_group, padding=8)
        saved_network_frame.pack(fill=tk.X)
        ttk.Label(saved_network_frame, textvariable=self.saved_network_var, wraplength=220, bootstyle=INFO).pack(anchor="w")
        self.forget_saved_network_button = ttk.Button(
            saved_network_frame,
            command=self.forget_saved_network,
            bootstyle=SECONDARY
        )
        self.forget_saved_network_button.pack(anchor="w", pady=(8, 0))

        self.legend_group = ttk.LabelFrame(parent)
        self.legend_group.pack(fill=tk.X, pady=(8, 0))
        legend_frame = ttk.Frame(self.legend_group, padding=8)
        legend_frame.pack(fill=tk.X)

        self.add_legend_row(legend_frame, "#2ca02c", ">= -60 dBm")
        self.add_legend_row(legend_frame, "#f2c94c", "-70 / -60 dBm")
        self.add_legend_row(legend_frame, "#d62728", "< -70 dBm")

    def add_legend_row(self, parent, color, label):
        row = ttk.Frame(parent)
        row.pack(fill=tk.X, pady=2)

        swatch = tk.Canvas(row, width=14, height=14, highlightthickness=0)
        swatch.create_oval(2, 2, 12, 12, fill=color, outline="white")
        swatch.pack(side=tk.LEFT)
        ttk.Label(row, text=label).pack(side=tk.LEFT, padx=(6, 0))

    def build_live_tab(self, parent):
        controls = ttk.Frame(parent, padding=(8, 8))
        controls.pack(side=tk.TOP, fill=tk.X)

        self.live_ssid_label = ttk.Label(controls, text="SSID")
        self.live_ssid_label.pack(side=tk.LEFT, padx=(0, 6))
        self.live_ssid_combo = ttk.Combobox(
            controls,
            textvariable=self.ssid_var,
            state="readonly",
            width=28
        )
        self.live_ssid_combo.pack(side=tk.LEFT, padx=(0, 12))
        self.live_ssid_combo.bind("<<ComboboxSelected>>", lambda _event: self.on_live_config_changed())

        self.live_band_label = ttk.Label(controls, text=self.tr("band"))
        self.live_band_label.pack(side=tk.LEFT, padx=(0, 6))
        self.live_band_combo = ttk.Combobox(
            controls,
            textvariable=self.band_var,
            state="readonly",
            values=("all", "2.4", "5"),
            width=8
        )
        self.live_band_combo.pack(side=tk.LEFT, padx=(0, 12))
        self.live_band_combo.bind("<<ComboboxSelected>>", lambda _event: self.on_live_config_changed())

        self.live_ap_filter_label = ttk.Label(controls, text=self.tr("ap_filter"))
        self.live_ap_filter_label.pack(side=tk.LEFT, padx=(0, 6))
        self.live_ap_filter_combo = ttk.Combobox(
            controls,
            textvariable=self.ap_group_filter_var,
            state="readonly",
            values=(self.tr("ap_filter_all"),),
            width=24
        )
        self.live_ap_filter_combo.pack(side=tk.LEFT, padx=(0, 12))
        self.live_ap_filter_combo.bind("<<ComboboxSelected>>", lambda _event: self.on_live_config_changed())

        self.live_map_type_label = ttk.Label(controls, text=self.tr("map_type"))
        self.live_map_type_label.pack(side=tk.LEFT, padx=(0, 6))
        self.live_map_type_combo = ttk.Combobox(
            controls,
            textvariable=self.live_map_type_choice_var,
            state="readonly",
            width=20
        )
        self.live_map_type_combo.pack(side=tk.LEFT, padx=(0, 12))
        self.live_map_type_combo.bind("<<ComboboxSelected>>", self.on_live_map_type_selected)
        self.refresh_live_map_type_options()

        self.live_auto_update_var = tk.BooleanVar(value=True)
        self.live_auto_update_check = ttk.Checkbutton(
            controls,
            text=self.tr("live_auto_update"),
            variable=self.live_auto_update_var
        )
        self.live_auto_update_check.pack(side=tk.LEFT, padx=(0, 12))
        self.live_update_button = ttk.Button(
            controls,
            text=self.tr("live_update_now"),
            command=self.update_live_preview,
            bootstyle=PRIMARY
        )
        self.live_update_button.pack(side=tk.LEFT)
        ttk.Separator(controls, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)
        ttk.Button(controls, text="-", width=3, command=self.live_zoom_out, bootstyle=SECONDARY).pack(
            side=tk.LEFT,
            padx=(0, 4)
        )
        ttk.Button(controls, text="+", width=3, command=self.live_zoom_in, bootstyle=SECONDARY).pack(
            side=tk.LEFT,
            padx=(0, 4)
        )
        self.live_fit_button = ttk.Button(controls, text=self.tr("fit"), width=5, command=self.live_fit_to_window, bootstyle=SECONDARY)
        self.live_fit_button.pack(side=tk.LEFT)

        live_options = ttk.Frame(parent, padding=(8, 0, 8, 8))
        live_options.pack(side=tk.TOP, fill=tk.X)

        self.live_interference_mode_label = ttk.Label(live_options, text=self.tr("interference_mode"))
        self.live_interference_mode_label.pack(side=tk.LEFT, padx=(0, 6))
        self.live_interference_mode_combo = ttk.Combobox(
            live_options,
            textvariable=self.interference_mode_var,
            state="readonly",
            values=("intra_ssid", "all"),
            width=12
        )
        self.live_interference_mode_combo.pack(side=tk.LEFT, padx=(0, 14))
        self.live_interference_mode_combo.bind("<<ComboboxSelected>>", lambda _event: self.on_live_config_changed())

        self.live_smoothing_label = ttk.Label(live_options, text="Smoothing")
        self.live_smoothing_label.pack(side=tk.LEFT, padx=(0, 6))
        self.live_smoothing_spinbox = ttk.Spinbox(
            live_options,
            from_=0.0,
            to=8.0,
            increment=0.5,
            textvariable=self.smoothing_var,
            width=6,
            command=self.on_live_config_changed
        )
        self.live_smoothing_spinbox.pack(side=tk.LEFT, padx=(0, 14))
        self.live_smoothing_spinbox.bind("<Return>", lambda _event: self.on_live_config_changed())
        self.live_smoothing_spinbox.bind("<FocusOut>", lambda _event: self.on_live_config_changed())

        self.live_distance_label = ttk.Label(live_options, text=self.get_max_distance_label())
        self.live_distance_label.pack(side=tk.LEFT, padx=(0, 6))
        distance_from, distance_to, distance_increment = self.get_distance_control_range()
        self.live_distance_spinbox = ttk.Spinbox(
            live_options,
            from_=distance_from,
            to=distance_to,
            increment=distance_increment,
            textvariable=self.distance_var,
            width=6,
            command=self.on_live_config_changed
        )
        self.live_distance_spinbox.pack(side=tk.LEFT, padx=(0, 14))
        self.live_distance_spinbox.bind("<Return>", lambda _event: self.on_live_config_changed())
        self.live_distance_spinbox.bind("<FocusOut>", lambda _event: self.on_live_config_changed())

        self.live_usable_check = ttk.Checkbutton(
            live_options,
            text=self.tr("usable_only"),
            variable=self.usable_only_var,
            command=self.on_live_config_changed
        )
        self.live_usable_check.pack(side=tk.LEFT, padx=(0, 14))

        self.live_color_scale_label = ttk.Label(live_options, text=self.tr("color_scale"))
        self.live_color_scale_label.pack(side=tk.LEFT, padx=(0, 6))
        self.live_color_scale_combo = ttk.Combobox(
            live_options,
            textvariable=self.color_scale_var,
            state="readonly",
            values=("fixed", "auto"),
            width=9
        )
        self.live_color_scale_combo.pack(side=tk.LEFT, padx=(0, 14))
        self.live_color_scale_combo.bind("<<ComboboxSelected>>", lambda _event: self.on_live_config_changed())

        self.live_interpolation_label = ttk.Label(live_options, text=self.tr("interpolation"))
        self.live_interpolation_label.pack(side=tk.LEFT, padx=(0, 6))
        self.live_interpolation_combo = ttk.Combobox(
            live_options,
            textvariable=self.interpolation_var,
            state="readonly",
            values=("rbf", "linear"),
            width=8
        )
        self.live_interpolation_combo.pack(side=tk.LEFT, padx=(0, 14))
        self.live_interpolation_combo.bind("<<ComboboxSelected>>", lambda _event: self.on_live_config_changed())

        self.live_aggregation_label = ttk.Label(live_options, text=self.tr("aggregation"))
        self.live_aggregation_label.pack(side=tk.LEFT, padx=(0, 6))
        self.live_aggregation_combo = ttk.Combobox(
            live_options,
            textvariable=self.aggregation_var,
            state="readonly",
            values=("max", "mean", "median"),
            width=8
        )
        self.live_aggregation_combo.pack(side=tk.LEFT)
        self.live_aggregation_combo.bind("<<ComboboxSelected>>", lambda _event: self.on_live_config_changed())

        body = ttk.Frame(parent, padding=(8, 0, 8, 8))
        body.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.live_canvas = tk.Canvas(body, bg="#6f6f6f", highlightthickness=0)
        self.live_canvas.pack(fill=tk.BOTH, expand=True)
        self.live_canvas.bind("<Configure>", lambda _event: self.render_live_canvas_image())
        self.live_canvas.bind("<Motion>", self.on_live_canvas_motion)
        self.live_canvas.bind("<Leave>", lambda _event: self.hide_live_tooltip())
        self.live_canvas.bind("<ButtonPress-1>", self.start_live_map_drag)
        self.live_canvas.bind("<B1-Motion>", self.drag_live_map)
        self.live_canvas.bind("<ButtonRelease-1>", self.end_live_map_drag)
        self.live_canvas.bind("<Control-MouseWheel>", self.on_live_ctrl_mousewheel)

        self.live_scale_parent = parent
        self.live_scale_frame = ttk.Frame(parent, padding=(8, 4, 8, 4))
        self.live_scale_frame.pack(side=tk.BOTTOM, fill=tk.X)
        self.live_scale_title_var = tk.StringVar(value="")
        ttk.Label(self.live_scale_frame, textvariable=self.live_scale_title_var, width=18, anchor="w").pack(
            side=tk.LEFT,
            padx=(0, 8)
        )
        self.live_scale_canvas = tk.Canvas(self.live_scale_frame, height=52, highlightthickness=0)
        self.live_scale_canvas.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.live_scale_canvas.bind("<Configure>", lambda _event: self.redraw_live_scale_bar())

        self.live_status_var = tk.StringVar(value=self.tr("live_preview_empty"))
        self.live_status_label = ttk.Label(parent, textvariable=self.live_status_var, anchor="w", style="ReadableMuted.TLabel")
        self.live_status_label.pack(
            side=tk.BOTTOM,
            fill=tk.X,
            padx=8,
            pady=(0, 4)
        )

    def get_available_themes(self):
        installed_themes = set(ttk.Style().theme_names())
        themes = [theme for theme in AVAILABLE_THEMES if theme in installed_themes]
        return themes or ["flatly"]

    def apply_selected_theme(self):
        theme_name = self.theme_var.get()

        if not theme_name:
            return

        ttk.Style().theme_use(theme_name)
        self.configure_app_styles()
        self.root.update_idletasks()
        self.update_live_scale_bar()
        self.status_var.set(self.tr("theme_applied", theme=theme_name))

    def open_ap_alias_dialog(self):
        dialog = self.create_modal_dialog(self.tr("ap_groups_title"))
        dialog.geometry("1560x780")
        dialog.minsize(1320, 700)

        frame = ttk.Frame(dialog, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text=self.tr("ap_groups_hint"), wraplength=1460, style="ReadableMuted.TLabel").pack(anchor="w", pady=(0, 10))

        detected_groups = self.get_detected_ap_groups()
        aliases = self.session.get_ap_aliases()
        saved_groups = self.session.get_ap_groups()
        groups = (
            merge_new_bssids_into_manual_groups(saved_groups, self.session.rows)
            if saved_groups
            else build_default_manual_groups(self.session.rows)
        )
        detected_by_bssid = {
            bssid: detected_group
            for detected_group in detected_groups
            for bssid in detected_group["bssids"]
        }

        for group in groups:
            group["alias"] = group.get("alias") or aliases.get(group["group_id"], "")
            seen_ssids = set()
            seen_channels = set()
            display_groups = set()
            for bssid in group.get("bssids", []):
                detected_group = detected_by_bssid.get(bssid)
                if not detected_group:
                    continue
                seen_ssids.update(detected_group["ssids"])
                seen_channels.update(detected_group["channels"])
                display_groups.update(detected_group["display_groups"])
            group["ssids"] = sorted(seen_ssids)
            group["channels"] = sorted(seen_channels, key=self.channel_sort_key)
            group["display_groups"] = sorted(display_groups) or [group["group_id"]]

        if not groups:
            ttk.Label(frame, text=self.tr("ap_aliases_empty"), bootstyle=WARNING).pack(anchor="w")
            dialog.bind("<Escape>", lambda _event: dialog.destroy())
            self.center_dialog(dialog)
            return

        search_frame = ttk.Frame(frame)
        search_frame.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(search_frame, text=self.tr("ap_alias_search")).pack(side=tk.LEFT)
        search_var = tk.StringVar(value="")
        search_entry = ttk.Entry(search_frame, textvariable=search_var, width=42)
        search_entry.pack(side=tk.LEFT, padx=(8, 0), fill=tk.X, expand=True)

        columns = ("status", "group", "alias", "bssids", "ssids", "channels", "locked")
        table_frame = ttk.Frame(frame)
        table_frame.pack(fill=tk.BOTH, expand=True)
        tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=16)
        tree.column("status", width=42, minwidth=36, anchor="center", stretch=False)
        tree.column("group", width=300, minwidth=220, anchor="w", stretch=True)
        tree.column("alias", width=260, minwidth=180, anchor="w", stretch=True)
        tree.column("bssids", width=430, minwidth=260, anchor="w", stretch=True)
        tree.column("ssids", width=340, minwidth=220, anchor="w", stretch=True)
        tree.column("channels", width=120, minwidth=90, anchor="center", stretch=False)
        tree.column("locked", width=110, minwidth=90, anchor="center", stretch=False)
        tree.tag_configure("aliased", background="#e9f7ef")
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        active_editor = {"entry": None, "item": None}
        sort_state = {"column": "ssids", "reverse": False}

        def get_group_display_values(group):
            alias = group.get("alias", "")
            return (
                "OK" if alias else "",
                ", ".join(group["display_groups"]),
                alias,
                ", ".join(group["bssids"]),
                ", ".join(group["ssids"]),
                ", ".join(group["channels"]),
                self.tr("yes") if group.get("locked") else self.tr("no"),
            )

        def group_matches_search(group, query):
            if not query:
                return True

            alias = group.get("alias", "")
            haystack = " ".join([
                group["group_id"],
                " ".join(group["display_groups"]),
                alias,
                " ".join(group["bssids"]),
                " ".join(group["ssids"]),
                " ".join(group["channels"]),
            ]).lower()
            return query.lower() in haystack

        def sort_value(group, column):
            alias = group.get("alias", "")
            if column == "status":
                return 0 if alias else 1
            if column == "alias":
                return alias.lower()
            if column == "bssids":
                return " ".join(group["bssids"]).lower()
            if column == "ssids":
                return " ".join(group["ssids"]).lower()
            if column == "channels":
                return [self.channel_sort_key(channel) for channel in group["channels"]]
            if column == "locked":
                return 0 if group.get("locked") else 1
            return " ".join(group["display_groups"]).lower()

        def render_alias_rows():
            close_alias_editor(False)
            query = search_var.get().strip()
            visible_groups = [
                group
                for group in groups
                if group_matches_search(group, query)
            ]
            visible_groups.sort(
                key=lambda group: sort_value(group, sort_state["column"]),
                reverse=sort_state["reverse"]
            )
            tree.delete(*tree.get_children())
            for group in visible_groups:
                tree.insert(
                    "",
                    tk.END,
                    iid=group["group_id"],
                    tags=("aliased",) if group.get("alias") else (),
                    values=get_group_display_values(group)
                )

        def sort_by_column(column):
            if column == "status":
                sort_state["column"] = column
                sort_state["reverse"] = False
            elif sort_state["column"] == column:
                sort_state["reverse"] = not sort_state["reverse"]
            else:
                sort_state["column"] = column
                sort_state["reverse"] = False
            render_alias_rows()

        tree.heading("status", text="", command=lambda: sort_by_column("status"))
        tree.heading("group", text=self.tr("ap_alias_group"), command=lambda: sort_by_column("group"))
        tree.heading("alias", text=self.tr("ap_alias_value"), command=lambda: sort_by_column("alias"))
        tree.heading("bssids", text=self.tr("ap_alias_bssids"), command=lambda: sort_by_column("bssids"))
        tree.heading("ssids", text=self.tr("ap_alias_ssids"), command=lambda: sort_by_column("ssids"))
        tree.heading("channels", text=self.tr("ap_alias_channels"), command=lambda: sort_by_column("channels"))
        tree.heading("locked", text=self.tr("ap_group_locked"), command=lambda: sort_by_column("locked"))
        search_entry.bind("<KeyRelease>", lambda _event: render_alias_rows())

        def schedule_alias_table_resize(_event=None):
            if self.alias_table_resize_after_id is not None:
                self.root.after_cancel(self.alias_table_resize_after_id)

            self.alias_table_resize_after_id = self.root.after(
                50,
                lambda: self.adjust_alias_table_columns(tree, columns)
            )

        def set_alias(group_key, value):
            value = value.strip()
            for group in groups:
                if group["group_id"] == group_key:
                    group["alias"] = value
                    group["locked"] = True
                    break

            current_values = list(tree.item(group_key, "values"))
            current_values[0] = "OK" if value else ""
            current_values[2] = value
            current_values[6] = self.tr("yes")
            tree.item(group_key, values=current_values)
            tree.item(group_key, tags=("aliased",) if value else ())

        def close_alias_editor(save_value=True):
            entry = active_editor.get("entry")
            group_key = active_editor.get("item")
            if entry is None:
                return

            if save_value and group_key:
                set_alias(group_key, entry.get())

            entry.destroy()
            active_editor["entry"] = None
            active_editor["item"] = None

        def begin_alias_edit(event):
            if tree.identify_column(event.x) != "#3":
                return

            group_key = tree.identify_row(event.y)
            if not group_key:
                return

            close_alias_editor()
            bbox = tree.bbox(group_key, "alias")
            if not bbox:
                return

            x, y, width, height = bbox
            entry = ttk.Entry(tree)
            group = next((item for item in groups if item["group_id"] == group_key), {})
            entry.insert(0, group.get("alias", ""))
            entry.place(x=x, y=max(0, y - 1), width=width, height=height + 6)
            entry.focus_set()
            entry.select_range(0, tk.END)
            active_editor["entry"] = entry
            active_editor["item"] = group_key
            entry.bind("<Return>", lambda _event: close_alias_editor(True))
            entry.bind("<Escape>", lambda _event: close_alias_editor(False))
            entry.bind("<FocusOut>", lambda _event: close_alias_editor(True))

        def save_aliases():
            close_alias_editor(True)
            aliases = {
                group["group_id"]: group.get("alias", "")
                for group in groups
                if group.get("alias", "").strip()
            }
            aliases_changed = self.session.set_ap_aliases(aliases)
            groups_changed = self.session.set_ap_groups(groups)
            if aliases_changed or groups_changed:
                self.session.dirty = True
            self.refresh_session_labels()
            self.schedule_live_update(force=True)
            self.status_var.set(self.tr("ap_groups_saved"))
            dialog.destroy()

        tree.bind("<Double-1>", begin_alias_edit)
        table_frame.bind("<Configure>", schedule_alias_table_resize)
        tree.bind("<Configure>", schedule_alias_table_resize, add="+")
        render_alias_rows()
        schedule_alias_table_resize()
        buttons = ttk.Frame(frame)
        buttons.pack(fill=tk.X, pady=(12, 0))
        ttk.Button(buttons, text=self.tr("cancel"), command=dialog.destroy, bootstyle=SECONDARY).pack(side=tk.RIGHT)
        ttk.Button(buttons, text=self.tr("save"), command=save_aliases, bootstyle=PRIMARY).pack(side=tk.RIGHT, padx=(0, 8))
        dialog.bind("<Escape>", lambda _event: dialog.destroy())
        self.center_dialog(dialog)

    def get_detected_ap_groups(self):
        return build_detected_ap_groups(self.session.rows, self.channel_sort_key)

    def adjust_alias_table_columns(self, tree, columns):
        self.alias_table_resize_after_id = None

        if not tree.winfo_exists():
            return

        body_font = self.get_treeview_font("Treeview")
        heading_font = self.get_treeview_font("Treeview.Heading")
        min_widths = {
            "status": 38,
            "group": 220,
            "alias": 180,
            "bssids": 260,
            "ssids": 220,
            "channels": 92,
            "locked": 90,
        }
        max_widths = {
            "status": 46,
            "group": 420,
            "alias": 360,
            "bssids": 620,
            "ssids": 440,
            "channels": 140,
            "locked": 120,
        }
        measured = {}

        for column in columns:
            heading = tree.heading(column).get("text", "")
            measured[column] = max(min_widths[column], heading_font.measure(str(heading)) + 28)

        for item in tree.get_children():
            values = tree.item(item, "values")
            for column, value in zip(columns, values):
                measured[column] = max(measured[column], body_font.measure(str(value)) + 34)

        fixed_columns = ("status", "channels", "locked")
        flexible_columns = ("group", "alias", "bssids", "ssids")
        widths = {
            column: min(max(measured[column], min_widths[column]), max_widths[column])
            for column in columns
        }
        available_width = max(0, tree.winfo_width() - 8)
        fixed_total = sum(widths[column] for column in fixed_columns)
        flexible_min_total = sum(min_widths[column] for column in flexible_columns)
        flexible_available = max(flexible_min_total, available_width - fixed_total)
        desired_flexible_total = sum(widths[column] for column in flexible_columns)

        if desired_flexible_total > flexible_available:
            scale = flexible_available / desired_flexible_total
            for column in flexible_columns:
                widths[column] = max(min_widths[column], int(widths[column] * scale))
        elif desired_flexible_total < flexible_available:
            extra = flexible_available - desired_flexible_total
            priority = ("bssids", "ssids", "group", "alias")
            for column in priority:
                room = max_widths[column] - widths[column]
                added = min(room, extra)
                widths[column] += added
                extra -= added
                if extra <= 0:
                    break

        for column in columns:
            tree.column(
                column,
                width=widths[column],
                minwidth=min_widths[column],
                stretch=column in flexible_columns
            )

    def channel_sort_key(self, channel):
        try:
            return int(float(channel))
        except (TypeError, ValueError):
            return 9999

    def get_live_ap_filter_groups(self, config):
        rows = self.session.rows
        groups = {}

        for row in rows:
            if config.ssid and str(row.get("ssid", "")).lower() != config.ssid.lower():
                continue

            if config.band != "all":
                try:
                    channel = float(row.get("channel", ""))
                except (TypeError, ValueError):
                    continue
                if config.band == "2.4" and not (1 <= channel <= 14):
                    continue
                if config.band == "5" and channel < 36:
                    continue

            bssid = row.get("bssid", "")
            if not bssid:
                continue

            group_key = get_ap_group_key(bssid)
            groups.setdefault(group_key, bssid)

        return [
            (group_key, self.format_ap_label(bssid, group_key))
            for group_key, bssid in sorted(groups.items(), key=lambda item: self.format_ap_label(item[1], item[0]).lower())
        ]

    def get_live_map_type_options(self):
        return [
            ("signal", self.tr("map_type_signal")),
            ("interference", self.tr("map_type_interference")),
            ("channel", self.tr("map_type_channel")),
            ("dominant", self.tr("map_type_dominant")),
        ]

    def refresh_live_map_type_options(self):
        if not hasattr(self, "live_map_type_combo"):
            return

        options = self.get_live_map_type_options()
        self.live_map_type_label_map = {label: value for value, label in options}
        self.live_map_type_value_map = {value: label for value, label in options}
        self.live_map_type_combo["values"] = [label for _value, label in options]
        self.sync_live_map_type_choice()

    def sync_live_map_type_choice(self):
        if not hasattr(self, "live_map_type_choice_var"):
            return

        label = getattr(self, "live_map_type_value_map", {}).get(self.map_type_var.get())
        if label:
            self.live_map_type_choice_var.set(label)

    def on_live_map_type_selected(self, _event=None):
        selected_label = self.live_map_type_choice_var.get()
        selected_value = getattr(self, "live_map_type_label_map", {}).get(selected_label)

        if selected_value:
            self.map_type_var.set(selected_value)

        self.on_live_config_changed()

    def refresh_live_ap_filter_options(self, config=None):
        if not hasattr(self, "live_ap_filter_combo"):
            return

        config = config or self.get_current_map_config()
        groups = self.get_live_ap_filter_groups(config)
        all_label = self.tr("ap_filter_all")
        labels = [all_label] + [label for _group_key, label in groups]
        self.live_ap_filter_label_map = {all_label: ""}
        self.live_ap_filter_label_map.update({label: group_key for group_key, label in groups})
        current_group = config.ap_group_filter
        selected_label = all_label
        for group_key, label in groups:
            if group_key == current_group:
                selected_label = label
                break

        self.live_ap_filter_combo["values"] = labels
        self.ap_group_filter_var.set(selected_label)

    def open_help_dialog(self):
        dialog = self.create_modal_dialog(self.tr("help_title"))
        dialog.geometry("760x720")
        dialog.minsize(740, 660)

        frame = ttk.Frame(dialog, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)

        notebook = ttk.Notebook(frame)
        notebook.pack(fill=tk.BOTH, expand=True)

        sections = [
            ("help_commands", "help_commands_text"),
            ("help_workflow", "help_workflow_text"),
            ("help_live", "help_live_text"),
            ("help_heatmap", "help_heatmap_text"),
            ("help_scan", "help_scan_text"),
        ]

        for title_key, body_key in sections:
            tab = ttk.Frame(notebook, padding=12)
            notebook.add(tab, text=self.tr(title_key))

            if title_key == "help_commands":
                self.build_commands_help(tab)
                continue

            if title_key == "help_workflow":
                self.build_steps_help(tab, "help_workflow_title", "help_workflow_steps")
                continue

            if title_key == "help_heatmap":
                self.build_steps_help(tab, "help_heatmap_title", "help_heatmap_steps")
                continue

            if title_key == "help_live":
                self.build_steps_help(tab, "help_live_title", "help_live_steps")
                continue

            if title_key == "help_scan":
                self.build_steps_help(tab, "help_scan_title", "help_scan_steps")
                continue

            self.add_help_text(tab, self.tr(body_key))

        dialog.bind("<Escape>", lambda _event: dialog.destroy())
        self.center_dialog(dialog)

    def build_commands_help(self, parent):
        actions = [
            (("right",), "mouse_right_action"),
            (("left",), "mouse_left_action"),
            (("left_select",), "mouse_marker_action"),
            (("ctrl", "wheel"), "mouse_ctrl_scroll_action"),
            (("wheel",), "mouse_wheel_action"),
            (("shift", "wheel"), "mouse_shift_scroll_action"),
        ]

        grid = ttk.Frame(parent)
        grid.pack(expand=True)

        for index, (icon_types, label_key) in enumerate(actions):
            row = index // 2
            column = index % 2
            item = ttk.Frame(grid, padding=(8, 6))
            item.grid(row=row, column=column, sticky="w", padx=12, pady=8)
            create_shortcut_icon(item, icon_types, size=(34, 34)).pack(side=tk.LEFT)
            ttk.Label(item, text=self.tr(label_key), font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(10, 0))

    def build_steps_help(self, parent, title_key, steps_key):
        container = ttk.Frame(parent, padding=(8, 4))
        container.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            container,
            text=self.tr(title_key),
            font=("Segoe UI", 13, "bold"),
            bootstyle=PRIMARY
        ).pack(anchor="w", pady=(0, 16))

        for step in self.tr(steps_key).splitlines():
            row = ttk.Frame(container)
            row.pack(fill=tk.X, anchor="w", pady=(0, 10))
            ttk.Label(row, text="•", bootstyle=PRIMARY, font=("Segoe UI", 11, "bold")).pack(side=tk.LEFT, anchor="n")
            ttk.Label(
                row,
                text=step,
                font=("Segoe UI", 10),
                wraplength=610,
                justify=tk.LEFT
            ).pack(side=tk.LEFT, anchor="w", padx=(8, 0), fill=tk.X, expand=True)

    def add_help_text(self, parent, body):
        text = tk.Text(
            parent,
            wrap=tk.WORD,
            height=12,
            relief=tk.FLAT,
            background=self.root.cget("background"),
            font=("Segoe UI", 10)
        )
        text.insert("1.0", body)
        text.configure(state=tk.DISABLED)
        text.pack(fill=tk.BOTH, expand=True)

    def build_points_table(self, parent):
        self.points_table_group = ttk.LabelFrame(parent)
        self.points_table_group.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        table_frame = ttk.Frame(self.points_table_group, padding=6)
        table_frame.pack(fill=tk.X)

        columns = ("index", "x", "y", "best", "quality", "ssid", "rows")
        self.points_table_columns = columns
        self.points_table = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            height=5,
            selectmode="browse"
        )

        headings = {
            "index": "#",
            "x": "X",
            "y": "Y",
            "best": self.tr("best_dbm"),
            "quality": self.tr("quality"),
            "ssid": "SSID",
            "rows": self.tr("rows")
        }
        widths = {
            "index": 45,
            "x": 70,
            "y": 70,
            "best": 80,
            "quality": 92,
            "ssid": 260,
            "rows": 60
        }

        for column in columns:
            self.points_table.heading(column, text=headings[column])
            anchor = "w" if column == "ssid" else "center"
            self.points_table.column(
                column,
                width=widths[column],
                minwidth=widths[column],
                anchor=anchor,
                stretch=(column == "ssid")
            )

        self.points_table.tag_configure("odd", background="#f7f9fb")
        self.points_table.tag_configure("even", background="#ffffff")

        table_scroll = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.points_table.yview)
        self.points_table.configure(yscrollcommand=table_scroll.set)
        self.points_table.grid(row=0, column=0, sticky="ew")
        table_scroll.grid(row=0, column=1, sticky="ns")

        buttons = ttk.Frame(table_frame)
        buttons.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        self.focus_point_button = ttk.Button(buttons, command=self.focus_selected_point, bootstyle=SECONDARY)
        self.focus_point_button.pack(side=tk.LEFT)
        self.delete_selected_button = ttk.Button(buttons, command=self.delete_selected_point, bootstyle=DANGER)
        self.delete_selected_button.pack(side=tk.LEFT, padx=(6, 0))
        self.delete_last_button = ttk.Button(buttons, command=self.delete_last_point, bootstyle=DANGER)
        self.delete_last_button.pack(side=tk.LEFT, padx=(6, 0))

        table_frame.grid_columnconfigure(0, weight=1)
        self.points_table.bind("<<TreeviewSelect>>", self.on_point_table_select)
        self.points_table.bind("<Double-1>", lambda _event: self.focus_selected_point())
        self.points_table.bind("<Motion>", self.on_points_table_motion)
        self.points_table.bind("<Leave>", lambda _event: self.hide_point_tooltip())
        table_frame.bind("<Configure>", self.schedule_points_table_resize)
        self.points_table.bind("<Configure>", self.schedule_points_table_resize, add="+")

    def get_treeview_font(self, style_name):
        font_name = ttk.Style().lookup(style_name, "font")
        if font_name:
            try:
                return tkfont.nametofont(font_name)
            except tk.TclError:
                return tkfont.Font(font=font_name)

        return tkfont.nametofont("TkDefaultFont")

    def schedule_points_table_resize(self, _event=None):
        if not hasattr(self, "points_table"):
            return

        if self.points_table_resize_after_id is not None:
            self.root.after_cancel(self.points_table_resize_after_id)

        self.points_table_resize_after_id = self.root.after(50, self.adjust_points_table_columns)

    def adjust_points_table_columns(self):
        self.points_table_resize_after_id = None

        if not hasattr(self, "points_table") or not self.points_table.winfo_exists():
            return

        body_font = self.get_treeview_font("Treeview")
        heading_font = self.get_treeview_font("Treeview.Heading")
        min_widths = {
            "index": 48,
            "x": 60,
            "y": 60,
            "best": 96,
            "quality": 90,
            "ssid": 180,
            "rows": 58
        }
        max_fixed_widths = {
            "index": 64,
            "x": 84,
            "y": 84,
            "best": 122,
            "quality": 124,
            "rows": 76
        }
        columns = getattr(self, "points_table_columns", ("index", "x", "y", "best", "quality", "ssid", "rows"))
        measured = {}

        for column in columns:
            heading = self.points_table.heading(column).get("text", "")
            measured[column] = max(min_widths[column], heading_font.measure(str(heading)) + 26)

        for item in self.points_table.get_children():
            values = self.points_table.item(item, "values")
            for column, value in zip(columns, values):
                padding = 36 if column == "ssid" else 24
                measured[column] = max(measured[column], body_font.measure(str(value)) + padding)

        fixed_widths = {
            column: min(measured[column], max_fixed_widths[column])
            for column in columns
            if column != "ssid"
        }
        available_width = max(0, self.points_table.winfo_width() - 8)
        fixed_total = sum(fixed_widths.values())
        ssid_width = max(min_widths["ssid"], available_width - fixed_total)
        ssid_width = max(ssid_width, min(measured["ssid"], available_width - fixed_total))

        for column in columns:
            if column == "ssid":
                self.points_table.column(column, width=max(min_widths["ssid"], ssid_width), minwidth=120, stretch=True)
            else:
                self.points_table.column(column, width=fixed_widths[column], minwidth=min_widths[column], stretch=False)

    def load_plan(self):
        file_path = filedialog.askopenfilename(
            title=self.tr("select_plan_title"),
            filetypes=[
                (self.tr("pdf_or_images"), "*.pdf *.png *.jpg *.jpeg"),
                ("PDF", "*.pdf"),
                (self.tr("images"), "*.png *.jpg *.jpeg")
            ]
        )

        if not file_path:
            return

        self.load_plan_file(file_path, save_metadata=True)

    def load_plan_file(self, file_path, save_metadata=False):
        self.image_path = file_path

        if file_path.lower().endswith(".pdf"):
            doc = fitz.open(file_path)
            page = doc[0]
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        else:
            img = Image.open(file_path).convert("RGB")

        self.bg_image = img
        self.map_var.set(os.path.basename(file_path))
        self.zoom_level = 1.0

        self.canvas.delete("all")
        self.point_markers.clear()
        self.refresh_points_state()
        self.render_canvas()

        if save_metadata:
            self.session.update_metadata({"map_file": os.path.abspath(file_path)})
            self.refresh_session_labels()

        loaded_points = self.draw_existing_points()
        self.refresh_ssid_options()
        self.schedule_live_update()

        if loaded_points:
            self.status_var.set(
                self.tr("map_loaded_points", count=loaded_points, name=self.session_display_name())
            )
        else:
            self.status_var.set(
                self.tr("map_loaded", name=self.session_display_name())
            )

    def load_saved_plan(self):
        metadata = self.session.metadata
        map_file = metadata.get("map_file")

        if not map_file:
            return

        if os.path.exists(map_file):
            self.load_plan_file(map_file)
            return

        messagebox.showwarning(
            self.tr("map_not_found_title"),
            self.tr("map_not_found", path=map_file)
        )

    def start_map_drag(self, event):
        if self.handle_scale_calibration_click(event):
            return "break"

        if not self.is_point_marker_at(event.x, event.y):
            self.clear_point_selection()

        self.canvas.scan_mark(event.x, event.y)
        self.canvas.config(cursor="fleur")

    def is_point_marker_at(self, x, y):
        nearby_items = self.canvas.find_overlapping(x - 2, y - 2, x + 2, y + 2)
        return any("point_marker" in self.canvas.gettags(item) for item in nearby_items)

    def drag_map(self, event):
        if self.scale_calibration_points:
            return "break"

        self.canvas.scan_dragto(event.x, event.y, gain=1)

    def end_map_drag(self, _event):
        if self.scale_calibration_points:
            return "break"

        self.canvas.config(cursor="")

    def start_scale_calibration(self):
        if self.bg_image is None:
            messagebox.showwarning(self.tr("warning"), self.tr("load_plan_first"), parent=self.root)
            return

        self.clear_scale_calibration_overlay()
        self.scale_calibration_points = []
        self.canvas.config(cursor="crosshair")
        self.status_var.set(self.tr("calibrate_scale_start"))

    def handle_scale_calibration_click(self, event):
        if self.canvas.cget("cursor") != "crosshair" and not self.scale_calibration_points:
            return False

        x = self.canvas.canvasx(event.x) / self.zoom_level
        y = self.canvas.canvasy(event.y) / self.zoom_level
        self.scale_calibration_points.append((x, y))
        sx = x * self.zoom_level
        sy = y * self.zoom_level
        marker = self.canvas.create_oval(sx - 5, sy - 5, sx + 5, sy + 5, fill="#0d6efd", outline="white", width=2)
        self.scale_calibration_items.append(marker)

        if len(self.scale_calibration_points) == 1:
            self.status_var.set(self.tr("calibrate_scale_second_point"))
            return True

        first_x, first_y = self.scale_calibration_points[0]
        line = self.canvas.create_line(
            first_x * self.zoom_level,
            first_y * self.zoom_level,
            sx,
            sy,
            fill="#0d6efd",
            width=3
        )
        self.scale_calibration_items.append(line)
        pixel_distance = ((x - first_x) ** 2 + (y - first_y) ** 2) ** 0.5
        meters = simpledialog.askfloat(
            self.tr("calibrate_scale_title"),
            self.tr("calibrate_scale_distance_prompt"),
            minvalue=0.01,
            parent=self.root
        )

        self.canvas.config(cursor="")
        if not meters:
            self.clear_scale_calibration_overlay()
            self.status_var.set(self.tr("calibrate_scale_invalid"))
            return True

        try:
            current_max_distance_px = self.distance_px_from_display(self.distance_var.get())
        except (tk.TclError, ValueError):
            current_max_distance_px = HEATMAP_MAX_DISTANCE_PX

        px_per_meter = pixel_distance / meters
        self.session.update_metadata({"px_per_meter": f"{px_per_meter:.6f}"})
        self.distance_var.set(self.distance_display_from_px(current_max_distance_px))
        self.update_distance_labels()
        self.refresh_session_labels()
        self.schedule_live_update(force=True)
        self.clear_scale_calibration_overlay()
        self.status_var.set(self.tr("calibrate_scale_saved", px_per_meter=px_per_meter))
        return True

    def clear_scale_calibration_overlay(self):
        for item in self.scale_calibration_items:
            self.canvas.delete(item)
        self.scale_calibration_items = []
        self.scale_calibration_points = []

    def create_point_from_event(self, event):
        if self.bg_image is None:
            messagebox.showwarning(self.tr("warning"), self.tr("load_plan_first"))
            return

        x = int(self.canvas.canvasx(event.x) / self.zoom_level)
        y = int(self.canvas.canvasy(event.y) / self.zoom_level)
        self.create_survey_point(x, y)

    def create_survey_point(self, x, y):
        while True:
            self.set_busy(True, self.tr("scanning", x=x, y=y))
            try:
                networks = self.scan_wifi_with_quality_check(x, y)
            finally:
                self.set_busy(False)

            action = self.validate_relevant_networks(networks)
            if action == "retry":
                continue
            if action == "cancel":
                networks = None
            break

        if networks is None:
            self.update_last_scan_panel([], [], x, y, "annullato")
            return

        if not networks:
            messagebox.showerror(self.tr("error"), self.tr("no_networks_found"))
            self.update_last_scan_panel([], [], x, y, "")
            return

        self.remember_good_scan(networks)
        scanned_networks = networks
        timestamp = self.session.add_points(
            x,
            y,
            networks,
            raw_networks=scanned_networks,
            relevant_ssids=self.relevant_ssids
        )

        best_signal = max(net["signal_dbm"] for net in networks)
        marker_id = self.create_point_marker(x, y, best_signal)
        self.point_markers.append({
            "item_id": marker_id,
            "timestamp": timestamp,
            "x": x,
            "y": y,
            "signal_dbm": best_signal
        })
        self.refresh_points_state()
        self.refresh_ssid_options()
        self.update_last_scan_panel(scanned_networks, networks, x, y, self.format_relevant_networks_label())
        self.refresh_session_labels()
        self.schedule_live_update()
        self.status_var.set(self.tr("point_saved", x=x, y=y, count=len(networks)))

    def validate_relevant_networks(self, networks):
        if networks is None:
            return "cancel"

        detected_ssids = self.get_detected_ssids(networks)
        if not detected_ssids:
            return "keep"

        if not self.relevant_ssids:
            selected = self.ask_relevant_networks(
                detected_ssids,
                title=self.tr("relevant_networks_title"),
                message=self.tr("relevant_networks_first_message"),
                default_connected=True
            )
            if selected is None:
                return "cancel"
            self.set_relevant_ssids(selected)
            self.known_ssids |= detected_ssids
            self.save_known_ssids()
            return "keep"

        missing_ssids = sorted(self.relevant_ssids - detected_ssids)
        if missing_ssids:
            return self.ask_missing_relevant_networks_action(missing_ssids)

        new_ssids = sorted(detected_ssids - self.known_ssids)
        if new_ssids:
            selected = self.ask_relevant_networks(
                new_ssids,
                title=self.tr("new_relevant_networks_title"),
                message=self.tr("new_relevant_networks_message"),
                default_connected=False
            )
            if selected is None:
                return "cancel"
            if selected:
                self.set_relevant_ssids(self.relevant_ssids | selected)
            self.known_ssids |= detected_ssids
            self.save_known_ssids()

        return "keep"

    def get_detected_ssids(self, networks):
        return {
            str(network.get("ssid", "")).strip()
            for network in networks
            if str(network.get("ssid", "")).strip()
        }

    def set_relevant_ssids(self, ssids):
        self.relevant_ssids = {
            str(ssid).strip()
            for ssid in ssids
            if str(ssid).strip()
        }
        serialized = json.dumps(sorted(self.relevant_ssids), ensure_ascii=False)
        self.session.update_metadata({RELEVANT_SSIDS_METADATA_KEY: serialized})
        self.known_ssids |= self.relevant_ssids
        self.update_saved_network_label()
        self.refresh_session_labels()

    def clear_relevant_ssids(self):
        changed = False
        if RELEVANT_SSIDS_METADATA_KEY in self.session.metadata:
            self.session.metadata.pop(RELEVANT_SSIDS_METADATA_KEY, None)
            changed = True
        if KNOWN_SSIDS_METADATA_KEY in self.session.metadata:
            self.session.metadata.pop(KNOWN_SSIDS_METADATA_KEY, None)
            changed = True
        self.relevant_ssids = set()
        self.known_ssids = set()
        if not changed:
            self.update_saved_network_label()
            return

        self.session.dirty = True
        self.update_saved_network_label()
        self.refresh_session_labels()

    def forget_saved_network(self):
        self.clear_relevant_ssids()

    def format_relevant_networks_label(self):
        if not self.relevant_ssids:
            return self.tr("relevant_networks_none")
        return ", ".join(sorted(self.relevant_ssids))

    def ask_relevant_networks(self, ssids, title, message, default_connected=False):
        dialog = self.create_modal_dialog(title)
        result = {"value": None}

        frame = ttk.Frame(dialog, padding=18)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            frame,
            text=title,
            font=("TkDefaultFont", 12, "bold")
        ).pack(anchor="w")
        ttk.Label(
            frame,
            text=message,
            wraplength=520,
            justify=tk.LEFT
        ).pack(anchor="w", pady=(8, 12))

        connected_ssid = get_connected_ssid() if default_connected else None
        choices = {}
        for ssid in sorted(ssids, key=str.casefold):
            default_value = bool(connected_ssid and ssid.lower() == connected_ssid.lower())
            var = tk.BooleanVar(value=default_value)
            choices[ssid] = var
            label = ssid
            if default_value:
                label = self.tr("connected_ssid_option", ssid=ssid)
            ttk.Checkbutton(frame, text=label, variable=var).pack(anchor="w", pady=1)

        buttons = ttk.Frame(frame)
        buttons.pack(fill=tk.X, pady=(16, 0))

        def confirm():
            result["value"] = {
                ssid
                for ssid, var in choices.items()
                if var.get()
            }
            dialog.destroy()

        def cancel():
            result["value"] = None
            dialog.destroy()

        ttk.Button(buttons, text=self.tr("cancel"), command=cancel, bootstyle=SECONDARY).pack(side=tk.RIGHT)
        ttk.Button(buttons, text=self.tr("save"), command=confirm, bootstyle=PRIMARY).pack(side=tk.RIGHT, padx=(0, 8))
        dialog.bind("<Return>", lambda _event: confirm())
        dialog.bind("<Escape>", lambda _event: cancel())
        self.center_dialog(dialog)
        self.root.wait_window(dialog)
        return result["value"]

    def ask_missing_relevant_networks_action(self, missing_ssids):
        dialog = self.create_modal_dialog(self.tr("missing_relevant_networks_title"))
        result = {"action": "cancel"}

        frame = ttk.Frame(dialog, padding=18)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            frame,
            text=self.tr("missing_relevant_networks_title"),
            font=("TkDefaultFont", 12, "bold"),
            bootstyle=WARNING
        ).pack(anchor="w")
        ttk.Label(
            frame,
            text=self.tr("missing_relevant_networks_message", ssids=", ".join(missing_ssids)),
            wraplength=520,
            justify=tk.LEFT
        ).pack(anchor="w", pady=(10, 0))

        buttons = ttk.Frame(frame)
        buttons.pack(fill=tk.X, pady=(18, 0))

        def choose(action):
            result["action"] = action
            dialog.destroy()

        ttk.Button(
            buttons,
            text=self.tr("cancel_point"),
            command=lambda: choose("cancel"),
            bootstyle=DANGER
        ).pack(side=tk.RIGHT)
        ttk.Button(
            buttons,
            text=self.tr("retry_scan"),
            command=lambda: choose("retry"),
            bootstyle=WARNING
        ).pack(side=tk.RIGHT, padx=(0, 8))
        ttk.Button(
            buttons,
            text=self.tr("keep_scan"),
            command=lambda: choose("keep"),
            bootstyle=PRIMARY
        ).pack(side=tk.RIGHT, padx=(0, 8))

        dialog.bind("<Escape>", lambda _event: choose("cancel"))
        self.center_dialog(dialog)
        self.root.wait_window(dialog)
        return result["action"]

    def delete_last_point(self):
        if not self.point_markers:
            messagebox.showwarning(self.tr("warning"), self.tr("no_point_to_delete"))
            return

        marker = self.point_markers.pop()
        self.canvas.delete(marker["item_id"])
        self.clear_point_highlight()
        self.hide_point_tooltip()

        removed_rows = self.session.delete_point(marker["timestamp"], marker["x"], marker["y"])
        self.refresh_points_state()
        self.refresh_session_labels()
        self.status_var.set(
            self.tr("last_point_deleted", x=marker["x"], y=marker["y"], rows=removed_rows)
        )
        self.refresh_ssid_options()

    def delete_selected_point(self):
        selected_items = self.points_table.selection()

        if not selected_items:
            messagebox.showwarning(self.tr("warning"), self.tr("select_point"))
            return

        timestamp, x, y = selected_items[0].split("|")
        x = int(x)
        y = int(y)
        marker = self.find_marker(timestamp, x, y)

        if marker is not None:
            self.canvas.delete(marker["item_id"])
            self.point_markers.remove(marker)
            self.clear_point_highlight()
            self.hide_point_tooltip()

        removed_rows = self.session.delete_point(timestamp, x, y)
        self.refresh_points_state()
        self.refresh_ssid_options()
        self.refresh_session_labels()
        self.status_var.set(self.tr("point_deleted", x=x, y=y, rows=removed_rows))

    def find_marker(self, timestamp, x, y):
        for marker in self.point_markers:
            if marker["timestamp"] == timestamp and marker["x"] == x and marker["y"] == y:
                return marker

        return None

    def set_busy(self, is_busy, message=None):
        self.root.config(cursor="watch" if is_busy else "")
        self.canvas.config(cursor="watch" if is_busy else "")

        if message:
            self.status_var.set(message)

        self.root.update_idletasks()

    def update_last_scan_panel(self, scanned_networks, saved_networks, x, y, ssid_filter):
        saved_ssids = sorted({net["ssid"] for net in saved_networks if net.get("ssid")})
        filter_label = ssid_filter if ssid_filter else self.tr("all_networks")

        self.last_scan_var.set(
            f"x={x}, y={y} | visti={len(scanned_networks)} | salvati={len(saved_networks)} | "
            f"SSID={len(saved_ssids)}"
        )
        self.scan_filter_var.set(f"{self.tr('saved_network')}: {filter_label}")
        self.scan_backend_used_var.set(self.tr("backend_used", backend=self.last_scan_backend_used))
        self.update_scan_quality(scanned_networks)

        if not saved_networks:
            self.best_scan_var.set(f"{self.tr('best')}: -")
            return

        best_network = max(saved_networks, key=lambda net: net["signal_dbm"])
        width = best_network.get("channel_width_mhz", "")
        width_label = f" / {width} MHz" if width else ""
        confidence_label = self.format_scan_confidence(best_network)
        self.best_scan_var.set(
            f"{self.tr('best')}: {best_network['ssid']} {best_network['signal_dbm']} dBm "
            f"CH {best_network.get('channel', '-')}{width_label}{confidence_label}"
        )

    def format_scan_confidence(self, network):
        samples_seen = network.get("samples_seen", "")
        samples_total = network.get("samples_total", "")

        if samples_seen in ("", None) or samples_total in ("", None):
            return ""

        return f" | {self.tr('confidence')}: {samples_seen}/{samples_total}"

    def update_scan_quality(self, scanned_networks):
        scanned_count = len(scanned_networks)
        if scanned_count == 0:
            self.scan_quality_var.set(self.tr("scan_quality_no_data"))
            self.scan_quality_label.configure(bootstyle=DANGER)
            return

        detected_ssids = self.get_detected_ssids(scanned_networks)
        missing_relevant = sorted(self.relevant_ssids - detected_ssids)
        if missing_relevant:
            self.scan_quality_var.set(
                self.tr("scan_quality_missing_relevant", ssids=", ".join(missing_relevant))
            )
            self.scan_quality_label.configure(bootstyle=DANGER)
            return

        self.scan_quality_var.set(self.tr("scan_quality_good"))
        self.scan_quality_label.configure(bootstyle=SUCCESS)

    def scan_wifi_with_quality_check(self, x, y):
        networks, backend_used = scan_wifi(self.scan_backend_var.get())
        self.last_scan_backend_used = backend_used

        return networks

    def ask_suspicious_scan_action(self, networks):
        dialog = self.create_modal_dialog(self.tr("suspicious_scan_title"))
        result = {"action": "cancel"}

        frame = ttk.Frame(dialog, padding=18)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            frame,
            text=self.tr("suspicious_scan_title"),
            font=("TkDefaultFont", 12, "bold"),
            bootstyle=WARNING
        ).pack(anchor="w")
        ttk.Label(
            frame,
            text=self.tr(
                "suspicious_scan_message",
                current=len(networks),
                previous=len(self.last_good_scan)
            ),
            wraplength=460,
            justify=tk.LEFT
        ).pack(anchor="w", pady=(10, 0))

        buttons = ttk.Frame(frame)
        buttons.pack(fill=tk.X, pady=(18, 0))

        def choose(action):
            result["action"] = action
            dialog.destroy()

        ttk.Button(
            buttons,
            text=self.tr("cancel_point"),
            command=lambda: choose("cancel"),
            bootstyle=DANGER
        ).pack(side=tk.RIGHT)
        ttk.Button(
            buttons,
            text=self.tr("retry_scan"),
            command=lambda: choose("retry"),
            bootstyle=WARNING
        ).pack(side=tk.RIGHT, padx=(0, 8))
        ttk.Button(
            buttons,
            text=self.tr("keep_scan"),
            command=lambda: choose("keep"),
            bootstyle=PRIMARY
        ).pack(side=tk.RIGHT, padx=(0, 8))

        dialog.bind("<Escape>", lambda _event: choose("cancel"))
        self.center_dialog(dialog)
        self.root.wait_window(dialog)
        return result["action"]

    def is_suspicious_scan(self, networks):
        if len(self.last_good_scan) < MIN_GOOD_SCAN_NETWORKS:
            return False

        if len(networks) <= 1:
            return True

        return len(networks) < len(self.last_good_scan) * SUSPICIOUS_SCAN_RATIO

    def remember_good_scan(self, networks):
        if len(networks) >= MIN_GOOD_SCAN_NETWORKS:
            self.last_good_scan = networks

    def draw_existing_points(self):
        seen_points = set()

        for point in self.session.get_points():
            timestamp = point["timestamp"]
            x = point["x"]
            y = point["y"]
            point_key = (timestamp, x, y)
            if point_key in seen_points:
                continue

            seen_points.add(point_key)
            signal_dbm = point["signal_dbm"]
            marker_id = self.create_point_marker(x, y, signal_dbm)
            self.point_markers.append({
                "item_id": marker_id,
                "timestamp": timestamp,
                "x": x,
                "y": y,
                "signal_dbm": signal_dbm
            })

        self.refresh_points_state()

        return len(self.point_markers)

    def refresh_points_state(self):
        self.points_var.set(str(len(self.point_markers)))

        if self.point_markers:
            last_point = self.point_markers[-1]
            self.last_point_var.set(f"x={last_point['x']}, y={last_point['y']}")
        else:
            self.last_point_var.set("-")

        self.update_footer_info()
        self.refresh_points_table()

    def refresh_points_table(self):
        if not hasattr(self, "points_table"):
            return

        self.point_quality_by_item = {}
        for item in self.points_table.get_children():
            self.points_table.delete(item)

        point_summaries = self.session.get_point_summaries()
        quality_by_point_id = evaluate_point_quality(
            self.session.rows,
            self.session.raw_scan_rows,
            relevant_ssids=self.relevant_ssids
        )
        total_points = len(point_summaries)

        for index, point in enumerate(reversed(point_summaries), start=1):
            survey_number = total_points - index + 1
            item_id = format_point_id(point["timestamp"], point["x"], point["y"])
            quality = quality_by_point_id.get(point.get("point_id", ""), {})
            self.point_quality_by_item[item_id] = quality
            row_tag = "even" if index % 2 == 0 else "odd"
            self.points_table.insert(
                "",
                tk.END,
                iid=item_id,
                values=(
                    survey_number,
                    point["x"],
                    point["y"],
                    f"{point['best_signal_dbm']:.1f}",
                    self.format_point_quality(quality.get("status")),
                    ", ".join(point["ssids"]),
                    point["row_count"]
                ),
                tags=(row_tag,)
            )

        self.schedule_points_table_resize()

    def on_points_table_motion(self, event):
        region = self.points_table.identify_region(event.x, event.y)
        column_id = self.points_table.identify_column(event.x)
        item_id = self.points_table.identify_row(event.y)

        if region != "cell" or column_id != "#5" or not item_id:
            self.hide_point_tooltip()
            return

        quality = self.point_quality_by_item.get(item_id)
        if not quality or not self.should_show_quality_tooltip(quality):
            self.hide_point_tooltip()
            return

        if getattr(self, "point_quality_tooltip_item", None) == item_id:
            return

        self.hide_point_tooltip()
        self.point_quality_tooltip_item = item_id
        self.tooltip_window = tk.Toplevel(self.root)
        self.tooltip_window.wm_overrideredirect(True)
        self.build_structured_tooltip(self.tooltip_window, self.build_quality_tooltip(quality))
        self.position_tooltip_window(self.tooltip_window, event)

    def should_show_quality_tooltip(self, quality):
        breakdown = quality.get("breakdown", [])
        if len(breakdown) > 1:
            return True

        if not breakdown:
            return False

        item = breakdown[0]
        return item.get("status") in {QUALITY_LOW_CONFIDENCE, QUALITY_UNSTABLE_SIGNAL}

    def build_quality_tooltip(self, quality):
        rows = [(self.tr("quality"), self.format_point_quality(quality.get("status")))]
        for item in quality.get("breakdown", []):
            rows.append((item.get("ssid", "-"), self.format_quality_breakdown_item(item)))

        return {
            "title": self.tr("quality_breakdown_title"),
            "accent": "#34495e",
            "rows": rows
        }

    def format_quality_breakdown_item(self, item):
        status = item.get("status")
        if status == QUALITY_GOOD:
            return self.tr("quality_good")
        if status == QUALITY_MISSING_RELEVANT:
            return self.tr("quality_missing_relevant")
        if status == QUALITY_LOW_CONFIDENCE:
            confidence = item.get("min_confidence")
            suffix = f" ({confidence:.2f})" if isinstance(confidence, float) else ""
            return f"{self.tr('quality_low_confidence')}{suffix}"
        if status == QUALITY_UNSTABLE_SIGNAL:
            range_db = item.get("range_db")
            suffix = f" ({range_db:.1f} dB)" if isinstance(range_db, float) else ""
            return f"{self.tr('quality_unstable_signal')}{suffix}"
        return self.format_point_quality(status)

    def format_point_quality(self, status):
        return {
            QUALITY_GOOD: self.tr("quality_good"),
            QUALITY_MISSING_RELEVANT: self.tr("quality_missing_relevant"),
            QUALITY_LOW_CONFIDENCE: self.tr("quality_low_confidence"),
            QUALITY_UNSTABLE_SIGNAL: self.tr("quality_unstable_signal"),
            QUALITY_SPARSE_DATA: self.tr("quality_sparse_data"),
        }.get(status, "-")

    def focus_selected_point(self):
        selected_items = self.points_table.selection()

        if not selected_items:
            messagebox.showwarning(self.tr("warning"), self.tr("select_point"))
            return

        timestamp, x, y = selected_items[0].split("|")
        self.focus_point(int(x), int(y))

    def on_point_table_select(self, _event):
        selected_items = self.points_table.selection()

        if not selected_items:
            return

        timestamp, x, y = selected_items[0].split("|")
        x = int(x)
        y = int(y)
        marker = self.find_marker(timestamp, x, y)

        if marker is not None:
            self.last_point_var.set(f"x={marker['x']}, y={marker['y']}")
            self.highlight_point(timestamp, x, y)

    def focus_point(self, x, y):
        if self.bg_image is None:
            return

        self.canvas.update_idletasks()
        scrollregion = self.canvas.bbox("all")

        if not scrollregion:
            return

        total_width = max(1, scrollregion[2] - scrollregion[0])
        total_height = max(1, scrollregion[3] - scrollregion[1])
        target_x = x * self.zoom_level - (self.canvas.winfo_width() / 2)
        target_y = y * self.zoom_level - (self.canvas.winfo_height() / 2)

        self.canvas.xview_moveto(max(0, min(1, target_x / total_width)))
        self.canvas.yview_moveto(max(0, min(1, target_y / total_height)))

    def select_point_from_marker(self, x, y):
        for marker in self.point_markers:
            if marker["x"] == x and marker["y"] == y:
                item_id = format_point_id(marker["timestamp"], marker["x"], marker["y"])

                if self.points_table.exists(item_id):
                    self.points_table.selection_set(item_id)
                    self.points_table.focus(item_id)
                    self.points_table.see(item_id)

                self.highlight_point(marker["timestamp"], marker["x"], marker["y"])
                return "break"

        return "break"

    def highlight_point(self, timestamp, x, y):
        self.selected_point_id = format_point_id(timestamp, x, y)
        self.redraw_point_highlight()

    def clear_point_selection(self):
        self.selected_point_id = None
        self.clear_point_highlight()
        if hasattr(self, "points_table"):
            self.points_table.selection_remove(self.points_table.selection())

    def redraw_point_highlight(self):
        self.clear_point_highlight()

        if not self.selected_point_id:
            return

        try:
            _timestamp, x, y = self.selected_point_id.split("|")
            x = int(x)
            y = int(y)
        except ValueError:
            return

        sx = x * self.zoom_level
        sy = y * self.zoom_level
        radius = max(8, int(11 * self.zoom_level))
        self.highlight_item_id = self.canvas.create_oval(
            sx - radius,
            sy - radius,
            sx + radius,
            sy + radius,
            outline="#111111",
            width=3
        )
        self.canvas.tag_raise(self.highlight_item_id)

    def clear_point_highlight(self):
        if self.highlight_item_id is not None:
            self.canvas.delete(self.highlight_item_id)
            self.highlight_item_id = None

    def show_point_tooltip(self, event, x, y):
        point = self.session.find_point_summary(x, y)

        if point is None:
            return

        self.hide_point_tooltip()
        self.tooltip_window = tk.Toplevel(self.root)
        self.tooltip_window.wm_overrideredirect(True)

        self.build_structured_tooltip(
            self.tooltip_window,
            {
                "title": self.tr("detected_points"),
                "accent": signal_to_color(point["best_signal_dbm"]),
                "rows": [
                    ("x/y", f"{point['x']}, {point['y']}"),
                    (self.tr("best"), f"{point['best_signal_dbm']:.1f} dBm"),
                    ("SSID", ", ".join(point["ssids"])),
                    (self.tr("rows"), point["row_count"]),
                    ("Timestamp", point["timestamp"]),
                ]
            }
        )
        self.position_tooltip_window(self.tooltip_window, event)

    def hide_point_tooltip(self):
        if self.tooltip_window is not None:
            self.tooltip_window.destroy()
            self.tooltip_window = None
        self.point_quality_tooltip_item = None

    def create_point_marker(self, x, y, signal_dbm):
        sx = x * self.zoom_level
        sy = y * self.zoom_level
        radius = max(4, int(6 * self.zoom_level))
        item_id = self.canvas.create_oval(
            sx - radius,
            sy - radius,
            sx + radius,
            sy + radius,
            fill=signal_to_color(signal_dbm),
            outline="white",
            width=2,
            tags=("point_marker",)
        )
        self.canvas.tag_bind(item_id, "<Enter>", lambda event, px=x, py=y: self.show_point_tooltip(event, px, py))
        self.canvas.tag_bind(item_id, "<Leave>", lambda _event: self.hide_point_tooltip())
        self.canvas.tag_bind(item_id, "<Button-1>", lambda _event, px=x, py=y: self.select_point_from_marker(px, py))
        return item_id

    def render_canvas(self):
        if self.bg_image is None:
            return

        width = max(1, int(self.bg_image.width * self.zoom_level))
        height = max(1, int(self.bg_image.height * self.zoom_level))
        resized_image = self.bg_image.resize((width, height), Image.Resampling.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(resized_image)

        self.canvas.delete("all")
        self.canvas_image = self.canvas.create_image(0, 0, anchor="nw", image=self.tk_image)
        self.canvas.config(scrollregion=(0, 0, width, height))
        self.redraw_point_markers()
        self.redraw_point_highlight()

    def redraw_point_markers(self):
        for marker in self.point_markers:
            marker["item_id"] = self.create_point_marker(
                marker["x"],
                marker["y"],
                marker.get("signal_dbm")
            )

    def on_live_config_changed(self):
        config = self.get_current_map_config()
        self.apply_map_config_to_controls(config)
        self.refresh_live_ap_filter_options(config)
        self.update_live_option_states(config)
        self.schedule_live_update(force=True)

    def update_live_option_states(self, config):
        if not hasattr(self, "live_interference_mode_combo"):
            return

        is_signal = config.is_signal
        is_interference = config.is_interference
        continuous_state = tk.NORMAL if config.is_continuous else tk.DISABLED
        signal_state = tk.NORMAL if is_signal else tk.DISABLED
        interference_state = "readonly" if is_interference else tk.DISABLED
        interpolation_state = "readonly" if config.is_continuous else tk.DISABLED
        aggregation_state = "readonly" if is_signal else tk.DISABLED
        ap_filter_state = "readonly" if (config.is_signal or config.is_channel) else tk.DISABLED

        if ap_filter_state == tk.DISABLED:
            self.ap_group_filter_var.set(self.tr("ap_filter_all"))
        self.live_ap_filter_combo.configure(state=ap_filter_state)
        self.live_interference_mode_combo.configure(state=interference_state)
        self.live_smoothing_spinbox.configure(state=continuous_state)
        self.live_distance_spinbox.configure(state=continuous_state)
        self.live_usable_check.configure(state=signal_state)
        self.live_color_scale_combo.configure(state="readonly" if is_signal else tk.DISABLED)
        self.live_interpolation_combo.configure(state=interpolation_state)
        self.live_aggregation_combo.configure(state=aggregation_state)

    def is_live_tab_visible(self):
        if not hasattr(self, "main_notebook"):
            return False

        try:
            return self.main_notebook.index(self.main_notebook.select()) == 1
        except tk.TclError:
            return False

    def on_main_tab_changed(self, _event=None):
        if self.is_live_tab_visible() and self.live_preview_dirty:
            self.schedule_live_update(force=True)

    def schedule_live_update(self, force=False):
        if not hasattr(self, "live_canvas"):
            return

        if not force and not self.live_auto_update_var.get():
            return

        if not self.is_live_tab_visible():
            self.live_preview_dirty = True
            return

        if self.live_update_after_id is not None:
            self.root.after_cancel(self.live_update_after_id)

        self.live_update_after_id = self.root.after(350, self.update_live_preview)

    def update_live_preview(self):
        self.live_update_after_id = None
        self.live_preview_dirty = False
        self.set_live_preview_busy(False)
        if self.live_quality_after_id is not None:
            self.root.after_cancel(self.live_quality_after_id)
            self.live_quality_after_id = None

        if self.bg_image is None:
            self.live_status_var.set(self.tr("load_plan_first"))
            return

        config = self.get_current_map_config()
        self.apply_map_config_to_controls(config)
        self.update_live_option_states(config)
        df = self.session.to_dataframe()

        if df.empty or not config.ssid:
            self.live_preview_image = self.bg_image.copy()
            self.live_point_infos = []
            self.live_scale_payload = None
            self.live_status_var.set(self.tr("live_preview_empty"))
            self.render_live_canvas_image()
            return

        self.refresh_live_ap_filter_options(config)
        missing_info = self.get_live_missing_data_info(df, config)
        missing_point_infos = self.get_live_missing_point_infos(df, config)

        if config.is_channel or config.is_dominant:
            if config.is_channel:
                has_points = self.build_live_channel_points(df, config)
            else:
                has_points = self.build_live_dominant_points(df, config)

            if not has_points:
                self.live_preview_image = self.bg_image.copy()
                self.live_point_infos = missing_point_infos
                self.live_scale_payload = None
                self.live_status_var.set(self.format_live_status(self.tr("live_preview_insufficient"), missing_info))
                self.render_live_canvas_image()
                return

            self.live_preview_image = self.bg_image.copy()
            self.live_point_infos.extend(missing_point_infos)
            self.render_live_canvas_image()
            self.live_status_var.set(self.format_live_status(self.tr("live_preview_updated"), missing_info))
            return

        if config.is_signal or config.is_interference:
            self.start_live_preview_worker(df, config, missing_info, missing_point_infos)
            return

        self.live_preview_image = self.bg_image.copy()
        self.live_point_infos = missing_point_infos
        self.live_scale_payload = None
        self.live_status_var.set(self.format_live_status(self.tr("live_preview_insufficient"), missing_info))
        self.render_live_canvas_image()

    def start_live_preview_worker(self, df, config, missing_info, missing_point_infos):
        self.live_preview_task_id += 1
        task_id = self.live_preview_task_id
        bg_image = self.bg_image.copy()
        df_copy = df.copy()

        future = self.live_preview_executor.submit(
            self.compute_live_preview_payload,
            df_copy,
            config,
            bg_image
        )
        future.add_done_callback(
            lambda completed_future: self.dispatch_live_preview_result(
                task_id,
                completed_future,
                missing_info,
                missing_point_infos
            )
        )
        self.set_live_preview_busy(True)
        self.live_status_var.set(self.tr("live_preview_rendering"))

    def set_live_preview_busy(self, busy):
        self.live_preview_busy = busy
        if hasattr(self, "live_update_button"):
            self.live_update_button.configure(state=tk.DISABLED if busy else tk.NORMAL)
        if hasattr(self, "live_status_label"):
            if busy:
                self.live_status_label.configure(bootstyle=INFO)
            else:
                self.live_status_label.configure(style="ReadableMuted.TLabel")

    def dispatch_live_preview_result(self, task_id, future, missing_info, missing_point_infos):
        try:
            self.root.after(
                0,
                self.finish_live_preview_worker,
                task_id,
                future,
                missing_info,
                missing_point_infos
            )
        except (RuntimeError, tk.TclError):
            return

    def finish_live_preview_worker(self, task_id, future, missing_info, missing_point_infos):
        if task_id != self.live_preview_task_id:
            return

        self.set_live_preview_busy(False)
        try:
            payload = future.result()
        except Exception as error:
            self.live_preview_image = self.bg_image.copy()
            self.live_point_infos = missing_point_infos
            self.live_scale_payload = None
            self.live_status_var.set(f"{self.tr('error')}: {error}")
            self.render_live_canvas_image()
            return

        if payload is None:
            self.live_preview_image = self.bg_image.copy()
            self.live_point_infos = missing_point_infos
            self.live_scale_payload = None
            self.live_status_var.set(self.format_live_status(self.tr("live_preview_insufficient"), missing_info))
            self.render_live_canvas_image()
            return

        self.live_preview_image = payload["image"]
        self.live_point_infos = payload["point_infos"] + missing_point_infos
        self.live_scale_payload = payload["scale_payload"]
        self.render_live_canvas_image()
        self.live_status_var.set(self.format_live_status(self.tr("live_preview_updated"), missing_info))

    def compute_live_preview_payload(self, df, config, bg_image):
        return render_live_continuous_map(
            df,
            config,
            bg_image,
            self.get_live_renderer_translations(),
            lambda map_type, row, raw_rows: self.build_live_renderer_tooltip(config, map_type, row, raw_rows),
            self.get_color_scale_limits,
        )

    def get_live_renderer_translations(self):
        return {
            "signal_title": self.tr("map_type_signal"),
            "interference_title": self.tr("map_type_interference"),
        }

    def build_live_renderer_tooltip(self, config, map_type, row, raw_rows):
        if map_type == "interference":
            return self.format_live_interference_tooltip(row, config)

        return self.format_live_signal_tooltip(row, config, raw_rows)

    def format_live_status(self, base_status, missing_info):
        parts = [base_status]

        if missing_info and missing_info["missing"] > 0:
            parts.append(
                self.tr(
                    "live_missing_band_points",
                    missing=missing_info["missing"],
                    total=missing_info["total"],
                    band=format_band_label(missing_info["band"], self.language)
                )
            )

        if self.live_point_infos:
            parts.append(self.format_live_legend_hint())

        return " | ".join(parts)

    def format_live_legend_hint(self):
        config = self.get_current_map_config()

        if config.is_interference:
            return self.tr("live_legend_interference")
        if config.is_channel:
            return self.tr("live_legend_channel")
        if config.is_dominant:
            return self.tr("live_legend_dominant")
        return self.tr("live_legend_signal")

    def get_live_missing_data_info(self, df, config):
        if config.band == "all" or not config.ssid:
            return None

        missing_points = self.get_live_missing_points(df, config)
        if missing_points is None:
            return None

        return {
            "missing": len(missing_points["missing"]),
            "total": len(missing_points["all_points"]),
            "band": config.band
        }

    def get_live_missing_point_infos(self, df, config):
        missing_points = self.get_live_missing_points(df, config)
        if missing_points is None:
            return []

        point_infos = []
        for _index, row in missing_points["missing"].iterrows():
            point_infos.append({
                "x": float(row["x"]),
                "y": float(row["y"]),
                "color": "",
                "outline": "#d62728",
                "shape": "cross",
                "tooltip": {
                    "title": self.tr("live_missing_data_title"),
                    "rows": [
                        ("SSID", config.ssid),
                        (self.tr("band"), format_band_label(config.band, self.language)),
                        ("x/y", f"{self.format_report_value(row.get('x', ''))}, {self.format_report_value(row.get('y', ''))}"),
                    ],
                    "accent": "#d62728"
                }
            })

        return point_infos

    def get_live_missing_points(self, df, config):
        if config.band == "all" or not config.ssid:
            return None

        rows = df.copy()
        rows["x"] = pd.to_numeric(rows["x"], errors="coerce")
        rows["y"] = pd.to_numeric(rows["y"], errors="coerce")
        rows = rows.dropna(subset=["timestamp", "x", "y"])

        if rows.empty:
            return None

        all_points = rows[["timestamp", "x", "y"]].drop_duplicates()
        selected = rows[rows["ssid"].str.lower() == config.ssid.lower()].copy()
        selected = filter_by_band(selected, config.band)
        covered = selected[["timestamp", "x", "y"]].drop_duplicates()
        covered_keys = set(tuple(row) for row in covered.to_numpy())
        missing_mask = [
            tuple(row) not in covered_keys
            for row in all_points.to_numpy()
        ]
        missing = all_points.loc[missing_mask]

        return {"missing": missing, "all_points": all_points}

    def build_live_channel_points(self, df, config):
        channel_df = get_channel_map_points(df, config.ssid, config.band)
        if channel_df.empty:
            return False

        legend_items = []
        self.live_point_infos = [
            {
                "x": float(row["x"]),
                "y": float(row["y"]),
                "color": get_channel_color(row["channel"], config.band),
                "outline": "black",
                "outline_width": 1,
                "legend_label": self.format_live_channel_legend_label(row),
                "legend_sort_key": get_channel_sort_key(row["channel"], config.band),
                "tooltip": self.format_live_channel_tooltip(row, config)
            }
            for _index, row in channel_df.iterrows()
            if not config.ap_group_filter or get_ap_group_key(row.get("bssid", "")) == config.ap_group_filter
        ]
        if not self.live_point_infos:
            return False
        for point in self.live_point_infos:
            label = point.get("legend_label", "")
            if label and label not in [item["label"] for item in legend_items]:
                legend_items.append({
                    "label": label,
                    "color": point.get("color", "#7f8c8d"),
                    "sort_key": point.get("legend_sort_key", (99, label.lower())) + (label.casefold(),)
                })
        legend_items.sort(key=lambda item: item.get("sort_key", (99, item.get("label", "").lower())))
        self.live_scale_payload = {
            "kind": "swatches",
            "title": self.tr("map_type_channel"),
            "items": legend_items,
        }
        return True

    def build_live_dominant_points(self, df, config):
        dominant_df = get_dominant_ap_points(df, config.ssid, config.band)
        if dominant_df.empty:
            return False

        color_map, _visible_ap_groups, _hidden_ap_count = get_limited_bssid_color_map(dominant_df)
        group_labels = self.build_dominant_ap_group_labels(dominant_df)
        legend_items = []
        self.live_point_infos = [
            {
                "x": float(row["x"]),
                "y": float(row["y"]),
                "color": color_map.get(row["dominant_ap_group"], "#7f8c8d"),
                "outline": "#f1c40f" if row.get("roaming_overlap") else "black",
                "outline_width": 1,
                "legend_label": group_labels.get(
                    row.get("dominant_ap_group", ""),
                    self.format_ap_label(row.get("dominant_bssid", ""), row.get("dominant_ap_group", ""))
                ),
                "tooltip": self.format_live_dominant_tooltip(row, config)
            }
            for _index, row in dominant_df.iterrows()
        ]
        for point in self.live_point_infos:
            label = point.get("legend_label", "")
            if label and label not in [item["label"] for item in legend_items]:
                legend_items.append({"label": label, "color": point.get("color", "#7f8c8d")})
        legend_items.sort(key=lambda item: item.get("label", "").casefold())
        if any(point.get("outline") == "#f1c40f" for point in self.live_point_infos):
            legend_items.append({"label": self.tr("dominant_map_roaming_overlap"), "color": "#f1c40f", "outline_only": True})
        self.live_scale_payload = {
            "kind": "swatches",
            "title": self.tr("map_type_dominant"),
            "items": legend_items,
        }
        return True

    def render_live_canvas_image(self, resample=None, update_scale=True):
        if self.live_preview_image is None or not hasattr(self, "live_canvas"):
            return

        canvas_width = max(1, self.live_canvas.winfo_width())
        canvas_height = max(1, self.live_canvas.winfo_height())
        image_width, image_height = self.live_preview_image.size
        fit_scale = min(canvas_width / image_width, canvas_height / image_height)
        scale = fit_scale * self.live_zoom_level
        width = max(1, int(image_width * scale))
        height = max(1, int(image_height * scale))
        offset_x = max(0, (canvas_width - width) // 2)
        offset_y = max(0, (canvas_height - height) // 2)
        if resample is None:
            resample = Image.Resampling.LANCZOS

        resized = self.live_preview_image.resize((width, height), resample)
        self.live_preview_tk_image = ImageTk.PhotoImage(resized)
        self.live_image_transform = {
            "offset_x": offset_x,
            "offset_y": offset_y,
            "scale": scale,
            "width": width,
            "height": height
        }
        self.live_canvas.delete("all")
        self.live_canvas.create_image(
            offset_x,
            offset_y,
            anchor="nw",
            image=self.live_preview_tk_image
        )
        self.live_canvas.config(scrollregion=(0, 0, max(canvas_width, width), max(canvas_height, height)))
        if self.live_zoom_level <= 1.0:
            self.live_canvas.xview_moveto(0)
            self.live_canvas.yview_moveto(0)
        self.draw_live_point_markers()
        self.draw_live_overlay_legend()
        if update_scale:
            self.update_live_scale_bar()

    def live_zoom_in(self):
        self.set_live_zoom(self.live_zoom_level * 1.25)

    def live_zoom_out(self):
        self.set_live_zoom(self.live_zoom_level / 1.25)

    def live_fit_to_window(self):
        self.set_live_zoom(1.0)

    def set_live_zoom(self, zoom_level):
        self.live_zoom_level = min(6.0, max(0.25, zoom_level))
        if self.live_quality_after_id is not None:
            self.root.after_cancel(self.live_quality_after_id)
            self.live_quality_after_id = None

        self.render_live_canvas_image(resample=Image.Resampling.BILINEAR, update_scale=False)
        self.live_quality_after_id = self.root.after(180, self.render_live_canvas_image_high_quality)
        self.live_status_var.set(f"{self.tr('live_zoom')}: {self.live_zoom_level:.0%}")

    def render_live_canvas_image_high_quality(self):
        self.live_quality_after_id = None
        self.render_live_canvas_image(resample=Image.Resampling.LANCZOS, update_scale=False)

    def start_live_map_drag(self, event):
        self.live_canvas.scan_mark(event.x, event.y)
        self.live_canvas.config(cursor="fleur")

    def drag_live_map(self, event):
        self.live_canvas.scan_dragto(event.x, event.y, gain=1)
        self.draw_live_overlay_legend()

    def end_live_map_drag(self, _event):
        self.live_canvas.config(cursor="")

    def on_live_ctrl_mousewheel(self, event):
        if event.delta > 0:
            self.live_zoom_in()
        else:
            self.live_zoom_out()
        return "break"

    def draw_live_point_markers(self):
        if not self.live_image_transform:
            return

        transform = self.live_image_transform
        marker_radius = max(4, min(12, int(4 * self.live_zoom_level)))
        for point in self.live_point_infos:
            sx = transform["offset_x"] + point["x"] * transform["scale"]
            sy = transform["offset_y"] + point["y"] * transform["scale"]
            if point.get("shape") == "cross":
                cross_radius = max(6, min(16, int(6 * self.live_zoom_level)))
                self.live_canvas.create_line(
                    sx - cross_radius,
                    sy - cross_radius,
                    sx + cross_radius,
                    sy + cross_radius,
                    fill=point.get("outline", "#d62728"),
                    width=max(2, int(2 * self.live_zoom_level))
                )
                self.live_canvas.create_line(
                    sx - cross_radius,
                    sy + cross_radius,
                    sx + cross_radius,
                    sy - cross_radius,
                    fill=point.get("outline", "#d62728"),
                    width=max(2, int(2 * self.live_zoom_level))
                )
                continue

            self.live_canvas.create_oval(
                sx - marker_radius,
                sy - marker_radius,
                sx + marker_radius,
                sy + marker_radius,
                fill=point.get("color", "#111111"),
                outline=point.get("outline", "white"),
                width=point.get("outline_width", 1)
            )

    def format_live_channel_legend_label(self, row):
        channel = self.format_report_value(row.get("channel", ""))
        ap_label = self.format_ap_label(row.get("bssid", ""))
        return f"CH {channel} - {ap_label}"

    def draw_live_overlay_legend(self):
        self.live_canvas.delete("live_overlay_legend")
        payload = self.live_scale_payload
        if not payload or payload.get("kind") != "swatches":
            return

        items = payload.get("items", [])
        if not items:
            return

        title_font = tkfont.Font(family="Segoe UI", size=11, weight="bold")
        body_font = tkfont.Font(family="Segoe UI", size=10)
        highlight_font = tkfont.Font(family="Segoe UI", size=10, weight="bold")
        marker_size = 14
        row_height = 29
        padding_x = 16
        padding_y = 14
        title_height = 46
        column_gap = 24
        marker_gap = 10
        visible_left = self.live_canvas.canvasx(0)
        visible_top = self.live_canvas.canvasy(0)
        visible_width = max(1, self.live_canvas.winfo_width())
        visible_height = max(1, self.live_canvas.winfo_height())
        max_box_height = max(80, visible_height - 28)
        max_rows = max(1, int((max_box_height - title_height - padding_y * 2) / row_height))
        columns = [items[index:index + max_rows] for index in range(0, len(items), max_rows)]
        column_widths = []

        for column_items in columns:
            text_width = max(
                highlight_font.measure(str(item.get("label", "")))
                for item in column_items
            )
            column_widths.append(marker_size + marker_gap + text_width + 10)

        title_width = title_font.measure(str(payload.get("title", "")))
        content_width = sum(column_widths) + column_gap * max(0, len(columns) - 1)
        box_width = max(title_width, content_width) + padding_x * 2
        box_height = title_height + padding_y * 2 + row_height * min(max_rows, len(items))
        right = visible_left + visible_width - 12
        bottom = visible_top + visible_height - 12
        x0 = max(visible_left + 8, right - box_width)
        y0 = max(visible_top + 8, bottom - box_height)
        x1 = x0 + box_width
        y1 = y0 + box_height

        self.live_canvas.create_rectangle(
            x0,
            y0,
            x1,
            y1,
            fill=getattr(self, "live_overlay_bg", "#ffffff"),
            outline=getattr(self, "live_overlay_border", "#2c3e50"),
            width=1,
            tags=("live_overlay_legend",)
        )
        self.live_canvas.create_text(
            x0 + padding_x,
            y0 + padding_y,
            text=payload.get("title", ""),
            anchor="nw",
            fill=getattr(self, "readable_text_color", "#2c3e50"),
            font=title_font,
            tags=("live_overlay_legend",)
        )
        self.live_canvas.create_line(
            x0 + padding_x,
            y0 + padding_y + title_height - 16,
            x1 - padding_x,
            y0 + padding_y + title_height - 16,
            fill=getattr(self, "live_overlay_separator", "#d7dde3"),
            width=1,
            tags=("live_overlay_legend",)
        )

        column_x = x0 + padding_x
        start_y = y0 + padding_y + title_height
        for column_index, column_items in enumerate(columns):
            y = start_y
            for item in column_items:
                color = item.get("color", "#7f8c8d")
                label = str(item.get("label", ""))
                is_highlighted = label and label == self.live_hover_legend_label
                marker_y = y + 5
                row_x0 = column_x - 4
                row_y0 = y - 2
                row_x1 = column_x + column_widths[column_index] + 4
                row_y1 = y + row_height - 2
                if is_highlighted:
                    self.live_canvas.create_rectangle(
                        row_x0,
                        row_y0,
                        row_x1,
                        row_y1,
                        fill=getattr(self, "live_overlay_highlight", "#e8f4ff"),
                        outline="#3498db",
                        width=1,
                        tags=("live_overlay_legend",)
                    )
                if item.get("outline_only"):
                    self.live_canvas.create_oval(
                        column_x,
                        marker_y,
                        column_x + marker_size,
                        marker_y + marker_size,
                        fill="",
                        outline=color,
                        width=3 if is_highlighted else 2,
                        tags=("live_overlay_legend",)
                    )
                else:
                    self.live_canvas.create_oval(
                        column_x,
                        marker_y,
                        column_x + marker_size,
                        marker_y + marker_size,
                        fill=color,
                        outline=getattr(self, "readable_text_color", "#2f3640"),
                        width=2 if is_highlighted else 1,
                        tags=("live_overlay_legend",)
                    )
                self.live_canvas.create_text(
                    column_x + marker_size + marker_gap,
                    y,
                    text=label,
                    anchor="nw",
                    fill=getattr(self, "readable_text_color", "#2f3640"),
                    font=highlight_font if is_highlighted else body_font,
                    tags=("live_overlay_legend",)
                )
                y += row_height

            column_x += column_widths[column_index] + column_gap

    def on_live_canvas_motion(self, event):
        point = self.find_live_point_at(
            self.live_canvas.canvasx(event.x),
            self.live_canvas.canvasy(event.y)
        )

        if point is None:
            self.hide_live_tooltip()
            return

        if point is self.live_tooltip_point:
            return

        self.show_live_tooltip(event, point)
        self.highlight_live_legend_item(point.get("legend_label"))

    def find_live_point_at(self, canvas_x, canvas_y):
        if not self.live_image_transform:
            return None

        transform = self.live_image_transform
        threshold = max(10, int(10 * self.live_zoom_level))
        best_point = None
        best_distance = threshold * threshold

        for point in self.live_point_infos:
            sx = transform["offset_x"] + point["x"] * transform["scale"]
            sy = transform["offset_y"] + point["y"] * transform["scale"]
            distance = (sx - canvas_x) ** 2 + (sy - canvas_y) ** 2
            if distance <= best_distance:
                best_distance = distance
                best_point = point

        return best_point

    def show_live_tooltip(self, event, point):
        self.hide_live_tooltip()
        self.live_tooltip_point = point
        self.live_tooltip_window = tk.Toplevel(self.root)
        self.live_tooltip_window.wm_overrideredirect(True)
        self.build_structured_tooltip(self.live_tooltip_window, point.get("tooltip") or point.get("text", ""))
        self.position_tooltip_window(self.live_tooltip_window, event)

    def hide_live_tooltip(self):
        if self.live_tooltip_window is not None:
            self.live_tooltip_window.destroy()
            self.live_tooltip_window = None
        self.live_tooltip_point = None
        self.highlight_live_legend_item(None)

    def highlight_live_legend_item(self, legend_label):
        if self.live_hover_legend_label == legend_label:
            return

        self.live_hover_legend_label = legend_label
        self.draw_live_overlay_legend()

    def position_tooltip_window(self, window, event):
        window.update_idletasks()
        offset = 12
        width = window.winfo_reqwidth()
        height = window.winfo_reqheight()
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        if event.x_root + offset + width <= screen_width:
            x = event.x_root + offset
        else:
            x = max(offset, event.x_root - width - offset)

        if event.y_root + offset + height <= screen_height:
            y = event.y_root + offset
        else:
            y = max(offset, event.y_root - height - offset)

        window.wm_geometry(f"+{x}+{y}")

    def build_structured_tooltip(self, parent, tooltip):
        if isinstance(tooltip, str):
            tooltip = {
                "title": "",
                "rows": [("", line) for line in tooltip.splitlines()],
                "accent": "#2c3e50"
            }

        bg = "#f8f9fa"
        border = "#2c3e50"
        accent = tooltip.get("accent") or border
        key_font = tkfont.Font(family="Segoe UI", size=8, weight="bold")
        value_font = tkfont.Font(family="Segoe UI", size=8)
        frame = tk.Frame(parent, background=bg, highlightbackground=border, highlightthickness=1, padx=0, pady=0)
        frame.pack()

        rows = tooltip.get("rows", [])
        screen_limit = max(360, parent.winfo_screenwidth() - 220)
        measured_value_width = max(
            [value_font.measure(str(value)) for _key, value in rows] or [360]
        )
        value_wraplength = min(screen_limit, max(360, measured_value_width + 18))

        title = tooltip.get("title", "")
        if title:
            title_frame = tk.Frame(frame, background=accent)
            title_frame.grid(row=0, column=0, columnspan=2, sticky="ew")
            tk.Label(
                title_frame,
                text=title,
                background=accent,
                foreground="#ffffff",
                font=("Segoe UI", 9, "bold"),
                padx=8,
                pady=4,
                anchor="w"
            ).pack(fill=tk.X)

        start_row = 1 if title else 0
        for index, (key, value) in enumerate(rows, start=start_row):
            row_bg = "#ffffff" if index % 2 == start_row % 2 else "#f1f3f5"
            if key:
                tk.Label(
                    frame,
                    text=str(key),
                    background=row_bg,
                    foreground="#495057",
                    font=key_font,
                    anchor="w",
                    padx=8,
                    pady=3
                ).grid(row=index, column=0, sticky="nw")
            tk.Label(
                frame,
                text=str(value),
                background=row_bg,
                foreground="#111111",
                font=value_font,
                anchor="w",
                justify=tk.LEFT,
                wraplength=value_wraplength,
                padx=8,
                pady=3
            ).grid(row=index, column=1 if key else 0, columnspan=1 if key else 2, sticky="nw")

        frame.grid_columnconfigure(1, weight=1)

    def update_live_scale_bar(self):
        if not hasattr(self, "live_scale_canvas"):
            return

        payload = self.live_scale_payload
        if not payload or payload.get("kind") != "gradient":
            self.set_live_scale_frame_visible(False)
            self.live_scale_title_var.set("")
            self.live_scale_canvas.delete("all")
            return

        self.set_live_scale_frame_visible(True)
        self.live_scale_title_var.set(payload.get("title", ""))
        self.redraw_live_scale_bar()

    def set_live_scale_frame_visible(self, visible):
        if visible:
            if not self.live_scale_frame.winfo_ismapped():
                pack_options = {"side": tk.BOTTOM, "fill": tk.X}
                if hasattr(self, "live_status_label") and self.live_status_label.winfo_ismapped():
                    pack_options["before"] = self.live_status_label
                self.live_scale_frame.pack(**pack_options)
            return

        if self.live_scale_frame.winfo_ismapped():
            self.live_scale_frame.pack_forget()

    def redraw_live_scale_bar(self):
        if not hasattr(self, "live_scale_canvas"):
            return

        payload = self.live_scale_payload
        self.live_scale_canvas.delete("all")
        if not payload or payload.get("kind") != "gradient":
            return

        if payload.get("kind") == "gradient":
            self.draw_live_gradient_scale(payload)

    def draw_live_gradient_scale(self, payload):
        if int(self.live_scale_canvas.cget("height")) != 52:
            self.live_scale_canvas.configure(height=52)
            return

        width = max(1, self.live_scale_canvas.winfo_width())
        bar_x = 4
        bar_y = 8
        bar_width = max(80, width - 8)
        bar_height = 12
        steps = min(180, bar_width)
        cmap = plt.get_cmap(payload.get("cmap", "RdYlGn"))

        for index in range(steps):
            ratio = index / max(1, steps - 1)
            color = self.matplotlib_color_to_hex(cmap(ratio))
            x0 = bar_x + int(index * bar_width / steps)
            x1 = bar_x + int((index + 1) * bar_width / steps) + 1
            self.live_scale_canvas.create_rectangle(
                x0,
                bar_y,
                x1,
                bar_y + bar_height,
                fill=color,
                outline=color
            )

        min_value = payload.get("min", 0)
        max_value = payload.get("max", 100)
        suffix = payload.get("suffix", "")
        mid_value = (float(min_value) + float(max_value)) / 2
        labels = [
            (bar_x, self.format_scale_value(min_value, suffix), "w"),
            (bar_x + bar_width // 2, self.format_scale_value(mid_value, suffix), "center"),
            (bar_x + bar_width, self.format_scale_value(max_value, suffix), "e"),
        ]
        for x, text, anchor in labels:
            self.live_scale_canvas.create_text(
                x,
                bar_y + bar_height + 18,
                text=text,
                anchor=anchor,
                fill=getattr(self, "readable_text_color", "#2f3640"),
                font=("Segoe UI", 8)
            )

    def draw_live_swatch_scale(self, payload):
        items = payload.get("items", [])
        if not items:
            return

        desired_height = 52 if self.live_swatch_scale_needs_wrap(items) else 30
        if int(self.live_scale_canvas.cget("height")) != desired_height:
            self.live_scale_canvas.configure(height=desired_height)
            return

        x = 4
        y = 8
        row_height = 22
        max_rows = 2
        current_row = 0
        item_gap = 24
        marker_to_text_gap = 8
        marker_size = 12
        max_width = max(1, self.live_scale_canvas.winfo_width())
        for index, item in enumerate(items):
            color = item.get("color", "#7f8c8d")
            label = self.truncate_live_scale_label(item.get("label", ""))
            text_width = max(42, min(126, len(str(label)) * 8))
            item_width = marker_size + marker_to_text_gap + text_width + item_gap

            if x > 4 and x + item_width > max_width - 50:
                current_row += 1
                if current_row >= max_rows:
                    remaining = len(items) - index
                    self.live_scale_canvas.create_text(
                        x,
                        y + 6,
                        text=f"+{remaining}",
                        anchor="w",
                        fill=getattr(self, "readable_text_color", "#2f3640"),
                        font=("Segoe UI", 8)
                    )
                    break
                x = 4
                y += row_height

            if item.get("outline_only"):
                self.live_scale_canvas.create_oval(x, y, x + marker_size, y + marker_size, fill="", outline=color, width=2)
            else:
                self.live_scale_canvas.create_oval(x, y, x + marker_size, y + marker_size, fill=color, outline=getattr(self, "readable_text_color", "#2f3640"), width=1)

            label_x = x + marker_size + marker_to_text_gap
            self.live_scale_canvas.create_text(
                label_x,
                y + 6,
                text=label,
                anchor="w",
                fill=getattr(self, "readable_text_color", "#2f3640"),
                font=("Segoe UI", 8)
            )
            x += item_width

    def live_swatch_scale_needs_wrap(self, items):
        x = 4
        item_gap = 24
        marker_to_text_gap = 8
        marker_size = 12
        max_width = max(1, self.live_scale_canvas.winfo_width())

        for item in items:
            label = self.truncate_live_scale_label(item.get("label", ""))
            text_width = max(42, min(126, len(str(label)) * 8))
            item_width = marker_size + marker_to_text_gap + text_width + item_gap
            if x > 4 and x + item_width > max_width - 50:
                return True
            x += item_width

        return False

    def matplotlib_color_to_hex(self, rgba):
        red, green, blue = [int(max(0, min(1, value)) * 255) for value in rgba[:3]]
        return f"#{red:02x}{green:02x}{blue:02x}"

    def format_scale_value(self, value, suffix=""):
        try:
            number = float(value)
        except (TypeError, ValueError):
            return f"{value}{suffix}"

        if number.is_integer():
            return f"{int(number)}{suffix}"
        return f"{number:.1f}{suffix}"

    def truncate_live_scale_label(self, label):
        text = str(label)
        if len(text) <= 16:
            return text
        return f"{text[:13]}..."

    def format_short_bssid(self, bssid):
        return format_short_bssid(bssid)

    def format_ap_label(self, bssid, ap_group=None):
        return format_ap_group_label(bssid, self.session.get_ap_aliases(), ap_group)

    def build_dominant_ap_group_labels(self, dominant_df):
        return build_ap_group_labels(dominant_df, self.session.get_ap_aliases())

    def format_live_signal_tooltip(self, row, config, raw_rows):
        signal = self.format_report_value(row.get("signal_dbm", ""), suffix=" dBm")
        confidence = self.format_row_confidence(row)
        return {
            "title": self.tr("map_type_signal"),
            "accent": "#111111",
            "rows": [
                ("SSID", config.ssid),
                ("x/y", f"{self.format_report_value(row.get('x', ''))}, {self.format_report_value(row.get('y', ''))}"),
                (self.tr("best"), signal),
                (self.tr("confidence"), confidence),
                (self.tr("band"), format_band_label(config.band, self.language)),
                (self.tr("rows"), raw_rows),
            ]
        }

    def format_live_channel_tooltip(self, row, config):
        width = self.format_report_value(row.get("channel_width_mhz", ""))
        width_label = f" / {width} MHz" if width != "-" else ""
        ap_label = self.format_ap_label(row.get("bssid", ""))
        return {
            "title": self.tr("map_type_channel"),
            "accent": get_channel_color(row.get("channel", ""), config.band),
            "rows": [
                ("SSID", config.ssid),
                ("x/y", f"{self.format_report_value(row.get('x', ''))}, {self.format_report_value(row.get('y', ''))}"),
                (self.tr("reference_ap"), ap_label),
                (self.tr("reference_channel"), f"CH {self.format_report_value(row.get('channel', ''))}{width_label}"),
                (self.tr("best"), self.format_report_value(row.get("signal_dbm", ""), suffix=" dBm")),
                (self.tr("confidence"), self.format_row_confidence(row)),
            ]
        }

    def format_live_dominant_tooltip(self, row, config):
        delta = self.format_report_value(row.get("delta_db", ""), suffix=" dB")
        dominant = self.format_ap_label(row.get("dominant_bssid", ""), row.get("dominant_ap_group", ""))
        second = self.format_ap_label(row.get("second_bssid", ""), row.get("second_ap_group", "")) if row.get("second_bssid", "") else "-"
        return {
            "title": self.tr("map_type_dominant"),
            "accent": "#f1c40f" if row.get("roaming_overlap") else "#34495e",
            "rows": [
                ("SSID", config.ssid),
                ("x/y", f"{self.format_report_value(row.get('x', ''))}, {self.format_report_value(row.get('y', ''))}"),
                (self.tr("reference_ap"), dominant),
                (self.tr("reference_channel"), f"CH {self.format_report_value(row.get('dominant_channel', ''))}"),
                (self.tr("best"), self.format_report_value(row.get("dominant_signal_dbm", ""), suffix=" dBm")),
                (self.tr("confidence"), self.format_named_confidence(row, "dominant")),
                (self.tr("second_ap"), second),
                (self.tr("second_confidence"), self.format_named_confidence(row, "second")),
                ("Delta", delta),
            ]
        }

    def format_live_interference_tooltip(self, row, config):
        risk = self.format_report_value(row.get("risk", ""), suffix="%")
        serving_width = self.format_report_value(row.get("serving_channel_width_mhz", ""), suffix=" MHz")
        interferer_width = self.format_report_value(
            row.get("strongest_interferer_channel_width_mhz", ""),
            suffix=" MHz"
        )
        width_label = self.format_interference_width_label(serving_width, interferer_width)
        serving = self.format_interference_endpoint(
            row.get("serving_ssid", config.ssid),
            row.get("serving_bssid", "-"),
            row.get("serving_ap_group", ""),
            row.get("serving_channel", ""),
            row.get("serving_signal_dbm", "")
        )
        interferer = self.format_interference_endpoint(
            row.get("strongest_interferer_ssid", "-"),
            row.get("strongest_interferer_bssid", "-"),
            row.get("strongest_interferer_ap_group", ""),
            row.get("strongest_interferer_channel", ""),
            row.get("strongest_interferer_dbm", "")
        )
        return {
            "title": self.tr("map_type_interference"),
            "accent": self.get_interference_marker_color(float(row.get("risk", 0) or 0)),
            "rows": [
                ("SSID", config.ssid),
                ("x/y", f"{self.format_report_value(row.get('x', ''))}, {self.format_report_value(row.get('y', ''))}"),
                (self.tr("channel_width"), width_label),
                (self.tr("reference_risk"), risk),
                (self.tr("serving_ap"), serving),
                (self.tr("confidence"), self.format_named_confidence(row, "serving")),
                (self.tr("interfering_ap"), interferer),
                (self.tr("interferer_confidence"), self.format_named_confidence(row, "strongest_interferer")),
            ]
        }

    def format_interference_width_label(self, serving_width, interferer_width):
        if serving_width == "-" and interferer_width == "-":
            return "-"
        if serving_width == interferer_width:
            return serving_width
        return f"{self.tr('serving_ap')}: {serving_width} | {self.tr('interfering_ap')}: {interferer_width}"

    def format_interference_endpoint(self, ssid, bssid, ap_group, channel, signal_dbm):
        ssid_label = ssid or "-"
        ap_label = self.format_ap_label(bssid, ap_group)
        channel_label = self.format_report_value(channel)
        signal_label = self.format_report_value(signal_dbm, suffix=" dBm")
        signal_part = f" | {signal_label}" if signal_label != "-" else ""
        return f"{ssid_label} | {ap_label} | CH {channel_label}{signal_part}"

    def format_row_confidence(self, row):
        samples_seen = row.get("samples_seen", "")
        samples_total = row.get("samples_total", "")
        confidence = self.format_report_value(row.get("scan_confidence", ""))

        if samples_seen in ("", None) or samples_total in ("", None):
            return "-"

        suffix = f" ({confidence})" if confidence != "-" else ""
        return f"{samples_seen}/{samples_total}{suffix}"

    def format_named_confidence(self, row, prefix):
        samples_seen = row.get(f"{prefix}_samples_seen", "")
        samples_total = row.get(f"{prefix}_samples_total", "")
        confidence = self.format_report_value(row.get(f"{prefix}_scan_confidence", ""))

        if samples_seen in ("", None) or samples_total in ("", None):
            return "-"

        suffix = f" ({confidence})" if confidence != "-" else ""
        return f"{samples_seen}/{samples_total}{suffix}"

    def get_interference_marker_color(self, risk):
        if risk >= 60:
            return "#d73027"
        if risk >= 30:
            return "#fee08b"
        return "#1a9850"

    def zoom_in(self):
        self.set_zoom(self.zoom_level * 1.25)

    def zoom_out(self):
        self.set_zoom(self.zoom_level / 1.25)

    def set_zoom(self, zoom_level):
        if self.bg_image is None:
            return

        self.zoom_level = min(5.0, max(0.15, zoom_level))
        self.render_canvas()
        self.status_var.set(self.tr("zoom", zoom=self.zoom_level))

    def fit_to_window(self):
        if self.bg_image is None:
            return

        self.canvas.update_idletasks()
        canvas_width = max(1, self.canvas.winfo_width())
        canvas_height = max(1, self.canvas.winfo_height())
        scale_x = canvas_width / self.bg_image.width
        scale_y = canvas_height / self.bg_image.height
        self.set_zoom(min(scale_x, scale_y))

    def on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def on_shift_mousewheel(self, event):
        self.canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")

    def on_ctrl_mousewheel(self, event):
        if event.delta > 0:
            self.zoom_in()
        else:
            self.zoom_out()

    def open_heatmap_dialog(self):
        if self.bg_image is None:
            messagebox.showwarning(self.tr("warning"), self.tr("load_plan_first"))
            return

        df = self.session.to_dataframe()

        if df.empty:
            messagebox.showwarning(self.tr("warning"), self.tr("empty_csv"))
            return

        ssids = sorted(df["ssid"].dropna().unique())
        self.refresh_ssid_options(ssids)

        if not ssids:
            messagebox.showwarning(self.tr("warning"), self.tr("no_ssid"))
            return

        dialog = self.create_modal_dialog(self.tr("generate_heatmap"))

        frame = ttk.Frame(dialog, padding=16)
        frame.pack(fill=tk.BOTH, expand=True)

        content = ttk.Frame(frame)
        content.pack(fill=tk.BOTH, expand=True)

        signal_only_widgets = []
        interference_only_widgets = []
        continuous_map_widgets = []
        point_label_widgets = []
        point_label_option_widgets = {}
        point_label_all_widget = None
        all_band_widget = None

        def set_widget_state(widgets, enabled):
            state = tk.NORMAL if enabled else tk.DISABLED
            for widget in widgets:
                widget.configure(state=state)

        def update_heatmap_dialog_state():
            config = self.get_current_map_config()
            self.apply_map_config_to_controls(config)
            set_widget_state(signal_only_widgets, config.is_signal)
            set_widget_state(interference_only_widgets, config.is_interference)
            set_widget_state(continuous_map_widgets, config.is_continuous)
            set_widget_state(point_label_widgets, not config.is_signal)

            if all_band_widget is not None:
                all_band_widget.configure(state=tk.DISABLED if config.is_interference else tk.NORMAL)
            if point_label_all_widget is not None:
                point_label_all_widget.configure(
                    state=tk.DISABLED if config.is_interference or config.is_signal else tk.NORMAL
                )
            if "auto" in point_label_option_widgets:
                point_label_option_widgets["auto"].configure(
                    state=tk.DISABLED if config.is_interference or config.is_signal else tk.NORMAL
                )

        ttk.Label(content, text="SSID").grid(row=0, column=0, columnspan=2, sticky="w")
        self.ssid_combo = ttk.Combobox(
            content,
            textvariable=self.ssid_var,
            state="readonly",
            values=ssids,
            width=42
        )
        self.ssid_combo.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(4, 14))
        self.refresh_ssid_options(ssids)

        left = ttk.Frame(content)
        left.grid(row=2, column=0, sticky="nw", padx=(0, 34))
        right = ttk.Frame(content)
        right.grid(row=2, column=1, sticky="nw")
        content.grid_columnconfigure(0, weight=1)
        content.grid_columnconfigure(1, weight=1)

        ttk.Label(left, text=self.tr("map_type")).pack(anchor="w")
        ttk.Radiobutton(
            left,
            text=self.tr("map_type_signal"),
            value="signal",
            variable=self.map_type_var,
            command=update_heatmap_dialog_state
        ).pack(anchor="w", pady=(3, 0))
        ttk.Radiobutton(
            left,
            text=self.tr("map_type_interference"),
            value="interference",
            variable=self.map_type_var,
            command=update_heatmap_dialog_state
        ).pack(anchor="w", pady=(2, 0))
        ttk.Radiobutton(
            left,
            text=self.tr("map_type_channel"),
            value="channel",
            variable=self.map_type_var,
            command=update_heatmap_dialog_state
        ).pack(anchor="w", pady=(2, 0))
        ttk.Radiobutton(
            left,
            text=self.tr("map_type_dominant"),
            value="dominant",
            variable=self.map_type_var,
            command=update_heatmap_dialog_state
        ).pack(anchor="w", pady=(2, 0))

        ttk.Label(left, text=self.tr("band")).pack(anchor="w", pady=(18, 0))
        all_band_widget = ttk.Radiobutton(left, text=self.tr("all_bands_option"), value="all", variable=self.band_var)
        all_band_widget.pack(anchor="w", pady=(3, 0))
        ttk.Radiobutton(left, text="2.4 GHz", value="2.4", variable=self.band_var).pack(anchor="w", pady=(2, 0))
        ttk.Radiobutton(left, text="5 GHz", value="5", variable=self.band_var).pack(anchor="w", pady=(2, 0))

        interpolation_label = ttk.Label(left, text=self.tr("interpolation"))
        interpolation_label.pack(anchor="w", pady=(18, 0))
        continuous_map_widgets.append(interpolation_label)
        for text, value, pady in (
            (self.tr("interpolation_rbf"), "rbf", (3, 0)),
            (self.tr("interpolation_linear"), "linear", (2, 0)),
        ):
            widget = ttk.Radiobutton(left, text=text, value=value, variable=self.interpolation_var)
            widget.pack(anchor="w", pady=pady)
            continuous_map_widgets.append(widget)

        aggregation_label = ttk.Label(right, text=self.tr("aggregation"))
        aggregation_label.pack(anchor="w")
        signal_only_widgets.append(aggregation_label)
        for text, value, pady in (
            (self.tr("aggregation_max"), "max", (3, 0)),
            (self.tr("aggregation_mean"), "mean", (2, 0)),
            (self.tr("aggregation_median"), "median", (2, 0)),
        ):
            widget = ttk.Radiobutton(right, text=text, value=value, variable=self.aggregation_var)
            widget.pack(anchor="w", pady=pady)
            signal_only_widgets.append(widget)

        interference_label = ttk.Label(right, text=self.tr("interference_mode"))
        interference_label.pack(anchor="w", pady=(18, 0))
        interference_only_widgets.append(interference_label)
        for text, value, pady in (
            (self.tr("interference_mode_intra_ssid"), "intra_ssid", (3, 0)),
            (self.tr("interference_mode_all"), "all", (2, 0)),
        ):
            widget = ttk.Radiobutton(right, text=text, value=value, variable=self.interference_mode_var)
            widget.pack(anchor="w", pady=pady)
            interference_only_widgets.append(widget)

        color_scale_label = ttk.Label(right, text=self.tr("color_scale"))
        color_scale_label.pack(anchor="w", pady=(18, 0))
        signal_only_widgets.append(color_scale_label)
        for text, value, pady in (
            (self.tr("color_scale_fixed"), "fixed", (3, 0)),
            (self.tr("color_scale_auto"), "auto", (2, 0)),
        ):
            widget = ttk.Radiobutton(right, text=text, value=value, variable=self.color_scale_var)
            widget.pack(anchor="w", pady=pady)
            signal_only_widgets.append(widget)

        usable_check = ttk.Checkbutton(
            right,
            text=self.tr("usable_only"),
            variable=self.usable_only_var
        )
        usable_check.pack(anchor="w", pady=(18, 0))
        signal_only_widgets.append(usable_check)

        numeric_frame = ttk.Frame(right)
        numeric_frame.pack(anchor="w", pady=(18, 0))

        smoothing_frame = ttk.Frame(numeric_frame)
        smoothing_frame.pack(side=tk.LEFT, padx=(0, 18))
        smoothing_label = ttk.Label(smoothing_frame, text="Smoothing")
        smoothing_label.pack(anchor="w")
        continuous_map_widgets.append(smoothing_label)
        smoothing_spinbox = ttk.Spinbox(
            smoothing_frame,
            from_=0.0,
            to=8.0,
            increment=0.5,
            textvariable=self.smoothing_var,
            width=8
        )
        smoothing_spinbox.pack(anchor="w", pady=(4, 0))
        continuous_map_widgets.append(smoothing_spinbox)

        distance_frame = ttk.Frame(numeric_frame)
        distance_frame.pack(side=tk.LEFT)
        distance_label = ttk.Label(distance_frame, text=self.get_max_distance_label())
        distance_label.pack(anchor="w")
        continuous_map_widgets.append(distance_label)
        distance_from, distance_to, distance_increment = self.get_distance_control_range()
        distance_spinbox = ttk.Spinbox(
            distance_frame,
            from_=distance_from,
            to=distance_to,
            increment=distance_increment,
            textvariable=self.distance_var,
            width=8
        )
        distance_spinbox.pack(anchor="w", pady=(4, 0))
        continuous_map_widgets.append(distance_spinbox)

        point_labels_label = ttk.Label(right, text=self.tr("point_labels"))
        point_labels_label.pack(anchor="w", pady=(18, 0))
        point_label_widgets.append(point_labels_label)
        for text, value, pady in (
            (self.tr("point_labels_auto"), "auto", (3, 0)),
            (self.tr("point_labels_critical"), "critical", (2, 0)),
            (self.tr("point_labels_all"), "all", (2, 0)),
            (self.tr("point_labels_none"), "none", (2, 0)),
        ):
            widget = ttk.Radiobutton(
                right,
                text=text,
                value=value,
                variable=self.point_label_mode_var
            )
            widget.pack(anchor="w", pady=pady)
            point_label_widgets.append(widget)
            point_label_option_widgets[value] = widget
            if value == "all":
                point_label_all_widget = widget

        buttons = ttk.Frame(frame)
        buttons.pack(fill=tk.X, pady=(18, 0))
        ttk.Button(buttons, text=self.tr("cancel"), command=dialog.destroy, bootstyle=SECONDARY).pack(side=tk.RIGHT)
        ttk.Button(
            buttons,
            text=self.tr("generate"),
            command=lambda: self.generate_heatmap_from_dialog(dialog),
            bootstyle=SUCCESS
        ).pack(side=tk.RIGHT, padx=(0, 8))
        dialog.bind("<Escape>", lambda _event: dialog.destroy())
        update_heatmap_dialog_state()
        self.center_dialog(dialog)

    def create_modal_dialog(self, title):
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)
        dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
        self.register_modal_dialog(dialog)
        return dialog

    def register_modal_dialog(self, dialog):
        self.modal_dialogs.append(dialog)

        def forget_dialog(_event=None):
            self.modal_dialogs = [
                existing_dialog
                for existing_dialog in self.modal_dialogs
                if existing_dialog is not dialog and existing_dialog.winfo_exists()
            ]

        dialog.bind("<Destroy>", forget_dialog, add="+")

    def get_active_modal_dialog(self):
        for dialog in reversed(self.modal_dialogs):
            if dialog.winfo_exists():
                return dialog

        return None

    def bring_dialog_to_front(self, dialog):
        if not dialog or not dialog.winfo_exists():
            return

        dialog.deiconify()
        dialog.lift(self.root)
        try:
            dialog.attributes("-topmost", True)
            dialog.after(150, lambda: dialog.winfo_exists() and dialog.attributes("-topmost", False))
        except tk.TclError:
            pass
        dialog.focus_force()

    def restore_active_modal_dialog(self, _event=None):
        dialog = self.get_active_modal_dialog()
        if dialog is not None:
            self.root.after(50, lambda: self.bring_dialog_to_front(dialog))

    def center_dialog(self, dialog):
        dialog.update_idletasks()

        parent_x = self.root.winfo_rootx()
        parent_y = self.root.winfo_rooty()
        parent_width = self.root.winfo_width()
        parent_height = self.root.winfo_height()
        dialog_width = dialog.winfo_width()
        dialog_height = dialog.winfo_height()

        if parent_width <= 1 or parent_height <= 1:
            parent_x = 0
            parent_y = 0
            parent_width = self.root.winfo_screenwidth()
            parent_height = self.root.winfo_screenheight()

        x = parent_x + max(0, (parent_width - dialog_width) // 2)
        y = parent_y + max(0, (parent_height - dialog_height) // 2)
        dialog.geometry(f"+{x}+{y}")
        self.bring_dialog_to_front(dialog)

    def generate_heatmap_from_dialog(self, dialog):
        if self.generate_heatmap():
            dialog.destroy()

    def generate_heatmap(self):
        df = self.session.to_dataframe()
        config = self.get_current_map_config()
        self.apply_map_config_to_controls(config)
        ssid = config.ssid

        if not ssid:
            messagebox.showwarning(self.tr("warning"), self.tr("select_ssid_heatmap"))
            return False

        if not self.ensure_saved_for_heatmap():
            self.status_var.set(self.tr("save_failed"))
            return False

        if config.is_interference:
            return self.generate_interference_map(df, config)

        if config.is_channel:
            return self.generate_channel_map(df, config)

        if config.is_dominant:
            return self.generate_dominant_ap_map(df, config)

        df = df[df["ssid"].str.lower() == ssid.lower()]
        band = config.band

        df = filter_by_band(df, band)
        raw_rows = len(df)
        df = collapse_heatmap_points(df, aggregation=config.aggregation)

        if len(df) < 3:
            messagebox.showwarning(
                self.tr("insufficient_data_title"),
                self.tr("insufficient_data", band=format_band_label(band, self.language))
            )
            return False

        x = df["x"].values
        y = df["y"].values
        signal = df["signal_dbm"].values

        width, height = self.bg_image.size

        grid_x, grid_y = np.mgrid[
            0:width:complex(HEATMAP_GRID_SIZE),
            0:height:complex(HEATMAP_GRID_SIZE)
        ]

        grid_z = interpolate_signal_grid(
            x,
            y,
            signal,
            grid_x,
            grid_y,
            method=config.interpolation
        )
        grid_z = smooth_heatmap_grid(grid_z, sigma=config.smoothing_sigma)
        grid_z = apply_distance_mask(
            grid_z,
            grid_x,
            grid_y,
            x,
            y,
            max_distance_px=config.max_distance_px
        )

        if config.usable_only:
            grid_z = apply_signal_threshold(grid_z, min_signal_dbm=-70)

        distance_alpha = get_distance_alpha(
            grid_x,
            grid_y,
            x,
            y,
            max_distance_px=config.max_distance_px
        )
        heatmap_alpha = np.where(np.isfinite(grid_z), distance_alpha * 0.55, 0)
        vmin, vmax = self.get_color_scale_limits(grid_z, config)
        bg = np.array(self.bg_image)

        plt.figure(figsize=(14, 8))
        plt.imshow(bg)
        plt.imshow(
            grid_z.T,
            extent=(0, width, height, 0),
            alpha=heatmap_alpha.T,
            cmap="RdYlGn",
            vmin=vmin,
            vmax=vmax,
            interpolation="bilinear"
        )
        plt.colorbar(label=self.tr("export_signal_colorbar"))
        plt.scatter(x, y, c="black", s=8)
        plt.title(
            f"{self.tr('export_signal_title')} - {ssid} - {format_band_label(band, self.language)} "
            f"({len(df)} {self.tr('export_points')}, {raw_rows} {self.tr('export_measurements')}"
            f"{', >= -70 dBm' if config.usable_only else ''})"
        )
        plt.axis("off")

        output_file = self.build_heatmap_output_path(ssid, band)
        plt.savefig(output_file, dpi=200, bbox_inches="tight")
        plt.close()

        messagebox.showinfo(self.tr("heatmap_generated"), self.tr("file_created", path=output_file))
        return True

    def generate_channel_map(self, df, config):
        ssid = config.ssid
        band = config.band
        channel_df = get_channel_map_points(df, ssid, band)

        if channel_df.empty:
            messagebox.showwarning(
                self.tr("insufficient_data_title"),
                self.tr("insufficient_data", band=format_band_label(band, self.language))
            )
            return False

        width, height = self.bg_image.size
        bg = np.array(self.bg_image)
        fig, ax = plt.subplots(figsize=(14, 8))
        ax.imshow(bg)

        colors = [
            get_channel_color(row["channel"], band)
            for _index, row in channel_df.iterrows()
        ]
        ax.scatter(
            channel_df["x"].values,
            channel_df["y"].values,
            c=colors,
            s=32,
            edgecolors="black",
            linewidths=0.45,
            zorder=3
        )
        references = annotate_channel_references(
            ax,
            channel_df,
            self.format_report_value,
            mode=config.point_label_mode,
            band=band,
            labels=self.get_reference_label_terms()
        )
        add_reference_table(
            ax,
            references,
            self.tr("reference_table_info"),
            overflow_label=self.tr("reference_more_in_report", count=max(0, len(references) - 10))
        )

        ax.legend(
            handles=build_channel_legend_handles(
                channel_df,
                band,
                self.tr("channel_map_intermediate_24"),
                self.format_report_value,
                other_label=self.tr("legend_other")
            ),
            title=self.tr("channel_map_legend_title"),
            loc="lower right",
            framealpha=0.88,
            facecolor="white",
            edgecolor="#333333"
        )
        ax.set_title(
            f"{self.tr('export_channel_title')} - {ssid} - {format_band_label(band, self.language)} "
            f"({len(channel_df)} {self.tr('export_points')})"
        )
        ax.axis("off")

        output_file = self.build_heatmap_output_path(ssid, f"channels_{band}")
        plt.savefig(output_file, dpi=200, bbox_inches="tight")
        plt.close()
        messagebox.showinfo(self.tr("heatmap_generated"), self.tr("file_created", path=output_file))
        return True

    def generate_dominant_ap_map(self, df, config):
        ssid = config.ssid
        band = config.band
        dominant_df = get_dominant_ap_points(df, ssid, band)

        if dominant_df.empty:
            messagebox.showwarning(
                self.tr("insufficient_data_title"),
                self.tr("insufficient_data", band=format_band_label(band, self.language))
            )
            return False

        bg = np.array(self.bg_image)
        fig, ax = plt.subplots(figsize=(14, 8))
        ax.imshow(bg)

        color_map, _visible_ap_groups, _hidden_ap_count = get_limited_bssid_color_map(dominant_df)
        colors = [
            color_map.get(row["dominant_ap_group"], "#7f8c8d")
            for _index, row in dominant_df.iterrows()
        ]
        edge_colors = [
            "#f1c40f" if row.get("roaming_overlap") else "black"
            for _index, row in dominant_df.iterrows()
        ]
        line_widths = [
            1.3 if row.get("roaming_overlap") else 0.45
            for _index, row in dominant_df.iterrows()
        ]
        ax.scatter(
            dominant_df["x"].values,
            dominant_df["y"].values,
            c=colors,
            s=36,
            edgecolors=edge_colors,
            linewidths=line_widths,
            zorder=3
        )
        references = annotate_dominant_ap_references(
            ax,
            dominant_df,
            self.format_report_value,
            mode=config.point_label_mode,
            labels=self.get_reference_label_terms()
        )
        add_reference_table(
            ax,
            references,
            self.tr("reference_table_info"),
            overflow_label=self.tr("reference_more_in_report", count=max(0, len(references) - 10))
        )
        ax.legend(
            handles=build_dominant_ap_legend_handles(
                dominant_df,
                color_map,
                self.tr("dominant_map_roaming_overlap"),
                other_label=self.tr("legend_other"),
                group_labels=self.build_dominant_ap_group_labels(dominant_df)
            ),
            title=self.tr("dominant_map_legend_title"),
            loc="lower right",
            framealpha=0.88,
            facecolor="white",
            edgecolor="#333333"
        )
        roaming_count = int(dominant_df["roaming_overlap"].sum())
        ax.set_title(
            f"{self.tr('export_dominant_title')} - {ssid} - {format_band_label(band, self.language)} "
            f"({len(dominant_df)} {self.tr('export_points')}, "
            f"{roaming_count} {self.tr('export_roaming_overlap')})"
        )
        ax.axis("off")

        output_file = self.build_heatmap_output_path(ssid, f"dominant_{band}")
        report_file = self.build_dominant_ap_report_output_path(output_file)
        plt.savefig(output_file, dpi=200, bbox_inches="tight")
        plt.close()
        self.save_dominant_ap_report(dominant_df, report_file)
        messagebox.showinfo(
            self.tr("heatmap_generated"),
            self.tr("files_created", paths=f"{output_file}\n{report_file}")
        )
        return True

    def generate_interference_map(self, df, config):
        ssid = config.ssid
        band = config.band

        if band not in {"2.4", "5"}:
            messagebox.showwarning(self.tr("warning"), self.tr("interference_requires_band"))
            return False

        risk_df = calculate_interference_points(
            df,
            ssid,
            band,
            mode=config.interference_mode,
            include_details=True
        )

        if len(risk_df) < 3:
            messagebox.showwarning(
                self.tr("insufficient_data_title"),
                self.tr("insufficient_data", band=format_band_label(band, self.language))
            )
            return False

        x = risk_df["x"].values
        y = risk_df["y"].values
        risk = risk_df["risk"].values
        width, height = self.bg_image.size

        grid_x, grid_y = np.mgrid[
            0:width:complex(HEATMAP_GRID_SIZE),
            0:height:complex(HEATMAP_GRID_SIZE)
        ]
        grid_z = interpolate_signal_grid(
            x,
            y,
            risk,
            grid_x,
            grid_y,
            method=config.interpolation
        )
        grid_z = smooth_heatmap_grid(grid_z, sigma=config.smoothing_sigma)
        grid_z = apply_distance_mask(
            grid_z,
            grid_x,
            grid_y,
            x,
            y,
            max_distance_px=config.max_distance_px
        )
        distance_alpha = get_distance_alpha(
            grid_x,
            grid_y,
            x,
            y,
            max_distance_px=config.max_distance_px
        )
        heatmap_alpha = np.where(np.isfinite(grid_z), distance_alpha * 0.58, 0)
        bg = np.array(self.bg_image)

        fig, ax = plt.subplots(figsize=(14, 8))
        ax.imshow(bg)
        heatmap_layer = ax.imshow(
            grid_z.T,
            extent=(0, width, height, 0),
            alpha=heatmap_alpha.T,
            cmap="RdYlGn_r",
            vmin=0,
            vmax=100,
            interpolation="bilinear"
        )
        cbar = fig.colorbar(heatmap_layer, ax=ax, fraction=0.035, pad=0.02)
        cbar.set_label(self.tr("interference_colorbar"))
        cbar.set_ticks([0, 30, 60, 100])
        cbar.set_ticklabels([
            f"0 {self.tr('interference_low')}",
            f"30 {self.tr('interference_medium')}",
            f"60 {self.tr('interference_high')}",
            "100"
        ])

        point_sizes = np.clip(16 + (risk * 0.28), 16, 44)
        ax.scatter(
            x,
            y,
            c=risk,
            s=point_sizes,
            cmap="RdYlGn_r",
            vmin=0,
            vmax=100,
            edgecolors="black",
            linewidths=0.45,
            zorder=3
        )
        references = annotate_interference_references(
            ax,
            risk_df,
            self.format_report_value,
            mode=config.point_label_mode,
            labels=self.get_reference_label_terms()
        )
        add_reference_table(
            ax,
            references,
            self.tr("reference_table_info"),
            overflow_label=self.tr("reference_more_in_report", count=max(0, len(references) - 10))
        )
        legend_handles = build_interference_legend_handles(
            self.tr("interference_low"),
            self.tr("interference_medium"),
            self.tr("interference_high")
        )
        ax.legend(
            handles=legend_handles,
            title=self.tr("interference_legend_title"),
            loc="lower right",
            framealpha=0.88,
            facecolor="white",
            edgecolor="#333333"
        )
        ax.set_title(
            f"{self.tr('export_interference_title')} - {ssid} - {format_band_label(band, self.language)} "
            f"({self.get_interference_mode_label(config)}) - "
            f"{self.tr('interference_top_risk')}: {float(risk_df['risk'].max()):.1f}%"
        )
        ax.axis("off")

        output_file = self.build_heatmap_output_path(ssid, f"interference_{band}")
        report_file = self.build_interference_report_output_path(output_file)
        plt.savefig(output_file, dpi=200, bbox_inches="tight")
        plt.close()
        self.save_interference_report(risk_df, report_file)
        self.show_interference_summary_dialog(
            risk_df,
            output_file,
            report_file,
            format_band_label(band, self.language)
        )
        return True

    def show_interference_summary_dialog(self, risk_df, output_file, report_file, band_label):
        worst_row = risk_df.loc[risk_df["risk"].idxmax()]
        risk_value = float(worst_row.get("risk", 0))
        x_value = self.format_report_value(worst_row.get("x", ""))
        y_value = self.format_report_value(worst_row.get("y", ""))
        serving_channel = self.format_report_value(worst_row.get("serving_channel", ""))
        serving_width = self.format_report_value(worst_row.get("serving_channel_width_mhz", ""), suffix=" MHz")
        interferer_channel = self.format_report_value(worst_row.get("strongest_interferer_channel", ""))
        interferer_width = self.format_report_value(
            worst_row.get("strongest_interferer_channel_width_mhz", ""),
            suffix=" MHz"
        )
        interferer_dbm = self.format_report_value(worst_row.get("strongest_interferer_dbm", ""), suffix=" dBm")

        dialog = self.create_modal_dialog(self.tr("interference_summary_title"))

        frame = ttk.Frame(dialog, padding=18)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            frame,
            text=self.tr("interference_summary_title"),
            font=("TkDefaultFont", 12, "bold")
        ).pack(anchor="w")

        details = ttk.Frame(frame)
        details.pack(fill=tk.X, pady=(14, 0))
        rows = [
            (self.tr("interference_summary_band"), band_label),
            (self.tr("interference_summary_max_risk"), f"{risk_value:.1f}%"),
            (self.tr("interference_summary_point"), f"{x_value}, {y_value}"),
            (self.tr("interference_summary_serving_ap"), worst_row.get("serving_bssid", "-")),
            (self.tr("interference_summary_serving_channel"), serving_channel),
            (self.tr("interference_summary_serving_width"), serving_width),
            (self.tr("interference_summary_interferer"), worst_row.get("strongest_interferer_bssid", "-")),
            (self.tr("interference_summary_interferer_ssid"), worst_row.get("strongest_interferer_ssid", "-")),
            (self.tr("interference_summary_interferer_channel"), interferer_channel),
            (self.tr("interference_summary_interferer_width"), interferer_width),
            (self.tr("interference_summary_interferer_dbm"), interferer_dbm),
        ]
        for row_index, (label, value) in enumerate(rows):
            ttk.Label(details, text=label).grid(row=row_index, column=0, sticky="w", pady=2, padx=(0, 18))
            ttk.Label(details, text=str(value or "-")).grid(row=row_index, column=1, sticky="w", pady=2)

        ttk.Separator(frame).pack(fill=tk.X, pady=(14, 12))
        ttk.Label(
            frame,
            text=self.tr("interference_summary_diagnosis"),
            font=("TkDefaultFont", 10, "bold")
        ).pack(anchor="w")
        ttk.Label(
            frame,
            text=self.get_interference_diagnosis(worst_row),
            wraplength=520,
            justify=tk.LEFT
        ).pack(anchor="w", pady=(4, 0))

        quality = get_interference_data_quality(risk_df)
        ttk.Separator(frame).pack(fill=tk.X, pady=(14, 12))
        ttk.Label(
            frame,
            text=self.tr("interference_quality_title"),
            font=("TkDefaultFont", 10, "bold")
        ).pack(anchor="w")
        ttk.Label(
            frame,
            text=self.tr(
                "interference_quality_width_coverage",
                available=quality["available"],
                total=quality["total"],
                percent=quality["percent"]
            )
        ).pack(anchor="w", pady=(4, 0))
        quality_style = WARNING if quality["percent"] < 70 else SUCCESS
        ttk.Label(
            frame,
            text=self.get_interference_quality_message(quality, band_label),
            bootstyle=quality_style,
            wraplength=520,
            justify=tk.LEFT
        ).pack(anchor="w", pady=(4, 0))

        ttk.Separator(frame).pack(fill=tk.X, pady=(14, 12))
        ttk.Label(
            frame,
            text=self.tr("files_created", paths=f"{output_file}\n{report_file}"),
            wraplength=560,
            justify=tk.LEFT
        ).pack(anchor="w")

        buttons = ttk.Frame(frame)
        buttons.pack(fill=tk.X, pady=(16, 0))
        ttk.Button(buttons, text="OK", command=dialog.destroy, bootstyle=PRIMARY).pack(side=tk.RIGHT)
        dialog.bind("<Escape>", lambda _event: dialog.destroy())
        self.center_dialog(dialog)

    def get_interference_quality_message(self, quality, band_label):
        if quality["percent"] >= 70:
            return self.tr("interference_quality_good")

        if band_label == "5 GHz":
            return self.tr("interference_quality_warning_5ghz")

        return self.tr("interference_quality_warning")

    def get_interference_diagnosis(self, row):
        risk = float(row.get("risk", 0) or 0)
        serving_channel = row.get("serving_channel", "")
        interferer_channel = row.get("strongest_interferer_channel", "")
        interferer_dbm = row.get("strongest_interferer_dbm", "")
        serving_width = self.parse_optional_float(row.get("serving_channel_width_mhz", ""))
        interferer_width = self.parse_optional_float(row.get("strongest_interferer_channel_width_mhz", ""))
        overlap = self.parse_optional_float(row.get("strongest_interferer_overlap", ""))

        if risk < 30:
            return self.tr("interference_diagnosis_low")

        try:
            same_channel = float(serving_channel) == float(interferer_channel)
        except (TypeError, ValueError):
            same_channel = False

        try:
            strong_interferer = float(interferer_dbm) >= -67
        except (TypeError, ValueError):
            strong_interferer = False

        if same_channel and strong_interferer:
            return self.tr("interference_diagnosis_same_channel_strong")
        if same_channel:
            return self.tr("interference_diagnosis_same_channel")
        if overlap and overlap > 0 and ((serving_width and serving_width > 20) or (interferer_width and interferer_width > 20)):
            return self.tr("interference_diagnosis_wide_channel")
        if strong_interferer:
            return self.tr("interference_diagnosis_strong")

        return self.tr("interference_diagnosis_nearby")

    def parse_optional_float(self, value):
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None

        if np.isnan(number):
            return None

        return number

    def format_report_value(self, value, suffix=""):
        try:
            number = float(value)
        except (TypeError, ValueError):
            return str(value or "-")

        if np.isnan(number):
            return "-"

        if number.is_integer():
            return f"{int(number)}{suffix}"

        return f"{number:.1f}{suffix}"

    def get_current_map_config(self):
        smoothing_sigma, max_distance_px = self.get_heatmap_settings()
        return MapConfig(
            ssid=self.ssid_var.get().strip(),
            band=self.band_var.get(),
            map_type=self.map_type_var.get(),
            interference_mode=self.interference_mode_var.get(),
            interpolation=self.interpolation_var.get(),
            aggregation=self.aggregation_var.get(),
            color_scale=self.color_scale_var.get(),
            point_label_mode=self.point_label_mode_var.get(),
            ap_group_filter=getattr(self, "live_ap_filter_label_map", {}).get(self.ap_group_filter_var.get(), ""),
            usable_only=bool(self.usable_only_var.get()),
            smoothing_sigma=smoothing_sigma,
            max_distance_px=max_distance_px,
        ).normalized()

    def apply_map_config_to_controls(self, config):
        self.ssid_var.set(config.ssid)
        self.band_var.set(config.band)
        self.map_type_var.set(config.map_type)
        self.sync_live_map_type_choice()
        self.interference_mode_var.set(config.interference_mode)
        self.interpolation_var.set(config.interpolation)
        self.aggregation_var.set(config.aggregation)
        self.color_scale_var.set(config.color_scale)
        self.point_label_mode_var.set(config.point_label_mode)
        self.usable_only_var.set(config.usable_only)
        self.smoothing_var.set(config.smoothing_sigma)
        self.distance_var.set(self.distance_display_from_px(config.max_distance_px))
        self.update_distance_labels()

    def get_reference_label_terms(self):
        return {
            "channel": self.tr("reference_channel"),
            "width": self.tr("reference_width"),
            "ap": self.tr("reference_ap"),
            "delta": self.tr("reference_delta"),
            "risk": self.tr("reference_risk"),
            "serving_channel": self.tr("reference_serving_channel"),
            "interferer_channel": self.tr("reference_interferer_channel"),
            "channel_short": "CH",
        }

    def get_interference_mode_label(self, config=None):
        interference_mode = config.interference_mode if config else self.interference_mode_var.get()
        if interference_mode == "all":
            return self.tr("interference_mode_all")

        return self.tr("interference_mode_intra_ssid")

    def ensure_saved_for_heatmap(self):
        if not self.session.csv_file:
            messagebox.showinfo(
                self.tr("save_required_title"),
                self.tr("save_required"),
                parent=self.root
            )

        if self.session.dirty or not self.session.csv_file:
            return self.save_survey()

        return True

    def build_heatmap_output_path(self, ssid, band):
        csv_path = Path(self.session.csv_file)
        band_token = {
            "all": "all",
            "2.4": "2.4ghz",
            "5": "5ghz",
            "interference_2.4": "interference_2.4ghz",
            "interference_5": "interference_5ghz",
            "channels_all": "channels_all",
            "channels_2.4": "channels_2.4ghz",
            "channels_5": "channels_5ghz",
            "dominant_all": "dominant_all",
            "dominant_2.4": "dominant_2.4ghz",
            "dominant_5": "dominant_5ghz"
        }.get(band, sanitize_filename(band))
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = (
            f"{sanitize_filename(csv_path.stem)}_"
            f"{sanitize_filename(ssid)}_"
            f"{band_token}_{timestamp}.png"
        )
        return str(csv_path.with_name(file_name))

    def build_interference_report_output_path(self, heatmap_output_file):
        output_path = Path(heatmap_output_file)
        return str(output_path.with_name(f"{output_path.stem}_report.csv"))

    def build_dominant_ap_report_output_path(self, heatmap_output_file):
        output_path = Path(heatmap_output_file)
        return str(output_path.with_name(f"{output_path.stem}_report.csv"))

    def save_interference_report(self, risk_df, report_file):
        report_df = risk_df.copy()
        report_df["diagnosis"] = report_df.apply(self.get_interference_diagnosis, axis=1)
        report_columns = [
            "timestamp",
            "x",
            "y",
            "ssid",
            "serving_ap_group",
            "serving_bssid",
            "serving_channel",
            "serving_channel_width_mhz",
            "serving_signal_dbm",
            "serving_samples_seen",
            "serving_samples_total",
            "serving_scan_confidence",
            "risk",
            "interferer_count",
            "same_physical_ap_ignored_count",
            "interfering_bssids",
            "strongest_interferer_ssid",
            "strongest_interferer_ap_group",
            "strongest_interferer_bssid",
            "strongest_interferer_channel",
            "strongest_interferer_channel_width_mhz",
            "strongest_interferer_dbm",
            "strongest_interferer_samples_seen",
            "strongest_interferer_samples_total",
            "strongest_interferer_scan_confidence",
            "strongest_interferer_overlap",
            "diagnosis",
        ]
        existing_columns = [column for column in report_columns if column in report_df.columns]
        report_df[existing_columns].to_csv(report_file, index=False, encoding="utf-8")

    def save_dominant_ap_report(self, dominant_df, report_file):
        report_df = dominant_df.copy()
        report_df["roaming_status"] = report_df["roaming_overlap"].map({
            True: "roaming_overlap",
            False: "stable"
        })
        report_columns = [
            "timestamp",
            "x",
            "y",
            "ssid",
            "dominant_ap_group",
            "dominant_bssid",
            "dominant_signal_dbm",
            "dominant_samples_seen",
            "dominant_samples_total",
            "dominant_scan_confidence",
            "dominant_channel",
            "dominant_channel_width_mhz",
            "second_ap_group",
            "second_bssid",
            "second_signal_dbm",
            "second_samples_seen",
            "second_samples_total",
            "second_scan_confidence",
            "second_channel",
            "second_channel_width_mhz",
            "delta_db",
            "roaming_status",
        ]
        existing_columns = [column for column in report_columns if column in report_df.columns]
        report_df[existing_columns].to_csv(report_file, index=False, encoding="utf-8")

    def get_color_scale_limits(self, grid_z, config=None):
        color_scale = config.color_scale if config else self.color_scale_var.get()
        if color_scale != "auto":
            return -90, -35

        valid_values = grid_z[np.isfinite(grid_z)]

        if len(valid_values) == 0:
            return -90, -35

        vmin = float(np.percentile(valid_values, 5))
        vmax = float(np.percentile(valid_values, 95))

        if vmax - vmin < 10:
            center = (vmin + vmax) / 2
            return center - 5, center + 5

        return vmin, vmax

    def open_csv(self):
        if self.session.csv_file and os.path.exists(self.session.csv_file):
            os.startfile(self.session.csv_file)
        else:
            messagebox.showwarning(self.tr("warning"), self.tr("csv_not_saved"))

    def new_survey(self):
        if not self.confirm_switch_survey():
            return

        self.load_survey_session(None)
        self.status_var.set(self.tr("active_survey", name=self.session_display_name()))

    def open_survey(self):
        if not self.confirm_switch_survey():
            return

        csv_file = open_existing_survey_file(self.root)
        if not csv_file:
            return

        try:
            self.load_survey_session(csv_file)
        except SurveyFormatError as exc:
            self.show_survey_format_error(exc)

    def confirm_switch_survey(self):
        if not self.session.dirty:
            return True

        choice = messagebox.askyesnocancel(
            self.tr("unsaved_changes_title"),
            self.tr("unsaved_changes"),
            parent=self.root
        )

        if choice is None:
            return False

        if choice:
            return self.save_survey()

        return True

    def load_survey_session(self, csv_file):
        self.session = SurveySession(csv_file)
        self.csv_file = self.session.csv_file
        self.image_path = None
        self.bg_image = None
        self.tk_image = None
        self.canvas_image = None
        self.point_markers.clear()
        self.selected_point_id = None
        self.highlight_item_id = None
        self.last_good_scan = []
        self.last_scan_backend_used = "-"
        self.relevant_ssids = self.load_relevant_ssids()
        self.known_ssids = self.load_known_ssids()
        self.live_preview_image = None
        self.live_preview_tk_image = None
        self.live_point_infos = []
        self.live_scale_payload = None
        self.live_image_transform = None
        self.canvas.delete("all")
        self.live_canvas.delete("all")
        self.update_live_scale_bar()
        self.map_var.set(self.tr("no_map"))
        self.last_scan_var.set(self.tr("no_scan"))
        self.best_scan_var.set("-")
        self.scan_filter_var.set("-")
        self.scan_quality_var.set(self.tr("scan_quality_empty"))
        self.scan_backend_used_var.set(self.tr("backend_used_empty"))
        self.live_status_var.set(self.tr("live_preview_empty"))
        self.refresh_points_state()
        self.refresh_ssid_options()
        self.update_saved_network_label()
        self.refresh_session_labels()
        self.load_saved_plan()

    def show_survey_format_error(self, error):
        key = str(error)
        message_key = {
            "raw_scan_file": "raw_scan_file_selected",
            "invalid_raw_scan_format": "invalid_raw_scan_format",
            "missing_survey_file": "invalid_survey_format",
        }.get(key, "invalid_survey_format")
        messagebox.showerror(
            self.tr("invalid_survey_title"),
            self.tr(message_key),
            parent=self.root
        )

    def save_survey(self):
        csv_file = self.session.csv_file

        if not csv_file:
            csv_file = save_survey_file_as(self.root)

        if not csv_file:
            return False

        self.session.save(csv_file)
        self.csv_file = self.session.csv_file
        self.refresh_session_labels()
        self.status_var.set(self.tr("survey_saved", name=self.session.display_name))
        return True

    def on_close(self):
        if not self.confirm_switch_survey():
            return

        self.shutdown_live_preview_worker()
        self.root.destroy()

    def shutdown_live_preview_worker(self):
        self.live_preview_task_id += 1
        if self.live_update_after_id is not None:
            self.root.after_cancel(self.live_update_after_id)
            self.live_update_after_id = None
        if self.live_quality_after_id is not None:
            self.root.after_cancel(self.live_quality_after_id)
            self.live_quality_after_id = None
        if hasattr(self, "live_preview_executor"):
            self.live_preview_executor.shutdown(wait=False, cancel_futures=True)

    def refresh_ssid_options(self, ssids=None):
        if ssids is None:
            ssids = self.session.get_ssids()

        if hasattr(self, "ssid_combo") and self.ssid_combo.winfo_exists():
            self.ssid_combo["values"] = ssids
        if hasattr(self, "live_ssid_combo") and self.live_ssid_combo.winfo_exists():
            self.live_ssid_combo["values"] = ssids

        if ssids and self.ssid_var.get() not in ssids:
            self.ssid_var.set(ssids[0])
        elif not ssids:
            self.ssid_var.set("")

        if hasattr(self, "live_ap_filter_combo"):
            self.refresh_live_ap_filter_options()

    def get_heatmap_settings(self):
        try:
            smoothing_sigma = max(0.0, float(self.smoothing_var.get()))
        except (tk.TclError, ValueError):
            smoothing_sigma = HEATMAP_SMOOTHING_SIGMA
            self.smoothing_var.set(smoothing_sigma)

        try:
            max_distance_px = self.distance_px_from_display(self.distance_var.get())
        except (tk.TclError, ValueError):
            max_distance_px = HEATMAP_MAX_DISTANCE_PX
            self.distance_var.set(self.distance_display_from_px(max_distance_px))

        return smoothing_sigma, max_distance_px
