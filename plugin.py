# -*- coding: utf-8 -*-
import json
from qgis.PyQt.QtCore import Qt, QSettings, QVariant
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import (
    QAction, QDockWidget, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QListWidget, QListWidgetItem, QPushButton, QMessageBox,
    QInputDialog, QDialog, QDialogButtonBox, QFormLayout, QFileDialog,
    QTableWidget, QTableWidgetItem, QAbstractItemView, QCheckBox
)
from qgis.core import QgsProject, QgsVectorLayer, QgsField, Qgis

SETTINGS_GROUP = "AttributeTemplateFiller"
TEMPLATES_KEY = "templates_json"
ACTIVE_KEY = "active_templates_json"
LANG_KEY = "ui_language"  # auto/en/ru

STRINGS = {
    "en": {
        "dock_title": "Attribute Templates",
        "layer": "Layer:",
        "templates": "Templates:",
        "active": "Active template:",
        "none": "(none)",
        "new": "New",
        "edit": "Edit",
        "duplicate": "Duplicate",
        "delete": "Delete",
        "set_active": "Set active",
        "clear_active": "Clear active",
        "apply_selected": "Apply to selected",
        "export": "Export…",
        "import_merge": "Import (merge)…",
        "import_replace": "Import (replace)…",
        "language": "Language:",
        "auto": "Auto",
        "english": "English",
        "russian": "Русский",
        "template_editor": "Template editor",
        "template_name": "Template name:",
        "from_selected": "Fill from selected feature",
        "only_checked": "Only checked fields are saved",
        "field": "Field",
        "type": "Type",
        "use": "Use",
        "value": "Value",
        "missing_name": "Template name cannot be empty.",
        "delete_q": "Delete template '{name}'?",
        "no_template": "Select a template or set an active one first.",
        "layer_not_editable": "Start editing the layer first.",
        "no_selection": "Select one or more features first.",
        "exported": "Exported templates to:\n{path}",
        "imported": "Templates imported successfully.",
        "import_failed": "Import failed",
        "export_failed": "Export failed",
        "invalid": "Invalid",
        "dup_title": "Duplicate template",
        "dup_prompt": "New template name:",
        "applied": "Template '{name}' applied to {n} feature(s).",
        "auto_applied": "Auto-applied template '{name}' to new feature.",
        "warn_no_fields": "Template has no matching fields in this layer.",
                "pk_skip": "Note: primary key fields (e.g., fid/id) are skipped to avoid UNIQUE constraint errors.",
"restart_needed": "Restart QGIS (or reload the plugin) to fully apply language changes."
    },
    "ru": {
        "dock_title": "Шаблоны атрибутов",
        "layer": "Слой:",
        "templates": "Шаблоны:",
        "active": "Активный шаблон:",
        "none": "(нет)",
        "new": "Создать",
        "edit": "Редактировать",
        "duplicate": "Дублировать",
        "delete": "Удалить",
        "set_active": "Сделать активным",
        "clear_active": "Снять активный",
        "apply_selected": "Применить к выделенным",
        "export": "Экспорт…",
        "import_merge": "Импорт (добавить)…",
        "import_replace": "Импорт (заменить)…",
        "language": "Язык:",
        "auto": "Авто",
        "english": "English",
        "russian": "Русский",
        "template_editor": "Редактор шаблона",
        "template_name": "Название шаблона:",
        "from_selected": "Заполнить из выделенного объекта",
        "only_checked": "Сохраняются только отмеченные поля",
        "field": "Поле",
        "type": "Тип",
        "use": "Исп.",
        "value": "Значение",
        "missing_name": "Название шаблона не может быть пустым.",
        "delete_q": "Удалить шаблон «{name}»?",
        "no_template": "Сначала выберите шаблон или сделайте его активным.",
        "layer_not_editable": "Сначала включите режим редактирования слоя.",
        "no_selection": "Сначала выделите один или несколько объектов.",
        "exported": "Шаблоны экспортированы в:\n{path}",
        "imported": "Шаблоны успешно импортированы.",
        "import_failed": "Ошибка импорта",
        "export_failed": "Ошибка экспорта",
        "invalid": "Некорректно",
        "dup_title": "Дублировать шаблон",
        "dup_prompt": "Новое имя шаблона:",
        "applied": "Шаблон «{name}» применён к объектам: {n}.",
        "auto_applied": "Авто-применение шаблона «{name}» к новому объекту.",
        "warn_no_fields": "В шаблоне нет полей, совпадающих с полями слоя.",
                "pk_skip": "Важно: поля первичного ключа (например fid/id) пропускаются, чтобы не было ошибки UNIQUE constraint.",
"restart_needed": "Перезапустите QGIS (или перезагрузите плагин), чтобы полностью применить смену языка."
    }
}

