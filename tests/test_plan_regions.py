"""Closed regions come from actual segment topology, never raster ink or bounds."""
from collections import deque
from copy import deepcopy
import random

import pytest
from PIL import Image
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QImage, QPainter, QPainterPath
from PySide6.QtTest import QTest

from survey.plan_drawing import rectangle_segments
from survey.plan_regions import closed_plan_regions
from tests.test_rectangle_design import editor
from tests.test_capture_adapter import window, qt_app


def line(x1, y1, x2, y2):
    return dict(x1=x1, y1=y1, x2=x2, y2=y2, color="#263238")


def face_path(regions):
    path = QPainterPath()
    path.setFillRule(Qt.FillRule.WindingFill)
    for face in regions.faces:
        path.moveTo(*face[0])
        for point in face[1:]:
            path.lineTo(*point)
        path.closeSubpath()
    return path


def contains(regions, x, y):
    return face_path(regions).contains(QPointF(x, y))


def test_rectangle_is_closed_but_three_sides_and_open_chains_are_not():
    lines = rectangle_segments(100, 100, 200, 100, "#123456")
    regions = closed_plan_regions(lines)
    assert len(regions.faces) == 1 and contains(regions, 200, 150)
    for missing in range(4):
        assert not closed_plan_regions(lines[:missing] + lines[missing + 1:]).faces
    assert not closed_plan_regions([]).faces


def test_concave_l_shaped_perimeter_is_detected_without_filling_the_notch():
    points = [(100, 100), (300, 100), (300, 200), (200, 200), (200, 300), (100, 300)]
    regions = closed_plan_regions([line(*a, *b) for a, b in zip(points, points[1:] + points[:1])])
    assert len(regions.faces) == 1
    assert contains(regions, 150, 250) and contains(regions, 250, 150)
    assert not contains(regions, 250, 250)


def test_crossings_and_t_junctions_split_real_segments_into_bounded_faces():
    lines = rectangle_segments(100, 100, 200, 200, "#123456")
    lines += [line(200, 50, 200, 350), line(50, 200, 350, 200)]
    regions = closed_plan_regions(lines)
    assert len(regions.faces) == 4
    assert all(contains(regions, x, y) for x in (150, 250) for y in (150, 250))
    assert not contains(regions, 175, 75)


def test_collinear_overlaps_duplicates_reversed_sides_and_tails_preserve_regions():
    original = rectangle_segments(100, 100, 200, 100, "#123456")
    lines = [line(100, 100, 220, 100), line(200, 100, 300, 100)] + original[1:]
    lines += [line(item["x2"], item["y2"], item["x1"], item["y1"]) for item in original]
    lines += [line(200, 100, 200, 50), line(200, 100, 200, 150)]
    before = deepcopy(lines)
    regions = closed_plan_regions(lines)
    assert len(regions.faces) == 1 and contains(regions, 250, 150)
    assert lines == before


@pytest.mark.parametrize("bridge", [False, True])
def test_nested_closed_shapes_remain_faded_inside_inner_and_outer_perimeters(bridge):
    lines = rectangle_segments(0, 0, 600, 400, "#123456")
    lines += rectangle_segments(100, 100, 100, 100, "#abcdef")
    if bridge:
        lines += [line(0, 100, 100, 100)]
    regions = closed_plan_regions(lines)
    assert contains(regions, 50, 50) and contains(regions, 150, 150)
    assert not contains(regions, 650, 150)


def test_overlapping_rectangles_recognize_union_without_parity_holes():
    lines = rectangle_segments(100, 100, 200, 200, "#123456")
    lines += rectangle_segments(200, 200, 200, 200, "#abcdef")
    regions = closed_plan_regions(lines)
    assert len(regions.faces) == 3
    assert all(contains(regions, *point) for point in ((150, 150), (250, 250), (350, 350)))
    assert not contains(regions, 150, 350)


def test_opening_one_room_does_not_remove_neighboring_closed_room():
    left = rectangle_segments(100, 100, 100, 100, "#123456")
    right = rectangle_segments(200, 100, 100, 100, "#abcdef")
    regions = closed_plan_regions(left[:3] + right)  # Delete left outside wall.
    assert not contains(regions, 150, 150) and contains(regions, 250, 150)


def test_disconnected_regions_and_corner_touching_remain_independent():
    lines = rectangle_segments(100, 100, 100, 100, "#123456")
    lines += rectangle_segments(200, 200, 100, 100, "#123456")
    lines += rectangle_segments(400, 100, 100, 100, "#123456")
    regions = closed_plan_regions(lines)
    assert len(regions.faces) == 3
    assert contains(regions, 150, 150) and contains(regions, 250, 250)
    assert not contains(regions, 350, 150)


