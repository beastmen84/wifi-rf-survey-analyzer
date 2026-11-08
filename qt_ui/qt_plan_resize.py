"""Origin-anchored canvas resizing; vectors, evidence and calibration stay fixed."""
from copy import deepcopy
import math
import os

from PIL import Image
from PySide6.QtCore import QSize, QRectF
from PySide6.QtGui import QImage, QPainter, QPixmap
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout, QLabel, QVBoxLayout
from app_core.units import distance_unit_label, display_units_to_meters, meters_to_display_units
from survey.plan_mode import is_drawn_plan
from survey.plan_layers import read_layers
from qt_ui.default_floorplan import (BLANK_PLAN_WIDTH_KEY, BLANK_PLAN_HEIGHT_KEY,
    BLANK_PLAN_PIXEL_WIDTH_KEY, BLANK_PLAN_PIXEL_HEIGHT_KEY, ensure_default_floorplan)
from qt_ui.qt_clean_plan import VectorPlanSource


def canvas_size(owner):
    size = owner.floorplan_view.pixmap_item.pixmap().size()
    return size.width(), size.height()


def validate_canvas(owner, size, document=None):
    if owner.session is None or not is_drawn_plan(owner.session.metadata) or not owner.floorplan_view.has_floorplan():
        raise ValueError('resize_draw_only')
    width, height = size
    if any(type(v) is not int or not 1 <= v <= 4096 for v in size):
        raise ValueError('resize_limit')
    density = owner.get_px_per_meter()
    if density is None or not math.isfinite(density) or density <= 0:
        raise ValueError('resize_scale')
    spacing = owner.floorplan_view.grid_spacing_pixels()
    if owner.floorplan_view.grid_visible and spacing and (width+height)/spacing > 100000:
        raise ValueError('resize_grid_limit')
    try:
        VectorPlanSource.from_layers(QSize(width,height),(document or read_layers(owner.session.metadata))['layers'])
    except (ValueError,TypeError,KeyError) as error:
        raise ValueError('resize_content') from error
    points = [*owner.session.get_points(), *owner.session.measurement_points(),
              *(g['position'] for g in owner.session.get_ap_groups() if g.get('position'))]
    for point in points:
        x,y = float(point['x']),float(point['y'])
        if not (math.isfinite(x) and math.isfinite(y) and 0 <= x <= width and 0 <= y <= height):
            raise ValueError('resize_points')
    mask = owner.floorplan_view.boundaries_mask_image
    if mask is not None:
        rgba = mask.convertToFormat(QImage.Format.Format_RGBA8888)
        image = Image.frombytes('RGBA',(rgba.width(),rgba.height()),bytes(rgba.constBits()),'raw','RGBA',rgba.bytesPerLine())
        box = image.getchannel('A').getbbox()
        if box and (box[2] > width or box[3] > height):
            raise ValueError('resize_mask')


def resize_canvas(owner, size, *, history=True, document=None):
    if owner.scan_in_progress:
        raise ValueError('resize_busy')
    if tuple(size) == canvas_size(owner):
        return False
    validate_canvas(owner,size,document)
    view, drawing = owner.floorplan_view, owner.plan_tools.controller
    # Prepare all allocations/files before changing the session or its history.
    base = QPixmap(*size)
    if base.isNull():
        raise ValueError('resize_limit')
    from PySide6.QtCore import Qt
    base.fill(Qt.GlobalColor.white)
    mask = None
    if view.boundaries_mask_image is not None:
        mask = QImage(*size,QImage.Format.Format_ARGB32_Premultiplied)
        if mask.isNull():
            raise ValueError('resize_limit')
        mask.fill(Qt.GlobalColor.transparent)
        painter = QPainter(mask)
        try:
            painter.drawImage(0,0,view.boundaries_mask_image)
        finally:
            painter.end()
    path = os.path.abspath(ensure_default_floorplan(*size))
    previous = drawing.snapshot() if history else None
    drawing.cancel()
    view.cancel_scale_calibration_pick(emit_signal=False)
    view.cancel_ap_position_pick(emit_signal=False)
    owner.set_boundaries_mode_enabled(False,show_status=False)
    view.hide_point_tooltip()
    if history:
        drawing.undo_stack.append(previous)
        del drawing.undo_stack[:-50]
        drawing.redo_stack.clear()
    if not hasattr(owner.session,'canvas_source_file'):
        owner.session.canvas_source_file = owner.session.metadata.get('map_file','')
    owner.session.metadata.update(map_file=path,**{
        BLANK_PLAN_WIDTH_KEY:f'{size[0]/owner.get_px_per_meter():.12g}',
        BLANK_PLAN_HEIGHT_KEY:f'{size[1]/owner.get_px_per_meter():.12g}',
        BLANK_PLAN_PIXEL_WIDTH_KEY:str(size[0]),BLANK_PLAN_PIXEL_HEIGHT_KEY:str(size[1])})
    # Keep the same pixmap item: the design controller and point items retain
    # their identities, coordinates and undo history.
    view.pixmap_item.setPixmap(base)
    view.scene.setSceneRect(QRectF(0,0,*size))
    if mask is not None:
        if view.boundaries_mask_item is not None:
            view.boundaries_mask_item.prepareGeometryChange()
            view.boundaries_mask_item.image = mask
            view.boundaries_mask_item.update()
        view.boundaries_mask_image = mask
    owner.session.dirty = True
    drawing.document = None  # Rebuild grid regions and layer paths at the new extent.
    owner.invalidate_live_preview()
    owner.refresh_session_labels()
    owner.sync_floorplan_grid_for_session()
    view.fit_to_view()
    owner.maybe_update_live_preview()
    owner.status.showMessage(owner.tr('resize_done'))
    return True


