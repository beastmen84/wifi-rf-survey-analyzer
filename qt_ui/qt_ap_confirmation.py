"""Accessible table check state rendered as a physical-AP approval badge."""

from PySide6.QtCore import QEvent, QPersistentModelIndex, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QApplication, QStyle, QStyledItemDelegate, QStyleOptionViewItem

from qt_ui.scaling import widget_px
from qt_ui.qt_theme import QT_THEMES


class APConfirmationDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        owner = self.parent()
        colors = QT_THEMES.get(getattr(owner.app, "theme", "light"), QT_THEMES["light"])
        styled = QStyleOptionViewItem(option)
        self.initStyleOption(styled, index)
        status = "M" if "M" in styled.text else ""
        styled.text = ""
        styled.features &= ~QStyleOptionViewItem.ViewItemFeature.HasCheckIndicator
        owner.table.style().drawControl(QStyle.ControlElement.CE_ItemViewItem, styled, painter, owner.table)
        size = widget_px(owner, 22)
        left = option.rect.center().x() - size / 2
        circle = QRectF(left, option.rect.center().y() - size / 2, size, size)
        checked = index.data(Qt.ItemDataRole.CheckStateRole) == Qt.CheckState.Checked.value
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        foreground = option.palette.highlightedText().color() if selected else QColor(colors["text"])
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if "M" in status:
            painter.setFont(styled.font)
            painter.setPen(foreground)
            painter.drawText(option.rect, Qt.AlignmentFlag.AlignCenter, "M")
            painter.restore()
            return
        border = QColor("#21864B") if checked else (foreground if selected else QColor(colors["muted"]))
        painter.setPen(QPen(border, widget_px(owner, 2)))
        painter.setBrush(QColor("#21864B") if checked else Qt.BrushStyle.NoBrush)
        painter.drawEllipse(circle.adjusted(1, 1, -1, -1))
        if checked:
            path = QPainterPath(QPointF(circle.left() + size * .25, circle.top() + size * .51))
            path.lineTo(circle.left() + size * .43, circle.top() + size * .69)
            path.lineTo(circle.left() + size * .76, circle.top() + size * .32)
            painter.setPen(QPen(QColor("#FFFFFF"), widget_px(owner, 2),
                                Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            painter.drawPath(path)
        painter.restore()

    def editorEvent(self, event, model, option, index):
        if event.type() == QEvent.Type.MouseButtonPress:
            self._pressed = ((QPersistentModelIndex(index), event.globalPosition())
                             if event.button() == Qt.MouseButton.LeftButton else None)
            return self._pressed is not None
        if event.type() == QEvent.Type.MouseButtonDblClick:
            self._pressed = None
            return True
        if event.type() == QEvent.Type.MouseButtonRelease:
            pressed = getattr(self, "_pressed", None)
            self._pressed = None
            activate = (event.button() == Qt.MouseButton.LeftButton and pressed is not None
                        and pressed[0] == index and option.rect.contains(event.position().toPoint())
                        and (event.globalPosition() - pressed[1]).manhattanLength() < QApplication.startDragDistance())
        elif event.type() == QEvent.Type.KeyPress:
            activate = event.key() in (Qt.Key.Key_Space, Qt.Key.Key_Select) and not event.isAutoRepeat()
        else:
            return False
        if not activate:
            return False
        if "M" in str(index.data(Qt.ItemDataRole.DisplayRole) or ""):
            owner = self.parent()
            owner.select_group_by_id(index.data(Qt.ItemDataRole.UserRole))
            owner.update_action_state()
            owner.memory_menu.popup(owner.table.viewport().mapToGlobal(option.rect.bottomLeft()))
            return True
        checked = index.data(Qt.ItemDataRole.CheckStateRole) == Qt.CheckState.Checked.value
        return model.setData(index, Qt.CheckState.Unchecked if checked else Qt.CheckState.Checked,
                             Qt.ItemDataRole.CheckStateRole)
