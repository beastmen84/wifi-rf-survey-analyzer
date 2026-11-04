"""Qt graphics view used for floor plans, survey points, and AP markers."""

from pathlib import Path
import math

from PySide6.QtCore import QPointF, QRect, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QImage, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsLineItem,
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsView,
)

from app_core.units import (
    MEASUREMENT_SYSTEM_IMPERIAL,
    distance_unit_label,
    display_units_to_meters,
    meters_to_display_units,
    normalize_measurement_system,
)
from ap.groups import normalize_ap_role
from qt_ui.pdf_floorplan import render_pdf_page_to_qimage
from qt_ui.qt_tooltips import build_html_tooltip, tooltip_section


AP_MARKER_BASE_SIZE = 20
SURVEY_POINT_MARKER_RADIUS = 7.0
FOCUS_POINT_DEFAULT_ZOOM_LEVEL = 1.4
FOCUS_POINT_VERTICAL_VIEWPORT_FRACTION = 0.25
METRIC_GRID_INTERVALS_M = (0.5, 1.0, 2.0, 5.0, 10.0, 20.0)
IMPERIAL_GRID_INTERVALS_FT = (1.0, 2.0, 3.0, 5.0, 10.0, 20.0, 50.0)
MIN_GRID_SPACING_PX = 40.0
GRID_MAJOR_EVERY = 5
BOUNDARIES_MASK_ALPHA = 78
BOUNDARIES_MASK_COLOR = QColor(37, 99, 235)
BOUNDARIES_BRUSH_SIZE_DEFAULT_PX = 40
BOUNDARIES_BRUSH_SIZE_MIN_PX = 20
BOUNDARIES_BRUSH_SIZE_MAX_PX = 120
BOUNDARIES_BRUSH_SIZE_STEP_PX = 10


class BoundariesMaskItem(QGraphicsItem):
    def __init__(self, image):
        super().__init__()
        self.image = image
        self.setZValue(6)
        self.setOpacity(BOUNDARIES_MASK_ALPHA / 255.0)

    def boundingRect(self):
        return QRectF(0, 0, self.image.width(), self.image.height())

    def paint(self, painter, option, widget=None):
        exposed_rect = option.exposedRect if option is not None else self.boundingRect()
        painter.drawImage(exposed_rect, self.image, exposed_rect)