def test_real_subpixel_gap_stays_open_but_arithmetic_noise_does_not_break_a_join():
    lines = rectangle_segments(100, 100, 200, 100, "#123456")
    lines[0]["x2"] -= 0.00001
    assert not closed_plan_regions(lines).faces
    lines[0]["x2"] = 300 - 5e-12
    assert len(closed_plan_regions(lines).faces) == 1


def test_complexity_limit_returns_no_partial_or_guessed_regions():
    lines = [line(x, 0, x, 200) for x in range(200)]
    lines += [line(0, y, 200, y) for y in range(200)]
    regions = closed_plan_regions(lines, max_intersections=1000)
    assert regions.limited and regions.faces == ()


def test_random_orthogonal_graphs_match_independent_cell_flood_fill():
    rng = random.Random(65319)
    size = 6
    for _ in range(100):
        probability = rng.uniform(.3, .95)
        walls = set()
        segments = []
        for x in range(size + 1):
            for y in range(size):
                if rng.random() < probability:
                    segments.append(line(x, y, x, y + 1))
                    walls.add(frozenset(((x - 1, y), (x, y))))
        for y in range(size + 1):
            for x in range(size):
                if rng.random() < probability:
                    segments.append(line(x, y, x + 1, y))
                    walls.add(frozenset(((x, y - 1), (x, y))))
        reached, pending = {(-1, -1)}, deque([(-1, -1)])
        while pending:
            x, y = pending.popleft()
            for other in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if (all(-1 <= value <= size for value in other) and other not in reached
                        and frozenset(((x, y), other)) not in walls):
                    reached.add(other)
                    pending.append(other)
        path = face_path(closed_plan_regions(segments))
        for x in range(size):
            for y in range(size):
                assert path.contains(QPointF(x + .5, y + .5)) == ((x, y) not in reached)


def scene_image(view):
    bounds = view.scene.sceneRect()
    image = QImage(int(bounds.width()), int(bounds.height()), QImage.Format.Format_RGB32)
    image.fill(Qt.GlobalColor.white)
    painter = QPainter(image)
    view.scene.render(painter, QRectF(image.rect()), bounds)
    painter.end()
    return image


def test_grid_pixels_fade_only_in_closed_area_and_restore_on_erase_undo_redo(editor):
    app, drawing = editor
    view = app.floorplan_view
    drawing.commit(QRectF(100, 100, 200, 200))
    assert view.grid_interior_path.contains(QPointF(150, 175))
    image = scene_image(view)
    inside, outside = 255 - image.pixelColor(150, 175).red(), 255 - image.pixelColor(150, 75).red()
    assert 0 < inside < outside * .5
    app.plan_tools.eraser_button.click()
    point = view.mapFromScene(QPointF(200, 100))
    QTest.mouseClick(view.viewport(), Qt.MouseButton.RightButton, pos=point)
    assert view.grid_interior_path.isEmpty()
    opened = scene_image(view)
    assert abs(opened.pixelColor(150, 175).red() - opened.pixelColor(150, 75).red()) <= 1
    drawing.undo()
    assert view.grid_interior_path.contains(QPointF(150, 175))
    drawing.redo()
    assert view.grid_interior_path.isEmpty()


def test_fading_is_derived_not_saved_and_survives_units_grid_theme_and_reopen(editor, tmp_path):
    app, drawing = editor
    view = app.floorplan_view
    drawing.commit(QRectF(100, 100, 200, 200))
    original = dict(app.session.metadata)
    for language in ("en", "it", "fr", "es"):
        app.change_language(language.upper())
        for theme in ("light", "soft", "dark", "contrast"):
            app.change_theme(theme)
            app.set_floorplan_grid_enabled(False, show_status=False)
            app.set_floorplan_grid_enabled(True, show_status=False)
            assert view.grid_interior_path.contains(QPointF(150, 175))
    assert app.session.metadata == original
    app.plan_tools.set_open(False)
    app.session.csv_file = str(tmp_path / "closed.csv")
    assert app.save_survey()
    assert app.open_survey(str(tmp_path / "closed.csv"))
    assert view.grid_interior_path.contains(QPointF(150, 175))
    # Decorative grid is not baked into survey/Live/HTML backgrounds.
    with Image.open(tmp_path / "closed.png") as image:
        assert image.getpixel((150, 175)) == (255, 255, 255)
    external = tmp_path / "imported.png"
    Image.new("RGB", (600, 400), "white").save(external)
    app.load_plan_file(str(external), save_metadata=True)
    assert view.grid_interior_path.isEmpty() and not drawing.regions.faces


def test_provisional_and_cancelled_rectangle_does_not_change_closed_grid(editor):
    app, drawing = editor
    drawing.begin_placement(200, 100, anchor=QPointF(150, 100))
    assert app.floorplan_view.grid_interior_path.isEmpty() and not drawing.regions.faces
    drawing.cancel()
    assert not app.session.dirty
    assert app.floorplan_view.grid_interior_path.isEmpty()
