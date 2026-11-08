"""Material edits preserve physical geometry, shared faces and vector rendering."""
from copy import deepcopy
from unittest.mock import patch

import pytest
from PIL import Image
from PySide6.QtCore import QRectF, QSize
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QDialog
from survey.wall_materials import MATERIALS, PATTERNS, appearance
from survey.wall_properties import validated_wall
from survey.wall_sides import stage_structure, wall_sides, apply_side_widths
from survey.wall_layout import plan_wall_layout
from survey.wall_conversion import convert_wall_reference
from survey.wall_geometry import wall_commands, wall_solids, path_area
from survey.wall_rendering import MaterialPath
from survey.plan_curve_geometry import normalize_plan
from survey.plan_curves import subcurve, transform_curves
from survey.plan_geometry import rotate_degrees, translate_segments
from survey.plan_drawing import render_plan_drawing
from survey.plan_faces import RegionPicker
from qt_ui.qt_clean_plan import VectorPlanSource
from qt_ui.qt_wall_sides import WallSidesDialog, edit_wall_sides
from tests.test_wall_thickness import state, rectangle, BOUNDS
from tests.test_plan_annotations import aperture
from tests.test_rectangle_design import editor as editor
from tests.test_capture_adapter import window as window, qt_app as qt_app


def thick():
    return plan_wall_layout(state(rectangle()),range(4),(),20,BOUNDS).state


def decorate(original, material='wood', pattern='auto', indices=None):
    indices = range(len(original['segments'])) if indices is None else indices
    sides = wall_sides(original,indices)
    return apply_side_widths(original,sides,{s.index:s.shape['wall']['width'] for s in sides},BOUNDS,
                             appearances={s.index:dict(material=material,pattern=pattern) for s in sides})


@pytest.mark.parametrize('material', MATERIALS)
def test_each_material_is_valid_and_changes_no_dimensions_or_areas(qt_app, material):
    original=thick(); before=deepcopy(original)
    result=decorate(original,material)
    assert original == before and not result.changed_positions
    assert result.moves == ((0,0),) and result.areas == (40000,)
    assert [{k:v for k,v in s.items() if k!='wall'} for s in result.state['segments']] == [
        {k:v for k,v in s.items() if k!='wall'} for s in original['segments']]
    assert all(appearance(s['wall']) == (material,'auto') for s in result.state['segments'])
    assert sum(path_area(p) for _,p in wall_solids(result.state['segments'])) == pytest.approx(17600)


@pytest.mark.parametrize('bad', [{'material':'cement'}, {'pattern':'texture'}, {'material':[]},
                                 {'pattern':None}, {'material':True}, {'coefficient':12}])
def test_material_properties_reject_unknown_or_malformed_values(bad):
    with pytest.raises(ValueError):
        validated_wall(dict(width=20,side=1,**bad))


def test_legacy_profiles_keep_exact_shape_and_default_appearance():
    assert validated_wall(dict(width=20,side=1)) == dict(width=20,side=1)
    assert validated_wall(dict(width=20,side=1,material='unspecified',pattern='auto')) == dict(width=20,side=1)


def test_different_materials_do_not_merge_but_identical_reversed_fragments_do(qt_app):
    first=dict(x1=100,y1=100,x2=200,y2=100,color='#263238',wall=dict(width=20,side=1,material='wood'))
    second=dict(first,x1=300,x2=200,wall=dict(width=20,side=-1,material='wood'))
    assert len(normalize_plan([first,second],[])[0]) == 1
    second['wall']['material']='brick'
    assert len(normalize_plan([first,second],[])[0]) == 2
    crossing=dict(x1=150,y1=50,x2=150,y2=150,color='#263238')
    lines,_=normalize_plan([first,crossing],[])
    assert len([s for s in lines if s.get('wall',{}).get('material')=='wood']) == 2
    transformed=translate_segments(rotate_degrees(lines,35,(150,150)),200,200)
    assert all(s['wall']==first['wall'] for s in transformed if s.get('wall'))


def test_material_survives_depth_edit_and_reference_conversion(qt_app):
    current=decorate(thick(),'reinforced_concrete','cross').state
    result=plan_wall_layout(current,range(4),(),25,BOUNDS)
    assert all(s['wall']['material']=='reinforced_concrete' for s in result.state['segments'])
    for mode in ('axis','face','keep'):
        converted=convert_wall_reference(current,range(4),(),20,BOUNDS,mode=mode)
        assert all(appearance(s['wall'])==('reinforced_concrete','cross') for s in converted.state['segments'])
        result=decorate(converted.state,'brick','grid')
        assert all(appearance(s['wall'])==('brick','grid') for s in result.state['segments'])


