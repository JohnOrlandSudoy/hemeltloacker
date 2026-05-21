#!/usr/bin/env python3
"""
Helmet Locker — main entry point.
Run on Raspberry Pi with hardware connected.
"""
import logging
import os
import sys

# Ensure project root is on path
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import config
from database import db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("helmetlocker")


def main():
    db.init_db()
    logger.info(
        "Starting Helmet Locker (simulate=%s, policy=%s)",
        config.SIMULATE_HARDWARE,
        config.UNLOCK_POLICY,
    )

    os.environ.setdefault("KIVY_GL_BACKEND", "gl")

    from kivy.app import App
    from kivy.core.window import Window
    from kivy.lang import Builder
    from kivy.uix.screenmanager import ScreenManager

    from ui.screens import AdminScreen, HomeScreen, RegisterScreen, UnlockScreen

    kv_path = os.path.join(ROOT, "ui", "app.kv")
    Builder.load_file(kv_path)

    class HelmetLockerApp(App):
        title = config.APP_TITLE

        def build(self):
            sm = ScreenManager()
            sm.add_widget(HomeScreen(name="home"))
            sm.add_widget(RegisterScreen(name="register"))
            sm.add_widget(UnlockScreen(name="unlock"))
            sm.add_widget(AdminScreen(name="admin"))
            if config.FULLSCREEN:
                Window.fullscreen = "auto"
            return sm

        def on_stop(self):
            try:
                from hardware import solenoid

                solenoid.cleanup()
            except Exception:
                pass

    HelmetLockerApp().run()


if __name__ == "__main__":
    main()