class FloorplanView(QGraphicsView):
    surveyPointRequested = Signal(int, int)
    apPositionPicked = Signal(str, int, int)
    apPositionCancelled = Signal()
    scaleCalibrationFirstPointPicked = Signal()
    scaleCalibrationCompleted = Signal(float)
    scaleCalibrationCancelled = Signal()
    pointSelected = Signal(dict)
    pointSelectionCleared = Signal()
    boundariesMaskChanged = Signal(bool)
    boundariesMaskEdited = Signal()
    zoomChanged = Signal(float)

    def __init__(self):
        super().__init__()
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.pixmap_item = None
        self.marker_items = []
        self.ap_marker_items = []
        self.grid_items = []
        self.scale_calibration_items = []
        self.scale_calibration_points = []
        self.selected_point_key = None
        self.zoom_level = 1.0
        self.focus_point_zoom_level = FOCUS_POINT_DEFAULT_ZOOM_LEVEL
        self.pending_ap_position_group_id = ""
        self.pending_ap_position_label = ""
        self.scale_calibration_active = False
        self.ap_position_icon = load_ap_position_icon()
        self.point_tooltip_formatter = None
        self.ap_tooltip_formatter = None
        self.grid_visible = False
        self.grid_px_per_meter = None
        self.grid_measurement_system = "metric"
        self.grid_color = "#3A6EA5"
        self.grid_label = ""
        self.grid_ui_scale = 1.0
        self.boundaries_edit_active = False
        self.boundaries_tool = "draw"
        self.boundaries_shape = "circle"
        self.boundaries_brush_size_px = float(BOUNDARIES_BRUSH_SIZE_DEFAULT_PX)
        self.boundaries_mask_image = None
        self.boundaries_mask_item = None
        self.boundaries_mask_has_content = False
        self.boundaries_drawing_active = False
        self.boundaries_last_point = None
        self.boundaries_stroke_points = []
        self.boundaries_stroke_base_image = None
        self.boundaries_stroke_dirty_rect = QRectF()
        self.boundaries_mask_dirty_rect = QRectF()
        self.boundaries_brush_preview_pos = None
        self.default_viewport_update_mode = self.viewportUpdateMode()

        self.setObjectName("floorplanView")
        self.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setBackgroundBrush(QBrush(Qt.GlobalColor.darkGray))

    def load_floorplan(self, file_path):
        pixmap = load_floorplan_pixmap(file_path)
        if pixmap.isNull():
            raise ValueError(f"Cannot load floor plan: {file_path}")

        self.reset_boundaries_mask(emit_signal=False)
        self.scene.clear()
        self.marker_items = []
        self.ap_marker_items = []
        self.grid_items = []
        self.scale_calibration_items = []
        self.scale_calibration_points = []
        self.selected_point_key = None
        self.scale_calibration_active = False
        self.boundaries_edit_active = False
        self.pending_ap_position_group_id = ""
        self.pending_ap_position_label = ""
        self.viewport().unsetCursor()
        self.pixmap_item = QGraphicsPixmapItem(pixmap)
        self.scene.addItem(self.pixmap_item)
        self.scene.setSceneRect(pixmap.rect())
        self.refresh_grid()
        self.resetTransform()
        self.zoom_level = 1.0
        self.fit_to_view()

    def clear_floorplan(self):
        self.reset_boundaries_mask(emit_signal=False)
        self.scene.clear()
        self.pixmap_item = None
        self.marker_items = []
        self.ap_marker_items = []
        self.grid_items = []
        self.grid_visible = False
        self.scale_calibration_items = []
        self.scale_calibration_points = []
        self.boundaries_edit_active = False
        self.boundaries_drawing_active = False
        self.boundaries_last_point = None
        self.boundaries_stroke_points = []
        self.boundaries_stroke_base_image = None
        self.boundaries_stroke_dirty_rect = QRectF()
        self.selected_point_key = None
        self.zoom_level = 1.0
        self.cancel_ap_position_pick(emit_signal=False)
        self.cancel_scale_calibration_pick(emit_signal=False)

    def has_floorplan(self):
        return self.pixmap_item is not None

    def set_boundaries_edit_mode(self, active):
        active = bool(active and self.has_floorplan())
        if active:
            self.cancel_ap_position_pick(emit_signal=False)
            self.cancel_scale_calibration_pick(emit_signal=False)

        self.boundaries_edit_active = active
        self.boundaries_drawing_active = False
        self.boundaries_last_point = None
        self.boundaries_stroke_points = []
        self.boundaries_stroke_base_image = None
        self.boundaries_stroke_dirty_rect = QRectF()
        self.setViewportUpdateMode(
            QGraphicsView.ViewportUpdateMode.FullViewportUpdate
            if active
            else self.default_viewport_update_mode
        )
        if self.boundaries_mask_item is not None:
            self.boundaries_mask_item.setVisible(active)
        if not active:
            self.hide_boundaries_brush_preview()
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.update_boundaries_cursor()

    def set_boundaries_tool_state(self, tool="draw", shape="circle"):
        self.boundaries_tool = "eraser" if tool == "eraser" else "draw"
        self.boundaries_shape = "square" if shape == "square" else "circle"
        self.update_boundaries_cursor()

    def set_boundaries_brush_size_px(self, size_px):
        try:
            size = int(round(float(size_px)))
        except (TypeError, ValueError):
            size = BOUNDARIES_BRUSH_SIZE_DEFAULT_PX
        size = max(BOUNDARIES_BRUSH_SIZE_MIN_PX, min(BOUNDARIES_BRUSH_SIZE_MAX_PX, size))
        if size == int(round(self.boundaries_brush_size_px)):
            return False

        old_rect = self.boundaries_brush_preview_viewport_rect()
        self.boundaries_brush_size_px = float(size)
        new_rect = self.boundaries_brush_preview_viewport_rect()
        self.update_boundaries_preview_region(old_rect, new_rect)
        return True

    def adjust_boundaries_brush_size_px(self, delta_px):
        return self.set_boundaries_brush_size_px(self.boundaries_brush_size_px + float(delta_px))

    def update_boundaries_cursor(self):
        if not self.boundaries_edit_active:
            self.viewport().unsetCursor()
            self.hide_boundaries_brush_preview()
            return

        if self.boundaries_brush_preview_pos is None:
            self.viewport().unsetCursor()
        else:
            self.viewport().setCursor(Qt.CursorShape.BlankCursor)
            self.update_boundaries_brush_preview()

    def update_boundaries_brush_preview(self, scene_point=None):
        if not self.boundaries_edit_active:
            self.hide_boundaries_brush_preview()
            return

        old_rect = self.boundaries_brush_preview_viewport_rect()
        if scene_point is not None:
            if not self.is_point_inside_floorplan(scene_point):
                self.hide_boundaries_brush_preview()
                self.viewport().unsetCursor()
                return
            self.boundaries_brush_preview_pos = scene_point
        if self.boundaries_brush_preview_pos is None:
            self.hide_boundaries_brush_preview()
            return

        self.viewport().setCursor(Qt.CursorShape.BlankCursor)
        new_rect = self.boundaries_brush_preview_viewport_rect()
        self.update_boundaries_preview_region(old_rect, new_rect)

    def boundaries_brush_preview_rect(self):
        if self.boundaries_brush_preview_pos is None:
            return QRectF()
        return self.boundaries_brush_preview_rect_for_point(
            self.boundaries_brush_preview_pos
        )

    def boundaries_brush_preview_rect_for_point(self, point):
        half = self.boundaries_brush_size_px / 2.0
        return QRectF(
            point.x() - half,
            point.y() - half,
            self.boundaries_brush_size_px,
            self.boundaries_brush_size_px,
        )

    def boundaries_brush_preview_viewport_rect(self):
        if self.boundaries_brush_preview_pos is None:
            return QRect()
        preview_rect = self.boundaries_brush_preview_rect()
        viewport_rect = self.mapFromScene(preview_rect).boundingRect()
        viewport_rect = viewport_rect.adjusted(-3, -3, 3, 3)
        return viewport_rect.intersected(self.viewport().rect())

    def update_boundaries_preview_region(self, *rects):
        dirty_rect = QRect()
        for rect in rects:
            if rect.isNull() or rect.isEmpty():
                continue
            dirty_rect = rect if dirty_rect.isNull() else dirty_rect.united(rect)
        if not dirty_rect.isNull() and not dirty_rect.isEmpty():
            self.viewport().update(dirty_rect)

    def draw_boundaries_brush_preview(self, painter, rect):
        if not self.boundaries_edit_active or self.boundaries_brush_preview_pos is None:
            return

        preview_rect = self.boundaries_brush_preview_rect()
        if not rect.intersects(preview_rect):
            return

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        fill = (
            QColor(37, 99, 235, 45)
            if self.boundaries_tool == "draw"
            else QColor(255, 255, 255, 45)
        )
        outline = (
            QColor(37, 99, 235, 230)
            if self.boundaries_tool == "draw"
            else QColor(185, 28, 28, 230)
        )
        pen = QPen(outline, 0)
        if self.boundaries_tool == "eraser":
            pen.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.setBrush(QBrush(fill))
        if self.boundaries_shape == "square":
            painter.drawRect(preview_rect)
        else:
            painter.drawEllipse(preview_rect)
        painter.restore()

    def hide_boundaries_brush_preview(self):
        if self.boundaries_brush_preview_pos is not None:
            old_rect = self.boundaries_brush_preview_viewport_rect()
            self.boundaries_brush_preview_pos = None
            self.update_boundaries_preview_region(old_rect)

    def is_point_inside_floorplan(self, point):
        return self.has_floorplan() and self.scene.sceneRect().contains(point)

    def has_boundaries_mask(self):
        return self.boundaries_mask_has_content

    def reset_boundaries_mask(self, emit_signal=True):
        self.boundaries_brush_preview_pos = None
        self.boundaries_mask_dirty_rect = QRectF()
        if (
            self.boundaries_mask_item is not None
            and self.boundaries_mask_item.scene() is self.scene
        ):
            self.scene.removeItem(self.boundaries_mask_item)
        self.boundaries_mask_image = None
        self.boundaries_mask_item = None
        self.boundaries_mask_has_content = False
        self.boundaries_drawing_active = False
        self.boundaries_last_point = None
        self.boundaries_stroke_points = []
        self.boundaries_stroke_base_image = None
        self.boundaries_stroke_dirty_rect = QRectF()
        if emit_signal:
            self.boundariesMaskChanged.emit(False)

    def clear_boundaries_mask(self):
        if self.boundaries_mask_image is None and self.boundaries_mask_item is None:
            if self.boundaries_mask_has_content:
                self.boundaries_mask_has_content = False
                self.boundariesMaskChanged.emit(False)
                self.boundariesMaskEdited.emit()
            return

        if self.boundaries_mask_image is not None:
            self.boundaries_mask_image.fill(Qt.GlobalColor.transparent)
        if self.boundaries_mask_item is not None:
            self.boundaries_mask_item.update()
        changed = self.boundaries_mask_has_content
        self.boundaries_mask_has_content = False
        self.boundaries_drawing_active = False
        self.boundaries_last_point = None
        self.boundaries_stroke_points = []
        self.boundaries_stroke_base_image = None
        self.boundaries_stroke_dirty_rect = QRectF()
        self.boundaries_mask_dirty_rect = QRectF()
        self.viewport().update()
        if changed:
            self.boundariesMaskChanged.emit(False)
            self.boundariesMaskEdited.emit()

    def ensure_boundaries_mask(self):
        if not self.has_floorplan():
            return False

        if self.boundaries_mask_image is None:
            source_pixmap = self.pixmap_item.pixmap()
            self.boundaries_mask_image = QImage(
                source_pixmap.size(),
                QImage.Format.Format_ARGB32_Premultiplied,
            )
            self.boundaries_mask_image.fill(Qt.GlobalColor.transparent)

        if self.boundaries_mask_item is None:
            self.boundaries_mask_item = BoundariesMaskItem(self.boundaries_mask_image)
            self.boundaries_mask_item.setVisible(self.boundaries_edit_active)
            self.scene.addItem(self.boundaries_mask_item)

        return True

    def save_boundaries_mask(self, file_path):
        if not self.has_boundaries_mask() or self.boundaries_mask_image is None:
            return False

        return bool(self.boundaries_mask_image.save(str(file_path), "PNG"))

    def load_boundaries_mask(self, file_path, emit_signal=True):
        if not self.has_floorplan():
            return False

        loaded_image = QImage(str(file_path))
        if loaded_image.isNull():
            return False

        source_size = self.pixmap_item.pixmap().size()
        if loaded_image.size() != source_size:
            return False

        self.reset_boundaries_mask(emit_signal=False)
        self.boundaries_mask_image = loaded_image.convertToFormat(
            QImage.Format.Format_ARGB32_Premultiplied
        )
        self.boundaries_mask_item = BoundariesMaskItem(self.boundaries_mask_image)
        self.boundaries_mask_item.setVisible(self.boundaries_edit_active)
        self.scene.addItem(self.boundaries_mask_item)
        self.boundaries_mask_has_content = True
        self.boundaries_mask_dirty_rect = QRectF(
            0,
            0,
            self.boundaries_mask_image.width(),
            self.boundaries_mask_image.height(),
        )
        self.boundaries_mask_item.update()
        self.viewport().update()
        if emit_signal:
            self.boundariesMaskChanged.emit(True)
        return True

    def get_boundaries_mask_image_copy(self):
        if not self.has_boundaries_mask() or self.boundaries_mask_image is None:
            return None

        return self.boundaries_mask_image.copy()

    def apply_boundaries_brush(self, x, y, refresh=True):
        if not self.ensure_boundaries_mask():
            return False

        point = self.clamp_boundaries_point(QPointF(float(x), float(y)))
        changed = self.apply_boundaries_polyline([point])
        if changed and refresh:
            self.refresh_boundaries_mask_after_change()
        return changed

    def apply_boundaries_segment(self, start_point, end_point):
        return self.apply_boundaries_polyline([start_point, end_point])

    def apply_boundaries_polyline(self, points):
        if not points:
            return False
        clamped_points = [
            self.clamp_boundaries_point(QPointF(float(point.x()), float(point.y())))
            for point in points
        ]
        painter = QPainter(self.boundaries_mask_image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        if self.boundaries_tool == "eraser":
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            color = QColor(0, 0, 0, 255)
        else:
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            color = QColor(
                BOUNDARIES_MASK_COLOR.red(),
                BOUNDARIES_MASK_COLOR.green(),
                BOUNDARIES_MASK_COLOR.blue(),
                255,
            )

        draw_points = (
            self.filtered_boundaries_polyline(clamped_points)
            if self.boundaries_shape == "square"
            else clamped_points
        )
        start_point = draw_points[0]
        dirty_rect = self.boundaries_points_dirty_rect(clamped_points)
        is_point_stroke = len(draw_points) == 1 or all(
            math.hypot(
                current_point.x() - previous_point.x(),
                current_point.y() - previous_point.y(),
            )
            < 0.01
            for previous_point, current_point in zip(draw_points, draw_points[1:])
        )
        if is_point_stroke:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(color))
            self.draw_boundaries_brush_shape(painter, start_point)
        elif self.boundaries_shape == "square":
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(color))
            self.draw_boundaries_square_polyline(painter, draw_points)
        else:
            path = QPainterPath(start_point)
            for point in draw_points[1:]:
                path.lineTo(point)
            pen = QPen(color, self.boundaries_brush_size_px)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.drawPath(path)
        painter.end()
        self.boundaries_mask_dirty_rect = dirty_rect
        return True

    def draw_boundaries_brush_shape(self, painter, point):
        half = self.boundaries_brush_size_px / 2.0
        rect = QRectF(
            point.x() - half,
            point.y() - half,
            self.boundaries_brush_size_px,
            self.boundaries_brush_size_px,
        )
        if self.boundaries_shape == "square":
            painter.drawRect(rect)
        else:
            painter.drawEllipse(rect)

    def filtered_boundaries_polyline(self, points):
        if len(points) <= 1:
            return points

        filtered_points = [points[0]]
        for point in points[1:]:
            previous_point = filtered_points[-1]
            if (
                math.hypot(
                    point.x() - previous_point.x(),
                    point.y() - previous_point.y(),
                )
                >= 0.25
            ):
                filtered_points.append(point)
        return filtered_points

    @staticmethod
    def convex_hull(points):
        unique_points = sorted({(float(point.x()), float(point.y())) for point in points})
        if len(unique_points) <= 1:
            return [QPointF(x, y) for x, y in unique_points]

        def cross(origin, first, second):
            return (
                (first[0] - origin[0]) * (second[1] - origin[1])
                - (first[1] - origin[1]) * (second[0] - origin[0])
            )

        lower = []
        for point in unique_points:
            while len(lower) >= 2 and cross(lower[-2], lower[-1], point) <= 0:
                lower.pop()
            lower.append(point)

        upper = []
        for point in reversed(unique_points):
            while len(upper) >= 2 and cross(upper[-2], upper[-1], point) <= 0:
                upper.pop()
            upper.append(point)

        return [QPointF(x, y) for x, y in lower[:-1] + upper[:-1]]

    def draw_boundaries_square_polyline(self, painter, points):
        for start_point, end_point in zip(points, points[1:]):
            self.draw_boundaries_square_sweep_segment(painter, start_point, end_point)

    def draw_boundaries_square_sweep_segment(self, painter, start_point, end_point):
        half = self.boundaries_brush_size_px / 2.0
        corners = []
        for point in (start_point, end_point):
            corners.extend(
                [
                    QPointF(point.x() - half, point.y() - half),
                    QPointF(point.x() + half, point.y() - half),
                    QPointF(point.x() + half, point.y() + half),
                    QPointF(point.x() - half, point.y() + half),
                ]
            )

        hull = self.convex_hull(corners)
        if len(hull) < 3:
            self.draw_boundaries_brush_shape(painter, start_point)
            return

        path = QPainterPath(hull[0])
        for point in hull[1:]:
            path.lineTo(point)
        path.closeSubpath()
        painter.drawPath(path)

    def boundaries_segment_dirty_rect(self, start_point, end_point):
        return self.boundaries_points_dirty_rect([start_point, end_point])

    def boundaries_points_dirty_rect(self, points):
        if not points:
            return QRectF()
        half = self.boundaries_brush_size_px / 2.0 + 8.0
        first_point = self.clamp_boundaries_point(
            QPointF(float(points[0].x()), float(points[0].y()))
        )
        dirty_rect = QRectF(first_point, first_point)
        for point in points[1:]:
            clamped_point = self.clamp_boundaries_point(
                QPointF(float(point.x()), float(point.y()))
            )
            dirty_rect = dirty_rect.united(QRectF(clamped_point, clamped_point))
        dirty_rect = dirty_rect.normalized().adjusted(
            -half,
            -half,
            half,
            half,
        )
        image_rect = QRectF(
            0,
            0,
            self.boundaries_mask_image.width(),
            self.boundaries_mask_image.height(),
        )
        return dirty_rect.intersected(image_rect)

    def refresh_boundaries_mask_after_change(self):
        if self.boundaries_mask_item is not None:
            if self.boundaries_mask_dirty_rect.isNull():
                self.boundaries_mask_item.update()
                self.repaint_or_update_boundaries_viewport()
            else:
                self.boundaries_mask_item.update(self.boundaries_mask_dirty_rect)
                self.update_boundaries_mask_viewport_region(
                    self.boundaries_mask_dirty_rect
                )
        if self.boundaries_tool != "eraser" and not self.boundaries_mask_has_content:
            self.boundaries_mask_has_content = True
            self.boundariesMaskChanged.emit(True)
        self.boundariesMaskEdited.emit()

    def update_boundaries_mask_viewport_region(self, rect):
        if rect.isNull() or rect.isEmpty():
            self.repaint_or_update_boundaries_viewport()
            return

        self.scene.invalidate(rect, QGraphicsScene.SceneLayer.AllLayers)
        viewport_rect = self.mapFromScene(rect).boundingRect().adjusted(-4, -4, 4, 4)
        viewport_rect = viewport_rect.intersected(self.viewport().rect())
        if viewport_rect.isNull() or viewport_rect.isEmpty():
            return

        self.repaint_or_update_boundaries_viewport(viewport_rect)

    def repaint_or_update_boundaries_viewport(self, rect=None):
        is_active_stroke = (
            self.boundaries_drawing_active
            and self.boundaries_stroke_base_image is not None
        )
        if rect is None:
            if is_active_stroke:
                self.viewport().repaint()
            else:
                self.viewport().update()
            return

        if is_active_stroke:
            self.viewport().repaint()
        else:
            self.viewport().update(rect)

    def apply_boundaries_stroke(self, start_point, end_point):
        if not self.ensure_boundaries_mask():
            return False
        changed = self.apply_boundaries_segment(start_point, end_point)
        if changed:
            self.refresh_boundaries_mask_after_change()
        return changed

    def apply_boundaries_live_stroke(self, points):
        if not self.ensure_boundaries_mask():
            return False
        if self.boundaries_stroke_base_image is not None:
            self.boundaries_stroke_points = [
                self.clamp_boundaries_point(QPointF(float(point.x()), float(point.y())))
                for point in points
            ]
            changed = self.apply_boundaries_active_stroke()
        else:
            changed = self.apply_boundaries_polyline(points)
        if changed:
            self.refresh_boundaries_mask_after_change()
        return changed

    def begin_boundaries_stroke(self, point):
        if not self.ensure_boundaries_mask():
            return False

        point = self.clamp_boundaries_point(point)
        self.boundaries_stroke_base_image = self.boundaries_mask_image.copy()
        self.boundaries_stroke_points = [point]
        self.boundaries_stroke_dirty_rect = QRectF()
        self.boundaries_last_point = point
        changed = self.apply_boundaries_active_stroke()
        if changed:
            self.refresh_boundaries_mask_after_change()
        return changed

    def continue_boundaries_stroke(self, point):
        if self.boundaries_stroke_base_image is None:
            return self.begin_boundaries_stroke(point)

        point = self.clamp_boundaries_point(point)
        self.boundaries_stroke_points.append(point)
        self.boundaries_last_point = point
        changed = self.apply_boundaries_active_stroke()
        if changed:
            self.refresh_boundaries_mask_after_change()
        return changed

    def finish_boundaries_stroke(self, point=None):
        if self.boundaries_stroke_base_image is None:
            self.boundaries_stroke_points = []
            self.boundaries_stroke_dirty_rect = QRectF()
            return False

        if point is not None:
            point = self.clamp_boundaries_point(point)
            if not self.boundaries_stroke_points or math.hypot(
                point.x() - self.boundaries_stroke_points[-1].x(),
                point.y() - self.boundaries_stroke_points[-1].y(),
            ) >= 0.01:
                self.boundaries_stroke_points.append(point)
            self.boundaries_last_point = point

        changed = self.apply_boundaries_active_stroke()
        if changed:
            self.refresh_boundaries_mask_after_change()
        self.boundaries_stroke_base_image = None
        self.boundaries_stroke_points = []
        self.boundaries_stroke_dirty_rect = QRectF()
        return changed

    def apply_boundaries_active_stroke(self):
        if not self.boundaries_stroke_points:
            return False

        new_dirty_rect = self.boundaries_points_dirty_rect(self.boundaries_stroke_points)
        repaint_rect = new_dirty_rect
        if not self.boundaries_stroke_dirty_rect.isNull():
            repaint_rect = repaint_rect.united(self.boundaries_stroke_dirty_rect)
        self.restore_boundaries_stroke_base_region(repaint_rect)
        changed = self.apply_boundaries_polyline(self.boundaries_stroke_points)
        self.boundaries_stroke_dirty_rect = new_dirty_rect
        self.boundaries_mask_dirty_rect = repaint_rect
        return changed

    def restore_boundaries_stroke_base_region(self, rect):
        if self.boundaries_stroke_base_image is None or rect.isNull() or rect.isEmpty():
            return

        image_rect = QRect(0, 0, self.boundaries_mask_image.width(), self.boundaries_mask_image.height())
        target_rect = rect.toAlignedRect().intersected(image_rect)
        if target_rect.isNull() or target_rect.isEmpty():
            return

        painter = QPainter(self.boundaries_mask_image)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        painter.drawImage(target_rect, self.boundaries_stroke_base_image, target_rect)
        painter.end()

    def clamp_boundaries_point(self, point):
        rect = self.scene.sceneRect()
        if rect.isNull():
            return point
        return QPointF(
            min(max(point.x(), rect.left()), rect.right()),
            min(max(point.y(), rect.top()), rect.bottom()),
        )

    def set_grid(
        self,
        visible,
        px_per_meter=None,
        measurement_system="metric",
        color="#3A6EA5",
        label="",
        ui_scale=1.0,
    ):
        self.grid_visible = bool(visible and px_per_meter)
        self.grid_px_per_meter = float(px_per_meter) if px_per_meter else None
        self.grid_measurement_system = normalize_measurement_system(measurement_system)
        self.grid_color = color
        self.grid_label = str(label or "") if self.grid_visible else ""
        self.grid_ui_scale = max(0.5, float(ui_scale or 1.0))
        self.refresh_grid()
        self.viewport().update()

    def refresh_grid(self):
        self.clear_grid_items()
        if not self.has_floorplan() or not self.grid_visible or not self.grid_px_per_meter:
            return

        interval_m = choose_grid_interval_meters(
            self.grid_px_per_meter,
            self.grid_measurement_system,
        )
        spacing_px = interval_m * self.grid_px_per_meter
        if spacing_px <= 0:
            return

        rect = self.scene.sceneRect()
        width = rect.width()
        height = rect.height()
        if width <= 0 or height <= 0:
            return

        minor_color = QColor(self.grid_color)
        minor_color.setAlpha(65)
        major_color = QColor(self.grid_color)
        major_color.setAlpha(115)
        minor_pen = QPen(minor_color, 1.0)
        major_pen = QPen(major_color, 1.5)

        x = 0.0
        index = 0
        while x <= width:
            item = QGraphicsLineItem(x, 0, x, height)
            item.setPen(major_pen if index % GRID_MAJOR_EVERY == 0 else minor_pen)
            item.setZValue(4)
            self.scene.addItem(item)
            self.grid_items.append(item)
            index += 1
            x = index * spacing_px

        y = 0.0
        index = 0
        while y <= height:
            item = QGraphicsLineItem(0, y, width, y)
            item.setPen(major_pen if index % GRID_MAJOR_EVERY == 0 else minor_pen)
            item.setZValue(4)
            self.scene.addItem(item)
            self.grid_items.append(item)
            index += 1
            y = index * spacing_px

    def clear_grid_items(self):
        for item in self.grid_items:
            self.scene.removeItem(item)
        self.grid_items = []

    def drawForeground(self, painter, rect):
        super().drawForeground(painter, rect)
        self.draw_boundaries_brush_preview(painter, rect)
        if not self.grid_visible or not self.grid_label:
            return

        painter.save()
        painter.resetTransform()
        painter.setClipping(False)
        font = painter.font()
        font.setBold(True)
        font.setPointSizeF(font.pointSizeF() * self.grid_ui_scale)
        painter.setFont(font)
        metrics = painter.fontMetrics()
        margin = scaled_grid_value(12, self.grid_ui_scale)
        padding_x = scaled_grid_value(10, self.grid_ui_scale)
        padding_y = scaled_grid_value(5, self.grid_ui_scale)
        extra_width = scaled_grid_value(8, self.grid_ui_scale)
        radius = scaled_grid_value(4, self.grid_ui_scale)
        text_width = metrics.horizontalAdvance(self.grid_label)
        text_height = metrics.height()
        label_rect = QRectF(
            margin,
            margin,
            text_width + padding_x * 2 + extra_width,
            text_height + padding_y * 2,
        )
        background = QColor("#FFFFFF")
        background.setAlpha(230)
        border = QColor(self.grid_color)
        border.setAlpha(180)
        painter.setBrush(QBrush(background))
        painter.setPen(QPen(border, 1.0))
        painter.drawRoundedRect(label_rect, radius, radius)
        painter.setPen(QColor(self.grid_color))
        painter.drawText(
            label_rect.adjusted(padding_x, padding_y, -padding_x, -padding_y),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            self.grid_label,
        )
        painter.restore()

    def set_points(self, points):
        for item in self.marker_items:
            self.scene.removeItem(item)
        self.marker_items = []

        if not self.has_floorplan():
            return

        for point in points:
            try:
                x = float(point.get("x", 0))
                y = float(point.get("y", 0))
                raw_signal = point.get("best_signal_dbm", point.get("signal_dbm"))
                signal = float(raw_signal) if raw_signal is not None else None
            except (TypeError, ValueError):
                continue

            radius = SURVEY_POINT_MARKER_RADIUS
            item = QGraphicsEllipseItem(x - radius, y - radius, radius * 2, radius * 2)
            self.style_point_marker(item, point_color(signal), self.point_key(point) == self.selected_point_key)
            tooltip = (
                self.point_tooltip_formatter(point)
                if callable(self.point_tooltip_formatter)
                else format_point_tooltip(point)
            )
            item.setToolTip(tooltip)
            item.setData(0, dict(point))
            self.scene.addItem(item)
            self.marker_items.append(item)

    def style_point_marker(self, item, color, selected=False):
        item.setBrush(QBrush(color))
        if selected:
            item.setPen(QPen(QColor("#1f2937"), 3.2))
            item.setZValue(20)
        else:
            item.setPen(QPen(Qt.GlobalColor.white, 2.0))
            item.setZValue(10)

    def point_key(self, point):
        point_id = str(point.get("point_id", "")).strip()
        if point_id:
            return ("id", point_id)

        return (
            "position",
            str(point.get("timestamp", "")),
            str(point.get("x", "")),
            str(point.get("y", "")),
        )

    def select_point(self, point):
        self.selected_point_key = self.point_key(point) if point else None
        self.refresh_point_marker_selection()

    def clear_selected_point(self):
        self.selected_point_key = None
        self.refresh_point_marker_selection()

    def refresh_point_marker_selection(self):
        for item in self.marker_items:
            point = item.data(0)
            if not isinstance(point, dict):
                continue
            try:
                raw_signal = point.get("best_signal_dbm", point.get("signal_dbm"))
                signal = float(raw_signal) if raw_signal is not None else None
            except (TypeError, ValueError):
                signal = -90
            self.style_point_marker(
                item,
                point_color(signal),
                self.point_key(point) == self.selected_point_key,
            )

    def set_ap_groups(self, groups):
        for item in self.ap_marker_items:
            self.scene.removeItem(item)
        self.ap_marker_items = []

        if not self.has_floorplan():
            return

        for group in groups or []:
            position = group.get("position") or {}
            try:
                x = int(position.get("x"))
                y = int(position.get("y"))
            except (TypeError, ValueError):
                continue

            label = str(group.get("alias", "")).strip() or str(group.get("group_id", ""))
            item = self.create_ap_marker(x, y, group, label)
            self.scene.addItem(item)
            self.ap_marker_items.append(item)

    def create_ap_marker(self, x, y, group, label):
        if self.ap_position_icon and not self.ap_position_icon.isNull():
            pixmap = self.ap_position_icon
            item = QGraphicsPixmapItem(pixmap)
            item.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
            item.setOffset(-pixmap.width() / 2, -pixmap.height() / 2)
            max_source_size = max(pixmap.width(), pixmap.height())
            if max_source_size > 0:
                item.setScale(AP_MARKER_BASE_SIZE / max_source_size)
            item.setPos(x, y)
        else:
            radius = AP_MARKER_BASE_SIZE / 2
            item = QGraphicsEllipseItem(-radius, -radius, radius * 2, radius * 2)
            item.setBrush(QBrush(QColor("#0d6efd")))
            item.setPen(QPen(Qt.GlobalColor.white, 1.6))
            item.setPos(x, y)

        item.setZValue(30)
        tooltip = (
            self.ap_tooltip_formatter(group, label, x, y)
            if callable(self.ap_tooltip_formatter)
            else format_ap_tooltip(group, label, x, y)
        )
        item.setToolTip(tooltip)
        return item

    def start_ap_position_pick(self, group_id, label):
        if not self.has_floorplan():
            return False

        self.cancel_scale_calibration_pick(emit_signal=False)
        self.pending_ap_position_group_id = str(group_id)
        self.pending_ap_position_label = str(label or group_id)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.viewport().setCursor(Qt.CursorShape.CrossCursor)
        return True

    def cancel_ap_position_pick(self, emit_signal=True):
        if not self.pending_ap_position_group_id:
            return False

        self.pending_ap_position_group_id = ""
        self.pending_ap_position_label = ""
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.viewport().unsetCursor()
        if emit_signal:
            self.apPositionCancelled.emit()
        return True

    def start_scale_calibration_pick(self):
        if not self.has_floorplan():
            return False

        self.cancel_ap_position_pick(emit_signal=False)
        self.clear_scale_calibration_overlay()
        self.scale_calibration_active = True
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.viewport().setCursor(Qt.CursorShape.CrossCursor)
        return True

    def cancel_scale_calibration_pick(self, emit_signal=True):
        if not self.scale_calibration_active and not self.scale_calibration_points:
            return False

        self.scale_calibration_active = False
        self.clear_scale_calibration_overlay()
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.viewport().unsetCursor()
        if emit_signal:
            self.scaleCalibrationCancelled.emit()
        return True

    def clear_scale_calibration_overlay(self):
        for item in self.scale_calibration_items:
            self.scene.removeItem(item)
        self.scale_calibration_items = []
        self.scale_calibration_points = []

    def pick_scale_calibration_point(self, x, y):
        self.scale_calibration_points.append((float(x), float(y)))
        marker = QGraphicsEllipseItem(float(x) - 5, float(y) - 5, 10, 10)
        marker.setBrush(QBrush(QColor("#0d6efd")))
        marker.setPen(QPen(Qt.GlobalColor.white, 1.6))
        marker.setZValue(40)
        self.scene.addItem(marker)
        self.scale_calibration_items.append(marker)

        if len(self.scale_calibration_points) == 1:
            self.scaleCalibrationFirstPointPicked.emit()
            return

        first_x, first_y = self.scale_calibration_points[0]
        line = QGraphicsLineItem(first_x, first_y, float(x), float(y))
        line.setPen(QPen(QColor("#0d6efd"), 3))
        line.setZValue(39)
        self.scene.addItem(line)
        self.scale_calibration_items.append(line)

        distance_px = math.hypot(float(x) - first_x, float(y) - first_y)
        self.scale_calibration_active = False
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.viewport().unsetCursor()
        self.scaleCalibrationCompleted.emit(distance_px)

    def zoom_in(self):
        self.set_zoom(self.zoom_level * 1.25)

    def zoom_out(self):
        self.set_zoom(self.zoom_level / 1.25)

    def set_zoom(self, zoom_level):
        if not self.has_floorplan():
            return

        zoom_level = min(6.0, max(0.1, zoom_level))
        factor = zoom_level / self.zoom_level
        self.zoom_level = zoom_level
        self.scale(factor, factor)
        self.update_boundaries_cursor()
        self.zoomChanged.emit(self.zoom_level)

    def fit_to_view(self):
        if not self.has_floorplan():
            return

        self.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        transform = self.transform()
        self.zoom_level = max(transform.m11(), transform.m22())
        self.update_boundaries_cursor()
        self.zoomChanged.emit(self.zoom_level)

    def set_focus_point_zoom_percent(self, percent):
        try:
            zoom_level = float(percent) / 100.0
        except (TypeError, ValueError):
            zoom_level = FOCUS_POINT_DEFAULT_ZOOM_LEVEL

        self.focus_point_zoom_level = min(2.0, max(1.0, zoom_level))

    def focus_target_zoom_level(self):
        return self.focus_point_zoom_level

    def wheelEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if event.angleDelta().y() > 0:
                self.zoom_in()
            else:
                self.zoom_out()
            event.accept()
            return
        if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            delta = event.angleDelta().y() or event.angleDelta().x()
            if delta:
                scroll_bar = self.horizontalScrollBar()
                scroll_bar.setValue(scroll_bar.value() - delta)
                event.accept()
                return

        super().wheelEvent(event)

    def mousePressEvent(self, event):
        if self.boundaries_edit_active and event.button() == Qt.MouseButton.RightButton:
            point = self.mapToScene(event.position().toPoint())
            point = self.clamp_boundaries_point(point)
            self.update_boundaries_brush_preview(point)
            self.boundaries_drawing_active = True
            self.begin_boundaries_stroke(point)
            event.accept()
            return

        if self.scale_calibration_active:
            if event.button() == Qt.MouseButton.LeftButton:
                point = self.mapToScene(event.position().toPoint())
                self.pick_scale_calibration_point(point.x(), point.y())
            event.accept()
            return

        if self.pending_ap_position_group_id:
            if event.button() == Qt.MouseButton.LeftButton:
                point = self.mapToScene(event.position().toPoint())
                group_id = self.pending_ap_position_group_id
                self.pending_ap_position_group_id = ""
                self.pending_ap_position_label = ""
                self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
                self.viewport().unsetCursor()
                self.apPositionPicked.emit(group_id, int(round(point.x())), int(round(point.y())))
            event.accept()
            return

        if self.has_floorplan() and event.button() == Qt.MouseButton.RightButton:
            point = self.mapToScene(event.position().toPoint())
            self.surveyPointRequested.emit(int(round(point.x())), int(round(point.y())))
            event.accept()
            return

        if self.has_floorplan() and event.button() == Qt.MouseButton.LeftButton:
            scene_point = self.mapToScene(event.position().toPoint())
            for item in self.scene.items(scene_point):
                point_data = item.data(0)
                if isinstance(point_data, dict):
                    self.select_point(point_data)
                    self.pointSelected.emit(point_data)
                    event.accept()
                    return
            self.pointSelectionCleared.emit()
            self.clear_selected_point()
            self.viewport().setCursor(Qt.CursorShape.ClosedHandCursor)

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        scene_point = self.mapToScene(event.position().toPoint())
        if (
            self.boundaries_edit_active
            and self.boundaries_drawing_active
            and event.buttons() & Qt.MouseButton.RightButton
            and self.boundaries_last_point is not None
        ):
            point = self.clamp_boundaries_point(scene_point)
            self.update_boundaries_brush_preview(point)
            self.continue_boundaries_stroke(point)
            event.accept()
            return

        super().mouseMoveEvent(event)
        if self.boundaries_edit_active:
            self.update_boundaries_brush_preview(scene_point)

    def mouseReleaseEvent(self, event):
        if self.boundaries_edit_active and event.button() == Qt.MouseButton.RightButton:
            point = self.clamp_boundaries_point(
                self.mapToScene(event.position().toPoint())
            )
            self.update_boundaries_brush_preview(point)
            if self.boundaries_drawing_active:
                self.finish_boundaries_stroke(point)
            self.boundaries_drawing_active = False
            self.boundaries_last_point = None
            self.boundaries_stroke_points = []
            event.accept()
            return

        super().mouseReleaseEvent(event)
        if not self.pending_ap_position_group_id and not self.scale_calibration_active:
            if self.boundaries_edit_active:
                self.update_boundaries_cursor()
            else:
                self.viewport().setCursor(Qt.CursorShape.ArrowCursor)

    def leaveEvent(self, event):
        self.hide_boundaries_brush_preview()
        super().leaveEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape and self.cancel_scale_calibration_pick():
            event.accept()
            return

        if event.key() == Qt.Key.Key_Escape and self.cancel_ap_position_pick():
            event.accept()
            return

        super().keyPressEvent(event)

    def focus_on(self, x, y):
        if not self.has_floorplan():
            return

        point = QPointF(float(x), float(y))
        target_zoom = self.focus_target_zoom_level()
        current_zoom = max(self.transform().m11(), self.transform().m22(), self.zoom_level)
        if current_zoom < target_zoom:
            self.set_zoom(target_zoom)

        self.centerOn(point)
        self.position_scene_point_in_viewport(
            point,
            0.5,
            FOCUS_POINT_VERTICAL_VIEWPORT_FRACTION,
        )

    def position_scene_point_in_viewport(self, point, x_fraction, y_fraction):
        viewport_rect = self.viewport().rect()
        if viewport_rect.isEmpty():
            return

        target_x = viewport_rect.left() + int(round(viewport_rect.width() * x_fraction))
        target_y = viewport_rect.top() + int(round(viewport_rect.height() * y_fraction))
        current_pos = self.mapFromScene(point)
        horizontal_bar = self.horizontalScrollBar()
        vertical_bar = self.verticalScrollBar()
        horizontal_bar.setValue(horizontal_bar.value() + current_pos.x() - target_x)
        vertical_bar.setValue(vertical_bar.value() + current_pos.y() - target_y)


