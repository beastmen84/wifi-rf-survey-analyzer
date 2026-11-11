"""Native paint accounting and composed-window capture for graphics diagnostics."""
from PySide6.QtCore import QObject,QEvent,QPoint
from PySide6.QtTest import QTest


class PaintCounter(QObject):
    def __init__(self,view):
        super().__init__(view.viewport())
        self.frames = 0
        view.viewport().installEventFilter(self)

    def eventFilter(self,source,event):
        if event.type() == QEvent.Type.Paint:
            self.frames += 1
        return False


def composed_canvas(view):
    """QOpenGLWidget.grabFramebuffer invokes its default clearing paintGL()."""
    viewport = view.viewport()
    if not hasattr(viewport,'grabFramebuffer'):
        return viewport.grab().toImage()
    window = view.window()
    window.raise_()
    assert QTest.qWaitForWindowExposed(window,3000), 'A composed GPU capture needs an exposed window'
    QTest.qWait(20)
    origin = viewport.mapTo(window,QPoint(0,0))
    return window.screen().grabWindow(window.winId(),origin.x(),origin.y(),viewport.width(),viewport.height()).toImage()
