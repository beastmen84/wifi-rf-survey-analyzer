"""Zoom emitted during scene replacement must not visit destroyed graphics."""
from unittest.mock import patch

from survey.plan_layers import add_layer
from tests.test_blank_plan import create_survey
from tests.test_network_plan_symbols import symbol
from tests.test_wall_thickness import rectangle
from tests.test_rectangle_design import editor as editor
from tests.test_capture_adapter import window as window, qt_app as qt_app


def test_new_survey_does_not_update_deleted_active_or_passive_symbol_items(editor,qt_app):
    owner,drawing=editor
    drawing.store(rectangle(),annotations=[symbol(identity='base',number=1)])
    drawing.change_layers(add_layer(drawing.layer_document(),'Furniture'))
    drawing.store([],annotations=[symbol(identity='upper',number=2,cx=550)])
    assert drawing.passive_items and drawing.annotation.items
    with patch('sys.excepthook') as uncaught:
        create_survey(owner,width=20,height=15)
        qt_app.processEvents()
        assert not uncaught.called, [str(call.args[1]) for call in uncaught.call_args_list]
    assert drawing.pixmap is drawing.view.pixmap_item
    assert not drawing.annotations() and not drawing.passive_items
    drawing.store([],annotations=[symbol(identity='new',number=1)])
    drawing.view.zoom_in()
    assert drawing.annotation.items
