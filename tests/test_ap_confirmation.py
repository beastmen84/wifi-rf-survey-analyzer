"""Physical-AP approval across real table interactions, memory and RF analysis."""

from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

from advisor.engine import analyze_survey
from advisor.presentation import finding_html, wording
from ap.groups import (build_default_manual_groups, build_manual_ap_group,
                       invalidate_ap_group_confirmation, is_ap_group_confirmed)
from ap.memory import (apply_ap_memory_to_groups, load_ap_memory,
                       save_ap_memory, update_ap_memory_from_groups)
from qt_ui.qt_ap_groups import APGroupManagerDialog
from survey.store import SurveySession
from tests.test_advisor import fixture_survey, findings
from translations.i18n import translate


@pytest.fixture(autouse=True)
def isolated_state(tmp_path, monkeypatch):
    monkeypatch.setenv("WIFI_HEATMAP_AP_MEMORY_FILE", str(tmp_path / "ap.memory"))
    monkeypatch.setenv("WIFI_HEATMAP_SETTINGS_FILE", str(tmp_path / "settings.json"))


@pytest.fixture
def runtime():
    return QApplication.instance() or QApplication([])


class ManagerApp(QDialog):
    def __init__(self, session):
        super().__init__()
        self.session = session
        self.theme = "light"
        self.language = "en"

    def tr(self, key, **kwargs):
        return translate(self.language, key, **kwargs)

    def channel_sort_key(self, channel):
        return int(channel)


@pytest.fixture
def manager(runtime):
    context = fixture_survey()
    session = SurveySession()
    session.rows, session.raw_scan_rows = context["rows"], context["raw_rows"]
    groups = context["groups"]
    for group in groups:
        group.update(physical_confirmed=False, locked=True)
    session.set_ap_groups(groups, update_memory=False)
    window = ManagerApp(session)
    dialog = APGroupManagerDialog(window)
    yield dialog
    dialog.close()
    dialog.deleteLater()
    window.deleteLater()
    runtime.processEvents()


def approval_item(dialog, group_id="a"):
    for row in range(dialog.table.rowCount()):
        item = dialog.table.item(row, 0)
        if item.data(Qt.ItemDataRole.UserRole) == group_id:
            return item
    raise AssertionError(group_id)


def approve(dialog, group_id="a"):
    approval_item(dialog, group_id).setCheckState(Qt.CheckState.Checked)
    QApplication.processEvents()
    return dialog.get_group_by_id(group_id)


def test_real_badge_click_and_space_toggle_and_save(manager, runtime):
    manager.show()
    runtime.processEvents()
    item = approval_item(manager)
    rect = manager.table.visualItemRect(item)
    QTest.mouseClick(manager.table.viewport(), Qt.MouseButton.LeftButton, pos=rect.center())
    runtime.processEvents()
    assert is_ap_group_confirmed(manager.get_group_by_id("a"))
    assert approval_item(manager).checkState() == Qt.CheckState.Checked
    assert "Confirmed" in approval_item(manager).data(Qt.ItemDataRole.AccessibleTextRole)
    manager.table.setCurrentItem(approval_item(manager))
    QTest.keyClick(manager.table, Qt.Key.Key_Space)
    runtime.processEvents()
    assert not is_ap_group_confirmed(manager.get_group_by_id("a"))
    approve(manager)
    assert all("physical" not in action.text().lower() for action in manager.alias_menu.actions())
    manager.save_groups()
    saved = next(g for g in manager.session.get_ap_groups() if g["group_id"] == "a")
    assert is_ap_group_confirmed(saved)
    assert load_ap_memory()["groups"][0]["physical_confirmed"] is True


def test_alias_change_invalidates_but_accepting_same_value_keeps_approval(manager):
    group = approve(manager)
    manager.set_alias(group, group["alias"])
    assert is_ap_group_confirmed(group)
    manager.set_alias(group, "Changed AP")
    assert not is_ap_group_confirmed(group)
    assert approval_item(manager).checkState() == Qt.CheckState.Unchecked
    assert group["physical_confirmation_revoked"]
    manager.persist_groups()
    manager.session.refresh_ap_groups_from_rows(update_memory=False)
    assert not is_ap_group_confirmed(next(g for g in manager.session.get_ap_groups() if g["group_id"] == "a"))


