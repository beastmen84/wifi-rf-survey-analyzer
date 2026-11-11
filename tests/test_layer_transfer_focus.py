"""A native layer dialog must not erase the selection it is transferring."""
from copy import deepcopy
from unittest.mock import patch

import pytest
from PySide6.QtCore import QEvent,QTimer
from PySide6.QtWidgets import QApplication,QInputDialog

from survey.plan_layers import add_layer
from tests.test_plan_text_fill import label
from tests.test_rectangle_design import editor
from tests.test_capture_adapter import window, qt_app


@pytest.mark.parametrize('tool',['select','annotation_select'])
@pytest.mark.parametrize('accepted',[True,False])
def test_layer_transfer_keeps_text_selection_through_modal_deactivation(editor,tool,accepted):
    owner,drawing = editor
    doc = add_layer(drawing.layer_document(),'Texts')
    doc['active'] = '0'
    drawing.change_layers(doc)
    drawing.store([],labels=[label()])
    owner.plan_tools.select_tool(tool)
    if tool == 'select':
        drawing.selection.set_selected((),(0,))
    else:
        drawing.annotation.select((),(0,))
    before = deepcopy(drawing.snapshot())
    history = len(drawing.undo_stack)
    def choose(*_args,**_kwargs):
        QApplication.sendEvent(owner,QEvent(QEvent.Type.WindowDeactivate))
        return 'Texts',accepted
    with patch('qt_ui.qt_layers.QInputDialog.getItem',side_effect=choose):
        owner.layers_panel.move_selected()
    if accepted:
        doc = drawing.layer_document()
        assert not doc['layers'][0]['drawing']['labels']
        assert len(doc['layers'][1]['drawing']['labels']) == 1
        assert len(drawing.undo_stack) == history+1
        assert drawing.undo() and drawing.labels() == before['labels']
        assert drawing.redo() and len(drawing.labels()) == 1
    else:
        assert drawing.snapshot() == before and len(drawing.undo_stack) == history
        controller = drawing.selection if tool == 'select' else drawing.annotation
        assert controller.selected_labels == (0,)


def test_transfer_exception_restores_external_deactivation_behavior(editor):
    owner,drawing = editor
    doc = add_layer(drawing.layer_document(),'Texts')
    doc['active'] = '0'
    drawing.change_layers(doc)
    drawing.store([],labels=[label()])
    owner.plan_tools.select_tool('select')
    drawing.selection.set_selected((),(0,))
    with patch('qt_ui.qt_layers.QInputDialog.getItem',side_effect=RuntimeError('dialog failed')):
        with pytest.raises(RuntimeError,match='dialog failed'):
            owner.layers_panel.move_selected()
    assert not owner.layers_panel.dialog_open and drawing.selection.selected_labels == (0,)
    QApplication.sendEvent(owner,QEvent(QEvent.Type.WindowDeactivate))
    assert not drawing.selection.has_selection()


def test_real_destination_dialog_keeps_selected_text_and_closes_guard(editor):
    owner,drawing = editor
    doc = add_layer(drawing.layer_document(),'Texts')
    doc['active'] = '0'
    drawing.change_layers(doc)
    drawing.store([],labels=[label()])
    owner.plan_tools.select_tool('select')
    drawing.selection.set_selected((),(0,))
    owner.layers_panel.set_open(True,save=False)
    assert owner.layers_panel.move_button.isEnabled()
    observed = []
    def answer():
        dialog = QApplication.activeModalWidget()
        observed.append(isinstance(dialog,QInputDialog) and owner.layers_panel.dialog_open)
        if dialog is not None:
            QApplication.sendEvent(owner,QEvent(QEvent.Type.WindowDeactivate))
            dialog.accept()
    QTimer.singleShot(0,answer)
    owner.layers_panel.move_button.click()
    assert observed == [True] and not owner.layers_panel.dialog_open
    assert drawing.layer_document()['layers'][0]['drawing']['labels'] == []
    assert len(drawing.labels()) == 1