class ResizePlanDialog(QDialog):
    def __init__(self,owner):
        super().__init__(owner)
        self.owner = owner
        self.original = canvas_size(owner)
        self.density = owner.get_px_per_meter()
        if self.density is None:
            raise ValueError('resize_scale')
        self.setWindowTitle(owner.tr('resize_title'))
        self.setMinimumWidth(owner.spx(460))
        layout = QVBoxLayout(self)
        hint = QLabel(owner.tr('resize_hint'))
        hint.setWordWrap(True)
        layout.addWidget(hint)
        form = QFormLayout()
        self.spins = []
        for key,pixels in zip(('blank_plan_width','blank_plan_height'),self.original):
            spin = QDoubleSpinBox()
            spin.setObjectName('blankPlanDimension')
            spin.setDecimals(2)
            spin.setRange(0,meters_to_display_units(4096/self.density,owner.measurement_system))
            spin.setSuffix(' '+distance_unit_label(owner.measurement_system))
            spin.setSingleStep(.5 if owner.measurement_system == 'metric' else 1)
            spin.setMinimumHeight(owner.spx(36))
            spin.setKeyboardTracking(False)
            spin.setValue(meters_to_display_units(pixels/self.density,owner.measurement_system))
            form.addRow(owner.tr(key),spin)
            self.spins.append(spin)
        self.initial = tuple(s.value() for s in self.spins)
        layout.addLayout(form)
        self.feedback = QLabel()
        self.feedback.setWordWrap(True)
        layout.addWidget(self.feedback)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.ok_button = buttons.button(QDialogButtonBox.StandardButton.Ok)
        self.ok_button.setText(owner.tr('resize_plan'))
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(owner.tr('cancel'))
        buttons.accepted.connect(self.try_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        for spin in self.spins:
            spin.valueChanged.connect(self.refresh)
        self.refresh()

    def dimensions(self):
        return tuple(old if spin.value() == initial else round(display_units_to_meters(spin.value(),self.owner.measurement_system)*self.density)
                     for old,spin,initial in zip(self.original,self.spins,self.initial))

    def refresh(self):
        try:
            validate_canvas(self.owner,self.dimensions())
            self.feedback.setText(self.owner.tr('resize_valid'))
            self.feedback.setStyleSheet('')
            self.ok_button.setEnabled(True)
        except (ValueError,TypeError,KeyError,OverflowError) as error:
            self.feedback.setText(self.owner.tr(str(error)))
            self.feedback.setStyleSheet('color:#ef4444')
            self.ok_button.setEnabled(False)

    def try_accept(self):
        self.refresh()
        if self.ok_button.isEnabled():
            self.accept()


def open_plan_resize(owner):
    if (owner.session is None or not is_drawn_plan(owner.session.metadata)
            or owner.scan_in_progress or not owner.floorplan_view.has_floorplan()):
        return False
    dialog = None
    session,token,pixmap = owner.session,deepcopy(owner.session.metadata),owner.floorplan_view.pixmap_item
    drawing = owner.plan_tools.controller
    if drawing.wall_dialog_open:
        return False
    drawing.wall_dialog_open = True
    try:
        drawing.cancel()
        dialog = ResizePlanDialog(owner)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return False
        if owner.session is not session or owner.session.metadata != token or owner.floorplan_view.pixmap_item is not pixmap:
            raise ValueError('wall_stale')
        return resize_canvas(owner,dialog.dimensions())
    except (ValueError,TypeError,KeyError,OverflowError,OSError) as error:
        owner.status.showMessage(owner.tr(str(error)))
        return False
    finally:
        drawing.wall_dialog_open = False
        if dialog is not None:
            dialog.deleteLater()