def test_dragging_rows_and_right_click_do_not_approve_a_group(manager, runtime):
    manager.show()
    runtime.processEvents()
    first = manager.table.visualItemRect(approval_item(manager, "a")).center()
    second = manager.table.visualItemRect(approval_item(manager, "b")).center()
    QTest.mousePress(manager.table.viewport(), Qt.MouseButton.LeftButton, pos=first)
    QTest.mouseMove(manager.table.viewport(), second)
    QTest.mouseRelease(manager.table.viewport(), Qt.MouseButton.LeftButton, pos=second)
    QTest.mouseClick(manager.table.viewport(), Qt.MouseButton.RightButton, pos=first)
    runtime.processEvents()
    assert not any(is_ap_group_confirmed(group) for group in manager.groups)


@pytest.mark.parametrize("field", ["role", "metadata"])
def test_model_edits_require_reapproval_but_no_op_does_not(manager, field):
    group = approve(manager)
    manager.select_group_by_id("a")
    if field == "role":
        with patch("qt_ui.qt_ap_groups.QInputDialog.getItem", return_value=(manager.tr("ap_group_role_internal"), True)):
            manager.prompt_role_for_selected_group()
        assert is_ap_group_confirmed(group)
        with patch("qt_ui.qt_ap_groups.QInputDialog.getItem", return_value=(manager.tr("ap_group_role_external"), True)):
            manager.prompt_role_for_selected_group()
    else:
        editor = Mock()
        editor.exec.return_value = QDialog.DialogCode.Accepted
        editor.metadata_values.return_value = group["metadata"]
        with patch("qt_ui.qt_ap_groups.MetadataDialog", return_value=editor):
            manager.open_metadata_dialog_for_selected_group()
        assert is_ap_group_confirmed(group)
        editor.metadata_values.return_value = {"vendor": "Changed vendor"}
        with patch("qt_ui.qt_ap_groups.MetadataDialog", return_value=editor):
            manager.open_metadata_dialog_for_selected_group()
    assert not is_ap_group_confirmed(group)


def test_split_and_move_invalidate_both_affected_groups(manager):
    first = approve(manager, "a")
    approve(manager, "b")
    assert manager.move_bssids_to_group("b", first["bssids"])
    assert manager.get_group_by_id("a") is None
    assert not is_ap_group_confirmed(manager.get_group_by_id("b"))
    approve(manager, "b")
    moved = manager.get_group_by_id("b")
    assert manager.split_bssids_to_new_group("b", [moved["bssids"][0]])
    assert all(not is_ap_group_confirmed(g) for g in manager.groups if set(g["bssids"]) & set(moved["bssids"]))


def test_reset_auto_does_not_silently_recover_revoked_approval(manager):
    approve(manager)
    manager.persist_groups()
    with patch("qt_ui.qt_ap_groups.QMessageBox.question", return_value=QMessageBox.StandardButton.Yes):
        manager.reset_groups_to_auto()
    assert not any(is_ap_group_confirmed(g) for g in manager.groups)
    manager.persist_groups()
    manager.session.refresh_ap_groups_from_rows(update_memory=False)
    assert not any(is_ap_group_confirmed(g) for g in manager.session.get_ap_groups())


def known_group():
    return build_manual_ap_group("known", ["02:00:00:00:00:10", "02:00:00:00:00:11"], alias="Known AP")


@pytest.mark.parametrize("membership,expected", [
    (["02:00:00:00:00:11", "02:00:00:00:00:10"], True),
    (["02:00:00:00:00:10"], False),
    (["02:00:00:00:00:10", "02:00:00:00:00:11", "02:00:00:00:00:12"], False),
    (["02:00:00:00:00:10", "02:00:00:00:00:12"], False),
])
def test_memory_restores_only_exact_membership_across_maps(membership, expected):
    update_ap_memory_from_groups([known_group()], map_file="old.png")
    memory = load_ap_memory()
    assert memory["groups"][0]["physical_confirmed"] is True
    group = build_manual_ap_group("new-survey", membership, locked=False)
    result, _ = apply_ap_memory_to_groups([group], map_file="new.png")
    assert is_ap_group_confirmed(result[0]) is expected
    assert "position" not in result[0]


