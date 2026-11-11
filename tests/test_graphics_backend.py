"""Hardware detection must be cached and preserve a usable software path."""
from unittest.mock import patch

import pytest

from qt_ui import graphics_backend
from qt_ui.qt_floorplan import FloorplanView
from tests.test_capture_adapter import qt_app


@pytest.fixture
def detection(qt_app,monkeypatch):
    previous = qt_app.property('wifiHeatmapOpenGL')
    qt_app.setProperty('wifiHeatmapOpenGL',None)
    monkeypatch.setenv('WIFI_HEATMAP_RENDERER','auto')
    yield qt_app
    qt_app.setProperty('wifiHeatmapOpenGL',previous)


def test_forced_software_does_not_probe_or_require_opengl(detection,monkeypatch):
    monkeypatch.setenv('WIFI_HEATMAP_RENDERER','software')
    with patch.object(graphics_backend,'probe_opengl',side_effect=AssertionError('unnecessary probe')):
        view = FloorplanView()
        assert view.graphics_backend['backend'] == 'software'
        view.close()


@pytest.mark.parametrize('info', [dict(available=False,reason='context_unavailable'),
                                  dict(available=True,renderer='llvmpipe (LLVM)')])
def test_unavailable_or_emulated_gl_falls_back_and_detection_is_cached(detection,info):
    with patch.object(graphics_backend,'probe_opengl',return_value=info) as probe:
        for _ in range(2):
            viewport,backend = graphics_backend.graphics_viewport()
            assert viewport is None and backend['backend'] == 'software'
        assert probe.call_count <= 1  # Headless platforms do not probe at all.


def test_probe_failure_does_not_break_startup(detection):
    with patch.object(graphics_backend,'probe_opengl',side_effect=RuntimeError('driver unavailable')):
        viewport,backend = graphics_backend.graphics_viewport()
        assert viewport is None and backend['backend'] == 'software'