def _qgis_locale_prefix():
    s = QSettings().value("locale/userLocale", "", type=str)
    return (s.split("_")[0] if s else "").lower()

def _get_ui_lang():
    s = QSettings()
    s.beginGroup(SETTINGS_GROUP)
    lang = s.value(LANG_KEY, "auto", type=str)
    s.endGroup()
    if lang == "auto":
        return "ru" if _qgis_locale_prefix() == "ru" else "en"
    return "ru" if lang.lower().startswith("ru") else "en"

def tr(key: str, **kwargs) -> str:
    lang = _get_ui_lang()
    txt = STRINGS.get(lang, STRINGS["en"]).get(key, key)
    return txt.format(**kwargs) if kwargs else txt

def _safe_json_load(s, default):
    try:
        return json.loads(s) if s else default
    except Exception:
        return default

def _layer_key(layer: QgsVectorLayer) -> str:
    return f"{layer.providerType()}::{layer.source()}"


def _pk_indexes(layer: QgsVectorLayer):
    try:
        idxs = list(layer.dataProvider().pkAttributeIndexes() or [])
        return set(int(i) for i in idxs)
    except Exception:
        return set()

def _looks_like_pk_field(name: str) -> bool:
    n = (name or "").strip().lower()
    return n in ("fid", "id", "ogc_fid", "objectid", "object_id", "pk")


class TemplateStore:
    def __init__(self):
        self.settings = QSettings()

    def _read_all(self):
        self.settings.beginGroup(SETTINGS_GROUP)
        data = _safe_json_load(self.settings.value(TEMPLATES_KEY, ""), {})
        self.settings.endGroup()
        return data

    def _write_all(self, data):
        self.settings.beginGroup(SETTINGS_GROUP)
        self.settings.setValue(TEMPLATES_KEY, json.dumps(data, ensure_ascii=False))
        self.settings.endGroup()

    def list_templates(self, layer: QgsVectorLayer):
        return self._read_all().get(_layer_key(layer), {})

    def save_template(self, layer: QgsVectorLayer, name: str, mapping: dict):
        data = self._read_all()
        lk = _layer_key(layer)
        data.setdefault(lk, {})
        data[lk][name] = mapping
        self._write_all(data)

    def delete_template(self, layer: QgsVectorLayer, name: str):
        data = self._read_all()
        lk = _layer_key(layer)
        if lk in data and name in data[lk]:
            del data[lk][name]
            if not data[lk]:
                del data[lk]
            self._write_all(data)

    def export_layer_templates(self, layer: QgsVectorLayer, path: str):
        payload = {"layer_key": _layer_key(layer), "layer_name": layer.name(), "templates": self.list_templates(layer)}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    def import_layer_templates(self, layer: QgsVectorLayer, path: str, merge=True):
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        incoming = payload.get("templates", {})
        if not isinstance(incoming, dict):
            return
        current = self.list_templates(layer)
        current = (current | incoming) if merge else incoming
        data = self._read_all()
        data[_layer_key(layer)] = current
        self._write_all(data)


class ActiveTemplateStore:
    def __init__(self):
        self.settings = QSettings()

    def _read(self):
        self.settings.beginGroup(SETTINGS_GROUP)
        data = _safe_json_load(self.settings.value(ACTIVE_KEY, ""), {})
        self.settings.endGroup()
        return data

    def _write(self, data):
        self.settings.beginGroup(SETTINGS_GROUP)
        self.settings.setValue(ACTIVE_KEY, json.dumps(data, ensure_ascii=False))
        self.settings.endGroup()

    def set_active(self, layer: QgsVectorLayer, template_name: str | None):
        data = self._read()
        lk = _layer_key(layer)
        if template_name:
            data[lk] = template_name
        else:
            data.pop(lk, None)
        self._write(data)

    def get_active(self, layer: QgsVectorLayer):
        return self._read().get(_layer_key(layer))