def test_legacy_memory_does_not_invent_approval_and_confirmation_from_memory_is_separate(manager):
    group = manager.get_group_by_id("a")
    record = dict(bssids=group["bssids"], alias="From old memory", role="internal")
    save_ap_memory({"groups": [record]})
    result, _ = apply_ap_memory_to_groups([group])
    assert result[0]["physical_confirmed"] is False
    group["memory_applied"] = True
    manager.select_group_by_id("a")
    manager.confirm_memory_for_selected_group()
    assert not is_ap_group_confirmed(group)
    assert not group.get("memory_applied")
    for candidate in manager.groups:
        candidate["memory_applied"] = True
    with patch("qt_ui.qt_ap_groups.QMessageBox.question", return_value=QMessageBox.StandardButton.Yes):
        manager.confirm_all_memory_groups()
    assert not any(is_ap_group_confirmed(candidate) for candidate in manager.groups)


def test_position_changes_outside_manager_invalidate_approval(manager):
    from qt_ui.qt_ap_workflow import ApWorkflowMixin
    group = approve(manager)
    manager.persist_groups()
    driver = SimpleNamespace(session=manager.session, refresh_session_labels=Mock(),
        refresh_points_table=Mock(), status=Mock(), tr=manager.tr,
        get_ap_group_display_name=lambda _id: "AP", maybe_update_live_preview=Mock())
    ApWorkflowMixin.save_ap_position(driver, "a", group["position"]["x"], group["position"]["y"])
    assert is_ap_group_confirmed(next(g for g in manager.session.get_ap_groups() if g["group_id"] == "a"))
    ApWorkflowMixin.save_ap_position(driver, "a", 250, 150)
    manager.session.refresh_ap_groups_from_rows(update_memory=False)
    assert not is_ap_group_confirmed(next(g for g in manager.session.get_ap_groups() if g["group_id"] == "a"))


def test_revocation_survives_refresh_csv_reopen_and_next_survey(tmp_path):
    group = known_group()
    update_ap_memory_from_groups([group])
    invalidate_ap_group_confirmation(group)
    result, _ = apply_ap_memory_to_groups([group])
    assert not is_ap_group_confirmed(result[0])
    session = SurveySession()
    session.rows = fixture_survey()["rows"]
    session.set_ap_groups([group])
    path = tmp_path / "revoked.csv"
    session.save(str(path))
    reopened = SurveySession(str(path))
    revoked = next(g for g in reopened.get_ap_groups() if g["group_id"] == "known")
    assert revoked["physical_confirmation_revoked"]
    assert not is_ap_group_confirmed(revoked)
    fresh = build_manual_ap_group("fresh", group["bssids"], locked=False)
    assert not is_ap_group_confirmed(apply_ap_memory_to_groups([fresh])[0][0])


def test_confirmed_regrouping_replaces_overlapping_approval_without_union_trust():
    original = known_group()
    update_ap_memory_from_groups([original])
    split = [build_manual_ap_group("part-1", [original["bssids"][0]], alias="One"),
             build_manual_ap_group("part-2", [original["bssids"][1]], alias="Two")]
    update_ap_memory_from_groups(split)
    records = load_ap_memory()["groups"]
    approved = {tuple(record["bssids"]) for record in records if record.get("physical_confirmed")}
    assert approved == {tuple(g["bssids"]) for g in split}
    combined = build_manual_ap_group("automatic", original["bssids"], locked=False)
    assert not is_ap_group_confirmed(apply_ap_memory_to_groups([combined])[0][0])
    for group in split:
        fresh = build_manual_ap_group("fresh", group["bssids"], locked=False)
        assert is_ap_group_confirmed(apply_ap_memory_to_groups([fresh])[0][0])


def test_automatic_union_cannot_acquire_physical_approval():
    original = known_group()
    update_ap_memory_from_groups([original])
    wider = build_manual_ap_group("suggested", original["bssids"] + ["02:00:00:00:00:12"], locked=False)
    update_ap_memory_from_groups([wider])
    assert not any(record.get("physical_confirmed") for record in load_ap_memory()["groups"])
    assert not is_ap_group_confirmed(apply_ap_memory_to_groups([wider])[0][0])


