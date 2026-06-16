import sys
import threading
import tkinter as tk
from tkinter import messagebox
import pystray
from PIL import Image, ImageDraw
from core.local_db import LocalDB, VERSION
from core.config_manager import ConfigManager
from core.sync_engine import SyncEngine
from ui.supervision_window import SupervisionWindow
from ui.setup_dialog import SetupDialog


def create_tray_icon(app):
    img = Image.new("RGB", (64, 64), color=(30, 30, 40))
    draw = ImageDraw.Draw(img)
    draw.ellipse([8, 8, 56, 56], fill=(0, 180, 120))
    draw.polygon([(22, 32), (44, 20), (44, 44)], fill=(255, 255, 255))

    def on_show(icon, item):
        app.window.show_window()

    def on_toggle(icon, item):
        if app.engine.running:
            app.engine.stop()
        else:
            app.engine.start()

    def on_quit(icon, item):
        app.engine.stop()
        icon.stop()
        app.window.root.after(0, app.window.root.destroy)

    menu = pystray.Menu(
        pystray.MenuItem("📊 Ouvrir supervision", on_show, default=True),
        pystray.MenuItem("⏸/▶ Pause / Reprendre", on_toggle),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("❌ Quitter", on_quit),
    )
    return pystray.Icon("MySQLSync", img, f"MySQLSync v{VERSION}", menu)


class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()

        self.local_db = LocalDB()

        # Premier démarrage : demander le mot de passe local
        if not self.local_db.is_configured():
            dlg = SetupDialog(self.root, self.local_db)
            self.root.wait_window(dlg.win)
            if not self.local_db.is_configured():
                sys.exit(0)

        # Connexion à la base locale
        try:
            self.local_db.connect()
        except Exception as e:
            messagebox.showerror("Erreur de connexion",
                f"Impossible de se connecter à la base locale :\n{e}\n\n"
                "Supprimez local_conn.json pour reconfigurer.")
            sys.exit(1)

        self.config = ConfigManager(self.local_db)
        self.engine = SyncEngine(self.config)
        self.window = SupervisionWindow(self.config, self.engine, self.root)

    def run(self):
        self.engine.start()
        icon = create_tray_icon(self)
        tray_thread = threading.Thread(target=icon.run, daemon=True)
        tray_thread.start()
        self.root.mainloop()


if __name__ == "__main__":
    app = App()
    app.run()
