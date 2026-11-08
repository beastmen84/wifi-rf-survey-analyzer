"""Final survey-analysis step: background analysis, evidence and report export."""

from copy import deepcopy
from pathlib import Path

from PySide6.QtCore import QObject, QThread, QTimer, Signal, Slot, Qt
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QDoubleSpinBox, QSpinBox, QLineEdit, QComboBox, QSplitter,
    QListWidget, QListWidgetItem, QTextBrowser, QMessageBox, QToolButton, QFrame, QScrollArea, QSizePolicy)

from advisor.engine import analyze_survey
from advisor.models import AnalysisProfile, analysis_fingerprint
from advisor.presentation import wording, finding_html, wrap_html
from advisor.recommendations import sections, recommendation_kind, empty_recommendation_key
from exporting.analysis_report import export_analysis_report
from qt_ui.qt_live_map import load_floorplan_image
from survey.plan_drawing import drawing_geometry, render_plan_drawing
from survey.plan_layers import PLAN_LAYERS_KEY, visible_layers, read_layers
from survey.plan_labels import drawing_labels
from survey.plan_annotations import drawing_annotations
from qt_ui.qt_theme import QT_THEMES
from qt_ui.qt_windowing import get_centered_save_file_name
from app_core.logging import log_exception
from wifi.band import get_row_band


class AnalysisWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, context):
        super().__init__()
        self.context = context

    @Slot()
    def run(self):
        try:
            self.finished.emit(analyze_survey(**self.context))
        except Exception as error:
            log_exception("survey analysis failed", error, logger_name="analysis")
            self.failed.emit(str(error))