class TemplateEditorDialog(QDialog):
    def __init__(self, parent, layer: QgsVectorLayer, name: str = "", mapping: dict | None = None):
        super().__init__(parent)
        self.layer = layer
        self._mapping = mapping or {}
        self._pk = _pk_indexes(layer)
        self.setWindowTitle(tr("template_editor"))

        self.name_combo = QComboBox()
        self.name_combo.setEditable(True)
        self.name_combo.setEditText(name)

        self.btn_from_selected = QPushButton(tr("from_selected"))
        self.only_checked = QLabel(tr("only_checked") + "\n" + tr("pk_skip"))
        self.only_checked.setWordWrap(True)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([tr("use"), tr("field"), tr("type"), tr("value")])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed)

        self._populate()

        form = QFormLayout()
        form.addRow(tr("template_name"), self.name_combo)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)

        top = QHBoxLayout()
        top.addWidget(self.btn_from_selected)
        top.addStretch(1)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addLayout(top)
        layout.addWidget(self.table)
        layout.addWidget(self.only_checked)
        layout.addWidget(btns)
        self.setLayout(layout)

        self.btn_from_selected.clicked.connect(self._fill_from_selected)

    def _field_type_name(self, f: QgsField) -> str:
        return f.typeName() or str(f.type())

    def _populate(self):
        fields = self.layer.fields()
        self.table.setRowCount(len(fields))
        for r, f in enumerate(fields):
            use_cb = QCheckBox()
            is_pk = (r in self._pk) or _looks_like_pk_field(f.name())
            use_cb.setChecked((f.name() in self._mapping) and (not is_pk))
            if is_pk:
                use_cb.setChecked(False)
                use_cb.setEnabled(False)
            self.table.setCellWidget(r, 0, use_cb)

            self.table.setItem(r, 1, QTableWidgetItem(f.name()))
            self.table.item(r, 1).setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)

            self.table.setItem(r, 2, QTableWidgetItem(self._field_type_name(f)))
            self.table.item(r, 2).setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)

            val = self._mapping.get(f.name(), "")
            self.table.setItem(r, 3, QTableWidgetItem("" if val is None else str(val)))

        self.table.resizeColumnsToContents()

    def _fill_from_selected(self):
        sel = self.layer.selectedFeatureIds()
        if not sel:
            QMessageBox.information(self, tr("invalid"), tr("no_selection"))
            return
        f = self.layer.getFeature(sel[0])
        if not f.isValid():
            return
        attrs = f.attributes()
        fields = self.layer.fields()
        for r, fld in enumerate(fields):
            if (r in self._pk) or _looks_like_pk_field(fld.name()):
                continue
            if (r in self._pk) or _looks_like_pk_field(fld.name()):
                continue
            use_cb = self.table.cellWidget(r, 0)
            if isinstance(use_cb, QCheckBox):
                use_cb.setChecked(True)
            val = attrs[r]
            self.table.item(r, 3).setText("" if val is None else str(val))

    def get_data(self):
        name = self.name_combo.currentText().strip()
        if not name:
            QMessageBox.warning(self, tr("invalid"), tr("missing_name"))
            return None
        mapping = {}
        fields = self.layer.fields()
        for r, fld in enumerate(fields):
            if (r in self._pk) or _looks_like_pk_field(fld.name()):
                continue
            use_cb = self.table.cellWidget(r, 0)
            use = use_cb.isChecked() if isinstance(use_cb, QCheckBox) else False
            if not use:
                continue
            raw = (self.table.item(r, 3).text() if self.table.item(r, 3) else "").strip()
            if raw == "":
                mapping[fld.name()] = None
                continue
            t = (fld.typeName() or "").lower()
            try:
                if any(x in t for x in ("int", "integer", "smallint", "bigint")):
                    mapping[fld.name()] = int(raw)
                elif any(x in t for x in ("real", "double", "float", "numeric", "decimal")):
                    mapping[fld.name()] = float(raw.replace(",", "."))
                elif "bool" in t:
                    mapping[fld.name()] = raw.lower() in ("1", "true", "yes", "y", "да")
                else:
                    mapping[fld.name()] = raw
            except Exception:
                mapping[fld.name()] = raw
        return name, mapping


