"""One transform for structure, furniture, labels and bound AP symbols."""
from copy import deepcopy
from unittest.mock import patch

import pytest
from PySide6.QtCore import QPointF, Qt
from PySide6.QtTest import QTest
from survey.plan_geometry import translate_segments
from survey.plan_annotations import transform_annotations
from survey.plan_labels import transform_labels
from survey.plan_layers import add_layer
from tests.test_rectangle_design import editor as editor, drag, move
from tests.test_capture_adapter import window as window, qt_app as qt_app
from tests.test_wall_thickness import rectangle
from tests.test_plan_objects import obj
from tests.test_plan_annotations import aperture, marker
from tests.test_plan_text_fill import label
from tests.test_network_plan_symbols import ap,symbol
from tests.test_plan_rotation import orbit


def content(editor):
    owner,d = editor
    owner.session.set_ap_groups([ap()],update_memory=False)
    items = [aperture(x1=200,y1=100,x2=250,y2=100),
             obj(cx=230,cy=200,width=60,height=40),
             marker(points=[[200,300],[300,330]]),
             symbol('wifi_ap','ap-icon',cx=400,cy=350,ap_group='ap-a'),
             obj(id='outside',cx=700,cy=220,width=60,height=40)]
    d.store(rectangle(w=400,h=400),labels=[dict(label(),x=300,y=250)],annotations=items)
    owner.plan_tools.select_tool('select')
    return owner,d


def at(d,x,y):
    return d.view.mapFromScene(QPointF(x,y))


def room(d):
    QTest.mouseClick(d.view.viewport(),Qt.MouseButton.RightButton,pos=at(d,150,450))


def test_click_room_selects_only_its_contents_and_move_keeps_one_history_entry(editor):
    owner,d = content(editor)
    room(d)
    s=d.selection
    assert len(s.selected)==4 and len(s.selected_annotations)==4 and len(s.selected_labels)==1
    original_items=deepcopy(d.annotations()); original_labels=deepcopy(d.labels())
    original_lines=deepcopy(d.segments()); history=len(d.undo_stack)
    assert s.begin_move()
    s.update_move(QPointF(at(d,250,450)),bypass=True)
    dx,dy = s.move_preview[0]['x1']-original_lines[0]['x1'],s.move_preview[0]['y1']-original_lines[0]['y1']
    assert dx == pytest.approx(100,abs=1) and dy == pytest.approx(0,abs=1)
    assert s.apply_transformed(s.move_preview,s.move_label_preview,s.move_curve_preview,s.move_annotation_preview)
    assert d.segments()==translate_segments(original_lines,dx,dy)
    expected=transform_annotations(original_items[:4],dx=dx,dy=dy)
    assert d.annotations()==expected+[original_items[4]]
    assert d.labels()==transform_labels(original_labels,dx=dx,dy=dy)
    assert owner.session.get_ap_groups()[0]['position']['x']==400+dx
    assert len(d.undo_stack)==history+1
    assert d.undo() and d.annotations()==original_items and d.labels()==original_labels
    assert d.redo() and d.annotations()==expected+[original_items[4]]


def test_rectangle_selection_combines_structure_text_and_annotations(editor):
    _owner,d=content(editor)
    drag(d.view,at(d,90,90),at(d,510,510))
    assert len(d.selection.selected)==4
    assert len(d.selection.selected_annotations)==4
    assert len(d.selection.selected_labels)==1


def test_structure_only_filter_preserves_independent_annotations_and_text(editor):
    owner,d=content(editor)
    owner.plan_tools.include_annotations.setChecked(False)
    room(d)
    s=d.selection
    assert len(s.selected)==4 and not (s.selected_annotations or s.selected_labels)
    before=deepcopy(d.annotations()); texts=deepcopy(d.labels())
    assert s.apply_transformed(translate_segments(d.segments(),100,0))
    assert d.annotations()[0]==transform_annotations([before[0]],dx=100)[0]  # Hosted door.
    assert d.annotations()[1:]==before[1:] and d.labels()==texts


@pytest.mark.parametrize('held',[False,True,'moving'])
def test_shared_rotation_carries_annotated_contents_and_ap_position(editor,held):
    owner,d=content(editor)
    room(d)
    before=deepcopy(d.annotations()); texts=deepcopy(d.labels())
    if held=='moving':
        assert d.selection.begin_move()
        d.selection.update_move(QPointF(at(d,250,450)),bypass=True)
        before=deepcopy(d.selection.move_annotation_preview)+[before[4]]
        texts=deepcopy(d.selection.move_label_preview)
    if held:
        QTest.keyPress(d.view,Qt.Key.Key_R)
        assert d.rotation.active and len(d.rotation.annotation_base)==4
        pivot=d.rotation.pivot
        orbit(owner,d,0);orbit(owner,d,35)
        assert d.rotation.angle==35
        QTest.keyRelease(d.view,Qt.Key.Key_R)
        angle=35
        if held=='moving':
            s=d.selection
            assert s.moving
            assert s.apply_transformed(s.move_preview,s.move_label_preview,s.move_curve_preview,s.move_annotation_preview)
    else:
        pivot=(300,300);angle=90
        QTest.keyClick(d.view,Qt.Key.Key_R)
    expected=transform_annotations(before[:4],angle,pivot)
    assert d.annotations()==expected+[before[4]]
    assert d.labels()==transform_labels(texts,angle,pivot)
    position=owner.session.get_ap_groups()[0]['position']
    assert position['x']==pytest.approx(expected[3]['cx']) and position['y']==pytest.approx(expected[3]['cy'])


