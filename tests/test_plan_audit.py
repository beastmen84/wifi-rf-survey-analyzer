"""Audit regressions: persisted styles, selection contrast, lifetime and printing."""
from copy import deepcopy
from unittest.mock import patch

from PIL import Image
import pytest
from PySide6.QtCore import QCoreApplication, QEvent, QMarginsF, QSize, Qt
from PySide6.QtGui import QColor, QImage, QPageSize, QPageLayout
from PySide6.QtPdf import QPdfDocument
from PySide6.QtPrintSupport import QPrinter
from PySide6.QtWidgets import QColorDialog, QDialog, QGraphicsScene

from app_core.settings import load_app_settings, save_app_settings
from app_core.plan_preferences import saved_palette, save_palette, tool_colors, save_tool_colors, FIELDS
from qt_ui.qt_plan_colors import choose_plan_color
from qt_ui.qt_text_editor import PlanTextDialog
from qt_ui.qt_plan_tools import PlanToolsOverlay
from qt_ui.qt_plan_printing import paint_plan_page, print_scale_reference, clean_plan_image
from survey.plan_label_rendering import label_item, selection_contrast
from survey.plan_drawing import render_plan_drawing
from tests.test_plan_objects import obj
from tests.test_plan_text_fill import label
from tests.test_rectangle_design import editor
from tests.test_capture_adapter import window, qt_app


def test_color_preferences_validate_preserve_unrelated_and_survive_new_controls(editor):
    app, d = editor
    save_app_settings(dict(theme="dark", plan_custom_colors=["#AABBCC", "bad"], plan_tool_colors=[]))
    assert saved_palette() == ["#aabbcc", None] and tool_colors("desk") == {}
    assert save_tool_colors("desk", dict(color="#123456", fill=None, cx=100, text="private"))
    assert save_tool_colors("structure", dict(color="#abcdef"))
    assert save_tool_colors("text", dict(color="#ffeedd", outline_color="#112233"))
    assert not save_tool_colors("unknown", dict(color="#000000"))
    assert tool_colors("desk") == dict(color="#123456", fill=None)
    assert load_app_settings()["theme"] == "dark"
    assert "private" not in str(load_app_settings()) and "cx" not in load_app_settings()["plan_tool_colors"]["desk"]
    # Newly constructed controls reload disk preferences; existing survey styles
    # remain authoritative when editing a saved object.
    tools = PlanToolsOverlay(app)
    try:
        assert tools.stroke_color.name() == "#abcdef"
        fresh, existing = PlanTextDialog(app), PlanTextDialog(app, label())
        try:
            assert fresh.values()["color"] == "#ffeedd"
            assert existing.values()["color"] == label()["color"]
        finally:
            fresh.deleteLater()
            existing.deleteLater()
    finally:
        # The additional palette is never opened and never modifies the scene.
        tools.deleteLater()
        tools.toggle_button.deleteLater()


def test_explicit_custom_colors_persist_even_when_picker_is_cancelled(window, qt_app):
    save_palette(["#123456"] * 16)
    def picker(*args):
        assert QColorDialog.customColor(0).name() == "#123456"
        QColorDialog.setCustomColor(7, QColor("#abcdef"))
        return QColor()  # Cancel the object color, keep Add to Custom Colors.
    with patch("qt_ui.qt_plan_colors.QColorDialog.getColor", side_effect=picker):
        assert not choose_plan_color("#000000", window).isValid()
    for i in range(16):
        QColorDialog.setCustomColor(i, QColor("#ffffff"))
    with patch("qt_ui.qt_plan_colors.QColorDialog.getColor", side_effect=lambda *args: QColorDialog.customColor(7)):
        assert choose_plan_color("#000000", window).name() == "#abcdef"


@pytest.mark.parametrize("color,expected", [("#000000", "#ffffff"), ("#ffffff", "#000000"),
    ("#173047", "#ffffff"), ("#ffff00", "#000000")])
