"""Ctrl toggles clicked items; Shift and modified boxes extend one active layer."""
from copy import deepcopy
from unittest.mock import patch

import pytest
from PySide6.QtCore import QPointF,Qt
from PySide6.QtTest import QTest

from survey.plan_layers import add_layer
from tests.test_plan_text_fill import label
from tests.test_plan_objects import obj
from tests.test_plan_annotations import aperture
from tests.test_rectangle_design import editor,move
from tests.test_capture_adapter import window,qt_app

CTRL = Qt.KeyboardModifier.ControlModifier
SHIFT = Qt.KeyboardModifier.ShiftModifier


def text_setup(editor,tool):
    owner,drawing = editor
    texts = [dict(label(),id=str(i),x=x,y=y) for i,(x,y) in enumerate(((150,150),(450,150),(150,350)))]
    drawing.store([],labels=texts)
    owner.plan_tools.select_tool(tool)
    return owner,drawing,drawing.selection if tool == 'select' else drawing.annotation


def click(drawing,point,modifiers=Qt.KeyboardModifier.NoModifier):
    QTest.mouseClick(drawing.view.viewport(),Qt.MouseButton.RightButton,modifiers,
                     drawing.view.mapFromScene(point))


def text_point(drawing,index):
    return drawing.text.bounds_path(drawing.labels()[index]).boundingRect().center()


def box(drawing,index,modifiers):
    rect = drawing.text.bounds_path(drawing.labels()[index]).boundingRect().adjusted(-5,-5,5,5)
    start,end = drawing.view.mapFromScene(rect.topLeft()),drawing.view.mapFromScene(rect.bottomRight())
    QTest.mousePress(drawing.view.viewport(),Qt.MouseButton.RightButton,modifiers,start)
    # The operation is captured on press, even if the modifier is released early.
    move(drawing.view,end,Qt.MouseButton.RightButton)
    QTest.mouseRelease(drawing.view.viewport(),Qt.MouseButton.RightButton,Qt.KeyboardModifier.NoModifier,end)


@pytest.mark.parametrize('tool',['select','annotation_select'])
def test_click_add_toggle_replace_and_clear_texts_without_modifying_document(editor,tool):
    owner,drawing,selection = text_setup(editor,tool)
    before = deepcopy(drawing.snapshot())
    history = len(drawing.undo_stack)
    click(drawing,text_point(drawing,0))
    click(drawing,text_point(drawing,1),CTRL)
    assert selection.selected_labels == (0,1)
    click(drawing,text_point(drawing,1),SHIFT)
    assert selection.selected_labels == (0,1)
    click(drawing,text_point(drawing,0),CTRL)
    assert selection.selected_labels == (1,)
    click(drawing,text_point(drawing,2))
    assert selection.selected_labels == (2,)
    click(drawing,text_point(drawing,2),CTRL)
    assert not selection.selected_labels and not drawing.measurement.isVisible()
    assert drawing.snapshot() == before and len(drawing.undo_stack) == history


@pytest.mark.parametrize('tool',['select','annotation_select'])
@pytest.mark.parametrize('modifiers',[CTRL,SHIFT])
def test_modified_box_adds_and_keeps_previous_items_in_preview(editor,tool,modifiers):
    _owner,drawing,selection = text_setup(editor,tool)
    click(drawing,text_point(drawing,0))
    box(drawing,1,modifiers)
    assert selection.selected_labels == (0,1)
    box(drawing,1,modifiers)
    assert selection.selected_labels == (0,1)
    box(drawing,1,Qt.KeyboardModifier.NoModifier)
    assert selection.selected_labels == (1,)


def test_mixed_selection_includes_straight_curved_text_and_furniture_and_undo(editor):
    owner,drawing = editor
    line = dict(x1=100,y1=500,x2=300,y2=500,color='#123456')
    curve = dict(kind='circle',cx=500,cy=400,radius=40,color='#123456')
    drawing.store([line],labels=[dict(label(),x=150,y=150)],curves=[curve],
                  annotations=[obj(cx=700,cy=400,width=80,height=60)])
    owner.plan_tools.select_tool('select')
    before = deepcopy(drawing.snapshot())
    click(drawing,QPointF(200,500))
    click(drawing,text_point(drawing,0),CTRL)
    click(drawing,QPointF(540,400),SHIFT)
    click(drawing,QPointF(700,400),CTRL)
    s = drawing.selection
    assert (s.selected,s.selected_labels,s.selected_curves,s.selected_annotations) == ((0,),(0,),(0,),(0,))
    assert s.delete_selected()
    assert not any(drawing.active_state().values())
    assert drawing.undo() and all(drawing.snapshot()[key] == before[key] for key in ('segments','curves','labels','annotations'))