def test_escape_cancels_group_preview_then_deselects_tool_without_closing_mode(editor):
    owner,d=content(editor)
    room(d)
    before=deepcopy(owner.session.metadata)
    assert d.selection.begin_move()
    move(d.view,at(d,250,450))
    QTest.keyClick(owner,Qt.Key.Key_Escape)
    assert not d.selection.moving and owner.plan_tools.active_tool is None
    assert owner.session.metadata==before
    assert all(item.opacity()==1 for item in d.annotation.items)
    assert owner.plan_tools.active_tool is None and owner.plan_tools.open
    assert not owner.plan_tools.select_button.isChecked()


def test_idle_escape_unchecks_tool_and_neutral_right_click_never_captures(editor):
    owner,d=editor
    for tool in ('rectangle','line','circle','arc','eraser','select','annotation_select','annotation_eraser'):
        owner.plan_tools.select_tool(tool)
        QTest.keyClick(owner,Qt.Key.Key_Escape)
        assert owner.plan_tools.active_tool is None and owner.plan_tools.open,tool
    captured=[]
    d.view.surveyPointRequested.connect(lambda *a:captured.append(a))
    drag(d.view,at(d,100,100),at(d,300,300))
    assert not captured and not d.segments() and d.pending_size is None
    assert d.view.viewport().cursor().shape()==Qt.CursorShape.ArrowCursor


def test_design_reopens_with_no_tool_selected(editor):
    owner,d=editor
    owner.plan_tools.select_tool('line')
    owner.plan_tools.set_open(False);owner.plan_tools.set_open(True)
    assert owner.plan_tools.active_tool is None
    assert not owner.plan_tools.line_button.isChecked()


def test_points_table_closes_design_and_resets_the_tool_before_reopening(editor):
    owner,d=editor
    owner.plan_tools.select_tool('line')
    owner.toggle_points_panel()
    assert not owner.plan_tools.open and owner.plan_tools.active_tool is None
    assert not owner.plan_tools.line_button.isChecked()
    owner.plan_tools.set_open(True)
    assert owner.plan_tools.active_tool is None and not owner.points_panel_expanded


def test_delete_shared_group_and_undo_restore_annotations_and_binding(editor):
    owner,d=content(editor)
    room(d)
    before=deepcopy(d.snapshot())
    assert d.selection.delete_selected()
    assert not d.segments() and not d.labels()
    assert [a['id'] for a in d.annotations()]==['outside']
    assert not owner.session.get_ap_groups()[0].get('position')
    assert d.undo() and d.annotations()==before['annotations'] and d.labels()==before['labels']
    assert owner.session.get_ap_groups()[0]['position']['x']==400


def test_layer_transfer_includes_shared_selection_and_keeps_other_layers_safe(editor):
    owner,d=content(editor)
    doc=add_layer(d.layer_document(),'Target');doc['active']='0'
    d.change_layers(doc)
    room(d)
    with patch('qt_ui.qt_layers.QInputDialog.getItem',return_value=('Target',True)):
        owner.layers_panel.move_selected()
    doc=d.layer_document()
    source=next(l for l in doc['layers'] if l['id']=='0')['drawing']
    target=next(l for l in doc['layers'] if l['name']=='Target')['drawing']
    assert not source['segments'] and [a['id'] for a in source['annotations']]==['outside']
    assert len(target['segments'])==4 and len(target['annotations'])==4 and len(target['labels'])==1


def test_clicking_annotation_in_main_select_moves_only_that_annotation(editor):
    _owner,d=content(editor)
    QTest.mouseClick(d.view.viewport(),Qt.MouseButton.RightButton,pos=at(d,230,200))
    assert not d.selection.selected and len(d.selection.selected_annotations)==1
    assert d.selection.begin_move()
    before=deepcopy(d.segments())
    assert before==d.segments()


def test_properties_return_selection_to_shared_controller_for_next_move(editor):
    owner,d=content(editor)
    d.selection.set_selected((),annotation_indices=[1])
    with patch.object(d.annotation,'edit') as edit:
        owner.plan_tools.edit_selected_text()
    assert edit.call_count==1
    assert d.selection.selected_annotations==(1,) and not d.annotation.selected
    assert d.selection.begin_move()


def test_partial_host_move_rejects_instead_of_silently_losing_door(editor):
    owner,d=editor
    lines=[dict(x1=100,y1=200,x2=250,y2=200,color='#123456'),
           dict(x1=250,y1=200,x2=400,y2=200,color='#654321')]
    d.store(lines,annotations=[aperture(x1=200,y1=200,x2=300,y2=200)])
    owner.plan_tools.select_tool('select')
    d.selection.set_selected([0])
    before=deepcopy(owner.session.metadata)
    assert not d.selection.apply_transformed(translate_segments([d.segments()[0]],0,100))
    assert owner.session.metadata==before and len(d.annotations())==1
    assert owner.status.currentMessage()==owner.tr('selection_opening_support')


def test_closed_region_selection_does_not_take_objects_or_markers_across_holes(qt_app):
    from survey.plan_faces import RegionPicker
    from survey.selection_geometry import region_contents
    from survey.plan_curve_geometry import normalize_plan
    lines,curves=normalize_plan(rectangle(w=500,h=400)+rectangle(x=250,y=200,w=100,h=100),[])
    path,region=max(RegionPicker(lines,curves).records,key=lambda item:item[1].area)
    items=[marker(points=[[200,250],[400,250]]),
           marker(id='inside',points=[[150,150],[450,150]]),
           obj(cx=300,cy=250,width=100,height=100)]
    indices,_labels=region_contents(path,items,[],[lines[i] for i in region.lines])
    assert indices==[1]
