"""Physical offsets preserve internal faces, including shared-room layout."""
from copy import deepcopy
import math

import pytest
from PySide6.QtCore import QPointF, QRectF
from survey.plan_drawing import rectangle_segments, validate_segments, encode_drawing, drawing_segments
from survey.plan_geometry import rotate_degrees, translate_segments
from survey.plan_curve_geometry import normalize_plan
from survey.plan_curves import subcurve, transform_curves
from survey.plan_faces import RegionPicker
from survey.wall_geometry import wall_solids, path_area, solid
from survey.wall_layout import plan_wall_layout
from tests.test_capture_adapter import qt_app

BOUNDS = QRectF(0, 0, 2000, 1500)


def state(lines=(), curves=(), annotations=()):
    lines, curves = normalize_plan(list(lines), list(curves))
    return dict(segments=lines, curves=curves, annotations=list(annotations), labels=[])


def rectangle(x=100, y=100, w=200, h=200):
    return rectangle_segments(x, y, w, h, "#263238")


@pytest.mark.parametrize("angle", [0, 35, 90, 180, 270])
@pytest.mark.parametrize("width", [1, 10, 20])
def test_single_room_grows_outside_preserving_area_and_lengths(qt_app, angle, width):
    original = state(translate_segments(rotate_degrees(rectangle(), angle), 200, 200))
    result = plan_wall_layout(original, range(4), (), width, BOUNDS)
    assert not result.changed_positions
    assert [r.area for _p, r in RegionPicker(result.state["segments"], []).records] == pytest.approx([40000])
    assert sorted(math.hypot(l["x2"]-l["x1"], l["y2"]-l["y1"]) for l in result.state["segments"]) == pytest.approx([200]*4)
    assert sum(path_area(p) for _c, p in wall_solids(result.state["segments"])) == pytest.approx((200+2*width)**2-40000, abs=.05)
    assert not any(p.contains(QPointF(400, 400)) for _c, p in wall_solids(result.state["segments"]))


@pytest.mark.parametrize("anchor", [0, 1])
def test_shared_rooms_separate_without_changing_interiors(qt_app, anchor):
    original = state(rectangle()+rectangle(x=300))
    result = plan_wall_layout(original, range(len(original["segments"])), (), 20, BOUNDS, anchor=anchor)
    assert result.changed_positions and result.moves[anchor] == (0, 0)
    assert sorted(abs(dx) for dx, _dy in result.moves) == pytest.approx([0, 20])
    rooms = RegionPicker(result.state["segments"], []).records
    assert len(rooms) == 2 and sorted(r.area for _p, r in rooms) == pytest.approx([40000]*2)
    boxes = sorted((p.boundingRect().left(), p.boundingRect().right()) for p, _r in rooms)
    assert boxes[1][0]-boxes[0][1] == pytest.approx(20)
    # Reapplying the same depth is idempotent, increasing/decreasing changes the gap.
    again = plan_wall_layout(result.state, range(len(result.state["segments"])), (), 20, BOUNDS)
    assert not again.changed_positions
    widened = plan_wall_layout(result.state, range(len(result.state["segments"])), (), 30, BOUNDS)
    assert sum(abs(dx) for dx, _dy in widened.moves) == pytest.approx(10)
    removed = plan_wall_layout(result.state, range(len(result.state["segments"])), (), 0, BOUNDS)
    assert len(RegionPicker(removed.state["segments"], []).records) == 2
    assert not any(l.get("wall") for l in removed.state["segments"])


def test_four_rooms_grid_keeps_tangential_alignment(qt_app):
    original = state([l for x, y in ((100, 100), (300, 100), (100, 300), (300, 300)) for l in rectangle(x, y)])
    result = plan_wall_layout(original, range(len(original["segments"])), (), 20, BOUNDS)
    assert [round(v, 6) for pair in sorted(result.moves) for v in pair] == [0, 0, 0, 20, 20, 0, 20, 20]
    assert len(RegionPicker(result.state["segments"], []).records) == 4


def test_t_room_layout_allows_tangential_slide_and_preserves_every_area(qt_app):
    original = state(rectangle(w=400)+rectangle(y=300)+rectangle(x=300, y=300))
    result = plan_wall_layout(original, range(len(original["segments"])), (), 20, BOUNDS)
    assert sorted(result.areas) == [40000, 40000, 80000]
    assert sorted(r.area for _p, r in RegionPicker(result.state["segments"], []).records) == [40000, 40000, 80000]


def test_circle_offsets_outwards_without_changing_radius_or_area(qt_app):
    circle = dict(kind="circle", cx=400, cy=400, radius=100, phase=0, color="#263238")
    result = plan_wall_layout(state(curves=[circle]), (), (0,), 20, BOUNDS)
    assert result.state["curves"][0]["radius"] == 100
    body = wall_solids([], result.state["curves"])[0][1]
    assert body.boundingRect() == QRectF(280, 280, 240, 240)
    assert not body.contains(QPointF(400, 400)) and body.contains(QPointF(510, 400))


