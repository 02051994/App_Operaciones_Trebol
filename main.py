import os
from datetime import datetime

from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.widget import Widget
from kivy.graphics import Color, Line
from kivy.clock import Clock

from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.list import OneLineAvatarIconListItem, IconLeftWidget
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.snackbar import Snackbar
from kivymd.uix.pickers import MDDatePicker, MDTimePicker
from kivymd.uix.textfield import MDTextField
from kivymd.uix.selectioncontrol import MDSwitch
from kivymd.uix.button import MDFlatButton

from db import LocalDB
from sync import SyncService
from utils import load_json, make_uuid, now_utc_iso, apply_calculo, ensure_dir


class SignaturePad(Widget):
    image_path = StringProperty("")

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return False
        with self.canvas:
            Color(0, 0, 0, 1)
            touch.ud["line"] = Line(points=(touch.x, touch.y), width=1.2)
        return True

    def on_touch_move(self, touch):
        if "line" in touch.ud and self.collide_point(*touch.pos):
            touch.ud["line"].points += [touch.x, touch.y]
            return True
        return False

    def clear_pad(self):
        self.canvas.clear()

    def save_signature(self, folder: str):
        ensure_dir(folder)
        file_name = f"firma_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.png"
        p = os.path.join(folder, file_name)
        self.export_to_png(p)
        self.image_path = p
        return p


class LoginScreen(MDScreen):
    pass


class FormsScreen(MDScreen):
    pass


class DynamicFormScreen(MDScreen):
    pass


class RecordsScreen(MDScreen):
    pass


class SyncScreen(MDScreen):
    pass