def load_floorplan_pixmap(file_path):
    if file_path.lower().endswith(".pdf"):
        return QPixmap.fromImage(render_pdf_page_to_qimage(file_path))

    return QPixmap(file_path)


def load_ap_position_icon():
    icon_path = Path(__file__).resolve().parent.parent / "images" / "wifi.png"
    if not icon_path.exists():
        return QPixmap()

    return QPixmap(str(icon_path))


def choose_grid_interval_meters(px_per_meter, measurement_system, min_spacing_px=MIN_GRID_SPACING_PX):
    px_per_meter = float(px_per_meter)
    if px_per_meter <= 0:
        return 1.0

    if normalize_measurement_system(measurement_system) == MEASUREMENT_SYSTEM_IMPERIAL:
        for interval_ft in IMPERIAL_GRID_INTERVALS_FT:
            interval_m = display_units_to_meters(interval_ft, MEASUREMENT_SYSTEM_IMPERIAL)
            if interval_m * px_per_meter >= min_spacing_px:
                return interval_m
        return display_units_to_meters(IMPERIAL_GRID_INTERVALS_FT[-1], MEASUREMENT_SYSTEM_IMPERIAL)

    for interval_m in METRIC_GRID_INTERVALS_M:
        if interval_m * px_per_meter >= min_spacing_px:
            return interval_m
    return METRIC_GRID_INTERVALS_M[-1]


