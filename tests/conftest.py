"""Unrelated UI tests keep zero-depth placement; side-editor tests override it."""
import pytest


@pytest.fixture(autouse=True)
def release_deferred_qt_objects():
    """Honor deleteLater between tests without an app.exec() event loop."""
    yield
    import gc
    from PySide6.QtCore import QCoreApplication, QEvent

    gc.collect()
    if QCoreApplication.instance() is not None:
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        gc.collect()


@pytest.fixture(autouse=True)
def accept_default_structure_review(monkeypatch):
    from PySide6.QtWidgets import QDialog
    from qt_ui.qt_wall_sides import WallSidesDialog
    monkeypatch.setattr(WallSidesDialog, 'exec', lambda self: QDialog.DialogCode.Accepted)