def test_memory_approval_survives_session_new_capture_and_save_reopen(tmp_path):
    context = fixture_survey()
    groups = build_default_manual_groups(context["rows"])
    for group in groups:
        group["physical_confirmed"] = True
    update_ap_memory_from_groups(groups)
    session = SurveySession()
    session.rows, session.raw_scan_rows = context["rows"], context["raw_rows"]
    session.refresh_ap_groups_from_rows()
    assert all(is_ap_group_confirmed(g) for g in session.get_ap_groups())
    path = tmp_path / "approved.csv"
    session.save(str(path))
    assert all(is_ap_group_confirmed(g) for g in SurveySession(str(path)).get_ap_groups())


def test_only_relevant_groups_need_confirmation_external_rf_evidence_is_retained():
    context = fixture_survey()
    for group in context["groups"]:
        group["physical_confirmed"] = False
    report = analyze_survey(**context)
    approvals = findings(report, "unconfirmed_group")
    assert {f.group_ids for f in approvals} == {("a",), ("b",)}
    assert any(r.ssid == "Neighbor" for r in report.readings)
    assert findings(report, "channel_overlap")
    for group in context["groups"][:2]:
        group["physical_confirmed"] = True
    approved = analyze_survey(**context)
    assert not findings(approved, "unconfirmed_group")
    assert any(r.ssid == "Neighbor" for r in approved.readings)
    assert findings(approved, "channel_change")


@pytest.mark.parametrize("field,value", [("scan_confidence", .1), ("channel_width_mhz", ""), ("channel", "")])
def test_unconfirmed_unrelated_neighbor_still_requires_sound_radio_evidence(field, value):
    context = fixture_survey()
    context["groups"][2]["physical_confirmed"] = False
    for row in context["rows"]:
        if row["ssid"] == "Neighbor":
            row[field] = value
    report = analyze_survey(**context)
    assert not findings(report, "unconfirmed_group")
    assert not findings(report, "channel_change")


def test_one_warning_per_proposed_group_keeps_all_real_bssid_evidence():
    context = fixture_survey()
    extra = deepcopy(context["rows"][0])
    extra["bssid"] = "02:00:00:00:00:11"
    extra["ssid"] = "Guest"
    context["rows"].append(extra)
    context["groups"][0].update(bssids=[context["groups"][0]["bssids"][0], extra["bssid"]],
                                 physical_confirmed=False)
    context["groups"][2]["physical_confirmed"] = False
    report = analyze_survey(**context)
    approval, = findings(report, "unconfirmed_group")
    assert approval.group_ids == ("a",)
    assert wording(approval, report, "en") == "Confirm the physical AP group: Corridoio"
    html = finding_html(approval, report, "en", interactive=True)
    assert "Office" in html and "Driver RSSI" in html
    assert "evidence_group_ids" not in html
    assert len({r.group_id for r in report.readings if r.group_id.startswith("02:")}) == 2
    context["relevant_ssids"] = {"Guest"}
    guest, = findings(analyze_survey(**context), "unconfirmed_group")
    assert guest.group_ids == ("a",)


def test_no_scope_and_test_roles_do_not_request_approvals():
    context = fixture_survey()
    for group in context["groups"]:
        group.update(physical_confirmed=False, role="test")
    assert not findings(analyze_survey(**context), "unconfirmed_group")
    context["relevant_ssids"] = ()
    assert not findings(analyze_survey(**context), "unconfirmed_group")


@pytest.mark.parametrize("language", ["en", "it", "fr", "es"])
def test_help_and_action_describe_first_column_and_relevant_scope(language):
    from translations.i18n import TRANSLATIONS
    texts = TRANSLATIONS[language]
    assert texts["advisor_group_confirmation_help"] in texts["help_ap_groups_body"]
    assert "advisor_" not in texts["advisor_group_confirmation_hint"]
    assert texts["advisor_action_unconfirmed_group"] != "advisor_action_unconfirmed_group"
