"""Retained layers must avoid geometry work without changing validation or ownership."""
# ruff: noqa: F401, F811 -- Qt fixtures are imported for pytest discovery.
from copy import deepcopy
from unittest.mock import patch

import pytest
from PySide6.QtCore import QSize, QRectF
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QGraphicsScene

from qt_ui.qt_clean_plan import VectorPlanSource
from qt_ui.qt_layer_scene import LayerScene
from survey import plan_layers
from survey.plan_layers import add_layer, active_layer, read_layers, validate_document, validate_state
from survey.wall_layout import plan_wall_layout
from tests.test_plan_annotations import line, marker
from tests.test_plan_text_fill import label
from tests.test_network_plan_symbols import symbol
from tests.test_wall_thickness import state, rectangle, BOUNDS
from tests.test_rectangle_design import editor
from tests.test_capture_adapter import window, qt_app


def document():
    result = read_layers({'_generated_floorplan':'1'})
    result['layers'][0]['drawing'].update(segments=[line()],labels=[label()],annotations=[marker()])
    result = add_layer(result,'Other')
    active_layer(result)['drawing']['segments'] = [line(200,300,500,300)]
    return validate_document(result)


def roots(entry):
    return tuple(item for group in entry.groups for item in group)


def test_validation_cache_returns_fresh_data_and_never_accepts_json_equivalent_invalid_types(qt_app):
    original = document()['layers'][0]['drawing']
    expected = validate_state(original)
    result = validate_state(original)
    result['labels'][0]['path'][0][1] += 1
    result['segments'].clear()
    assert validate_state(original) == expected
    for field in ('segments','labels','curves','annotations'):
        invalid = deepcopy(original)
        invalid[field] = tuple(invalid[field])
        with pytest.raises(ValueError):
            validate_state(invalid)
    invalid = deepcopy(original)
    invalid['labels'][0]['path'][0][1] = float('nan')
    with pytest.raises(ValueError):
        validate_state(invalid)


def test_cached_states_do_not_bypass_cross_layer_symbol_uniqueness_or_loaded_plan_rules(qt_app):
    result = document()
    a = result['layers'][0]['drawing']
    b = result['layers'][1]['drawing']
    a['annotations'] = [symbol(identity='duplicated',number=1)]
    b['annotations'] = [symbol(identity='duplicated',number=2)]
    validate_state(a)
    validate_state(b)
    with pytest.raises(ValueError):
        validate_document(result)
    from survey.plan_mode import PLAN_MODE_KEY, LOAD_PLAN
    with pytest.raises(ValueError,match='loaded_plan_annotations_only'):
        plan_layers.validate_plan_document({PLAN_MODE_KEY:LOAD_PLAN},document())


def test_validation_cache_is_bounded_and_uncacheable_values_still_validate(qt_app):
    # A small byte budget exercises eviction with genuine valid states.
    with patch.object(plan_layers,'_STATE_CACHE_LIMIT',512):
        plan_layers._STATE_CACHE.clear()
        plan_layers._STATE_CACHE_BYTES = 0
        for x in range(20):
            validate_state(dict(segments=[line(x+10,200,x+50,200)]))
        assert plan_layers._STATE_CACHE_BYTES <= 512
    assert validate_state(dict(segments=[],ignored=object()))['segments'] == []


@pytest.mark.parametrize('action',['activate','visibility','lock','rename','order'])
def test_layer_flags_reuse_all_scene_items_and_model_indexes(qt_app,action):
    scene = QGraphicsScene()
    cache = LayerScene(scene,QSize(900,600))
    doc = document()
    cache.prepare(doc)
    entries = dict(cache.layers)
    before = {k:roots(e) for k,e in entries.items()}
    snapper = entries['0'].snapper
    composite = cache.composite(doc)
    if action == 'activate':
        doc['active'] = '0'
    elif action == 'visibility':
        doc['layers'][1]['visible'] = False
    elif action == 'lock':
        doc['layers'][1]['locked'] = True
    elif action == 'rename':
        doc['layers'][1]['name'] = 'Renamed'
    else:
        doc['layers'].reverse()
    with patch.object(VectorPlanSource,'for_layer',side_effect=AssertionError('unchanged vectors rebuilt')):
        cache.prepare(doc)
    assert cache.layers == entries
    assert {k:roots(e) for k,e in cache.layers.items()} == before
    assert entries['0'].snapper is snapper
    if action not in ('visibility','order'):
        assert cache.composite(doc) is composite
    for layer in doc['layers']:
        assert all(i.isVisible() == layer['visible'] for i in roots(cache.layers[layer['id']]))
    if action == 'order':
        assert max(i.zValue() for i in roots(cache.layers[doc['layers'][0]['id']])) < min(
            i.zValue() for i in roots(cache.layers[doc['layers'][1]['id']]))


