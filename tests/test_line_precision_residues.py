"""Legacy floating-point cuts must not block committing a dragged diagonal."""
from copy import deepcopy
import json
import math

import pytest
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor
from PySide6.QtTest import QTest

from survey.plan_drawing import PLAN_DRAWING_KEY, drawing_segments, rectangle_segments
from survey.plan_geometry import normalize_segments, split_segments
from survey.planar_geometry import EPSILON
from survey.plan_regions import closed_plan_regions
from tests.test_drawing_edit import line
from tests.test_rectangle_design import editor, move
from tests.test_capture_adapter import window, qt_app


@pytest.mark.parametrize("delta", [1e-12, -1e-12, math.ulp(200)])
def test_general_split_skips_collapsed_legacy_edges_without_losing_source_identity(delta):
    segments = [line(100, 200, 100, 200 + delta), line(100, 100, 500, 100), line(600, 300, 700, 450)]
    original = deepcopy(segments)
    pieces, sources = split_segments(segments, with_sources=True)
    assert pieces == segments[1:] and sources == [1, 2]
    assert segments == original
    joined, owners = normalize_segments(segments, with_sources=True)
    assert joined == segments[1:] and owners == [frozenset({1}), frozenset({2})]
    assert normalize_segments(joined) == joined


def test_orthogonal_intersections_do_not_create_new_subprecision_fragments():
    # Near-identical heights at different X coordinates used to create slivers
    # even when neither original input edge was itself short.
    segments = [line(100, 100, 100, 200), line(0, 200 - 1e-12, 300, 200 - 1e-12),
                line(100, 200, 100, 400)]
    pieces = split_segments(segments)
    assert all(math.hypot(s["x2"] - s["x1"], s["y2"] - s["y1"]) > EPSILON for s in pieces)
    normalized = normalize_segments(segments)
    assert len(normalized) == 4 and normalize_segments(normalized) == normalized
    assert len(normalize_segments(normalized + [line(500, 300, 700, 450)])) == 5


@pytest.mark.parametrize("oblique", [False, True])
def test_real_gaps_and_short_features_above_precision_remain_intact(oblique):
    short = line(100, 100, 100, 100 + EPSILON * 4)
    segments = [short, line(200, 200, 300, 200), line(300 + 1e-5, 200, 400, 200)]
    if oblique:
        segments.append(line(600, 300, 700, 450))
    result = normalize_segments(segments)
    assert len(result) == len(segments) and short in result
    assert not any(s["x1"] == 200 and s["x2"] == 400 for s in result)
    assert normalize_segments(result) == result


def test_legacy_noise_normalizes_on_read_without_metadata_or_room_dimension_changes():
    room = rectangle_segments(100, 100, 300, 200, "#123456")
    source = room + [line(400, 100, 400, math.nextafter(100, math.inf))]
    raw = json.dumps(dict(version=1, segments=source))
    metadata = {"_generated_floorplan": "1", PLAN_DRAWING_KEY: raw}
    assert drawing_segments(metadata) == room and metadata[PLAN_DRAWING_KEY] == raw
    regions = closed_plan_regions(drawing_segments(metadata))
    assert len(regions.faces) == 1
    face = regions.faces[0]
    assert abs(sum(a[0] * b[1] - a[1] * b[0] for a, b in zip(face, face[1:] + face[:1]))) / 2 == 60000


@pytest.mark.parametrize("first,last", [((500, 350), (700, 450)), ((700, 450), (500, 350)),
    ((500, 350), (700, 350)), ((500, 350), (500, 500))])
def test_drag_release_commits_in_legacy_plan_and_survives_history_and_reopen(editor, tmp_path, first, last):
    app, d = editor
    room = rectangle_segments(100, 100, 300, 200, "#123456")
    raw = json.dumps(dict(version=1, segments=room + [line(400, 100, 400, math.nextafter(100, math.inf))]))
    app.session.metadata[PLAN_DRAWING_KEY] = raw
    app.refresh_session_labels()
    app.session.dirty = False
    assert app.session.metadata[PLAN_DRAWING_KEY] == raw
    app.plan_tools.line_button.click()
    app.plan_tools.stroke_color = QColor("#d84315")
    view = app.floorplan_view
    start, end = (view.mapFromScene(QPointF(*p)) for p in (first, last))
    captures = []
    view.surveyPointRequested.connect(lambda *args: captures.append(args))
    QTest.mousePress(view.viewport(), Qt.MouseButton.RightButton, pos=start)
    move(view, end, Qt.MouseButton.RightButton)
    preview = d.line.preview.line()
    assert preview.length() > 0 and not app.session.dirty
    QTest.mouseRelease(view.viewport(), Qt.MouseButton.RightButton, pos=end)
    result = d.segments()
    drawn = [s for s in result if s["color"] == "#d84315"]
    assert len(drawn) == 1 and len(d.undo_stack) == 1 and app.session.dirty and not captures
    assert math.hypot(drawn[0]["x2"] - drawn[0]["x1"], drawn[0]["y2"] - drawn[0]["y1"]) == pytest.approx(preview.length())
    assert d.line.preview is None and d.line.origin is None
    d.undo()
    assert d.segments() == room
    d.redo()
    assert d.segments() == result
    app.plan_tools.set_open(False)
    app.session.csv_file = str(tmp_path / "line.csv")
    assert app.save_survey() and app.open_survey(str(tmp_path / "line.csv"))
    assert d.segments() == result