class AnalysisView(QWidget):
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.report = None
        self.thread = self.worker = None
        self.pending = False
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(180)
        self.timer.timeout.connect(self.update_analysis)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(app.spx(18), app.spx(14), app.spx(18), app.spx(12))
        self.heading = QLabel()
        self.heading.setObjectName("sectionTitle")
        heading_row = QHBoxLayout()
        heading_row.addWidget(self.heading, 1)
        self.run_button, self.export_button = QPushButton(), QPushButton()
        self.run_button.clicked.connect(self.update_analysis)
        self.export_button.clicked.connect(self.export_report)
        heading_row.addWidget(self.run_button)
        heading_row.addWidget(self.export_button)
        layout.addLayout(heading_row)
        self.hint = QLabel()
        self.hint.setWordWrap(True)
        self.hint.setObjectName("mutedText")
        layout.addWidget(self.hint)
        target_row = QHBoxLayout()
        self.target_label, self.confidence_label, self.minimum_label = QLabel(), QLabel(), QLabel()
        self.target = QDoubleSpinBox()
        self.target.setRange(-95, -45)
        self.target.setDecimals(0)
        self.target.setSuffix(" dBm")
        self.target.setValue(-70)
        self.target.setMinimumWidth(app.spx(150))
        self.confidence = QDoubleSpinBox()
        self.confidence.setRange(10, 100)
        self.confidence.setSingleStep(5)
        self.confidence.setDecimals(0)
        self.confidence.setSuffix("%")
        self.confidence.setValue(60)
        self.confidence.setMinimumWidth(app.spx(130))
        self.minimum = QSpinBox()
        self.minimum.setRange(2, 20)
        self.minimum.setValue(3)
        self.minimum.setMinimumWidth(app.spx(130))
        target_row.addWidget(self.target_label)
        target_row.addWidget(self.target)
        self.target_hint = QLabel()
        self.target_hint.setObjectName("mutedText")
        self.target_hint.setWordWrap(True)
        target_row.addWidget(self.target_hint, 1)
        self.settings_button = QToolButton()
        self.settings_button.setCheckable(True)
        self.settings_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.settings_button.setArrowType(Qt.ArrowType.RightArrow)
        self.settings_button.toggled.connect(self.toggle_settings)
        target_row.addWidget(self.settings_button)
        layout.addLayout(target_row)
        self.settings_summary = QLabel()
        self.settings_summary.setWordWrap(True)
        self.settings_summary.setObjectName("mutedText")
        layout.addWidget(self.settings_summary)
        self.policy_notice = QLabel()
        self.policy_notice.setWordWrap(True)
        layout.addWidget(self.policy_notice)
        self.settings_panel = QFrame()
        self.settings_panel.setObjectName("analysisSettings")
        advanced = QVBoxLayout(self.settings_panel)
        controls = QGridLayout()
        for index, (label, control) in enumerate(((self.confidence_label, self.confidence), (self.minimum_label, self.minimum))):
            controls.addWidget(label, 0, index * 2)
            controls.addWidget(control, 0, index * 2 + 1)
            control.valueChanged.connect(self.inputs_changed)
        self.target.valueChanged.connect(self.inputs_changed)
        advanced.addLayout(controls)
        self.policy_label = QLabel()
        self.policy_label.setWordWrap(True)
        advanced.addWidget(self.policy_label)
        policy = QHBoxLayout()
        self.channel_edits = {}
        for band, text in (("2.4", "1, 6, 11"), ("5", ""), ("6", "")):
            policy.addWidget(QLabel(band + " GHz"))
            edit = QLineEdit(text)
            edit.setMaxLength(256)
            edit.textChanged.connect(self.inputs_changed)
            self.channel_edits[band] = edit
            policy.addWidget(edit)
        advanced.addLayout(policy)
        self.policy_hint = QLabel()
        self.policy_hint.setWordWrap(True)
        self.policy_hint.setObjectName("mutedText")
        advanced.addWidget(self.policy_hint)
        self.settings_scroll = QScrollArea()
        self.settings_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.settings_scroll.setWidgetResizable(True)
        self.settings_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.settings_scroll.setMaximumHeight(app.spx(170))
        self.settings_scroll.setWidget(self.settings_panel)
        layout.addWidget(self.settings_scroll)
        self.settings_panel.hide()
        self.settings_scroll.hide()
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)
        self.quality_panel = QFrame()
        self.quality_panel.setObjectName("recommendationQuality")
        quality_row = QHBoxLayout(self.quality_panel)
        self.quality_summary = QLabel()
        self.quality_summary.setTextFormat(Qt.TextFormat.PlainText)
        self.quality_summary.setWordWrap(True)
        quality_row.addWidget(self.quality_summary, 1)
        quality_actions = QHBoxLayout()
        self.quality_button, self.prerequisites_button = QPushButton(), QPushButton()
        self.quality_button.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        self.prerequisites_button.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        self.quality_button.clicked.connect(app.open_quality_dashboard)
        self.prerequisites_button.clicked.connect(lambda: self.filter.setCurrentIndex(self.filter.findData("prerequisites")))
        quality_actions.addWidget(self.quality_button)
        quality_actions.addWidget(self.prerequisites_button)
        quality_row.addLayout(quality_actions)
        layout.addWidget(self.quality_panel)
        self.filter = QComboBox()
        self.filter.currentIndexChanged.connect(self.render_findings)
        layout.addWidget(self.filter)
        self.order_hint = QLabel()
        self.order_hint.setWordWrap(True)
        self.order_hint.setObjectName("mutedText")
        layout.addWidget(self.order_hint)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        self.findings = QListWidget()
        self.findings.setWordWrap(True)
        self.findings.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.findings.setMinimumWidth(app.spx(260))
        self.findings.currentRowChanged.connect(self.render_selected)
        splitter.addWidget(self.findings)
        self.detail = QTextBrowser()
        self.detail.setOpenLinks(False)
        self.detail.setOpenExternalLinks(False)
        self.detail.anchorClicked.connect(self.focus_evidence)
        detail_panel = QWidget()
        detail_layout = QVBoxLayout(detail_panel)
        detail_layout.setContentsMargins(0, 0, 0, 0)
        detail_layout.addWidget(self.detail, 1)
        self.evidence_button = QToolButton()
        self.evidence_button.setCheckable(True)
        self.evidence_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.evidence_button.toggled.connect(self.toggle_evidence)
        detail_layout.addWidget(self.evidence_button)
        splitter.addWidget(detail_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter, 1)
        self.retranslate()

    @property
    def busy(self):
        return self.thread is not None

    def text(self, key, **kwargs):
        return self.app.tr("advisor_" + key, **kwargs)

    def toggle_settings(self, expanded):
        self.size_settings()
        self.settings_panel.setVisible(expanded)
        self.settings_scroll.setVisible(expanded)
        self.settings_button.setArrowType(Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow)

    def size_settings(self):
        self.settings_scroll.setMaximumHeight(max(self.app.spx(85), min(self.app.spx(170), int(self.height() * .22))))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "settings_scroll"):
            self.size_settings()

    def refresh_settings_summary(self):
        channels = " · ".join(band + " GHz: " + (edit.text().strip() or self.text("review_only"))
            for band, edit in self.channel_edits.items())
        self.settings_summary.setText(self.app.tr("report_settings_summary",
            confidence=f"{self.confidence.value():g}", points=self.minimum.value()))
        self.settings_summary.setToolTip(channels)
        observed = {get_row_band(row) for row in self.app.session.rows} if self.app.session else set()
        missing = [band for band in ("5", "6") if band in observed and not self.channel_edits[band].text().strip()]
        self.policy_notice.setText(self.app.tr("report_channel_missing", bands=" / ".join(missing)) if missing else "")
        self.policy_notice.setVisible(bool(missing))

    def profile(self):
        def channels(band):
            text = self.channel_edits[band].text().replace(";", ",").replace(" ", ",")
            return tuple(sorted({int(value) for value in text.split(",") if value}))
        return AnalysisProfile(self.target.value(), self.confidence.value() / 100, self.minimum.value(),
            channels("2.4"), channels("5"), channels("6"))

    def context(self):
        session = self.app.session
        if session is None:
            return None
        metadata = deepcopy(session.metadata)
        if PLAN_LAYERS_KEY in metadata:
            try:
                # Presentation changes are not changes to the RF evidence.
                layers = read_layers(metadata)["layers"]
                metadata[PLAN_LAYERS_KEY] = [(layer["id"], layer["drawing"])
                    for layer in sorted(layers, key=lambda layer: layer["id"])]
            except (ValueError, TypeError, KeyError):
                pass  # Retain malformed input in the fingerprint; drawing UI reports it.
        path = Path(str(metadata.get("map_file", "")))
        try:
            stat = path.stat() if metadata.get("map_file") and path.is_file() else None
            metadata["_plan_file_state"] = (stat.st_size, stat.st_mtime_ns) if stat else None
        except OSError:
            metadata["_plan_file_state"] = None
        return dict(rows=session.rows, raw_rows=session.raw_scan_rows, groups=session.get_ap_groups(),
            relevant_ssids=tuple(sorted(self.app.relevant_ssids)), profile=self.profile(),
            px_per_meter=self.app.get_px_per_meter(), survey_name=self.app.session_display_name(),
            context_metadata=metadata)

    @staticmethod
    def fingerprint(context):
        return analysis_fingerprint(context["rows"], context["raw_rows"], context["groups"],
            context["relevant_ssids"], context["px_per_meter"], context["profile"], context["survey_name"],
            context["context_metadata"])

    def inputs_changed(self, *_args):
        self.refresh_settings_summary()
        self.export_button.setEnabled(False)
        self.summary.setText(self.text("stale"))
        self.findings.setEnabled(False)
        self.evidence_button.setEnabled(False)
        self.quality_summary.setText(self.text("stale"))
        self.pending = True
        if self.app.tabs.currentIndex() == 2:
            self.timer.start()

    def sync_state(self):
        self.refresh_settings_summary()
        enabled = self.app.session is not None and not self.app.scan_in_progress
        self.run_button.setEnabled(enabled and not self.busy)
        self.quality_button.setEnabled(enabled)
        current = enabled and self.report_is_current()
        self.findings.setEnabled(current)
        self.evidence_button.setEnabled(current and self.findings.currentItem() is not None)
        self.quality_panel.setVisible(self.report is not None and self.app.session is not None)
        if not enabled:
            self.export_button.setEnabled(False)
        if self.app.session is None:
            self.report = None
            self.findings.clear()
            self.detail.clear()
            self.summary.setText(self.text("empty"))
            self.evidence_button.setEnabled(False)
        elif self.app.tabs.currentIndex() == 2 and enabled:
            self.export_button.setEnabled(False)
            self.summary.setText(self.text("stale") if self.report else self.text("busy"))
            self.timer.start()

    def update_analysis(self):
        self.timer.stop()
        if self.app.session is None or self.app.scan_in_progress:
            self.sync_state()
            return
        if self.busy:
            self.pending = True
            return
        try:
            context = self.context()
            if self.report is not None and self.report.fingerprint == self.fingerprint(context):
                self.pending = False
                self.render_summary()
                self.toggle_evidence(self.evidence_button.isChecked())
                self.export_button.setEnabled(True)
                return
        except ValueError:
            self.summary.setText(self.text("invalid_profile"))
            self.export_button.setEnabled(False)
            return
        self.pending = False
        self.summary.setText(self.text("busy"))
        self.quality_summary.setText(self.text("busy"))
        self.findings.setEnabled(False)
        self.evidence_button.setEnabled(False)
        self.export_button.setEnabled(False)
        self.run_button.setEnabled(False)
        self.thread = QThread(self)
        self.worker = AnalysisWorker(deepcopy(context))
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.accept_report)
        self.worker.failed.connect(self.fail_report)
        self.worker.finished.connect(self.thread.quit)
        self.worker.failed.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.failed.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.cleanup_thread)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    def accept_report(self, report):
        try:
            context = self.context()
            if context is None or report.fingerprint != self.fingerprint(context):
                self.pending = context is not None
                return
        except ValueError:
            self.pending = True
            return
        self.report = report
        self.render_findings()
        self.render_summary()

    def fail_report(self, message):
        self.summary.setText(self.app.tr("error") + ": " + message)
        self.export_button.setEnabled(False)

    def cleanup_thread(self):
        self.thread = self.worker = None
        self.run_button.setEnabled(self.app.session is not None and not self.app.scan_in_progress)
        self.export_button.setEnabled(self.report_is_current() and not self.app.scan_in_progress)
        if self.pending and self.app.tabs.currentIndex() == 2:
            self.timer.start()

    def render_summary(self):
        if self.report:
            self.hint.hide()
            grouped = sections(self.report)
            current = self.report_is_current() and not self.app.scan_in_progress
            self.findings.setEnabled(current)
            self.evidence_button.setEnabled(current and self.findings.currentItem() is not None)
            self.summary.setText(self.text("summary", points=len(self.report.points),
                checks=len(grouped.prerequisites), observations=len(grouped.observations), actions=len(grouped.recommendations)))
            self.quality_panel.show()
            self.quality_summary.setText(self.text("quality_summary", checks=len(grouped.prerequisites),
                points=grouped.affected_points) if grouped.prerequisites else self.text("quality_ready"))
            if not current:
                self.quality_summary.setText(self.text("stale"))
            self.prerequisites_button.setVisible(bool(grouped.prerequisites))
            palette = QT_THEMES[self.app.theme]
            border = palette["metric_warning"] if grouped.prerequisites else palette["border"]
            self.quality_panel.setStyleSheet(f"QFrame#recommendationQuality {{background:{palette['panel_alt']};border:1px solid {border};border-radius:6px;}}")

    def report_is_current(self):
        try:
            context = self.context()
            return self.report is not None and context is not None and self.report.fingerprint == self.fingerprint(context)
        except ValueError:
            return False

    def render_findings(self, *_args):
        current = self.findings.currentItem()
        previous = current.data(Qt.ItemDataRole.UserRole).finding_id if current else None
        self.findings.clear()
        if self.report is None:
            self.quality_panel.hide()
            self.order_hint.hide()
            self.hint.show()
            return
        grouped = sections(self.report)
        current_report = self.report_is_current() and not self.app.scan_in_progress
        self.findings.setEnabled(current_report)
        mode = self.filter.currentData() or "recommendations"
        counts = {"recommendations": len(grouped.recommendations), "prerequisites": len(grouped.prerequisites),
                  "observations": len(grouped.observations), "everything": len(self.report.findings)}
        for index in range(self.filter.count()):
            key = self.filter.itemData(index)
            self.filter.setItemText(index, self.text(key) + f" ({counts[key]})")
        ordered = (*grouped.recommendations, *grouped.prerequisites, *grouped.observations)
        selected = ordered if mode == "everything" else getattr(grouped, mode)
        ranks = {finding.finding_id: rank for rank, finding in enumerate(grouped.recommendations, 1)}
        prerequisite_ids = {finding.finding_id for finding in grouped.prerequisites}
        for finding in selected:
            text = wording(finding, self.report, self.app.language)
            rank = ranks.get(finding.finding_id)
            prefix = f"{rank}. " if rank else ""
            classification = self.text(recommendation_kind(finding)) if rank else self.text("prerequisites" if finding.finding_id in prerequisite_ids else "observations")
            item = QListWidgetItem(prefix + text + "\n" + classification + " · " + self.text("confidence") + ": " + self.text(finding.confidence))
            item.setToolTip(text)
            item.setData(Qt.ItemDataRole.UserRole, finding)
            self.findings.addItem(item)
        self.order_hint.setVisible(mode in ("recommendations", "everything"))
        if not current_report:
            self.detail.setHtml(wrap_html(self.text("stale"), QT_THEMES[self.app.theme]))
            self.evidence_button.setEnabled(False)
            return
        if self.findings.count():
            row = next((i for i in range(self.findings.count()) if self.findings.item(i).data(Qt.ItemDataRole.UserRole).finding_id == previous), 0)
            self.findings.setCurrentRow(row)
        else:
            message = empty_recommendation_key(grouped) if mode == "recommendations" else "section_empty"
            self.detail.setHtml(wrap_html(self.text(message), QT_THEMES[self.app.theme]))

    def render_selected(self, _row=None):
        self.evidence_button.blockSignals(True)
        self.evidence_button.setChecked(False)
        self.evidence_button.blockSignals(False)
        self.toggle_evidence(False)

    def toggle_evidence(self, expanded):
        self.evidence_button.setArrowType(Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow)
        self.evidence_button.setText(self.text("hide_support" if expanded else "show_support"))
        item = self.findings.currentItem()
        current = item is not None and self.report_is_current() and not self.app.scan_in_progress
        self.evidence_button.setEnabled(current)
        if current:
            finding = item.data(Qt.ItemDataRole.UserRole)
            self.detail.setHtml(wrap_html(finding_html(finding, self.report, self.app.language, True,
                                         expanded=expanded, compact=True),
                                         QT_THEMES[self.app.theme]))
        elif item and self.report:
            self.detail.setHtml(wrap_html(self.text("stale"), QT_THEMES[self.app.theme]))

    def focus_evidence(self, url):
        if url.scheme() != "point" or self.report is None or self.app.scan_in_progress:
            return
        if not self.report_is_current():
            self.inputs_changed()
            return
        try:
            index = int(url.path())
            if not 0 <= index < len(self.report.points):
                return
            point = self.report.points[index]
        except (ValueError, IndexError):
            return
        if not self.app.floorplan_view.has_floorplan():
            self.app.status.showMessage(self.app.tr("load_plan_first"))
            return
        self.app.tabs.setCurrentIndex(0)
        self.app.select_point_in_table(vars(point))
        self.app.floorplan_view.focus_on(point.x, point.y)

    def export_report(self):
        if self.app.scan_in_progress:
            return False
        try:
            context = self.context()
            if self.busy or self.report is None or context is None or self.report.fingerprint != self.fingerprint(context):
                self.update_analysis()
                return False
            path = Path(self.app.session.csv_file or "survey.csv").with_suffix(".analysis.html")
            output, _selected_filter = get_centered_save_file_name(self.app, self.text("export"), str(path),
                self.app.tr("report_html_filter"))
            if not output:
                return False
            if Path(output).suffix.lower() != ".html":
                output += ".html"
            image = None
            plan = self.app.session.metadata.get("map_file", "")
            if plan and Path(plan).is_file():
                image = load_floorplan_image(plan)
                lines, curves = drawing_geometry(self.app.session.metadata)
                image = render_plan_drawing(image, lines, drawing_labels(self.app.session.metadata), curves, drawing_annotations(self.app.session.metadata), layers=visible_layers(self.app.session.metadata))
            # A modal file dialog can process survey events: validate again.
            if self.report.fingerprint != self.fingerprint(self.context()):
                self.inputs_changed()
                return False
            export_analysis_report(self.report, output, self.app.language, image)
            self.app.status.showMessage(self.app.tr("file_created", path=output))
            return True
        except Exception as error:
            log_exception("analysis export failed", error, logger_name="analysis")
            QMessageBox.warning(self.app, self.app.tr("error"), str(error))
            return False

    def retranslate(self):
        self.quality_button.setText(self.text("quality_open"))
        self.prerequisites_button.setText(self.text("show_prerequisites"))
        self.order_hint.setText(self.text("order_hint"))
        self.heading.setToolTip(self.text("hint"))
        self.settings_button.setText(self.app.tr("report_settings"))
        self.target_hint.setText(self.app.tr("report_target_hint"))
        self.refresh_settings_summary()
        for label, key in ((self.heading, "title"), (self.hint, "hint"), (self.target_label, "target"),
                (self.confidence_label, "min_confidence"), (self.minimum_label, "minimum"),
                (self.policy_label, "policy"), (self.policy_hint, "policy_hint"),
                (self.run_button, "run"), (self.export_button, "export")):
            label.setText(self.text(key))
        previous = self.filter.currentData()
        self.filter.blockSignals(True)
        self.filter.clear()
        for key in ("recommendations", "prerequisites", "observations", "everything"):
            self.filter.addItem(self.text(key), key)
        self.filter.setCurrentIndex(max(0, self.filter.findData(previous)))
        self.filter.blockSignals(False)
        self.render_findings()
        if self.report:
            self.render_summary()
        else:
            self.summary.setText(self.text("empty"))
        self.toggle_evidence(self.evidence_button.isChecked())
        self.export_button.setEnabled(self.report_is_current() and not self.busy and not self.app.scan_in_progress)