def format_grid_interval(px_per_meter, measurement_system):
    measurement_system = normalize_measurement_system(measurement_system)
    interval_m = choose_grid_interval_meters(px_per_meter, measurement_system)
    value = meters_to_display_units(interval_m, measurement_system)
    if abs(value - round(value)) < 0.01:
        value_text = str(int(round(value)))
    else:
        value_text = f"{value:.1f}".rstrip("0").rstrip(".")
    return f"{value_text} {distance_unit_label(measurement_system)}"


def scaled_grid_value(value, ui_scale):
    return max(1, int(round(float(value) * float(ui_scale or 1.0))))


def point_color(signal_dbm):
    if signal_dbm is None:
        return QColor("#6b7280")
    if signal_dbm >= -60:
        return QColor("#4E8F5A")
    if signal_dbm >= -70:
        return QColor("#D6B84A")
    if signal_dbm >= -80:
        return QColor("#D49A32")
    return QColor("#C65A5A")


def format_point_tooltip(point, translations=None):
    ssids = [str(ssid) for ssid in point.get("ssids", []) if str(ssid)]
    ssid_text = ssids or "-"
    signal_scope = str(point.get("signal_scope", "all"))
    scope_label = (
        tooltip_text(translations, "tooltip_scope_relevant", "Relevant Networks")
        if signal_scope == "relevant"
        else tooltip_text(translations, "tooltip_scope_all", "All Networks")
    )
    row_count = format_tooltip_scalar(point.get("row_count", "-"))
    relevant_count = numeric_count(point.get("relevant_row_count", 0))
    rows_value = (
        tooltip_template(
            translations,
            "tooltip_rows_relevant",
            "{relevant}/{total} relevant",
            relevant=relevant_count,
            total=row_count,
        )
        if relevant_count
        else row_count
    )
    signal_value = point.get("best_signal_dbm", "-")
    signal_text = format_signal_dbm(signal_value)
    try:
        accent = point_color(float(signal_value)).name()
    except (TypeError, ValueError):
        accent = "#111111"

    rows = [
        tooltip_section(tooltip_text(translations, "tooltip_section_location", "Location")),
        ("x/y", f"{format_tooltip_scalar(point.get('x', '-'))}, {format_tooltip_scalar(point.get('y', '-'))}"),
        (tooltip_text(translations, "tooltip_time", "Time"), point.get("timestamp", "-")),
        tooltip_section(tooltip_text(translations, "tooltip_section_signal", "Signal")),
        (tooltip_text(translations, "signal", "Signal"), signal_text),
    ]
    quality_label = str(point.get("quality_label", "") or "").strip()
    if quality_label and quality_label != "-":
        rows.append((tooltip_text(translations, "quality", "Quality"), quality_label))
    rows.extend([
        (tooltip_text(translations, "tooltip_signal_scope", "Signal Scope"), scope_label),
        (tooltip_text(translations, "rows", "Rows"), rows_value),
        tooltip_section(tooltip_text(translations, "tooltip_section_networks", "Networks")),
        (tooltip_text(translations, "tooltip_detected_ssids", "Detected SSIDs"), ssid_text),
    ])
    return build_html_tooltip(
        tooltip_text(translations, "survey_point_tooltip_title", "Survey Point"),
        rows,
        accent,
    )


