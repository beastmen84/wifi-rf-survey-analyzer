"""Shared Qt test setup and teardown."""
import gc

import pytest
from PySide6.QtCore import QCoreApplication, QEvent


@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_runtest_teardown(item, nextitem):
    """Honor deleteLater between tests without an app.exec() event loop."""
    try:
        return (yield)
    finally:
        # A full collection scans the growing test session, so run it at module
        # boundaries. Qt still destroys queued widgets after each test.
        if nextitem is None or nextitem.path != item.path:
            gc.collect()
        if QCoreApplication.instance() is not None:
            QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


@pytest.fixture(autouse=True)
def accept_default_structure_review(monkeypatch):
    from PySide6.QtWidgets import QDialog
    from qt_ui.qt_wall_sides import WallSidesDialog
    monkeypatch.setattr(WallSidesDialog, 'exec', lambda self: QDialog.DialogCode.Accepted)
