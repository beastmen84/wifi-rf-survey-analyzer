"""Hardware viewport selection; model geometry and export painters stay vector."""
import os

from PySide6.QtGui import QOffscreenSurface, QOpenGLContext, QSurfaceFormat
from PySide6.QtWidgets import QApplication


def viewport_format():
    fmt = QSurfaceFormat()
    fmt.setVersion(2,0)
    fmt.setSamples(4)
    fmt.setStencilBufferSize(8)
    # Request unsynchronized swaps; the platform may negotiate another value.
    fmt.setSwapInterval(0)
    return fmt


def probe_opengl():
    context = QOpenGLContext()
    context.setFormat(viewport_format())
    if not context.create():
        return dict(available=False,reason='context_unavailable')
    surface = QOffscreenSurface()
    surface.setFormat(context.format())
    surface.create()
    if not surface.isValid() or not context.makeCurrent(surface):
        return dict(available=False,reason='surface_unavailable')
    try:
        functions = context.functions()
        return dict(available=True,renderer=functions.glGetString(0x1F01),
                    vendor=functions.glGetString(0x1F00),version=functions.glGetString(0x1F02))
    finally:
        context.doneCurrent()


def graphics_viewport():
    """Use real GL acceleration when available; retain the software fallback."""
    app = QApplication.instance()
    requested = os.environ.get('WIFI_HEATMAP_RENDERER','auto').lower()
    if requested == 'software' or app.platformName() in ('offscreen','minimal'):
        return None,dict(backend='software',reason='requested_or_headless')
    info = app.property('wifiHeatmapOpenGL')
    if info is None:
        try:
            info = probe_opengl()
        except (RuntimeError,ImportError,AttributeError):
            info = dict(available=False,reason='probe_failed')
        app.setProperty('wifiHeatmapOpenGL',info)
    renderer = str(info.get('renderer','')).lower()
    software_gl = any(name in renderer for name in ('llvmpipe','softpipe','swiftshader','gdi generic','software rasterizer'))
    if not info['available'] or (software_gl and requested != 'opengl'):
        return None,dict(info,backend='software')
    try:
        from PySide6.QtOpenGLWidgets import QOpenGLWidget
        viewport = QOpenGLWidget()
        viewport.setFormat(viewport_format())
    except (ImportError,RuntimeError):
        return None,dict(backend='software',reason='viewport_unavailable')
    return viewport,dict(info,backend='opengl')
