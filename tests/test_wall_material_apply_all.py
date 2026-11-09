"""Bulk material editing stays within one shape and the existing transaction."""
from copy import deepcopy
from unittest.mock import patch

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QDialog

from qt_ui.qt_wall_sides import WallSidesDialog, edit_wall_sides
from survey.wall_conversion import reference_regions
from survey.wall_layout import plan_wall_layout
from survey.wall_materials import appearance
from survey.wall_sides import same_wall_faces, stage_structure, wall_sides
from tests.test_wall_thickness import state, rectangle, BOUNDS
from tests.test_rectangle_design import editor
from tests.test_capture_adapter import window, qt_app


def rooms(shared=False):
    original = state(rectangle() + rectangle(x=300 if shared else 550))
    result = plan_wall_layout(original, range(len(original['segments'])), (), 20, BOUNDS).state
    for i, shape in enumerate(result['segments']):
        shape['wall'].update(material='wood', pattern=('cross', 'dots', 'grid')[i % 3])
    # Shared physical faces must start with the same appearance.
    for i, shape in enumerate(result['segments']):
        for other in result['segments'][i+1:]:
            if same_wall_faces(shape, other):
                other['wall'].update(material='wood', pattern=shape['wall']['pattern'])
    return result


def first_room(original):
    return min(reference_regions(original).records, key=lambda pair: pair[0].boundingRect().left())[1]


def click_all(dialog):
    assert dialog.apply_all_material_button.isEnabled()
    QTest.mouseClick(dialog.apply_all_material_button, Qt.MouseButton.LeftButton)


def test_material_copies_to_current_form_preserving_patterns_widths_and_other_rooms(editor):
    owner, drawing = editor
    original = rooms()
    drawing.store(original['segments'])
    indices = list(first_room(original).lines)
    before, history = deepcopy(owner.session.metadata), len(drawing.undo_stack)
    dialog = WallSidesDialog(owner, original, wall_sides(original, indices), form_indices=indices)
    patterns = {side.index: appearance(dialog.appearances[side.index])[1] for side in dialog.sides}
    widths = dict(dialog.values)
    dialog.material.setCurrentIndex(dialog.material.findData('brick'))
    click_all(dialog)
    assert dialog.candidate and not dialog.result.changed_positions
    assert dialog.values == widths
    expected = deepcopy(original)
    for index in indices:
        expected['segments'][index]['wall']['material'] = 'brick'
        assert appearance(dialog.appearances[index]) == ('brick', patterns[index])
    assert dialog.result.state == expected
    assert owner.session.metadata == before and len(drawing.undo_stack) == history
    dialog.reject()
    dialog.deleteLater()


@pytest.mark.parametrize('shared', [False, True])
def test_multiple_selected_shapes_apply_only_to_the_shape_of_the_selected_side(editor, shared):
    owner, _drawing = editor
    original = rooms(shared)
    indices = set(first_room(original).lines)
    dialog = WallSidesDialog(owner, original, wall_sides(original, range(len(original['segments']))))
    row = next(i for i, side in enumerate(dialog.sides) if side.index in indices and not side.shared)
    dialog.table.selectRow(row)
    assert {side.index for side in dialog.material_targets()} == indices
    dialog.material.setCurrentIndex(dialog.material.findData('glass'))
    click_all(dialog)
    assert dialog.candidate and not dialog.result.changed_positions
    for i, shape in enumerate(original['segments']):
        associated = i in indices or any(same_wall_faces(shape, original['segments'][j]) for j in indices)
        assert appearance(dialog.result.state['segments'][i]['wall'])[0] == ('glass' if associated else 'wood')
        assert appearance(dialog.appearances[i])[0] == ('glass' if associated else 'wood')
    if shared:
        assert dialog.shared_signature and not dialog.apply_button.isEnabled()
    for i, side in enumerate(dialog.sides):
        if sum(side.index in form for form in dialog.material_forms) > 1:
            dialog.table.selectRow(i)
            assert not dialog.apply_all_material_button.isEnabled()
    dialog.reject()
    dialog.deleteLater()


