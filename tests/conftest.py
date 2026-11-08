"""Unrelated UI tests keep zero-depth placement; side-editor tests override it."""
import pytest


@pytest.fixture(autouse=True)
def accept_default_structure_review(monkeypatch):
    from PySide6.QtWidgets import QDialog
    from qt_ui.qt_wall_sides import WallSidesDialog
    monkeypatch.setattr(WallSidesDialog, 'exec', lambda self: QDialog.DialogCode.Accepted)
