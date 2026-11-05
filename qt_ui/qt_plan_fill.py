"""Fill Boundaries from actual closed vector faces, including nested rooms."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath

from survey.plan_drawing import drawing_geometry
from survey.curved_regions import closed_drawing_regions


def closed_fill_paths(faces):
    if len(faces) > 2000:
        raise ValueError("Too many closed regions")
    paths = []
    for face in faces:
        path = QPainterPath()
        path.setFillRule(Qt.FillRule.WindingFill)
        if face:
            path.moveTo(*face[0])
            for point in face[1:]:
                path.lineTo(*point)
            path.closeSubpath()
            paths.append(path)
    # Disconnected nested loops form separate rooms. Filling the surrounding
    # room must respect the inner wall instead of flooding its interior too.
    result = []
    for path in paths:
        region = QPainterPath(path)
        bounds = path.boundingRect()
        for inner in paths:
            if (inner is not path and bounds != inner.boundingRect()
                    and bounds.contains(inner.boundingRect()) and path.contains(inner)):
                region = region.subtracted(inner)
        if not region.isEmpty():
            result.append(region)
    return result


def fill_closed_boundaries(owner, point=None):
    tools = getattr(owner, "plan_tools", None)
    if not tools or not tools.available() or not owner.floorplan_view.boundaries_edit_active:
        return False
    try:
        lines, curves = drawing_geometry(owner.session.metadata)
        regions = closed_drawing_regions(lines or [], curves)
        if regions.limited:
            raise ValueError("Closed-area detection limited")
        paths = closed_fill_paths(regions.faces)
    except (ValueError, TypeError, KeyError):
        owner.status.showMessage(owner.tr("design_regions_limited"))
        return False
    if point is not None:
        paths = [path for path in paths if path.contains(point)]
        if paths:
            paths = [min(paths, key=lambda path: path.boundingRect().width() * path.boundingRect().height())]
    if not paths:
        owner.status.showMessage(owner.tr("boundaries_fill_no_region"))
        return False
    view = owner.floorplan_view
    if not view.ensure_boundaries_mask():
        return False
    original = view.boundaries_mask_image.copy()
    painter = QPainter(view.boundaries_mask_image)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(37, 99, 235))
    for path in paths:
        painter.drawPath(path)
    painter.end()
    if view.boundaries_mask_image == original:
        return False
    view.boundaries_mask_dirty_rect = view.scene.sceneRect()
    view.refresh_boundaries_mask_after_change()
    owner.status.showMessage(owner.tr("boundaries_fill_done", count=len(paths)))
    return True