def test_new_shape_skips_sides_without_thickness(editor):
    owner, _drawing = editor
    staged, sides, anchor = stage_structure(state(), rectangle())
    dialog = WallSidesDialog(owner, staged, sides, anchor, placing=True)
    assert not dialog.apply_all_material_button.isEnabled()
    dialog.spins[0].setValue(.2)
    dialog.spins[1].setValue(.4)
    dialog.table.selectRow(0)
    dialog.material.setCurrentIndex(dialog.material.findData('metal'))
    widths = dict(dialog.values)
    click_all(dialog)
    assert dialog.candidate and dialog.values == widths
    for side in dialog.sides:
        shape = dialog.result.state['segments'][side.index]
        if widths[side.index] > 0:
            assert shape['wall']['material'] == 'metal'
        else:
            assert 'wall' not in shape and dialog.appearances[side.index] == {}
    dialog.reject()
    dialog.deleteLater()


def test_bulk_shared_change_requires_fresh_confirmation_and_cancel_discards_it(editor):
    owner, drawing = editor
    original = plan_wall_layout(state(rectangle()), range(4), (), 20, BOUNDS).state
    for shape in original['segments']:
        shape['wall']['material'] = 'wood'
    drawing.store(original['segments'])
    before, history = deepcopy(owner.session.metadata), len(drawing.undo_stack)
    staged, sides, anchor = stage_structure(original, rectangle(x=300))
    dialog = WallSidesDialog(owner, staged, sides, anchor, placing=True)
    for spin in dialog.spins:
        spin.setValue(.4)
    row = next(i for i, side in enumerate(sides) if not side.shared)
    dialog.table.selectRow(row)
    dialog.material.setCurrentIndex(dialog.material.findData('brick'))
    click_all(dialog)
    assert dialog.candidate and dialog.shared_signature and not dialog.apply_button.isEnabled()
    dialog.confirm_shared.setChecked(True)
    assert dialog.apply_button.isEnabled()
    dialog.material.setCurrentIndex(dialog.material.findData('glass'))
    click_all(dialog)
    assert not dialog.confirm_shared.isChecked() and not dialog.apply_button.isEnabled()
    dialog.reject()
    assert owner.session.metadata == before and len(drawing.undo_stack) == history
    dialog.deleteLater()


def test_bulk_edit_commits_once_and_survives_undo_redo_and_reopening(editor, tmp_path):
    owner, drawing = editor
    original = rooms()
    drawing.store(original['segments'])
    region = first_room(original)
    before, history = deepcopy(drawing.snapshot()), len(drawing.undo_stack)

    def review(dialog):
        dialog.material.setCurrentIndex(dialog.material.findData('concrete'))
        click_all(dialog)
        assert dialog.candidate and dialog.apply_button.isEnabled()
        return QDialog.DialogCode.Accepted

    with patch.object(WallSidesDialog, 'exec', review):
        assert edit_wall_sides(owner, region)
    changed = deepcopy(drawing.snapshot())
    changed_lines = deepcopy(drawing.segments())
    assert len(drawing.undo_stack) == history + 1
    assert drawing.undo() and drawing.snapshot() == before
    assert drawing.redo() and drawing.snapshot() == changed
    owner.session.csv_file = str(tmp_path / 'all-materials.csv')
    assert owner.save_survey() and owner.open_survey(owner.session.csv_file)
    assert drawing.segments() == changed_lines


def test_current_form_material_includes_curved_sides(editor):
    owner, _drawing = editor
    line = dict(x1=100, y1=300, x2=500, y2=300, color='#263238')
    arc = dict(kind='arc', x1=500, y1=300, x2=100, y2=300, height=120, color='#263238')
    original = plan_wall_layout(state([line], [arc]), [0], [0], 20, BOUNDS).state
    original['segments'][0]['wall'].update(material='wood', pattern='cross')
    original['curves'][0]['wall'].update(material='wood', pattern='dots')
    dialog = WallSidesDialog(owner, original, wall_sides(original, [0, 1]))
    dialog.material.setCurrentIndex(dialog.material.findData('glass'))
    click_all(dialog)
    assert dialog.candidate and not dialog.result.changed_positions
    assert appearance(dialog.result.state['segments'][0]['wall']) == ('glass', 'cross')
    assert appearance(dialog.result.state['curves'][0]['wall']) == ('glass', 'dots')
    dialog.reject()
    dialog.deleteLater()
