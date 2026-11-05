"""Compact plan-text editor with a live, font-independent outline preview."""
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (QCheckBox, QColorDialog, QComboBox, QDialog, QDialogButtonBox,
    QDoubleSpinBox, QFontComboBox, QFormLayout, QGraphicsScene, QGraphicsView,
    QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QVBoxLayout)

from qt_ui.scaling import widget_px
from survey.plan_label_rendering import build_label, label_item


class GlyphPreview(QGraphicsView):
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not self.sceneRect().isEmpty():
            self.fitInView(self.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)


class PlanTextDialog(QDialog):
    def __init__(self, owner, previous=None):
        super().__init__(owner)
        self.owner = owner
        tr = owner.tr
        self.setWindowTitle(tr("plan_text_title"))
        self.resize(widget_px(owner, 540), widget_px(owner, 570))
        previous = previous or dict(text="", family="Segoe UI", size=24, bold=False, italic=False,
            color="#263238", outline_color="#ffffff", outline_width=0, alignment="left")
        self.colors = {key: previous[key] for key in ("color", "outline_color")}
        layout = QVBoxLayout(self)
        layout.setSpacing(widget_px(owner, 10))
        self.content = QPlainTextEdit(previous["text"])
        self.content.setPlaceholderText(tr("plan_text_placeholder"))
        self.content.setMaximumHeight(widget_px(owner, 100))
        layout.addWidget(self.content)
        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        self.family = QFontComboBox()
        self.family.setCurrentFont(QFont(previous["family"]))
        form.addRow(tr("plan_text_font"), self.family)
        self.size = QDoubleSpinBox()
        self.size.setRange(1, 300)
        self.size.setDecimals(1)
        self.size.setSuffix(" pt")
        self.size.setValue(previous["size"])
        style = QHBoxLayout()
        style.addWidget(self.size)
        self.bold, self.italic = QCheckBox(tr("plan_text_bold")), QCheckBox(tr("plan_text_italic"))
        self.bold.setChecked(previous["bold"])
        self.italic.setChecked(previous["italic"])
        style.addWidget(self.bold)
        style.addWidget(self.italic)
        form.addRow(tr("plan_text_size"), style)
        self.alignment = QComboBox()
        for value in ("left", "center", "right"):
            self.alignment.addItem(tr("plan_text_align_" + value), value)
        self.alignment.setCurrentIndex(self.alignment.findData(previous["alignment"]))
        form.addRow(tr("plan_text_alignment"), self.alignment)
        self.color_buttons = {}
        for key in ("color", "outline_color"):
            button = QPushButton()
            button.clicked.connect(lambda _checked=False, field=key: self.choose_color(field))
            self.color_buttons[key] = button
            form.addRow(tr("plan_text_" + key), button)
        self.outline = QDoubleSpinBox()
        self.outline.setRange(0, 16)
        self.outline.setDecimals(1)
        self.outline.setSuffix(" px")
        self.outline.setValue(previous["outline_width"])
        form.addRow(tr("plan_text_outline_width"), self.outline)
        layout.addLayout(form)
        self.preview_scene = QGraphicsScene(self)
        self.preview = GlyphPreview(self.preview_scene)
        self.preview.setBackgroundBrush(QColor("#ffffff"))
        self.preview.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.preview.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.preview.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.preview.setMinimumHeight(widget_px(owner, 110))
        layout.addWidget(self.preview, 1)
        self.hint = QLabel(tr("plan_text_preview_hint"))
        self.hint.setWordWrap(True)
        layout.addWidget(self.hint)
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(tr("cancel"))
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        for signal in (self.content.textChanged, self.family.currentFontChanged, self.size.valueChanged,
                       self.bold.toggled, self.italic.toggled, self.alignment.currentIndexChanged, self.outline.valueChanged):
            signal.connect(self.refresh_preview)
        self.refresh_preview()

    def choose_color(self, field):
        color = QColorDialog.getColor(QColor(self.colors[field]), self, self.owner.tr("plan_text_" + field))
        if color.isValid():
            self.colors[field] = color.name()
            self.refresh_preview()

    def values(self):
        return dict(text=self.content.toPlainText(), family=self.family.currentFont().family(),
            size=self.size.value(), bold=self.bold.isChecked(), italic=self.italic.isChecked(),
            alignment=self.alignment.currentData(), outline_width=self.outline.value(), **self.colors)

    def refresh_preview(self, *_args):
        self.preview_scene.clear()
        for key, button in self.color_buttons.items():
            button.setText(self.colors[key].upper())
            size = widget_px(self.owner, 16)
            pixmap = QPixmap(size, size)
            pixmap.fill(QColor(self.colors[key]))
            painter = QPainter(pixmap)
            painter.setPen(QColor("#8194aa"))
            painter.drawRect(0, 0, size - 1, size - 1)
            painter.end()
            button.setIcon(QIcon(pixmap))
            button.setIconSize(QSize(size, size))
        valid = False
        try:
            label = build_label(self.values())
            self.preview_scene.addItem(label_item(label))
            bounds = self.preview_scene.itemsBoundingRect().adjusted(-12, -12, 12, 12)
            self.preview_scene.setSceneRect(bounds)
            self.preview.fitInView(bounds, Qt.AspectRatioMode.KeepAspectRatio)
            valid = True
        except (ValueError, KeyError, TypeError):
            pass
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(valid)
