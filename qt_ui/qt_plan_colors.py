"""Persist Qt's explicitly saved custom color slots, including on picker cancel."""
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QColorDialog

from app_core.plan_preferences import saved_palette, save_palette


def choose_plan_color(initial, parent, title=""):
    colors = saved_palette()
    for index in range(QColorDialog.customCount()):
        value = colors[index] if index < len(colors) else None
        QColorDialog.setCustomColor(index, QColor(value or "#ffffff"))
    try:
        return QColorDialog.getColor(QColor(initial), parent, title)
    finally:
        save_palette([QColorDialog.customColor(index).name() for index in range(QColorDialog.customCount())])
