"""A confirmed selection remains visible and usable when entering Layers."""
from copy import deepcopy

import pytest
from PySide6.QtCore import QEvent,QPointF,QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication,QInputDialog

from survey.plan_layers import add_layer
from tests.test_capture_adapter import window,qt_app
from tests.test_rectangle_design import editor,move
from tests.test_plan_text_fill import label
from tests.test_plan_objects import obj


def selected_editor(editor,tool,kind='text'):
    owner,drawing = editor
    doc = add_layer(drawing.layer_document(),'Target')
    doc['active'] = '0'
    drawing.change_layers(doc)
    drawing.store([],labels=[label()],annotations=[obj(cx=650,cy=250)])
    owner.layers_panel.set_open(True,save=False)
    owner.plan_tools.select_tool(tool)
    labels = (0,) if kind in ('text','mixed') else ()
    annotations = (0,) if kind in ('object','mixed') else ()
    if tool == 'select':
        drawing.selection.set_selected((),labels,annotation_indices=annotations)
        drawing.selection.show_count(QPointF(200,200))
        selection = drawing.selection
    else:
        drawing.annotation.select(annotations,labels)
        selection = drawing.annotation
    return owner,drawing,selection,labels,annotations


def leave_for_layers(owner,drawing,qt_app):
    owner.layers_panel.set_open(True,save=False)
    QApplication.sendEvent(drawing.view.viewport(),QEvent(QEvent.Type.Leave))
    QApplication.sendEvent(drawing.view,QEvent(QEvent.Type.Leave))
    tree = owner.layers_panel.tree
    QTest.mouseMove(tree.viewport(),tree.visualItemRect(tree.topLevelItem(0)).center())
    qt_app.processEvents()
    QTest.mouseMove(owner.layers_panel.move_button,owner.layers_panel.move_button.rect().center())
    qt_app.processEvents()


@pytest.mark.parametrize('tool',['select','annotation_select'])
@pytest.mark.parametrize('kind',['text','object','mixed'])
def test_pointer_to_layers_preserves_highlights_count_and_transfer(editor,qt_app,tool,kind):
    owner,drawing,selection,labels,annotations = selected_editor(editor,tool,kind)
    before = deepcopy(drawing.snapshot())
    history = len(drawing.undo_stack)
    highlights = list(drawing.annotation.preview)+list(drawing.selection.highlights)
    assert highlights and all(item.isVisible() for item in highlights)
    assert drawing.measurement.isVisible()
    leave_for_layers(owner,drawing,qt_app)
    actual_annotations = selection.selected_annotations if tool == 'select' else selection.selected
    assert selection.selected_labels == labels and actual_annotations == annotations
    assert all(item.isVisible() for item in highlights)
    assert drawing.measurement.isVisible() and owner.layers_panel.move_button.isEnabled()
    assert drawing.snapshot() == before and len(drawing.undo_stack) == history
    observed = []
    def accept():
        dialog = QApplication.activeModalWidget()
        observed.append(isinstance(dialog,QInputDialog))
        if dialog is not None:
            dialog.accept()
    QTimer.singleShot(0,accept)
    owner.layers_panel.move_button.click()
    assert observed == [True]
    assert len(drawing.labels()) == len(labels) and len(drawing.annotations()) == len(annotations)
    assert len(drawing.undo_stack) == history+1


@pytest.mark.parametrize('tool',['select','annotation_select'])
def test_move_preview_hides_when_pointer_leaves_and_returns_without_editing(editor,qt_app,tool):
    owner,drawing,selection,_labels,_annotations = selected_editor(editor,tool)
    before = deepcopy(drawing.snapshot())
    assert selection.begin_move()
    position = QPointF(drawing.view.mapFromScene(QPointF(450,350)))
    selection.update_move(position)
    previews = list(drawing.text.preview_items)+list(drawing.annotation.preview)+list(drawing.selection.highlights)
    assert previews and any(item.isVisible() for item in previews)
    leave_for_layers(owner,drawing,qt_app)
    assert selection.moving and all(not item.isVisible() for item in previews)
    assert not drawing.measurement.isVisible() and drawing.snapshot() == before
    move(drawing.view,position.toPoint())
    previews = list(drawing.text.preview_items)+list(drawing.annotation.preview)+list(drawing.selection.highlights)
    assert previews and any(item.isVisible() for item in previews)


def test_pending_rectangle_still_hides_when_entering_layers(editor,qt_app):
    owner,drawing = editor
    drawing.begin_placement(200,150)
    assert drawing.preview.isVisible()
    leave_for_layers(owner,drawing,qt_app)
    assert not drawing.preview.isVisible() and drawing.pending_size == (200,150)
    assert not owner.session.dirty