def test_selected_text_contrast_is_cosmetic_visible_and_never_exported(qt_app, color, expected):
    text = dict(label(), color=color)
    before = deepcopy(text)
    assert selection_contrast(color) == expected
    plain, selected = label_item(text), label_item(text, selected=True)
    assert not plain.childItems() and len(selected.childItems()) == 2
    halo, frame = selected.childItems()
    assert halo.pen().color().name() == expected and halo.pen().isCosmetic()
    assert frame.pen().style() == Qt.PenStyle.DashLine
    assert all(i.acceptedMouseButtons() == Qt.MouseButton.NoButton for i in selected.childItems())
    scene = QGraphicsScene()
    scene.addItem(selected)
    assert text == before
    rendered = render_plan_drawing(Image.new("RGB", (900, 600), "white"), [], [text])
    assert (2, 132, 199) not in [c for _n, c in rendered.getcolors(900 * 600)]


def test_label_above_furniture_matches_native_and_clean_raster(editor):
    app, d = editor
    text = label()
    desk = obj(cx=text["x"], cy=text["y"], width=500, height=300, fill="#abcdef")
    d.store([], labels=[text], annotations=[desk])
    assert d.text.items[0].zValue() > d.annotation.items[0].zValue()
    assert d.annotation.pick((text["x"], text["y"])) == ((), (0,))
    image = clean_plan_image(d.view, app.session.metadata)
    count = sum(image.pixelColor(x, y).name() == text["color"] for y in range(170, 270) for x in range(150, 450))
    assert count > 20


@pytest.mark.parametrize("result", [QDialog.DialogCode.Rejected, QDialog.DialogCode.Accepted])
def test_text_editor_releases_every_dialog_and_does_not_dirty_on_cancel(editor, qt_app, result):
    app, d = editor
    before, dirty = deepcopy(app.session.metadata), app.session.dirty
    count = len(app.findChildren(PlanTextDialog))
    with patch.object(PlanTextDialog, "exec", return_value=result):
        for _ in range(8):
            d.text.read_editor(label() if result == QDialog.DialogCode.Accepted else None)
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    qt_app.processEvents()
    assert len(app.findChildren(PlanTextDialog)) == count
    assert app.session.metadata == before and app.session.dirty == dirty


@pytest.mark.parametrize("density", [None, "bad", 0, -1, float("nan"), float("inf")])
def test_invalid_scale_never_invents_a_physical_reference(density):
    assert print_scale_reference(1000, density) is None


@pytest.mark.parametrize("system", ["metric", "imperial"])
@pytest.mark.parametrize("orientation", [QPageLayout.Orientation.Portrait, QPageLayout.Orientation.Landscape])
def test_printed_graphical_scale_matches_rendered_plan_after_page_fit(qt_app, tmp_path, system, orientation):
    from tests.test_plan_printing import pillow
    from translations.i18n import translate
    image = QImage(1000, 600, QImage.Format.Format_RGB888)
    image.fill(QColor("#123456"))
    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
    path = tmp_path / "scale.pdf"
    printer.setOutputFileName(str(path))
    printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    printer.setPageOrientation(orientation)
    printer.setPageMargins(QMarginsF(10, 10, 10, 10), QPageLayout.Unit.Millimeter)
    paint_plan_page(printer, image, 100, system, lambda key: translate("it", key))
    document = QPdfDocument()
    try:
        assert document.load(str(path)) == QPdfDocument.Error.None_
        assert document.pageCount() == 1
        text = document.getAllText(0).text()
        reference = print_scale_reference(1000, 100, system)
        assert reference["unit"] in text and translate("it", "print_plan_scale") in text
        page = document.pagePointSize(0)
        rendered = pillow(document.render(0, QSize(1200, round(1200 * page.height() / page.width()))))
        # Locate unique plan fill and the dark horizontal reference separately.
        pixels = rendered.load()
        plan = [(x, y) for y in range(rendered.height) for x in range(rendered.width)
                if max(abs(v - target) for v, target in zip(pixels[x, y], (18, 52, 86))) <= 2]
        left, right = min(x for x, _y in plan), max(x for x, _y in plan)
        bottom = max(y for _x, y in plan)
        spans = []
        for y in range(bottom + 1, rendered.height):
            run = longest = 0
            for x in range(rendered.width):
                run = run + 1 if max(pixels[x, y]) < 200 else 0
                longest = max(longest, run)
            spans.append((longest, y))
        # The reference bar is the longest contiguous ink row in the footer.
        span, _y = max(spans)
        assert span == pytest.approx((right - left + 1) * reference["source_pixels"] / 1000, abs=3)
    finally:
        document.close()
