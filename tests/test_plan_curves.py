import math

import pytest

from survey.plan_curves import (curve_info, curve_bounds, validate_curves, point_at,
                                project_curve, transform_curves, subcurve)
from survey.plan_curve_geometry import normalize_plan, line_curve_intersections, curve_intersections
from survey.plan_geometry import rotate_degrees


def circle(x=300, y=300, radius=100):
    return dict(kind="circle", cx=x, cy=y, radius=radius, phase=0, color="#123456")


def arc(h=50):
    return dict(kind="arc", x1=200, y1=200, x2=400, y2=200, height=h, color="#123456")


def line(a, b):
    return dict(x1=a[0], y1=a[1], x2=b[0], y2=b[1], color="#123456")


@pytest.mark.parametrize("h", [1e-4, .1, 30, -30, 100, -100, 300, -300])
def test_arc_preserves_chord_sagitta_and_rigid_transform(h):
    curve = arc(h)
    assert point_at(curve, .5) == pytest.approx((300, 200 + h), abs=1e-7)
    assert point_at(curve, 0) == (200, 200)
    assert point_at(curve, 1) == (400, 200)
    moved = transform_curves([curve], 35, (300, 200), 100, 100)[0]
    assert curve_info(moved)[2] == pytest.approx(curve_info(curve)[2])
    assert math.dist(point_at(moved, 0), point_at(moved, 1)) == pytest.approx(200)
    assert moved["height"] == h


@pytest.mark.parametrize("h", [1e-4, .1, 50, -50, 200, -200])
def test_line_arc_intersections_exact_endpoints_and_midpoint(h):
    curve = arc(h)
    points = line_curve_intersections(line((300, 0), (300, 600)), curve)
    assert any(math.dist(p, (300, 200 + h)) < 1e-6 for p in points)
    endpoints = line_curve_intersections(line((100, 200), (500, 200)), curve)
    assert sorted(endpoints) == [(200, 200), (400, 200)]


def test_circle_crossing_splits_and_removal_heals_without_flattening():
    wall = line((100, 300), (500, 300))
    lines, curves = normalize_plan([wall], [circle()])
    assert len(lines) == 3 and len(curves) == 2
    assert all(c["kind"] == "arc" for c in curves)
    assert normalize_plan(lines, curves) == (lines, curves)
    joined, healed = normalize_plan([], curves)
    assert joined == [] and len(healed) == 1 and healed[0]["kind"] == "circle"
    assert curve_info(healed[0])[:3] == pytest.approx((300, 300, 100))
    straight, _ = normalize_plan(lines, [])
    assert straight == [wall]


def test_two_circles_split_at_both_crossings_and_heal_after_move():
    _, curves = normalize_plan([], [circle(), circle(400)])
    assert len(curves) == 4
    assert len(curve_intersections(circle(), circle(400))) == 2
    moved = transform_curves(curves[2:], dx=300)
    _, joined = normalize_plan([], curves[:2] + moved)
    assert len(joined) == 2 and all(c["kind"] == "circle" for c in joined)


def test_tangent_circle_does_not_create_empty_fragment():
    lines, curves = normalize_plan([line((0, 200), (600, 200))], [circle()])
    assert len(lines) == 2 and len(curves) == 1
    assert curves[0]["kind"] == "circle"
    assert normalize_plan(lines, curves) == (lines, curves)


def test_same_color_line_overlap_unites_but_keeps_real_curve_contacts_and_sources():
    lines = [line((100, 300), (500, 300)), line((250, 300), (350, 300))]
    result, curves, owners, curve_owners = normalize_plan(lines, [circle()], with_sources=True)
    assert result == [line((100, 300), (200, 300)), line((200, 300), (400, 300)), line((400, 300), (500, 300))]
    assert len(curves) == 2 and curve_owners == [frozenset({0}), frozenset({0})]
    assert owners == [frozenset({0, 1})] * 3
    assert normalize_plan(result, curves) == (result, curves)


def test_colored_arc_pieces_and_real_gap_do_not_heal():
    source = circle()
    pieces = [subcurve(source, .1, .4), subcurve(source, .6, .9)]
    assert len(normalize_plan([], pieces)[1]) == 2
    pieces = [subcurve(source, 0, .5), dict(subcurve(source, .5, 1), color="#ff0000")]
    assert len(normalize_plan([], pieces)[1]) == 2


def test_bounds_projection_and_validation():
    assert curve_bounds(circle()) == pytest.approx((200, 200, 400, 400))
    assert project_curve(arc(50), (300, 400)) == pytest.approx((300, 250))
    for bad in [circle(radius=0), circle(radius=float("nan")), circle(x=0), arc(0)]:
        with pytest.raises(ValueError):
            validate_curves([bad])


@pytest.mark.parametrize("angle", range(0, 360, 5))
def test_every_rotation_preserves_circle_cuts_closed_faces_and_healing(angle):
    from survey.curved_regions import closed_drawing_regions
    lines = rotate_degrees([line((100, 300), (500, 300))], angle, (300, 300))
    curves = transform_curves([circle()], angle, (300, 300))
    lines, curves = normalize_plan(lines, curves)
    assert len(lines) == 3 and len(curves) == 2
    assert normalize_plan(lines, curves) == (lines, curves)
    regions = closed_drawing_regions(lines, curves)
    assert len(regions.faces) == 2 and not regions.limited
    healed = normalize_plan([], curves)[1]
    assert len(healed) == 1 and healed[0]["kind"] == "circle"
    assert curve_info(healed[0])[:3] == pytest.approx((300, 300, 100))


@pytest.mark.parametrize("h", [.0001, .01, 50, -50])
def test_shallow_arc_circle_shared_endpoints_are_exact_and_do_not_acquire_micro_fragments(h):
    curves = [arc(h), circle(300, 200)]
    lines, normalized = normalize_plan([], curves)
    assert not lines and len(normalized) == 3
    assert normalize_plan([], normalized) == ([], normalized)
    assert all(curve["kind"] == "arc" for curve in normalized)


@pytest.mark.parametrize("angle", range(0, 360, 5))
def test_external_tangent_circle_faces_at_every_orientation(angle):
    from survey.curved_regions import closed_drawing_regions
    curves = transform_curves([circle(250, 300), circle(450, 300)], angle, (350, 300))
    regions = closed_drawing_regions([], curves)
    assert len(regions.faces) == 2 and not regions.limited


@pytest.mark.parametrize("height", [.0001, .01, .1, 1, 50, -50, 200])
def test_shallow_arc_recovers_one_parametric_arc_after_crossing_is_removed(height):
    _, pieces = normalize_plan([line((300, 0), (300, 600))], [arc(height)])
    assert len(pieces) == 2
    healed = normalize_plan([], pieces)[1]
    assert len(healed) == 1 and healed[0]["kind"] == "arc"
    assert healed[0]["height"] == pytest.approx(height, abs=1e-9)


@pytest.mark.parametrize("angle", range(0, 360, 5))
@pytest.mark.parametrize("kind", ["circle", "arc"])
def test_tangent_straight_wall_does_not_create_microscopic_curve_fragments(angle, kind):
    curve = circle() if kind == "circle" else arc(50)
    y, pivot = (200, (300, 300)) if kind == "circle" else (250, (300, 200))
    wall = rotate_degrees([line((100, y), (500, y))], angle, pivot)
    curves = transform_curves([curve], angle, pivot)
    lines, cut_curves = normalize_plan(wall, curves)
    assert len(lines) == 2 and len(cut_curves) == (1 if kind == "circle" else 2)
    assert normalize_plan(lines, cut_curves) == (lines, cut_curves)