def test_ctrl_toggle_of_wall_removes_its_automatically_selected_opening(editor):
    owner,drawing = editor
    drawing.store([dict(x1=100,y1=200,x2=300,y2=200,color='#123456')],
                  annotations=[aperture(x1=150,y1=200,x2=190,y2=200)])
    owner.plan_tools.select_tool('select')
    click(drawing,QPointF(270,200))
    assert drawing.selection.selected == (0,) and drawing.selection.selected_annotations == (0,)
    click(drawing,QPointF(270,200),CTRL)
    assert not drawing.selection.has_selection()


@pytest.mark.parametrize('tool',['select','annotation_select'])
def test_multi_text_selection_transfers_together_with_unchanged_ids_and_positions(editor,tool,tmp_path):
    owner,drawing,selection = text_setup(editor,tool)
    doc = add_layer(drawing.layer_document(),'Texts')
    doc['active'] = '0'
    drawing.change_layers(doc)
    owner.plan_tools.select_tool(tool)
    click(drawing,text_point(drawing,0))
    click(drawing,text_point(drawing,1),CTRL)
    original = deepcopy(drawing.labels())
    assert selection.selected_labels == (0,1)
    with patch('qt_ui.qt_layers.QInputDialog.getItem',return_value=('Texts',True)):
        owner.layers_panel.move_selected()
    doc = drawing.layer_document()
    assert doc['layers'][0]['drawing']['labels'] == original[2:]
    assert doc['layers'][1]['drawing']['labels'] == original[:2]
    assert drawing.undo() and drawing.labels() == original
    assert drawing.redo() and drawing.labels() == original[:2]
    owner.session.csv_file = str(tmp_path/'selection.csv')
    assert owner.save_survey() and owner.open_survey(owner.session.csv_file)
    assert drawing.labels() == original[:2]


@pytest.mark.parametrize('restriction',['locked','hidden'])
def test_transfer_excludes_locked_and_hidden_destinations_without_losing_selection(editor,restriction):
    owner,drawing,selection = text_setup(editor,'select')
    doc = add_layer(drawing.layer_document(),'Target')
    doc['layers'][1]['locked' if restriction == 'locked' else 'visible'] = restriction == 'locked'
    doc['active'] = '0'
    drawing.change_layers(doc)
    owner.plan_tools.select_tool('select')
    click(drawing,text_point(drawing,0))
    click(drawing,text_point(drawing,1),CTRL)
    before = deepcopy(drawing.snapshot())
    with patch('qt_ui.qt_layers.QInputDialog.getItem',side_effect=AssertionError('no editable target')):
        owner.layers_panel.move_selected()
    assert selection.selected_labels == (0,1) and drawing.snapshot() == before


@pytest.mark.parametrize('tool',['select','annotation_select'])
def test_modifier_selection_does_not_pick_passive_layer_text(editor,tool):
    owner,drawing,selection = text_setup(editor,tool)
    doc = add_layer(drawing.layer_document(),'Passive')
    doc['layers'][1]['drawing']['labels'] = [dict(label(),id='passive',x=700,y=150)]
    doc['active'] = '0'
    drawing.change_layers(doc)
    owner.plan_tools.select_tool(tool)
    click(drawing,text_point(drawing,0))
    click(drawing,drawing.text.bounds_path(doc['layers'][1]['drawing']['labels'][0]).boundingRect().center(),CTRL)
    assert selection.selected_labels == (0,)


def test_loaded_plan_texts_support_multi_selection_and_layer_transfer(editor,tmp_path):
    from PIL import Image
    owner,drawing = editor
    path = tmp_path/'source.png'
    Image.new('RGB',(900,600),'#abcdef').save(path)
    source = path.read_bytes()
    owner.load_plan_file(str(path),save_metadata=True)
    owner.session.metadata['px_per_meter'] = '50'
    owner.refresh_session_labels()
    drawing.store([],labels=[dict(label(),id=str(i),x=x,y=150) for i,x in enumerate((150,450))])
    doc = add_layer(drawing.layer_document(),'Texts')
    doc['active'] = '0'
    drawing.change_layers(doc)
    owner.plan_tools.set_open(True)
    owner.plan_tools.select_tool('annotation_select')
    click(drawing,text_point(drawing,0))
    click(drawing,text_point(drawing,1),SHIFT)
    assert drawing.annotation.selected_labels == (0,1)
    with patch('qt_ui.qt_layers.QInputDialog.getItem',return_value=('Texts',True)):
        owner.layers_panel.move_selected()
    assert len(drawing.labels()) == 2 and not drawing.layer_document()['layers'][0]['drawing']['labels']
    assert path.read_bytes() == source
