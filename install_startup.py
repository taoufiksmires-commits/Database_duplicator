"""
install_startup.py
------------------
Enregistre MySQLSync dans le registre Windows pour démarrage automatique.
Lancer avec : python install_startup.py
"""
import sys
import os

try:
    import winreg
except ImportError:
    print("Ce script doit être exécuté sous Windows.")
    sys.exit(1)

APP_NAME = "MySQLSync"
REG_KEY  = r"Software\Microsoft\Windows\CurrentVersion\Run"


def install():
    exe_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "dist", "MySQLSync.exe")
    )
    if not os.path.exists(exe_path):
        # Mode développement : lancer via pythonw (pas de console)
        pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
        main_py = os.path.abspath(os.path.join(os.path.dirname(__file__), "main.py"))
        cmd = f'"{pythonw}" "{main_py}"'
    else:
        cmd = f'"{exe_path}"'

    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_SET_VALUE)
    winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
    winreg.CloseKey(key)
    print(f"✔ MySQLSync enregistré au démarrage Windows.")
    print(f"  Commande : {cmd}")


def uninstall():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_SET_VALUE)
        winreg.DeleteValue(key, APP_NAME)
        winreg.CloseKey(key)
        print("✔ MySQLSync supprimé du démarrage Windows.")
    except FileNotFoundError:
        print("MySQLSync n'était pas dans le démarrage Windows.")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--uninstall":
        uninstall()
    else:
        install()
