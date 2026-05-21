"""Kivy screens for Helmet Locker."""
import threading

from kivy.clock import mainthread
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen

import config
from database import db
from services import register_user, unlock


class HomeScreen(Screen):
    pass


class RegisterScreen(Screen):
    _busy = False

    def start_registration(self):
        if self._busy:
            return
        name = self.ids.name_input.text.strip()
        if not name:
            self._set_status("Please enter a name")
            return
        self._busy = True
        self._set_status("Starting registration...")
        threading.Thread(target=self._run_register, args=(name,), daemon=True).start()

    def _run_register(self, name: str):
        def on_status(msg: str):
            mainthread(self._set_status)(msg)

        result = register_user.register(name, on_status=on_status)
        mainthread(self._on_done)(result)

    @mainthread
    def _on_done(self, result):
        self._busy = False
        color = (0.3, 0.85, 0.4, 1) if result.success else (0.9, 0.3, 0.3, 1)
        self._set_status(result.message, color)
        if result.success:
            self.ids.name_input.text = ""

    @mainthread
    def _set_status(self, text: str, color=(0.9, 0.9, 0.9, 1)):
        lbl = self.ids.status_label
        lbl.text = text
        lbl.color = color

    def go_home(self):
        self.manager.current = "home"


class UnlockScreen(Screen):
    _busy = False
    _rfid_thread = None
    _rfid_stop = False

    def on_enter(self, *args):
        self._rfid_stop = False
        self._rfid_thread = threading.Thread(target=self._rfid_loop, daemon=True)
        self._rfid_thread.start()

    def on_leave(self, *args):
        self._rfid_stop = True

    def _rfid_loop(self):
        while not self._rfid_stop:
            if self._busy:
                continue
            result = unlock.poll_unlock_once()
            if result and result.success:
                mainthread(self._show_result)(result)
                break
            import time

            time.sleep(0.3)

    def unlock_fingerprint(self):
        self._run_unlock(unlock.try_unlock_from_fingerprint)

    def unlock_face(self):
        self._run_unlock(unlock.try_unlock_from_face)

    def _run_unlock(self, func):
        if self._busy:
            return
        self._busy = True
        self._set_status("Verifying...")
        threading.Thread(target=self._run, args=(func,), daemon=True).start()

    def _run(self, func):
        result = func()
        mainthread(self._show_result)(result)

    @mainthread
    def _show_result(self, result):
        self._busy = False
        if result.success:
            self._set_status(result.message, (0.3, 0.9, 0.4, 1))
        else:
            self._set_status(result.message, (0.95, 0.35, 0.35, 1))

    @mainthread
    def _set_status(self, text: str, color=(0.9, 0.9, 0.9, 1)):
        lbl = self.ids.unlock_status
        lbl.text = text
        lbl.color = color

    def go_home(self):
        self.manager.current = "home"


class AdminScreen(Screen):
    _authenticated = False

    def check_pin(self):
        if self.ids.pin_input.text == config.ADMIN_PIN:
            self._authenticated = True
            self._set_status("Admin unlocked — select user to delete")
            self.refresh_users()
        else:
            self._authenticated = False
            self._set_status("Wrong PIN", (0.9, 0.3, 0.3, 1))

    def refresh_users(self):
        if not self._authenticated:
            self._set_status("Enter PIN first")
            return
        grid = self.ids.user_list
        grid.clear_widgets()
        users = db.list_users()
        if not users:
            grid.add_widget(Label(text="No users registered", size_hint_y=None, height=40))
            return
        for u in users:
            row = BoxLayout(size_hint_y=None, height=48, spacing=8)
            info = (
                f"{u['name']} | FP:{u.get('fingerprint_id')} "
                f"| RFID:{u.get('rfid_uid', '-')}"
            )
            row.add_widget(Label(text=info, font_size=14))
            btn = Button(
                text="Delete",
                size_hint_x=None,
                width=90,
                background_color=(0.75, 0.2, 0.2, 1),
                background_normal="",
            )
            uid = u["id"]
            btn.bind(on_release=lambda _, i=uid: self._delete_user(i))
            row.add_widget(btn)
            grid.add_widget(row)

    def _delete_user(self, user_id: int):
        user = db.get_user_by_id(user_id)
        if user and user.get("fingerprint_id"):
            try:
                from hardware import fingerprint as fp

                fp.delete_template(user["fingerprint_id"])
            except Exception:
                pass
        if db.delete_user(user_id):
            self._set_status(f"Deleted user id {user_id}")
            self.refresh_users()
        else:
            self._set_status("Delete failed", (0.9, 0.3, 0.3, 1))

    @mainthread
    def _set_status(self, text: str, color=(0.9, 0.9, 0.9, 1)):
        self.ids.admin_status.text = text
        self.ids.admin_status.color = color

    def go_home(self):
        self._authenticated = False
        self.ids.pin_input.text = ""
        self.manager.current = "home"
