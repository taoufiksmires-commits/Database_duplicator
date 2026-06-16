import tkinter as tk
from tkinter import messagebox
import mysql.connector

BG     = "#0f1117"
PANEL  = "#1a1d27"
BORDER = "#2a2d3a"
ACCENT = "#00c47a"
TEXT   = "#e8eaf0"
MUTED  = "#6b7080"
FONT_UI = ("Segoe UI", 10)
FONT_MONO = ("Consolas", 10)
FONT_BIG  = ("Segoe UI Semibold", 13)


class SetupDialog:
    def __init__(self, parent, local_db):
        self.local_db = local_db

        self.win = tk.Toplevel(parent)
        self.win.title("MySQLSync — Configuration initiale")
        self.win.geometry("420x280")
        self.win.resizable(False, False)
        self.win.configure(bg=BG)
        self.win.grab_set()
        self.win.protocol("WM_DELETE_WINDOW", self.win.destroy)

        tk.Label(self.win, text="MySQLSync", font=("Segoe UI Semibold", 16),
                 fg=ACCENT, bg=BG).pack(pady=(24, 4))
        tk.Label(self.win, text="Premier démarrage — connexion MySQL locale",
                 font=FONT_UI, fg=MUTED, bg=BG).pack()

        tk.Frame(self.win, bg=BORDER, height=1).pack(fill="x", pady=16)

        info = tk.Frame(self.win, bg=BG)
        info.pack(fill="x", padx=32)

        tk.Label(info, text="Hôte : 127.0.0.1   Utilisateur : root",
                 font=FONT_UI, fg=MUTED, bg=BG).pack(anchor="w", pady=(0, 12))

        row = tk.Frame(info, bg=BG)
        row.pack(fill="x")
        tk.Label(row, text="Mot de passe MySQL :", font=FONT_UI, fg=TEXT,
                 bg=BG, width=22, anchor="w").pack(side="left")
        self._pwd_var = tk.StringVar()
        pwd_entry = tk.Entry(row, textvariable=self._pwd_var, font=FONT_MONO,
                             bg=PANEL, fg=TEXT, insertbackground=TEXT,
                             relief="flat", show="*",
                             highlightthickness=1, highlightcolor=ACCENT,
                             highlightbackground=BORDER)
        pwd_entry.pack(side="left", fill="x", expand=True, ipady=6)
        pwd_entry.focus_set()
        pwd_entry.bind("<Return>", lambda e: self._connect())

        btn = tk.Button(self.win, text="Se connecter", command=self._connect,
                        bg=ACCENT, fg="#000", font=("Segoe UI Semibold", 10),
                        relief="flat", padx=20, pady=8, cursor="hand2", bd=0)
        btn.pack(pady=20)

    def _connect(self):
        pwd = self._pwd_var.get()
        try:
            tmp = mysql.connector.connect(
                host="127.0.0.1", port=3306,
                user="root", password=pwd, connection_timeout=5
            )
            tmp.close()
            self.local_db.save_local_cfg(pwd)
            self.win.destroy()
        except Exception as e:
            messagebox.showerror("Connexion échouée",
                f"Impossible de se connecter :\n{e}", parent=self.win)