def test_curves_retain_material_after_splitting_and_rotation(qt_app):
    curve=dict(kind='circle',cx=400,cy=400,radius=100,phase=0,color='#263238',
               wall=dict(width=20,side=-1,material='concrete',pattern='dots'))
    arc=subcurve(curve,.1,.4)
    assert transform_curves([arc],35,(400,400))[0]['wall']==curve['wall']
    original=state(curves=[curve]);sides=wall_sides(original,[0])
    result=apply_side_widths(original,sides,{0:20},BOUNDS,appearances={0:dict(material='glass')})
    assert result.state['curves'][0]['wall']['material']=='glass'


@pytest.mark.parametrize('outer', [False,True])
def test_new_shared_side_inherits_material_and_pattern(qt_app, outer):
    old=decorate(thick(),'concrete_block','cross').state
    staged,sides,anchor=stage_structure(old,rectangle(x=320 if outer else 300))
    shared=[s for s in sides if s.shared]
    assert len(shared)==1 and appearance(shared[0].shape['wall'])==('concrete_block','cross')
    result=apply_side_widths(staged,sides,{s.index:s.shape.get('wall',{}).get('width',0) for s in sides},BOUNDS,anchor=anchor)
    assert len([s for s in result.state['segments'] if s.get('wall',{}).get('material')=='concrete_block']) >= 5


def test_shared_material_change_propagates_without_moving_any_room(qt_app):
    original=plan_wall_layout(state(rectangle()+rectangle(x=300)),range(7),(),20,BOUNDS).state
    room=RegionPicker(original['segments'],[]).records[0][1]
    sides=wall_sides(original,room.lines)
    result=apply_side_widths(original,sides,{s.index:s.shape['wall']['width'] for s in sides},BOUNDS,
                            appearances={s.index:dict(material='brick') if s.shared else {} for s in sides})
    assert not result.changed_positions
    assert len([s for s in result.state['segments'] if s['wall'].get('material')=='brick'])==2


def test_material_controls_require_depth_and_preserve_values_per_side(editor):
    owner,_d=editor
    staged,sides,anchor=stage_structure(state(),rectangle())
    dialog=WallSidesDialog(owner,staged,sides,anchor)
    assert not dialog.material.isEnabled() and not dialog.pattern.isEnabled()
    dialog.spins[0].setValue(.2)
    assert dialog.material.isEnabled()
    dialog.material.setCurrentIndex(dialog.material.findData('wood'))
    dialog.pattern.setCurrentIndex(dialog.pattern.findData('cross'))
    dialog.table.selectRow(1)
    assert dialog.material.currentData()=='unspecified' and not dialog.material.isEnabled()
    dialog.table.selectRow(0)
    assert dialog.material.currentData()=='wood' and dialog.pattern.currentData()=='cross'
    assert dialog.candidate and dialog.result.state['segments'][0]['wall']['material']=='wood'
    dialog.deleteLater()


def test_shared_material_or_pattern_change_requires_new_acknowledgment(editor):
    owner,d=editor
    original=thick();d.store(original['segments'])
    staged,sides,anchor=stage_structure(original,rectangle(x=300))
    dialog=WallSidesDialog(owner,staged,sides,anchor,placing=True)
    row=next(i for i,s in enumerate(sides) if s.shared)
    dialog.table.selectRow(row)
    dialog.material.setCurrentIndex(dialog.material.findData('drywall'))
    assert dialog.shared_signature and not dialog.apply_button.isEnabled()
    dialog.confirm_shared.setChecked(True)
    assert dialog.apply_button.isEnabled()
    dialog.pattern.setCurrentIndex(dialog.pattern.findData('dots'))
    assert not dialog.confirm_shared.isChecked() and not dialog.apply_button.isEnabled()
    dialog.material.setCurrentIndex(0);dialog.pattern.setCurrentIndex(0)
    assert not dialog.shared_signature and dialog.apply_button.isEnabled()
    dialog.deleteLater()


def test_material_only_commit_after_rf_capture_is_atomic_and_survives_save(editor,tmp_path):
    owner,d=editor
    d.store(thick()['segments'])
    region=RegionPicker(d.segments(),[]).records[0][1]
    before=deepcopy(d.snapshot());metadata=deepcopy(owner.session.metadata);count=len(d.undo_stack)
    def edit(dialog):
        dialog.material.setCurrentIndex(dialog.material.findData('clay_block'))
        assert dialog.candidate and not dialog.result.changed_positions
        return QDialog.DialogCode.Accepted
    with patch.object(WallSidesDialog,'exec',edit),patch.object(owner.session,'get_points',return_value=[{}]):
        assert edit_wall_sides(owner,region)
    assert len(d.undo_stack)==count+1
    changed=deepcopy(d.segments())
    assert d.undo() and d.snapshot()==before
    assert d.redo() and d.segments()==changed
    # No existing non-drawing metadata was changed by the material edit.
    for key,value in metadata.items():
        if key not in ('plan_layers','plan_drawing'):
            assert owner.session.metadata.get(key)==value
    owner.session.csv_file=str(tmp_path/'materials.csv')
    assert owner.save_survey() and owner.open_survey(owner.session.csv_file)
    assert d.segments()==changed


