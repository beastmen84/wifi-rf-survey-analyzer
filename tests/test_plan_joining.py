"""Same-color straight ink unites while real junctions, colors and gaps survive."""
import json
from copy import deepcopy

import pytest
from PIL import Image
from PySide6.QtCore import QLineF, QPointF, Qt
from PySide6.QtGui import QColor
from PySide6.QtTest import QTest

from survey.plan_drawing import PLAN_DRAWING_KEY, drawing_segments, encode_drawing, rectangle_segments, render_plan_drawing
from survey.plan_geometry import normalize_segments, rotate_degrees, translate_segments
from tests.test_rectangle_design import editor, move
from tests.test_capture_adapter import window, qt_app


def line(x1, y1, x2, y2, color="#123456"):
    return dict(x1=x1, y1=y1, x2=x2, y2=y2, color=color)


def point(app, x, y):
    return app.floorplan_view.mapFromScene(QPointF(x, y))


@pytest.mark.parametrize("lines,expected", [
    ([line(100, 200, 300, 200), line(300, 200, 500, 200)], line(100, 200, 500, 200)),
    ([line(300, 200, 100, 200), line(300, 200, 500, 200)], line(500, 200, 100, 200)),
    ([line(200, 500, 200, 300), line(200, 100, 200, 300)], line(200, 500, 200, 100)),
    ([line(200, 200, 300, 200), line(100, 200, 200, 200), line(300, 200, 400, 200)], line(100, 200, 400, 200)),
])
def test_straight_contiguous_chains_join_preserving_color_and_first_direction(lines, expected):
    original = deepcopy(lines)
    result, sources = normalize_segments(lines, with_sources=True)
    assert result == [expected] and lines == original
    assert sources == [frozenset(range(len(lines)))]
    assert normalize_segments(result) == result


@pytest.mark.parametrize("lines,count", [
    ([line(100, 200, 300, 200), line(300, 200, 500, 200), line(300, 200, 300, 300)], 3),
    ([line(100, 200, 500, 200), line(300, 100, 300, 300)], 4),
    ([line(100, 200, 300, 200), line(300, 200, 300, 300)], 2),
    ([line(100, 200, 300, 200), line(300, 200, 500, 200, "#abcdef")], 2),
    ([line(100, 200, 300, 200), line(300.00001, 200, 500, 200)], 2),
    ([line(100, 200, 300, 200), line(300, 200.00001, 500, 200.00001)], 2),
    ([line(100, 200, 300, 200), line(300, 200, 100, 200, "#abcdef")], 2),
    ([line(100, 200, 400, 200), line(200, 200, 500, 200, "#abcdef")], 4),
])
def test_real_junctions_corners_color_transitions_and_gaps_remain_separate(lines, count):
    result = normalize_segments(lines)
    assert len(result) == count and normalize_segments(result) == result
    base = Image.new("RGB", (600, 400), "white")
    assert render_plan_drawing(base, result).tobytes() == render_plan_drawing(base, lines).tobytes()


@pytest.mark.parametrize("lines,expected", [
    ([line(100, 200, 300, 200), line(300, 200, 100, 200)], line(100, 200, 300, 200)),
    ([line(100, 200, 400, 200), line(200, 200, 500, 200)], line(100, 200, 500, 200)),
    ([line(300, 100, 300, 500), line(300, 150, 300, 250)], line(300, 100, 300, 500)),
    ([line(300, 500, 300, 100), line(300, 250, 300, 150)], line(300, 500, 300, 100)),
    ([line(100, 100, 300, 300), line(400, 400, 200, 200)], line(100, 100, 400, 400)),
])
def test_same_color_overlaps_form_one_stroke_and_retain_all_source_indices(lines, expected):
    original = deepcopy(lines)
    result, sources = normalize_segments(lines, with_sources=True)
    assert result == [expected] and lines == original
    assert sources == [frozenset(range(len(lines)))]
    assert normalize_segments(result) == result


@pytest.mark.parametrize("angle", range(0, 360, 5))
def test_overlapping_rotated_strokes_unite_without_a_false_cut(angle):
    lines = rotate_degrees([line(100, 200, 400, 200), line(200, 200, 500, 200)], angle, (300, 300))
    result, sources = normalize_segments(lines, with_sources=True)
    expected = rotate_degrees([line(100, 200, 500, 200)], angle, (300, 300))[0]
    assert len(result) == 1 and sources == [frozenset({0, 1})]
    assert result[0] == pytest.approx(expected)
    assert normalize_segments(result) == result


