"""Retained per-layer graphics; flag changes never reconstruct wall/text paths."""
from copy import deepcopy

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGraphicsPathItem

from qt_ui.qt_clean_plan import VectorPlanSource
from survey.wall_rendering import wall_item
from survey.plan_label_rendering import label_item
from survey.plan_annotation_rendering import annotation_item
from survey.curved_regions import closed_drawing_regions
from survey.plan_faces import RegionPicker
from survey.plan_clearances import ClearanceIndex
from survey.plan_snapping import PlanSnapper


class LayerGeometry:
    """Model indexes shared across text edits, without retaining scene items."""
    def __init__(self,state):
        self.state = {k:deepcopy(state[k]) for k in ('segments','curves','annotations')}
        self._regions = self._picker = self._snapper = None

    @property
    def regions(self):
        if self._regions is None:
            self._regions = closed_drawing_regions(self.state['segments'] or [],self.state['curves'])
        return self._regions

    @property
    def picker(self):
        if self._picker is None:
            self._picker = RegionPicker(self.state['segments'] or [],self.state['curves'])
        return self._picker

    @property
    def snapper(self):
        if self._snapper is None:
            self._snapper = PlanSnapper(self.state['segments'] or [],self.state['curves'],region_centers=lambda:self.picker.centers())
        return self._snapper


class LayerGraphics:
    def __init__(self,state,source,geometry=None):
        self.state = deepcopy(state)
        self.source = source
        self.groups = None
        self.geometry = geometry or LayerGeometry(state)

    def build(self,scene):
        if self.groups is not None:
            return
        state,source = self.state,self.source
        def paths(commands):
            result = []
            for path,pen,brush in commands:
                item = QGraphicsPathItem(path)
                item.setPen(pen)
                item.setBrush(brush)
                result.append(item)
            return result
        self.groups = (
            [wall_item(*command) for command in source._wall_commands],
            paths(source._line_commands),paths(source._curve_commands),
            [annotation_item(a,parts=parts) for a,parts in zip(state['annotations'],source._annotation_parts)],
            [label_item(label,path=path) for label,path in zip(state['labels'],source._label_paths)])
        for group in self.groups:
            for item in group:
                item.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
                scene.addItem(item)

    def configure(self,visible,rank):
        if self.groups is not None:
            for group,offset in zip(self.groups,(.0005,.001,.002,.006,.009)):
                for item in group:
                    item.setVisible(visible)
                    item.setZValue(7+rank*.02+offset)

    def remove(self,scene):
        if self.groups is not None:
            for group in self.groups:
                for item in group:
                    if item.scene() is scene:
                        scene.removeItem(item)

    @property
    def regions(self):
        return self.geometry.regions

    @property
    def picker(self):
        return self.geometry.picker

    @property
    def snapper(self):
        return self.geometry.snapper


class LayerScene:
    def __init__(self,scene,size):
        self.scene,self.size = scene,size
        self.layers = {}
        self.composites = {}

    def prepare(self,document):
        # Validate all layers before changing scene items, including hidden ones.
        sources = {layer['id']:(self.layers[layer['id']].source
                               if layer['id'] in self.layers and self.layers[layer['id']].state == layer['drawing']
                               else VectorPlanSource.for_layer(self.size,layer['drawing'])) for layer in document['layers']}
        desired = {layer['id']:layer for layer in document['layers']}
        geometries = {}
        for identity,entry in list(self.layers.items()):
            if identity not in desired or entry.state != desired[identity]['drawing']:
                if identity in sources and entry.source._geometry_key == sources[identity]._geometry_key:
                    geometries[identity] = entry.geometry
                else:
                    self.composites.clear()
                entry.remove(self.scene)
                del self.layers[identity]
        for rank,layer in enumerate(document['layers']):
            entry = self.layers.get(layer['id'])
            if entry is None:
                entry = self.layers[layer['id']] = LayerGraphics(layer['drawing'],sources[layer['id']],geometries.get(layer['id']))
            if layer['visible'] or layer['id'] == document['active']:
                entry.build(self.scene)
            entry.configure(layer['visible'],rank)

    def composite(self,document):
        entries = tuple(self.layers[layer['id']].geometry for layer in document['layers'] if layer['visible'])
        if entries not in self.composites:
            lines = [s for e in entries for s in e.state['segments'] or []]
            curves = [s for e in entries for s in e.state['curves']]
            annotations = [s for e in entries for s in e.state['annotations']]
            if len(self.composites) >= 8:
                self.composites.clear()
            self.composites[entries] = (
                ClearanceIndex(lines,curves,annotations),
                PlanSnapper(lines,curves,region_centers=lambda:[c for e in entries for c in e.picker.centers()]))
        return self.composites[entries]
