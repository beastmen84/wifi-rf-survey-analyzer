"""Bounds and closed-region membership for mixed drawing selections."""
from PySide6.QtCore import QPointF
from PySide6.QtGui import QPainterPathStroker
from survey.plan_annotation_rendering import annotation_path
from survey.plan_annotations import annotation_points, HOSTED_ANNOTATIONS, supported


def merge_selection(previous, picked, *, toggle=False):
    """Merge independent index groups without duplicates, in stable index order."""
    return tuple(tuple(sorted(set(a)^set(b) if toggle else set(a)|set(b)))
                 for a,b in zip(previous,picked,strict=True))


def annotation_geometry(items, lines=()):
    result = []
    for item in items:
        b = annotation_path(item, lines).boundingRect()
        points = [(b.left(),b.top()),(b.right(),b.top()),(b.right(),b.bottom()),(b.left(),b.bottom())]
        result.extend(dict(x1=a[0],y1=a[1],x2=c[0],y2=c[1],color=item['color'])
                      for a,c in zip(points,points[1:]+points[:1]))
    return result


def annotation_intersects(item,rect,lines=()):
    path = annotation_path(item, lines)
    stroke = QPainterPathStroker()
    stroke.setWidth(max(2,item['stroke']))
    return path.intersects(rect) or stroke.createStroke(path).intersects(rect)


def region_contents(path, annotations, labels, selected_lines):
    stroke = QPainterPathStroker()
    stroke.setWidth(.0002)
    boundary = stroke.createStroke(path)
    region = path.united(boundary)
    ink = QPainterPathStroker()
    ink.setWidth(.0001)
    def inside(point):
        p = QPointF(*point)
        return path.contains(p) or boundary.contains(p)
    def contained(item):
        if not all(inside(p) for p in annotation_points(item)):
            return False
        shape = annotation_path(item)
        footprint = ink.createStroke(shape)
        if item['kind'] != 'marker':
            footprint = shape.united(footprint)
        return footprint.subtracted(region).simplified().isEmpty()
    indices = [i for i,a in enumerate(annotations) if (a['kind'] in HOSTED_ANNOTATIONS and supported(a,selected_lines))
               or (a['kind'] not in HOSTED_ANNOTATIONS and contained(a))]
    texts = [i for i,label in enumerate(labels) if inside((label['x'],label['y']))]
    return indices,texts
