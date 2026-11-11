"""Bounded immutable topology reuse, including style and boundary-index changes."""
from copy import deepcopy
from dataclasses import FrozenInstanceError
from unittest.mock import patch

import pytest

from survey import curved_regions
from survey.curved_regions import closed_drawing_regions, clear_region_cache
from survey.plan_drawing import rectangle_segments


@pytest.fixture(autouse=True)
def cache():
    clear_region_cache()
    yield
    clear_region_cache()


def room(x=100):
    return rectangle_segments(x,100,200,200,'#263238')


def test_equal_copies_reuse_frozen_results_without_aliasing_the_input():
    lines = room()
    with patch.object(curved_regions,'_closed_drawing_regions',wraps=curved_regions._closed_drawing_regions) as build:
        first = closed_drawing_regions(lines,with_boundaries=True)
        second = closed_drawing_regions(deepcopy(lines),with_boundaries=True)
        assert first is second and build.call_count == 1
        lines[0]['x1'] += 10
        assert first.faces[0][0] != (lines[0]['x1'],lines[0]['y1'])
        closed_drawing_regions(lines,with_boundaries=True)
        assert build.call_count == 2
    with pytest.raises(FrozenInstanceError):
        first.faces = ()


def test_wall_properties_and_boundary_mode_invalidate_reuse():
    lines = room()
    with patch.object(curved_regions,'_closed_drawing_regions',wraps=curved_regions._closed_drawing_regions) as build:
        closed_drawing_regions(lines)
        assert not closed_drawing_regions(lines).boundaries
        assert closed_drawing_regions(lines,with_boundaries=True).boundaries
        lines[0]['wall'] = dict(width=20,side=-1)
        closed_drawing_regions(lines,with_boundaries=True)
        lines[0]['wall']['width'] = 30
        closed_drawing_regions(lines,with_boundaries=True)
        assert build.call_count == 4


def test_entry_count_and_point_budget_are_bounded(monkeypatch):
    for i in range(20):
        closed_drawing_regions(room(i*300))
    assert len(curved_regions._REGION_CACHE) <= 8
    assert curved_regions._REGION_CACHE_WEIGHT <= curved_regions._REGION_CACHE_LIMIT
    clear_region_cache()
    monkeypatch.setattr(curved_regions,'_REGION_CACHE_LIMIT',1)
    closed_drawing_regions(room())
    assert not curved_regions._REGION_CACHE