def format_ap_tooltip(group, label, x, y, translations=None):
    bssids = format_tooltip_list(group.get("bssids", []))
    metadata = group.get("metadata") if isinstance(group.get("metadata"), dict) else {}
    rows = [
        tooltip_section(tooltip_text(translations, "tooltip_section_identity", "Identity")),
        (tooltip_text(translations, "ap_alias_group", "AP Group"), group.get("group_id", "-")),
        (tooltip_text(translations, "ap_alias_value", "Alias"), label),
        (tooltip_text(translations, "ap_group_role", "Role"), format_ap_role_label(group, translations)),
        (tooltip_text(translations, "ap_alias_bssids", "BSSID"), bssids),
    ]
    rows.append(tooltip_section(tooltip_text(translations, "tooltip_section_position", "Position")))
    rows.append(("x/y", f"{format_tooltip_scalar(x)}, {format_tooltip_scalar(y)}"))

    radio_rows = [
        (tooltip_text(translations, "ap_alias_ssids", "Seen SSIDs"), format_tooltip_list(group.get("ssids", []))),
        (tooltip_text(translations, "ap_alias_channels", "Channels"), format_tooltip_list(group.get("channels", []))),
        (tooltip_text(translations, "ap_alias_bands", "Bands"), format_tooltip_list(group.get("bands", []))),
    ]
    radio_rows = [row for row in radio_rows if row[1] != "-"]
    if radio_rows:
        rows.append(tooltip_section(tooltip_text(translations, "tooltip_section_radio", "Radio")))
        rows.extend(radio_rows)

    metadata_rows = [
        (tooltip_text(translations, "ap_group_metadata_vendor", "Vendor"), format_tooltip_list(metadata.get("vendor", ""))),
        (tooltip_text(translations, "ap_group_metadata_model", "Model"), format_tooltip_list(metadata.get("model", ""))),
        (tooltip_text(translations, "ap_group_metadata_mounting", "Mounting"), format_tooltip_list(metadata.get("mounting", ""))),
        (tooltip_text(translations, "ap_group_metadata_expected_bands", "Expected Bands"), format_tooltip_list(metadata.get("expected_bands", ""))),
        (tooltip_text(translations, "ap_group_metadata_expected_channels", "Expected Channels"), format_tooltip_list(metadata.get("expected_channels", ""))),
        (tooltip_text(translations, "ap_group_metadata_coverage_scope", "Coverage Scope"), format_tooltip_list(metadata.get("coverage_scope", ""))),
        (tooltip_text(translations, "ap_group_metadata_coverage_radius", "Coverage Radius"), format_tooltip_list(metadata.get("coverage_radius_m", ""))),
    ]
    metadata_rows = [row for row in metadata_rows if row[1] != "-"]
    if metadata_rows:
        rows.append(tooltip_section(tooltip_text(translations, "tooltip_section_metadata", "Metadata")))
        rows.extend(metadata_rows)

    return build_html_tooltip(
        tooltip_text(translations, "wifi_ap_tooltip_title", "Wi-Fi AP"),
        rows,
        "#0d6efd",
    )


def tooltip_text(translations, key, fallback):
    if callable(translations):
        value = translations(key)
        return fallback if value == key else value
    if isinstance(translations, dict):
        return translations.get(key, fallback)
    return fallback


def tooltip_template(translations, key, fallback, **values):
    template = tooltip_text(translations, key, fallback)
    try:
        return template.format(**values)
    except (KeyError, ValueError):
        return fallback.format(**values)


def numeric_count(value):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def format_tooltip_scalar(value):
    if value in (None, ""):
        return "-"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if math.isnan(number):
        return "-"
    if number.is_integer():
        return str(int(number))
    return f"{number:.1f}"


def format_signal_dbm(value):
    formatted = format_tooltip_scalar(value)
    return "-" if formatted == "-" else f"{formatted} dBm"


def format_tooltip_list(values):
    if values in (None, ""):
        return "-"
    if isinstance(values, (list, tuple, set)):
        clean_values = [str(value).strip() for value in values if str(value).strip()]
        return clean_values or "-"
    return str(values).strip() or "-"


def format_ap_role_label(group, translations):
    role = normalize_ap_role(group.get("role"))
    return tooltip_text(translations, f"ap_group_role_{role}", role.replace("_", " ").title())
