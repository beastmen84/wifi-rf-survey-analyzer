"""Compact rack configuration and one-switch-at-a-time legend editing."""
from copy import deepcopy
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog,QDialogButtonBox,QFormLayout,QHeaderView,QLabel,
    QLineEdit,QSpinBox,QTableWidget,QTableWidgetItem,QVBoxLayout,QHBoxLayout,QWidget,
    QTreeWidget,QTreeWidgetItem,QAbstractItemView)
from survey.rack_inventory import (MAX_SWITCHES,MAX_SWITCH_PORTS,MAX_RACK_PORTS,
    validate_rack,rack_label,table_title)
from qt_ui.scaling import widget_px


class RackConfigurationDialog(QDialog):
    def __init__(self,owner,value):
        super().__init__(owner)
        self.owner=owner
        self.pool=deepcopy(value.get('switches',[]))
        self.setWindowTitle(owner.tr('rack_configure'))
        self.resize(widget_px(owner,540),widget_px(owner,430))
        layout=QVBoxLayout(self)
        form=QFormLayout()
        self.name=QLineEdit(value.get('name',''));self.name.setMaxLength(80)
        self.name.setPlaceholderText(owner.tr('rack_name_hint'))
        self.count=QSpinBox();self.count.setRange(0,MAX_SWITCHES);self.count.setValue(len(self.pool))
        form.addRow(owner.tr('rack_name'),self.name)
        form.addRow(owner.tr('rack_switch_count'),self.count)
        layout.addLayout(form)
        self.table=QTableWidget(0,2)
        self.table.setHorizontalHeaderLabels([owner.tr('rack_switch'),owner.tr('rack_port_count')])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().hide()
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table,1)
        hint=QLabel(owner.tr('rack_configuration_hint'));hint.setWordWrap(True);layout.addWidget(hint)
        self.status=QLabel();self.status.setWordWrap(True);layout.addWidget(self.status)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(owner.tr('cancel'))
        self.ok=buttons.button(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept);buttons.rejected.connect(self.reject);layout.addWidget(buttons)
        self.count.valueChanged.connect(self.rebuild)
        self.rebuild()

    def rebuild(self):
        count=self.count.value()
        self.pool.extend(dict(ports=[]) for _ in range(count-len(self.pool)))
        self.table.setRowCount(count)
        self.spins=[]
        for i in range(count):
            cell=QTableWidgetItem(self.owner.tr('rack_switch_number').format(number=i+1))
            self.table.setItem(i,0,cell)
            spin=QSpinBox();spin.setRange(0,MAX_SWITCH_PORTS)
            spin.setValue(self.pool[i].get('_count',len(self.pool[i]['ports'])))
            spin.setMinimumHeight(widget_px(self.owner,32))
            spin.valueChanged.connect(lambda value,index=i:self.ports_changed(index,value))
            self.table.setCellWidget(i,1,spin);self.spins.append(spin)
        self.table.resizeRowsToContents()
        self.update_status()

    def ports_changed(self,index,count):
        ports=self.pool[index]['ports']
        ports.extend('' for _ in range(count-len(ports)))
        self.pool[index]['_count']=count
        self.update_status()

    def properties(self):
        return validate_rack(dict(name=self.name.text(),switches=[dict(ports=switch['ports'][:spin.value()])
            for switch,spin in zip(self.pool,self.spins)]))

    def update_status(self):
        count=sum(s.value() for s in self.spins)
        self.ok.setEnabled(count<=MAX_RACK_PORTS)
        self.status.setText(self.owner.tr('rack_inventory_limit') if count>MAX_RACK_PORTS else
                            self.owner.tr('rack_ports_total').format(count=count))

    def accept(self):
        try:
            self.properties()
        except ValueError:
            self.status.setText(self.owner.tr('rack_inventory_invalid'))
            return
        super().accept()


class RackInventoryPanel(QWidget):
    def __init__(self,owner,document,entries):
        super().__init__()
        self.owner,self.document=owner,document
        self.loading=True;self.current=None
        row=QHBoxLayout(self)
        self.tree=QTreeWidget();self.tree.setHeaderHidden(True)
        self.tree.setMinimumWidth(widget_px(owner,180));row.addWidget(self.tree,1)
        detail=QVBoxLayout();self.heading=QLabel();self.heading.setWordWrap(True)
        self.heading.setTextFormat(Qt.TextFormat.PlainText)
        detail.addWidget(self.heading)
        self.table=QTableWidget(0,2)
        self.table.setHorizontalHeaderLabels([owner.tr('rack_port_number'),owner.tr('legend_description')])
        self.table.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1,QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().hide();self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        from qt_ui.qt_plan_legend import DescriptionDelegate
        self.table.setItemDelegateForColumn(1,DescriptionDelegate(self.table))
        detail.addWidget(self.table,1)
        self.hint=QLabel(owner.tr('rack_legend_hint'));self.hint.setWordWrap(True);detail.addWidget(self.hint)
        row.addLayout(detail,3)
        roots={}
        for entry in entries:
            key=entry['layer'],entry['id']
            if key not in roots:
                root=QTreeWidgetItem([rack_label(entry,owner.tr)+' · '+entry['layer_name']])
                root.setToolTip(0,root.text(0))
                self.tree.addTopLevelItem(root);roots[key]=root
            child=QTreeWidgetItem([owner.tr('rack_switch_number').format(number=entry['switch']+1)+
                                  f" ({len(entry['rows'])})"])
            child.setToolTip(0,table_title(entry,owner.tr)+' · '+owner.tr('rack_ports_total').format(count=len(entry['rows'])))
            child.setData(0,Qt.ItemDataRole.UserRole,entry)
            roots[key].addChild(child)
        self.tree.expandAll()
        self.tree.currentItemChanged.connect(self.select_switch)
        self.table.itemChanged.connect(self.store_description)
        self.loading=False
        if self.tree.topLevelItemCount():
            self.tree.setCurrentItem(self.tree.topLevelItem(0).child(0))

    def selected_model(self):
        entry=self.current
        layer=next(l for l in self.document['layers'] if l['id']==entry['layer'])
        item=next(a for a in layer['drawing']['annotations'] if a['id']==entry['id'])
        return layer,item['rack']['switches'][entry['switch']]['ports']

    def select_switch(self,item,_previous=None):
        self.finish_edit()
        self.loading=True
        self.current=item.data(0,Qt.ItemDataRole.UserRole) if item else None
        self.table.setRowCount(0)
        if self.current:
            layer,ports=self.selected_model()
            self.heading.setText(table_title(self.current,self.owner.tr))
            self.table.setRowCount(len(ports))
            for i,description in enumerate(ports):
                ref=QTableWidgetItem(str(i+1));ref.setFlags(ref.flags()&~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(i,0,ref)
                text=QTableWidgetItem(description)
                if not layer['visible'] or layer['locked']:
                    text.setFlags(text.flags()&~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(i,1,text)
            if not ports:
                self.heading.setText(self.heading.text()+' · '+self.owner.tr('rack_no_ports'))
        else:
            self.heading.setText(self.owner.tr('rack_select_switch'))
        self.loading=False

    def finish_edit(self):
        from qt_ui.qt_plan_legend import finish_table_edit
        finish_table_edit(self.table)

    def store_description(self,cell):
        if self.loading or self.current is None or cell.column()!=1:
            return
        layer,ports=self.selected_model()
        if layer['visible'] and not layer['locked']:
            ports[cell.row()]=cell.text()[:2000]