class TemplateDock(QDockWidget):
    def __init__(self, plugin, parent=None):
        super().__init__(tr("dock_title"), parent)
        self.plugin = plugin

        w = QWidget()
        self.setWidget(w)

        self.lang_combo = QComboBox()
        self.lang_combo.addItem(tr("auto"), "auto")
        self.lang_combo.addItem(tr("english"), "en")
        self.lang_combo.addItem(tr("russian"), "ru")

        self.layer_combo = QComboBox()
        self.template_list = QListWidget()
        self.active_label = QLabel()

        self.btn_new = QPushButton(tr("new"))
        self.btn_edit = QPushButton(tr("edit"))
        self.btn_dup = QPushButton(tr("duplicate"))
        self.btn_del = QPushButton(tr("delete"))

        self.btn_set_active = QPushButton(tr("set_active"))
        self.btn_clear_active = QPushButton(tr("clear_active"))
        self.btn_apply_selected = QPushButton(tr("apply_selected"))

        self.btn_export = QPushButton(tr("export"))
        self.btn_import_merge = QPushButton(tr("import_merge"))
        self.btn_import_replace = QPushButton(tr("import_replace"))

        layout = QVBoxLayout()

        lang_row = QHBoxLayout()
        lang_row.addWidget(QLabel(tr("language")))
        lang_row.addWidget(self.lang_combo)
        layout.addLayout(lang_row)

        layout.addWidget(QLabel(tr("layer")))
        layout.addWidget(self.layer_combo)
        layout.addWidget(QLabel(tr("templates")))
        layout.addWidget(self.template_list)
        layout.addWidget(self.active_label)

        row1 = QHBoxLayout()
        for b in (self.btn_new, self.btn_edit, self.btn_dup, self.btn_del):
            row1.addWidget(b)
        layout.addLayout(row1)

        row2 = QHBoxLayout()
        for b in (self.btn_set_active, self.btn_clear_active, self.btn_apply_selected):
            row2.addWidget(b)
        layout.addLayout(row2)

        row3 = QHBoxLayout()
        for b in (self.btn_export, self.btn_import_merge, self.btn_import_replace):
            row3.addWidget(b)
        layout.addLayout(row3)

        w.setLayout(layout)

        self._load_lang_setting()

        self.lang_combo.currentIndexChanged.connect(self._on_lang_changed)
        self.layer_combo.currentIndexChanged.connect(self.refresh_templates)
        self.btn_new.clicked.connect(self.create_template)
        self.btn_edit.clicked.connect(self.edit_template)
        self.btn_dup.clicked.connect(self.duplicate_template)
        self.btn_del.clicked.connect(self.delete_template)
        self.btn_set_active.clicked.connect(self.set_active)
        self.btn_clear_active.clicked.connect(self.clear_active)
        self.btn_apply_selected.clicked.connect(self.apply_to_selected)
        self.btn_export.clicked.connect(self.export_templates)
        self.btn_import_merge.clicked.connect(lambda: self.import_templates(merge=True))
        self.btn_import_replace.clicked.connect(lambda: self.import_templates(merge=False))

        self.refresh_layers()

    def _load_lang_setting(self):
        s = QSettings()
        s.beginGroup(SETTINGS_GROUP)
        lang = s.value(LANG_KEY, "auto", type=str)
        s.endGroup()
        idx = self.lang_combo.findData(lang)
        if idx >= 0:
            self.lang_combo.setCurrentIndex(idx)

    def _on_lang_changed(self):
        lang = self.lang_combo.currentData()
        s = QSettings()
        s.beginGroup(SETTINGS_GROUP)
        s.setValue(LANG_KEY, lang)
        s.endGroup()
        QMessageBox.information(self, "Info", tr("restart_needed"))

    def current_layer(self):
        lyr = self.layer_combo.currentData()
        return lyr if isinstance(lyr, QgsVectorLayer) else None

    def refresh_layers(self):
        self.layer_combo.blockSignals(True)
        self.layer_combo.clear()
        for lyr in QgsProject.instance().mapLayers().values():
            if isinstance(lyr, QgsVectorLayer) and lyr.isValid():
                self.layer_combo.addItem(lyr.name(), lyr)
        self.layer_combo.blockSignals(False)
        self.refresh_templates()

    def refresh_templates(self):
        self.template_list.clear()
        layer = self.current_layer()
        if not layer:
            self.active_label.setText(f"{tr('active')} {tr('none')}")
            return
        templates = self.plugin.store.list_templates(layer)
        for name in sorted(templates.keys()):
            self.template_list.addItem(QListWidgetItem(name))
        active = self.plugin.active_store.get_active(layer)
        self.active_label.setText(f"{tr('active')} {active if active else tr('none')}")

    def _selected_template_name(self):
        items = self.template_list.selectedItems()
        return items[0].text() if items else None

    def create_template(self):
        layer = self.current_layer()
        if not layer:
            return
        dlg = TemplateEditorDialog(self, layer)
        if dlg.exec_():
            data = dlg.get_data()
            if not data:
                return
            name, mapping = data
            self.plugin.store.save_template(layer, name, mapping)
            self.refresh_templates()

    def edit_template(self):
        layer = self.current_layer()
        if not layer:
            return
        name = self._selected_template_name()
        if not name:
            return
        mapping = self.plugin.store.list_templates(layer).get(name, {})
        dlg = TemplateEditorDialog(self, layer, name=name, mapping=mapping)
        if dlg.exec_():
            data = dlg.get_data()
            if not data:
                return
            new_name, new_mapping = data
            if new_name != name:
                self.plugin.store.delete_template(layer, name)
            self.plugin.store.save_template(layer, new_name, new_mapping)
            if self.plugin.active_store.get_active(layer) == name and new_name != name:
                self.plugin.active_store.set_active(layer, new_name)
            self.refresh_templates()

    def duplicate_template(self):
        layer = self.current_layer()
        if not layer:
            return
        name = self._selected_template_name()
        if not name:
            return
        mapping = self.plugin.store.list_templates(layer).get(name, {})
        new_name, ok = QInputDialog.getText(self, tr("dup_title"), tr("dup_prompt"), text=f"{name} copy")
        if ok and new_name.strip():
            self.plugin.store.save_template(layer, new_name.strip(), mapping)
            self.refresh_templates()

    def delete_template(self):
        layer = self.current_layer()
        if not layer:
            return
        name = self._selected_template_name()
        if not name:
            return
        if QMessageBox.question(self, tr("delete"), tr("delete_q", name=name)) != QMessageBox.Yes:
            return
        self.plugin.store.delete_template(layer, name)
        if self.plugin.active_store.get_active(layer) == name:
            self.plugin.active_store.set_active(layer, None)
        self.refresh_templates()

    def set_active(self):
        layer = self.current_layer()
        if not layer:
            return
        name = self._selected_template_name()
        if not name:
            return
        self.plugin.active_store.set_active(layer, name)
        self.refresh_templates()
        self.plugin._info(tr("auto_applied", name=name))

    def clear_active(self):
        layer = self.current_layer()
        if not layer:
            return
        self.plugin.active_store.set_active(layer, None)
        self.refresh_templates()

    def apply_to_selected(self):
        layer = self.current_layer()
        if not layer:
            return
        name = self._selected_template_name() or self.plugin.active_store.get_active(layer)
        if not name:
            QMessageBox.information(self, "Info", tr("no_template"))
            return
        self.plugin.apply_template_to_selected(layer, name)

    def export_templates(self):
        layer = self.current_layer()
        if not layer:
            return
        path, _ = QFileDialog.getSaveFileName(self, tr("export"), "", "JSON (*.json)")
        if not path:
            return
        try:
            self.plugin.store.export_layer_templates(layer, path)
            QMessageBox.information(self, "OK", tr("exported", path=path))
        except Exception as e:
            QMessageBox.critical(self, tr("export_failed"), str(e))

    def import_templates(self, merge=True):
        layer = self.current_layer()
        if not layer:
            return
        path, _ = QFileDialog.getOpenFileName(self, tr("import_merge") if merge else tr("import_replace"), "", "JSON (*.json)")
        if not path:
            return
        try:
            self.plugin.store.import_layer_templates(layer, path, merge=merge)
            self.refresh_templates()
            QMessageBox.information(self, "OK", tr("imported"))
        except Exception as e:
            QMessageBox.critical(self, tr("import_failed"), str(e))


class AttributeTemplateFillerPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.action = None
        self.dock = None
        self.store = TemplateStore()
        self.active_store = ActiveTemplateStore()
        self._connected = set()

    def initGui(self):
        self.action = QAction(QIcon(self._icon_path()), tr("dock_title"), self.iface.mainWindow())
        self.action.setCheckable(True)
        self.action.toggled.connect(self._toggle)
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu("&Attribute Template Filler", self.action)

        QgsProject.instance().layersAdded.connect(self._on_layers_added)
        QgsProject.instance().layersWillBeRemoved.connect(self._on_layers_removed)
        self._connect_existing()

    def unload(self):
        try:
            QgsProject.instance().layersAdded.disconnect(self._on_layers_added)
            QgsProject.instance().layersWillBeRemoved.disconnect(self._on_layers_removed)
        except Exception:
            pass
        self._disconnect_all()
        if self.dock:
            self.iface.removeDockWidget(self.dock)
            self.dock = None
        if self.action:
            self.iface.removeToolBarIcon(self.action)
            self.iface.removePluginMenu("&Attribute Template Filler", self.action)
            self.action = None

    def _icon_path(self):
        import os
        return os.path.join(os.path.dirname(__file__), "icon.png")

    def _toggle(self, checked):
        if checked:
            if not self.dock:
                self.dock = TemplateDock(self, self.iface.mainWindow())
                self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dock)
            self.dock.show()
            self.dock.raise_()
        else:
            if self.dock:
                self.dock.hide()

    def _info(self, msg):
        try:
            self.iface.messageBar().pushMessage("AT", msg, level=Qgis.Info, duration=3)
        except Exception:
            pass

    def _warn(self, msg):
        try:
            self.iface.messageBar().pushMessage("AT", msg, level=Qgis.Warning, duration=5)
        except Exception:
            pass

    def _connect_existing(self):
        for lyr in QgsProject.instance().mapLayers().values():
            self._connect_layer(lyr)

    def _on_layers_added(self, layers):
        for lyr in layers:
            self._connect_layer(lyr)
        if self.dock:
            self.dock.refresh_layers()

    def _on_layers_removed(self, layer_ids):
        self._connected = {lid for lid in self._connected if lid not in set(layer_ids)}
        if self.dock:
            self.dock.refresh_layers()

    def _connect_layer(self, layer):
        if not isinstance(layer, QgsVectorLayer) or not layer.isValid():
            return
        if layer.id() in self._connected:
            return
        layer.featureAdded.connect(lambda fid, lyr=layer: self._on_feature_added(lyr, fid))
        self._connected.add(layer.id())

    def _disconnect_all(self):
        for lyr in QgsProject.instance().mapLayers().values():
            if isinstance(lyr, QgsVectorLayer):
                try:
                    lyr.featureAdded.disconnect()
                except Exception:
                    pass
        self._connected.clear()

    def _on_feature_added(self, layer, fid):
        name = self.active_store.get_active(layer)
        if not name:
            return
        ok = self.apply_template_to_feature(layer, fid, name)
        if ok:
            self._info(tr("auto_applied", name=name))

    def apply_template_to_feature(self, layer, fid, template_name):
        mapping = self.store.list_templates(layer).get(template_name)
        if not isinstance(mapping, dict) or not layer.isEditable():
            return False
        fields = layer.fields()
        pk = _pk_indexes(layer)
        applied_any = False
        for field_name, value in mapping.items():
            idx = fields.indexOf(field_name)
            if idx < 0:
                continue
            if idx in pk or _looks_like_pk_field(field_name):
                continue
            v = QVariant() if value is None else value
            if layer.changeAttributeValue(fid, idx, v):
                applied_any = True
        if not applied_any:
            self._warn(tr("warn_no_fields"))
            return False
        layer.triggerRepaint()
        return True

    def apply_template_to_selected(self, layer, template_name):
        if not layer.isEditable():
            QMessageBox.information(self.iface.mainWindow(), "Info", tr("layer_not_editable"))
            return
        ids = layer.selectedFeatureIds()
        if not ids:
            QMessageBox.information(self.iface.mainWindow(), "Info", tr("no_selection"))
            return
        mapping = self.store.list_templates(layer).get(template_name)
        if not isinstance(mapping, dict):
            return
        fields = layer.fields()
        pk = _pk_indexes(layer)
        n = 0
        for fid in ids:
            applied_any = False
            for field_name, value in mapping.items():
                idx = fields.indexOf(field_name)
                if idx < 0:
                    continue
                v = QVariant() if value is None else value
                if layer.changeAttributeValue(fid, idx, v):
                    applied_any = True
            if applied_any:
                n += 1
        layer.triggerRepaint()
        self._info(tr("applied", name=template_name, n=n))
