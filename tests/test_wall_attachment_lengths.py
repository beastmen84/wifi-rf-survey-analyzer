"""An exact 1.30 m line retains 1.30 m beyond an attached 0.10 m wall."""
from copy import deepcopy
import math
from unittest.mock import patch

import pytest
from PySide6.QtCore import QLineF, QPointF
from PySide6.QtWidgets import QDialog

from survey.wall_attachments import WallAttachmentIndex
from survey.plan_geometry import rotate_degrees
from qt_ui.qt_wall_sides import WallSidesDialog
from tests.test_wall_thickness import state
from tests.test_plan_annotations import aperture, at, choose
from tests.test_rectangle_design import editor, move
from tests.test_capture_adapter import window, qt_app


def host(side=1):
    profile=dict(width=5,side=side)
    if side==0:
        profile['reference']='axis'
    return dict(x1=100,y1=200,x2=700,y2=200,color='#475569',wall=profile)


@pytest.mark.parametrize('side,sign,hidden', [(1,1,5),(-1,-1,5),(0,1,2.5),(0,-1,2.5)])
@pytest.mark.parametrize('angle',[0,35,90,180])
def test_exact_numeric_length_compensates_only_the_hidden_attachment(editor,side,sign,hidden,angle):
    owner,drawing=editor
    pivot=(400,300)
    lines=rotate_degrees([host(side)],angle,pivot)
    drawing.store(lines)
    choose(owner,'line')
    owner.plan_tools.snap_button.setChecked(False)
    source=rotate_degrees([dict(x1=400,y1=200,x2=400,y2=200+65*sign,color='#475569')],angle,pivot)[0]
    drawing.line.angle=(90*sign+angle)%360
    drawing.line.begin_placement(65,QPointF(source['x1'],source['y1']))
    placed=drawing.line.geometry(QPointF(source['x1'],source['y1']))
    assert placed.length()==pytest.approx(65+hidden)
    assert (placed.x1(),placed.y1())==pytest.approx((source['x1'],source['y1']))
    assert drawing.line.measured_line(placed).length()==pytest.approx(65)
    drawing.line.show_preview(placed,QPointF(at(owner,source['x1'],source['y1'])))
    assert drawing.line.preview.line().length()==pytest.approx(65)
    assert '1,30' in drawing.measurement.text() or '1.30' in drawing.measurement.text()


def test_oblique_departure_adds_the_actual_crossed_depth():
    index=WallAttachmentIndex([state([host()])])
    u=math.sqrt(.5)
    assert index.hidden((400,200),(u,u))==pytest.approx(5/u)
    assert index.hidden((400,200),(1,0))==0  # Shared/collinear construction stays unchanged.
    assert index.hidden((400,205),(0,1))==0  # Already beyond the physical face.


@pytest.mark.parametrize('x',[100,700])
def test_end_cap_attachments_also_add_the_ten_centimeters(x):
    index=WallAttachmentIndex([state([host()])])
    assert index.hidden((x,200),(0,1))==pytest.approx(5)


def test_opposite_shared_faces_are_counted_once():
    other=dict(host(),x1=700,y1=205,x2=100,y2=205)
    index=WallAttachmentIndex([state([host(),other])])
    assert index.hidden((400,200),(0,1))==pytest.approx(5)


def test_end_anchor_extends_the_other_endpoint_and_alt_keeps_literal_coordinates(editor):
    owner,drawing=editor
    drawing.store([host(-1)])
    choose(owner,'line')
    drawing.line.angle=90
    drawing.line.begin_placement(65,QPointF(400,135))
    placed=drawing.line.geometry(QPointF(400,135))
    assert (placed.y1(),placed.y2())==pytest.approx((130,200))
    assert drawing.line.measured_line(placed).length()==pytest.approx(65)
    raw=drawing.line.geometry(QPointF(400,135),bypass=True)
    assert (raw.y1(),raw.y2(),raw.length())==pytest.approx((135,200,65))


def test_drag_readout_reports_the_exposed_length_without_moving_the_pointer(editor):
    owner,drawing=editor
    drawing.store([host()])
    choose(owner,'line')
    drawing.line.origin=QPointF(400,200)
    line=drawing.line.geometry(QPointF(400,270))
    assert line.p2()==QPointF(400,270)
    drawing.line.show_preview(line,QPointF(at(owner,400,270)))
    assert drawing.line.preview.line()==QLineF(400,205,400,270)
    assert '1,30' in drawing.measurement.text() or '1.30' in drawing.measurement.text()


def test_commit_review_hover_and_reopening_keep_the_useful_length(editor,tmp_path):
    owner,drawing=editor
    drawing.store([host()])
    before,history=deepcopy(drawing.snapshot()),len(drawing.undo_stack)
    choose(owner,'line')
    drawing.line.angle=90
    drawing.line.begin_placement(65,QPointF(400,200))
    line=drawing.line.geometry(QPointF(400,200))
    seen=[]
    def review(dialog):
        seen.extend(dialog.table.item(i,1).text() for i in range(dialog.table.rowCount()))
        return QDialog.DialogCode.Accepted
    with patch.object(WallSidesDialog,'exec',review):
        assert drawing.line.commit(line)
    assert any(float(text.split()[0].replace(',','.'))==pytest.approx(1.3) for text in seen)
    drawing.line.cancel()
    assert len(drawing.undo_stack)==history+1
    added=next(s for s in drawing.segments() if s['x1']==s['x2']==400)
    assert (added['y1'],added['y2'])==pytest.approx((200,270))
    move(drawing.view,at(owner,400,240))
    values=drawing.dimensions.values
    assert values and values['before_m']+values['after_m']==pytest.approx(1.3)
    changed=deepcopy(drawing.segments())
    assert drawing.undo() and drawing.snapshot()==before
    assert drawing.redo() and drawing.segments()==changed
    owner.session.csv_file=str(tmp_path/'clear-130.csv')
    assert owner.save_survey() and owner.open_survey(owner.session.csv_file)
    assert drawing.segments()==changed


def test_opening_gaps_do_not_add_a_wall_that_is_not_there():
    opening=aperture(variant='frame',x1=350,y1=200,x2=450,y2=200)
    index=WallAttachmentIndex([state([host()],annotations=[opening])])
    assert index.hidden((400,200),(0,1))==0


def test_unfit_numeric_length_is_rejected_without_history_or_partial_changes(editor):
    owner,drawing=editor
    second=dict(host(-1),y1=280,y2=280,wall=dict(width=30,side=-1))
    drawing.store([host(),second])
    before,history=deepcopy(owner.session.metadata),len(drawing.undo_stack)
    choose(owner,'line')
    drawing.line.angle=90
    drawing.line.begin_placement(65,QPointF(400,200))
    line=drawing.line.geometry(QPointF(400,200))
    assert not drawing.line.commit(line)
    assert owner.session.metadata==before and len(drawing.undo_stack)==history


def test_compensation_must_not_push_the_line_outside_the_sheet(editor):
    owner,drawing=editor
    drawing.store([dict(host(),y1=535,y2=535)])
    before,history=deepcopy(owner.session.metadata),len(drawing.undo_stack)
    choose(owner,'line')
    drawing.line.angle=90
    drawing.line.begin_placement(65,QPointF(400,535))
    line=drawing.line.geometry(QPointF(400,535))
    assert line.y2()>drawing.view.scene.sceneRect().bottom()
    assert not drawing.line.commit(line)
    assert owner.session.metadata==before and len(drawing.undo_stack)==history