def test_overlapping_extension_joins_below_real_t_and_keeps_its_source_ownership():
    lines = [line(300, 100, 300, 500), line(300, 150, 300, 250), line(100, 150, 300, 150)]
    result, sources = normalize_segments(lines, with_sources=True)
    assert result == [line(300, 100, 300, 150), line(300, 150, 300, 500), lines[2]]
    assert sources == [frozenset({0}), frozenset({0, 1}), frozenset({2})]
    assert normalize_segments(result) == result


def test_drawing_overlapping_line_unites_selection_erasure_history_and_saved_geometry(editor, tmp_path):
    app, drawing = editor
    drawing.apply_edit([line(300, 100, 300, 500), line(100, 150, 300, 150)])
    before = drawing.segments()
    app.plan_tools.line_button.click()
    app.plan_tools.stroke_color = QColor("#123456")
    count = len(drawing.undo_stack)
    drawing.line.commit(QLineF(300, 150, 300, 250))
    assert drawing.segments() == before
    # A completely covered stroke adds no geometry or redundant undo entry.
    assert len(drawing.undo_stack) == count
    drawing.line.commit(QLineF(300, 450, 300, 600))
    result = drawing.segments()
    assert result == [line(300, 100, 300, 150), line(300, 150, 300, 600), line(100, 150, 300, 150)]
    drawing.undo()
    assert drawing.segments() == before
    drawing.redo()
    assert drawing.segments() == result
    app.plan_tools.select_button.click()
    QTest.mouseClick(app.floorplan_view.viewport(), Qt.MouseButton.RightButton, pos=point(app, 300, 200))
    assert drawing.selection.selected == (1,)
    app.plan_tools.eraser_button.click()
    move(app.floorplan_view, point(app, 300, 200))
    assert drawing.eraser.targets == (1,)
    assert (300, 250) not in drawing.snapper.vertices
    app.plan_tools.set_open(False)
    app.session.csv_file = str(tmp_path / "overlap.csv")
    assert app.save_survey() and app.open_survey(str(tmp_path / "overlap.csv"))
    assert drawing.segments() == result
    assert len(json.loads(app.session.metadata[PLAN_DRAWING_KEY])["segments"]) == 3


def test_joined_outputs_track_all_sources_without_absorbing_unrelated_sources():
    lines = [line(100, 200, 300, 200), line(300, 200, 500, 200), line(600, 100, 600, 300)]
    result, sources = normalize_segments(lines, with_sources=True)
    assert result == [line(100, 200, 500, 200), lines[2]]
    assert sources == [frozenset({0, 1}), frozenset({2})]


def test_old_saved_obsolete_cuts_join_on_read_without_metadata_mutation():
    lines = [line(100, 200, 300, 200), line(300, 200, 500, 200)]
    raw = json.dumps(dict(version=1, segments=lines))
    metadata = {"_generated_floorplan": "1", PLAN_DRAWING_KEY: raw}
    assert drawing_segments(metadata) == [line(100, 200, 500, 200)]
    assert metadata[PLAN_DRAWING_KEY] == raw
    assert len(json.loads(encode_drawing(lines))["segments"]) == 1


def test_move_away_rejoins_old_and_moved_lines_with_one_undo_action(editor):
    app, drawing = editor
    drawing.apply_edit([line(100, 200, 500, 200), line(300, 100, 300, 300)])
    original = drawing.segments()
    assert len(original) == 4
    app.plan_tools.select_button.click()
    selection = drawing.selection
    selection.set_selected(index for index, item in enumerate(original) if item["x1"] == item["x2"])
    move(app.floorplan_view, point(app, 300, 200))
    count = len(drawing.undo_stack)
    captures = []
    app.floorplan_view.surveyPointRequested.connect(lambda *args: captures.append(args))
    QTest.keyClick(app, Qt.Key.Key_M)
    target = point(app, 650, 200)
    move(app.floorplan_view, target)
    assert drawing.segments() == original  # Rejoining is committed with the move.
    QTest.mouseClick(app.floorplan_view.viewport(), Qt.MouseButton.RightButton, pos=target)
    result = drawing.segments()
    assert len(result) == 2 and line(100, 200, 500, 200) in result
    assert len(selection.selected) == 1 and not captures
    assert (300, 200) not in drawing.snapper.vertices
    assert len(drawing.undo_stack) == count + 1
    drawing.undo()
    assert drawing.segments() == original
    assert (300, 200) in drawing.snapper.vertices
    drawing.redo()
    assert drawing.segments() == result
    app.plan_tools.eraser_button.click()
    move(app.floorplan_view, point(app, 200, 200))
    assert len(drawing.eraser.targets) == 1
    assert drawing.eraser.lines[drawing.eraser.targets[0]] == line(100, 200, 500, 200)


