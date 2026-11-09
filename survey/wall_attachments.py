"""Useful straight-line lengths outside the physical walls at their ends."""
import math

from PySide6.QtCore import QPointF

from survey.planar_geometry import point_projection
from survey.wall_geometry import EPS, solid, aperture_channels, united


class WallAttachmentIndex:
    def __init__(self, states=()):
        self.records = []
        for state in states:
            lines, curves = state['segments'] or [], state['curves']
            cuts = united(aperture_channels(lines, state.get('annotations', ())))
            for shape in [*lines, *curves]:
                if not shape.get('wall'):
                    continue
                body = solid(shape).subtracted(cuts)
                edges = []
                for polygon in body.toSubpathPolygons():
                    points = [(p.x(), p.y()) for p in polygon]
                    edges.extend((a,b) for a,b in zip(points, points[1:]+points[:1]) if math.dist(a,b)>EPS)
                self.records.append((shape, body, edges))

    def hidden(self, point, direction):
        intervals = []
        ux,uy = direction
        for shape,body,edges in self.records:
            if 'kind' not in shape:
                dx,dy = shape['x2']-shape['x1'],shape['y2']-shape['y1']
                if abs(dx*uy-dy*ux) <= EPS*math.hypot(dx,dy):
                    # A coincident/shared wall is not a perpendicular attachment.
                    continue
            hits = [0.0]
            for a,b in edges:
                vx,vy = b[0]-a[0],b[1]-a[1]
                determinant = ux*vy-uy*vx
                if abs(determinant) <= 1e-10*math.hypot(vx,vy):
                    continue
                ax,ay = a[0]-point[0],a[1]-point[1]
                distance = (ax*vy-ay*vx)/determinant
                fraction = (ax*uy-ay*ux)/determinant
                if distance > EPS and -EPS <= fraction <= 1+EPS:
                    hits.append(distance)
            hits = sorted(set(hits))
            for low,high in zip(hits,hits[1:]):
                if high-low <= EPS:
                    continue
                mid = (point[0]+ux*(low+high)/2,point[1]+uy*(low+high)/2)
                if (body.contains(QPointF(*mid)) or any(
                        math.dist(mid,point_projection(mid,a,b)) <= EPS for a,b in edges)):
                    intervals.append((low,high))
        end = 0.0
        for low,high in sorted(intervals):
            if low > end+EPS:
                break
            end = max(end,high)
        return end

    def clear_ends(self, a, b):
        length = math.dist(a,b)
        if length <= EPS:
            return 0.0,0.0
        direction = ((b[0]-a[0])/length,(b[1]-a[1])/length)
        return self.hidden(a,direction),self.hidden(b,(-direction[0],-direction[1]))

    def clear_length(self, a, b):
        before,after = self.clear_ends(a,b)
        return max(0.0,math.dist(a,b)-before-after)