def test_text_edits_reuse_wall_vectors_indexes_and_composite_but_refresh_glyphs(qt_app):
    scene = QGraphicsScene()
    cache = LayerScene(scene,QSize(900,600))
    doc = document()
    cache.prepare(doc)
    old = cache.layers['0']
    composite = cache.composite(doc)
    old_items = roots(old)
    doc['layers'][0]['drawing']['labels'][0]['x'] += 30
    with patch('qt_ui.qt_clean_plan.WallReferenceInk',side_effect=AssertionError('text rebuilt wall geometry')):
        cache.prepare(doc)
    new = cache.layers['0']
    assert new is not old and new.source is not old.source
    assert new.geometry is old.geometry and new.snapper is old.snapper
    assert cache.composite(doc) is composite
    assert all(i.scene() is None for i in old_items)
    assert new.groups[-1][0].path() != old.groups[-1][0].path()
    old_geometry = new.geometry
    doc['layers'][0]['drawing']['segments'].append(line(100,400,600,400))
    cache.prepare(doc)
    assert cache.layers['0'].geometry is not old_geometry
    assert cache.composite(doc) is not composite


def test_layer_deletion_and_hidden_geometry_bounds_remain_safe(qt_app):
    scene = QGraphicsScene()
    cache = LayerScene(scene,QSize(900,600))
    doc = document()
    cache.prepare(doc)
    before = roots(cache.layers[doc['active']])
    invalid = deepcopy(doc)
    invalid['layers'][1]['visible'] = False
    invalid['layers'][1]['drawing']['segments'] = [line(100,100,2000,100)]
    with pytest.raises(ValueError):
        cache.prepare(invalid)
    assert all(i.scene() is scene and i.isVisible() for i in before)
    doc['layers'].pop()
    doc['active'] = '0'
    cache.prepare(doc)
    assert list(cache.layers) == ['0']
    assert all(i.scene() is None for i in before)


def test_cached_sources_preserve_material_ink_and_refresh_bounds(qt_app):
    drawing = plan_wall_layout(state(rectangle()),range(4),(),10,BOUNDS).state
    drawing['labels'] = [label()]
    size = QSize(900,600)
    cached = VectorPlanSource.for_layer(size,drawing)
    plain = VectorPlanSource(size,drawing['segments'],drawing['curves'],drawing['labels'],drawing['annotations'])
    images = []
    for source in (cached,plain,VectorPlanSource.for_layer(size,deepcopy(drawing))):
        image = QImage(size,QImage.Format.Format_RGB32)
        image.fill('white')
        painter = QPainter(image)
        source.paint_plan(painter,QRectF(0,0,900,600))
        painter.end()
        images.append(image)
    assert images[0] == images[1] == images[2]
    doc = read_layers({'_generated_floorplan':'1'})
    doc['layers'][0]['drawing'] = drawing
    scene = QGraphicsScene()
    scene.setSceneRect(QRectF(0,0,900,600))
    LayerScene(scene,size).prepare(doc)
    image = QImage(size,QImage.Format.Format_RGB32)
    image.fill('white')
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    scene.render(painter)
    painter.end()
    assert image == images[0]
    with pytest.raises(ValueError):
        VectorPlanSource.for_layer(QSize(200,200),drawing)


def test_native_layer_item_reuse_survives_undo_redo_resize_and_scene_replacement(editor):
    owner,drawing = editor
    assert drawing.change_layers(document())
    entry = drawing._layer_scene.layers['0']
    original = roots(entry)
    doc = deepcopy(drawing.layer_document())
    doc['active'] = '0'
    assert drawing.change_layers(doc,history=False)
    assert drawing.items == entry.groups[1] and drawing.text.items == entry.groups[-1]
    assert roots(drawing._layer_scene.layers['0']) == original
    doc = deepcopy(drawing.layer_document())
    doc['layers'][0]['name'] = 'Renamed base'
    assert drawing.change_layers(doc)
    assert drawing.undo() and drawing.redo()
    assert roots(drawing._layer_scene.layers['0']) == original
    from qt_ui.qt_plan_resize import resize_canvas
    assert resize_canvas(owner,(1200,900))
    assert all(i.scene() is None for i in original)
    assert drawing._layer_scene.size == QSize(1200,900)
    from tests.test_blank_plan import create_survey
    create_survey(owner,width=18,height=12)
    assert drawing._layer_scene is None