def test_rotating_branch_away_rejoins_straight_line(editor):
    app, drawing = editor
    drawing.apply_edit([line(100, 200, 500, 200), line(300, 200, 300, 300)])
    original = drawing.segments()
    app.plan_tools.select_button.click()
    drawing.selection.set_selected(index for index, item in enumerate(original) if item["x1"] == item["x2"])
    QTest.keyClick(app, Qt.Key.Key_R)
    assert drawing.segments() == [line(100, 200, 500, 200), line(350, 250, 250, 250)]
    assert drawing.selection.selected == (1,)


def test_removing_a_branch_rejoins_but_removing_only_one_arm_of_a_cross_does_not(editor):
    app, drawing = editor
    drawing.apply_edit([line(100, 200, 500, 200), line(300, 100, 300, 300)])
    app.plan_tools.eraser_button.click()
    QTest.mouseClick(app.floorplan_view.viewport(), Qt.MouseButton.RightButton, pos=point(app, 300, 150))
    assert len(drawing.segments()) == 3  # A T joint still exists.
    QTest.mouseClick(app.floorplan_view.viewport(), Qt.MouseButton.RightButton, pos=point(app, 300, 250))
    assert drawing.segments() == [line(100, 200, 500, 200)]
    drawing.undo()
    assert len(drawing.segments()) == 3


def test_deleted_divider_rejoins_room_walls_and_preserves_closed_area(editor, tmp_path):
    app, drawing = editor
    drawing.apply_edit(rectangle_segments(100, 100, 400, 300, "#123456") + [line(300, 100, 300, 400)])
    assert len(drawing.segments()) == 7 and len(drawing.regions.faces) == 2
    app.plan_tools.eraser_button.click()
    QTest.mouseClick(app.floorplan_view.viewport(), Qt.MouseButton.RightButton, pos=point(app, 300, 250))
    assert len(drawing.segments()) == 4 and len(drawing.regions.faces) == 1
    assert app.floorplan_view.grid_interior_path.contains(QPointF(200, 200))
    app.plan_tools.set_open(False)
    app.session.csv_file = str(tmp_path / "joined.csv")
    assert app.save_survey() and app.open_survey(str(tmp_path / "joined.csv"))
    assert len(drawing.segments()) == 4 and len(drawing.regions.faces) == 1
    assert len(json.loads(app.session.metadata[PLAN_DRAWING_KEY])["segments"]) == 4


def test_joining_to_stationary_geometry_does_not_select_it_for_next_move(editor):
    app, drawing = editor
    drawing.apply_edit([line(100, 200, 300, 200), line(400, 200, 600, 200)])
    app.plan_tools.select_button.click()
    drawing.selection.set_selected([1])
    assert drawing.selection.apply_transformed(translate_segments([drawing.segments()[1]], -100, 0))
    assert drawing.segments() == [line(100, 200, 500, 200)]
    assert not drawing.selection.selected
    assert not drawing.selection.begin_move()


def test_moving_into_a_same_color_overlap_does_not_absorb_stationary_geometry_into_selection(editor):
    app, drawing = editor
    drawing.apply_edit([line(100, 200, 400, 200), line(500, 200, 700, 200)])
    app.plan_tools.select_button.click()
    drawing.selection.set_selected([1])
    assert drawing.selection.apply_transformed(translate_segments([drawing.segments()[1]], -200, 0))
    assert drawing.segments() == [line(100, 200, 500, 200)]
    assert not drawing.selection.selected and not drawing.selection.begin_move()
    drawing.undo()
    assert drawing.segments() == [line(100, 200, 400, 200), line(500, 200, 700, 200)]


def test_join_preserves_erased_gap_after_branches_disappear(editor):
    app, drawing = editor
    drawing.apply_edit([line(100, 200, 500, 200), line(250, 150, 250, 250), line(350, 150, 350, 250)])
    app.plan_tools.eraser_button.click()
    QTest.mouseClick(app.floorplan_view.viewport(), Qt.MouseButton.RightButton, pos=point(app, 300, 200))
    drawing.apply_edit([item for item in drawing.segments() if item["y1"] == item["y2"]])
    assert drawing.segments() == [line(100, 200, 250, 200), line(350, 200, 500, 200)]