def test_open_lines_require_explicit_side_and_bounds_are_checked(qt_app):
    original = state([dict(x1=100, y1=100, x2=300, y2=100, color="#263238")])
    with pytest.raises(ValueError, match="wall_open_side"):
        plan_wall_layout(original, (0,), (), 20, BOUNDS)
    for side, y in ((1, 110), (-1, 90)):
        result = plan_wall_layout(original, (0,), (), 20, BOUNDS, open_side=side)
        assert solid(result.state["segments"][0]).contains(QPointF(200, y))
    with pytest.raises(ValueError, match="wall_outside"):
        plan_wall_layout(state(rectangle(0, 0)), range(4), (), 20, BOUNDS)


def test_nested_rooms_conflict_is_atomic_instead_of_distorting_dimensions(qt_app):
    original = state(rectangle(w=500, h=500)+rectangle(200, 200, 100, 100))
    before = deepcopy(original)
    with pytest.raises(ValueError, match="wall_constraints_conflict"):
        plan_wall_layout(original, range(len(original["segments"])), (), 20, BOUNDS)
    assert original == before


def test_wall_attributes_survive_reverse_split_join_and_curves(qt_app):
    first = dict(x1=100, y1=100, x2=300, y2=100, color="#263238", wall=dict(width=20, side=1))
    reverse = dict(first, x1=500, x2=300, wall=dict(width=20, side=-1))
    lines, _ = normalize_plan([first, reverse], [])
    assert len(lines) == 1 and lines[0]["wall"] == first["wall"]
    reverse["wall"]["width"] = 30
    assert len(normalize_plan([first, reverse], [])[0]) == 2
    crossing = dict(x1=200, y1=50, x2=200, y2=150, color="#263238")
    lines, _ = normalize_plan([first, crossing], [])
    assert len([l for l in lines if l.get("wall") == first["wall"]]) == 2
    meta = dict(_generated_floorplan="1", plan_drawing=encode_drawing(lines))
    assert drawing_segments(meta) == lines
    circle = dict(kind="circle", cx=400, cy=400, radius=100, phase=0, color="#263238", wall=dict(width=20, side=-1))
    assert subcurve(circle, 0, .25)["wall"] == circle["wall"]
    assert transform_curves([circle], 90)[0]["wall"] == circle["wall"]


@pytest.mark.parametrize("wall", [None, {}, dict(width=-1, side=1), dict(width=float("nan"), side=1), dict(width=True, side=1), dict(width=20, side=True)])
def test_invalid_wall_properties_reject_corrupt_files(wall):
    with pytest.raises(ValueError):
        validate_segments([dict(rectangle()[0], wall=wall)])


@pytest.mark.parametrize("columns,rows", [(1, 1), (2, 1), (1, 3), (2, 2), (3, 2), (4, 3)])
@pytest.mark.parametrize("angle", [0, 35, 90])
@pytest.mark.parametrize("width", [.5, 4, 10])
def test_layout_matrix_preserves_rigid_rooms_and_never_mutates_source(qt_app, columns, rows, angle, width):
    lines = [l for row in range(rows) for col in range(columns) for l in rectangle(100+col*130, 100+row*90, 130, 90)]
    original = state(translate_segments(rotate_degrees(lines, angle, (100, 100)), 600, 500))
    before = deepcopy(original)
    result = plan_wall_layout(original, range(len(original["segments"])), (), width, QRectF(0, 0, 3000, 3000))
    assert original == before
    rooms = RegionPicker(result.state["segments"], []).records
    assert len(rooms) == columns*rows
    assert [r.area for _p, r in rooms] == pytest.approx([11700]*(columns*rows), abs=1e-5)
    assert result.moves[0] == (0, 0)


def test_shared_curved_interface_and_inward_radius_collapse_are_explicit_conflicts(qt_app):
    curve = dict(kind="arc", x1=300, y1=100, x2=300, y2=300, height=30, color="#263238")
    src = state(rectangle()+rectangle(x=300), [curve])
    with pytest.raises(ValueError, match="wall_shared_curve"):
        plan_wall_layout(src, range(len(src["segments"])), range(len(src["curves"])), 20, BOUNDS)
    curve["wall"] = dict(width=1000, side=-1)
    with pytest.raises(ValueError, match="wall_radius_conflict"):
        solid(curve)


def test_thin_duplicate_preserves_existing_physical_face_and_schema_guard(qt_app):
    import json
    first = dict(rectangle()[0], wall=dict(width=20, side=-1))
    thin = {k: v for k, v in first.items() if k != "wall"}
    assert normalize_plan([thin, first], [])[0] == [first]
    assert json.loads(encode_drawing([first]))["version"] == 2
    assert json.loads(encode_drawing([thin]))["version"] == 1


def test_obsolete_shared_face_cuts_rejoin_after_crossing_is_removed(qt_app):
    first = dict(x1=300, y1=100, x2=300, y2=300, color="#263238", wall=dict(width=20, side=-1))
    second = dict(first, x1=320, x2=320, wall=dict(width=20, side=1))
    branch = dict(x1=200, y1=200, x2=300, y2=200, color="#263238")
    lines, _ = normalize_plan([first, second, branch], [])
    assert len(lines) == 5
    lines, _ = normalize_plan([l for l in lines if l.get("wall")], [])
    assert len(lines) == 2
    assert normalize_plan(lines, [])[0] == lines