def test_cancel_material_review_leaves_metadata_and_history_untouched(editor):
    owner,d=editor;d.store(thick()['segments'])
    region=RegionPicker(d.segments(),[]).records[0][1]
    before=deepcopy(owner.session.metadata);count=len(d.undo_stack)
    def cancel(dialog):
        dialog.material.setCurrentIndex(dialog.material.findData('metal'))
        return QDialog.DialogCode.Rejected
    with patch.object(WallSidesDialog,'exec',cancel):
        assert not edit_wall_sides(owner,region)
    assert owner.session.metadata==before and len(d.undo_stack)==count


def rendered(source,scale):
    image=QImage(source.width()*scale,source.height()*scale,QImage.Format.Format_RGB32)
    image.fill(0xffffffff);painter=QPainter(image)
    try:
        source.paint_plan(painter,QRectF(0,0,image.width(),image.height()))
    finally:
        painter.end()
    return image


@pytest.mark.parametrize('pattern',PATTERNS)
def test_vector_hatch_stays_inside_band_and_cuts_apertures_at_any_output_scale(qt_app,pattern):
    line=dict(x1=100,y1=200,x2=400,y2=200,color='#263238',
              wall=dict(width=30,side=1,material='wood',pattern=pattern))
    opening=aperture(x1=220,x2=270,y1=200,y2=200,variant='frame')
    source=VectorPlanSource(QSize(500,400),[line],[],[],[opening])
    assert isinstance(source._commands[0][0],MaterialPath)
    for scale in (1,4):
        image=rendered(source,scale)
        assert image.pixelColor(245*scale,215*scale).name()=='#ffffff'
        assert image.pixelColor(180*scale,215*scale).name()!='#ffffff'
        assert image.pixelColor(180*scale,240*scale).name()=='#ffffff'
    raster=render_plan_drawing(Image.new('RGB',(500,400),'white'),[line],annotations=[opening])
    assert raster.getpixel((245,215))==(255,255,255)


def test_legacy_commands_and_large_vector_patterns_remain_bounded(qt_app):
    line=dict(x1=100,y1=200,x2=90000,y2=200,color='#263238',wall=dict(width=500,side=1))
    assert not isinstance(wall_commands([line])[0][0],MaterialPath)
    line['wall']['material']='brick'
    path=wall_commands([line])[0][0]
    assert path.hatch.elementCount()+path.joints.elementCount() < 8000


@pytest.mark.parametrize('curved',[False,True])
def test_disconnected_pattern_bodies_preserve_room_holes_and_total_solid_area(qt_app,curved):
    curves=[dict(kind='circle',cx=200+i*300,cy=200,radius=80,phase=0,color='#263238',
                 wall=dict(width=20,side=-1,material='brick')) for i in range(3)] if curved else []
    lines=[] if curved else [dict(s,wall=dict(width=20,side=-1,material='brick'))
                              for i in range(3) for s in rectangle(100+i*300,100,160,160)]
    commands=wall_commands(lines,curves)
    assert len(commands)==3
    assert sum(path_area(p) for p,_,_ in commands)==pytest.approx(sum(path_area(p) for _,p in wall_solids(lines,curves)),abs=.02)
    source=VectorPlanSource(QSize(1000,400),lines,curves,[],[])
    image=rendered(source,2)
    assert all(image.pixelColor((200+i*300)*2,200*2).name()=='#ffffff' for i in range(3))


def test_polygon_hole_bridges_never_become_visible_wall_edges(qt_app):
    lines=[dict(s,wall=dict(width=20,side=-1,material='wood',pattern='solid'))
           for s in rectangle(100,100,160,160)]
    source=VectorPlanSource(QSize(400,400),lines,[],[],[])
    image=rendered(source,2)
    fill=MATERIALS['wood'][0]
    assert all(image.pixelColor(x*2,y*2).name()==fill for x in range(120,241,5) for y in range(85,96))


@pytest.mark.parametrize('kind',['circle','arc'])
@pytest.mark.parametrize('side',[-1,0,1])
@pytest.mark.parametrize('angle',[0,35])
def test_styled_curves_retain_original_cubic_solids_for_face_and_axis_profiles(qt_app,kind,side,angle):
    curve=dict(kind='circle',cx=400,cy=400,radius=100,phase=0,color='#263238') if kind=='circle' else dict(
        kind='arc',x1=200,y1=400,x2=600,y2=400,height=60,color='#263238')
    curve['wall']=dict(width=20,side=side,material='concrete')
    if side==0:
        curve['wall']['reference']='axis'
    curve=transform_curves([curve],angle,(400,400))[0]
    commands=wall_commands([], [curve])
    assert sum(path_area(p) for p,_,_ in commands)==pytest.approx(sum(path_area(p) for _,p in wall_solids([],[curve])),abs=.01)
    assert any(p.elementAt(i).isCurveTo() for p,_,_ in commands for i in range(p.elementCount()))