class OperacionesApp(MDApp):
    def build(self):
        self.title = "Operaciones Trebol"
        self.theme_cls.primary_palette = "BlueGray"
        self.theme_cls.theme_style = "Light"

        self.config_data = load_json("config.json", default={})
        ensure_dir(self.config_data.get("data_dir", "data"))
        ensure_dir(self.config_data.get("signatures_dir", "signatures"))

        self.db = LocalDB(self.config_data.get("sqlite_path", "data/app.db"))
        self.sync_service = SyncService(self.db, self.config_data)

        self.current_user = None
        self.current_form = None
        self.field_widgets = {}
        self.select_menus = []

        return Builder.load_file("kv/main.kv")

    def on_start(self):
        if self.config_data.get("seed_demo_data", True):
            self._seed_if_empty()
        self.refresh_forms()
        self.refresh_records_view()

    def _seed_if_empty(self):
        if self.db.get_forms():
            return
        users = [{"id": "1", "usuario": "admin", "password": "1234", "activo": True, "updated_at": now_utc_iso()}]
        forms = [{"form_id": "declaracion_jurada", "nombre": "Declaración Jurada", "sheet_destino": "Declaracion Jurada", "activo": True}]
        fields = [
            {"form_id": "declaracion_jurada", "campo": "FECHA", "tipo": "FECHA", "calculo": "hoy()", "orden": 1, "obligatorio": True},
            {"form_id": "declaracion_jurada", "campo": "DNI", "tipo": "TEXTO", "orden": 2, "obligatorio": True},
            {"form_id": "declaracion_jurada", "campo": "NOMBRES Y APELLIDOS", "tipo": "TEXTO", "orden": 3, "obligatorio": True},
            {"form_id": "declaracion_jurada", "campo": "EMPRESA", "tipo": "TEXTO", "orden": 4, "obligatorio": True},
            {"form_id": "declaracion_jurada", "campo": "AREA POR VISITAR", "tipo": "LISTA", "opciones": ["sanidad", "riego", "administracion", "sig", "calidad", "sst", "rrhh", "produccion", "cosecha"], "orden": 5, "obligatorio": True},
            {"form_id": "declaracion_jurada", "campo": "MOTIVO DE VISITA", "tipo": "TEXTO", "orden": 6, "obligatorio": True},
            {"form_id": "declaracion_jurada", "campo": "FIRMA", "tipo": "FIRMA", "orden": 7, "obligatorio": True},
        ]
        self.db.upsert_users(users)
        self.db.replace_forms_catalog(forms, fields)

    def snack(self, message):
        """Muestra un snackbar compatible con distintas APIs de KivyMD."""
        try:
            Snackbar(text=message, duration=2).open()
            return
        except TypeError:
            pass

        # Compatibilidad con variantes donde ``text`` ya no es una propiedad.
        sb = Snackbar(duration=2)
        if hasattr(sb, "text"):
            sb.text = message
        elif hasattr(sb, "add_widget"):
            try:
                from kivymd.uix.label import MDLabel
                sb.add_widget(MDLabel(text=message))
            except Exception:
                return
        sb.open()

    def sync_catalogs(self, notify: bool = True):
        try:
            result = self.sync_service.pull_catalogs()
            self.refresh_forms()
            if notify:
                self.snack(
                    f"Datos actualizados: usuarios={result['users']}, formularios={result['forms']}"
                )
            return result
        except Exception as e:
            if notify:
                self.snack(f"No se pudo actualizar datos: {e}")
            return None

    def do_login(self):
        user = self.root.get_screen("login").ids.username.text.strip()
        pw = self.root.get_screen("login").ids.password.text.strip()

        # Antes de validar, intenta traer usuarios actualizados desde la hoja.
        self.sync_catalogs(notify=False)

        if self.db.validate_login(user, pw):
            self.current_user = user
            self.root.current = "forms"
            self.refresh_forms()
            return
        self.snack("Usuario o contraseña inválidos")

    def logout(self):
        self.current_user = None
        self.root.current = "login"

    def refresh_forms(self):
        screen = self.root.get_screen("forms")
        cont = screen.ids.forms_list
        cont.clear_widgets()
        for f in self.db.get_forms():
            item = OneLineAvatarIconListItem(text=f["nombre"], on_release=lambda x, form=f: self.open_form(form))
            item.add_widget(IconLeftWidget(icon="file-document-outline"))
            cont.add_widget(item)

    def open_form(self, form):
        self.current_form = form
        self.field_widgets = {}
        for m in self.select_menus:
            m.dismiss()
        self.select_menus = []

        screen = self.root.get_screen("dynamic_form")
        screen.ids.form_title.text = form["nombre"]
        box = screen.ids.fields_box
        box.clear_widgets()

        fields = self.db.get_form_fields(form["form_id"])
        for fld in fields:
            ftype = (fld["tipo"] or "").upper()
            label = fld["campo"]
            required = bool(fld["obligatorio"])
            hint = f"{label}{' *' if required else ''}"

            if ftype in {"TEXTO", "AUTOCOMPLETADO", "NUMERO ENTERO", "DECIMAL", "FECHA", "HORA"}:
                tf = MDTextField(hint_text=hint, mode="rectangle", size_hint_y=None, height=dp(58))
                if ftype == "NUMERO ENTERO":
                    tf.input_filter = "int"
                elif ftype == "DECIMAL":
                    tf.input_filter = "float"
                default = apply_calculo(fld.get("calculo"), ftype)
                if default:
                    tf.text = str(default)
                if ftype == "FECHA":
                    tf.readonly = True
                    tf.on_focus = lambda inst, val, t=tf: self._open_date_picker(t) if val else None
                elif ftype == "HORA":
                    tf.readonly = True
                    tf.on_focus = lambda inst, val, t=tf: self._open_time_picker(t) if val else None
                if not fld.get("editable", 1):
                    tf.readonly = True
                self.field_widgets[label] = tf
                box.add_widget(tf)

            elif ftype == "LISTA":
                tf = MDTextField(hint_text=hint, mode="rectangle", size_hint_y=None, height=dp(58), readonly=True)
                options = fld.get("opciones", [])
                menu_items = [{"text": o, "on_release": lambda x=o, t=tf: self._set_menu_value(t, x)} for o in options]
                menu = MDDropdownMenu(caller=tf, items=menu_items, width_mult=4)
                self.select_menus.append(menu)
                tf.on_focus = lambda inst, val, m=menu: m.open() if val else None
                default = apply_calculo(fld.get("calculo"), ftype)
                if default:
                    tf.text = str(default)
                self.field_widgets[label] = tf
                box.add_widget(tf)

            elif ftype in {"BOOLEANO", "SI-NO"}:
                row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(52), spacing=dp(12))
                text = MDTextField(text=hint, readonly=True, mode="fill", size_hint_x=0.8)
                sw = MDSwitch(size_hint_x=0.2)
                default = apply_calculo(fld.get("calculo"), ftype)
                sw.active = str(default).upper() in {"SI", "TRUE", "1"}
                row.add_widget(text)
                row.add_widget(sw)
                self.field_widgets[label] = sw
                box.add_widget(row)

            elif ftype == "FIRMA":
                container = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(230), spacing=dp(8))
                title = MDTextField(text=hint, readonly=True, mode="fill")
                pad = SignaturePad(size_hint_y=None, height=dp(160))
                actions = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(42), spacing=dp(8))
                btn_clear = MDFlatButton(text="Limpiar", on_release=lambda x, p=pad: p.clear_pad())
                btn_save = MDFlatButton(text="Guardar firma", on_release=lambda x, p=pad: self._save_signature_field(p))
                actions.add_widget(btn_clear)
                actions.add_widget(btn_save)
                container.add_widget(title)
                container.add_widget(pad)
                container.add_widget(actions)
                self.field_widgets[label] = pad
                box.add_widget(container)

            else:
                tf = MDTextField(hint_text=hint, mode="rectangle", size_hint_y=None, height=dp(58))
                self.field_widgets[label] = tf
                box.add_widget(tf)

        self.root.current = "dynamic_form"

    def _open_date_picker(self, tf):
        picker = MDDatePicker()
        picker.bind(on_save=lambda inst, val, dr: self._set_date(tf, val))
        picker.open()

    def _set_date(self, tf, value):
        tf.text = value.strftime("%Y-%m-%d")

    def _open_time_picker(self, tf):
        picker = MDTimePicker()
        picker.bind(time=lambda inst, val: self._set_time(tf, val))
        picker.open()

    def _set_time(self, tf, value):
        tf.text = value.strftime("%H:%M")

    def _set_menu_value(self, tf, value):
        tf.text = value
        for m in self.select_menus:
            if m.caller == tf:
                m.dismiss()
                break

    def _save_signature_field(self, pad):
        folder = self.config_data.get("signatures_dir", "signatures")
        saved = pad.save_signature(folder)
        self.snack(f"Firma guardada: {os.path.basename(saved)}")

    def save_current_form(self):
        if not self.current_form or not self.current_user:
            self.snack("Debe iniciar sesión")
            return

        fields = self.db.get_form_fields(self.current_form["form_id"])
        payload = {}
        errors = []

        for fld in fields:
            label = fld["campo"]
            ftype = (fld["tipo"] or "").upper()
            required = bool(fld["obligatorio"])
            w = self.field_widgets.get(label)

            value = None
            if ftype in {"BOOLEANO", "SI-NO"}:
                value = "SI" if getattr(w, "active", False) else "NO"
            elif ftype == "FIRMA":
                value = getattr(w, "image_path", "")
            else:
                value = getattr(w, "text", "").strip()

            if required and not value:
                errors.append(f"{label} es obligatorio")
            payload[label] = value

        if errors:
            self.snack(errors[0])
            return

        local_id = make_uuid()
        self.db.insert_record(
            local_id=local_id,
            form_id=self.current_form["form_id"],
            usuario=self.current_user,
            payload=payload,
            created_at=now_utc_iso(),
        )
        self.snack("Registro guardado en local")
        self.refresh_records_view()
        self.root.current = "forms"

    def refresh_records_view(self):
        dashboard = self.db.get_records_dashboard()
        screen = self.root.get_screen("records")
        screen.ids.lbl_pending.text = f"Pendientes: {dashboard['pending']}"
        screen.ids.lbl_synced.text = f"Sincronizados: {dashboard['synced']}"
        screen.ids.lbl_ready_delete.text = f"Listos para borrado: {dashboard['ready_delete']}"

        box = screen.ids.records_list
        box.clear_widgets()
        for r in dashboard["rows"]:
            status = r["status"]
            title = f"{r['form_id']} · {status}"
            subtitle = f"{r['local_id'][:8]}... | {r['created_at']}"
            item = OneLineAvatarIconListItem(text=f"{title} | {subtitle}")
            item.add_widget(IconLeftWidget(icon="sync" if status == "pending" else "check-circle"))
            box.add_widget(item)

    def run_full_sync(self):
        self.root.get_screen("sync").ids.sync_log.text = "Iniciando sincronización..."

        def _job(_dt):
            log = []
            try:
                r1 = self.sync_service.pull_catalogs()
                log.append(f"Catálogos: users={r1['users']}, forms={r1['forms']}, fields={r1['fields']}")
            except Exception as e:
                log.append(f"Catálogos: ERROR {e}")

            try:
                r2 = self.sync_service.push_pending()
                log.append(f"Push: enviados={r2['sent']}, ok={r2['ok']}, error={r2['errors']}")
            except Exception as e:
                log.append(f"Push: ERROR {e}")

            r3 = self.sync_service.purge_synced()
            log.append(f"Purge: eliminados={r3['purged']}")

            self.root.get_screen("sync").ids.sync_log.text = "\n".join(log)
            self.refresh_forms()
            self.refresh_records_view()

        Clock.schedule_once(_job, 0.1)


if __name__ == "__main__":
    OperacionesApp().run()
