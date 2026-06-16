import sys
import threading
import pystray
from PIL import Image, ImageDraw
from ui.supervision_window import SupervisionWindow
from core.sync_engine import SyncEngine
from core.config_manager import ConfigManager


def create_tray_icon(app):
    """Crée l'icône systray avec menu contextuel."""
    img = Image.new("RGB", (64, 64), color=(30, 30, 40))
    draw = ImageDraw.Draw(img)
    draw.ellipse([8, 8, 56, 56], fill=(0, 180, 120))
    draw.polygon([(22, 32), (44, 20), (44, 44)], fill=(255, 255, 255))

    def on_show(icon, item):
        app.window.show_window()

    def on_toggle_sync(icon, item):
        if app.engine.running:
            app.engine.stop()
            icon.menu = build_menu(icon, app, running=False)
        else:
            app.engine.start()
            icon.menu = build_menu(icon, app, running=True)

    def on_quit(icon, item):
        app.engine.stop()
        icon.stop()
        app.window.root.after(0, app.window.root.destroy)

    def build_menu(icon, app, running=True):
        label = "⏸ Pause synchronisation" if running else "▶ Reprendre synchronisation"
        return pystray.Menu(
            pystray.MenuItem("📊 Ouvrir supervision", on_show, default=True),
            pystray.MenuItem(label, on_toggle_sync),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("❌ Quitter", on_quit),
        )

    icon = pystray.Icon("MySQLSync", img, "MySQLSync", build_menu(None, app))
    return icon


class App:
    def __init__(self):
        self.config = ConfigManager()
        self.engine = SyncEngine(self.config)
        self.window = SupervisionWindow(self.config, self.engine)

    def run(self):
        self.engine.start()
        icon = create_tray_icon(self)
        tray_thread = threading.Thread(target=icon.run, daemon=True)
        tray_thread.start()
        self.window.root.mainloop()


if __name__ == "__main__":
    app = App()
    app.run()
