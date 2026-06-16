import tkinter as tk
from tkinter import ttk, messagebox
import threading


# ── Palette ──────────────────────────────────────────────────────────────────
BG       = "#0f1117"
PANEL    = "#1a1d27"
BORDER   = "#2a2d3a"
ACCENT   = "#00c47a"
ACCENT2  = "#0099ff"
WARN     = "#ffaa00"
ERROR    = "#ff4455"
TEXT     = "#e8eaf0"
MUTED    = "#6b7080"
FONT_UI  = ("Segoe UI", 10)
FONT_MONO= ("Consolas", 9)
FONT_BIG = ("Segoe UI Semibold", 12)
FONT_H   = ("Segoe UI Semibold", 10)


class SupervisionWindow:
    def __init__(self, config, engine):
        self.config = config
        self.engine = engine

        self.root = tk.Tk()
        self.root.title("MySQLSync — Supervision")
        self.root.geometry("860x620")
        self.root.minsize(700, 500)
        self.root.configure(bg=BG)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # Icône fenêtre
        try:
            self.root.iconbitmap(default="assets/icon.ico")
        except Exception:
            pass

        engine.add_log_callback(self._on_log)
        self._build_ui()
        self._start_refresh()

    # ── Fermeture → minimiser dans le systray ─────────────────────────────────
    def _on_close(self):
        self.root.withdraw()

    def show_window(self):
        self.root.after(0, self._do_show)

    def _do_show(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    # ── Construction UI ───────────────────────────────────────────────────────
    def _build_ui(self):
        # Header
        header = tk.Frame(self.root, bg=PANEL, height=54)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(header, text="● MySQLSync", font=("Segoe UI Semibold", 14),
                 fg=ACCENT, bg=PANEL).pack(side="left", padx=18, pady=14)

        self._status_lbl = tk.Label(header, text="◉ En cours", font=FONT_UI,
                                     fg=ACCENT, bg=PANEL)
        self._status_lbl.pack(side="right", padx=18)

        sep = tk.Frame(self.root, bg=BORDER, height=1)
        sep.pack(fill="x")

        # Notebook
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Dark.TNotebook", background=BG, borderwidth=0)
        style.configure("Dark.TNotebook.Tab", background=PANEL, foreground=MUTED,
                         font=FONT_H, padding=[16, 8])
        style.map("Dark.TNotebook.Tab",
                  background=[("selected", BG)],
                  foreground=[("selected", TEXT)])

        nb = ttk.Notebook(self.root, style="Dark.TNotebook")
        nb.pack(fill="both", expand=True, padx=0, pady=0)

        self._tab_dashboard = self._build_dashboard(nb)
        self._tab_config    = self._build_config(nb)
        self._tab_logs      = self._build_logs(nb)

        nb.add(self._tab_dashboard, text="  Tableau de bord  ")
        nb.add(self._tab_config,    text="  Configuration  ")
        nb.add(self._tab_logs,      text="  Logs  ")

    # ── Onglet Dashboard ──────────────────────────────────────────────────────
    def _build_dashboard(self, parent):
        frame = tk.Frame(parent, bg=BG)

        cards = tk.Frame(frame, bg=BG)
        cards.pack(fill="x", padx=20, pady=20)

        self._card_rows    = self._stat_card(cards, "Lignes synchronisées", "0", ACCENT)
        self._card_errors  = self._stat_card(cards, "Erreurs", "0", ERROR)
        self._card_table   = self._stat_card(cards, "Table destination",
                                              self.config.get_dest_table_name(), ACCENT2)
        self._card_last    = self._stat_card(cards, "Dernière synchro", "—", MUTED)

        # Boutons
        btns = tk.Frame(frame, bg=BG)
        btns.pack(fill="x", padx=20)

        self._btn_toggle = self._btn(btns, "⏸  Pause", self._toggle_sync, WARN)
        self._btn_toggle.pack(side="left", padx=(0, 10))
        self._btn(btns, "↺  Forcer synchro", self._force_sync, ACCENT2).pack(side="left")

        # Info connexions
        info = tk.Frame(frame, bg=PANEL, bd=0, relief="flat")
        info.pack(fill="x", padx=20, pady=20)

        self._conn_src = self._conn_row(info, "Source", self.config.source)
        self._conn_dst = self._conn_row(info, "Destination", self.config.destination)

        return frame

    def _stat_card(self, parent, label, value, color):
        card = tk.Frame(parent, bg=PANEL, width=160, height=80)
        card.pack(side="left", padx=(0, 12))
        card.pack_propagate(False)

        tk.Label(card, text=label, font=("Segoe UI", 8), fg=MUTED,
                 bg=PANEL).pack(anchor="w", padx=12, pady=(12, 0))
        val_lbl = tk.Label(card, text=value, font=("Segoe UI Semibold", 18),
                            fg=color, bg=PANEL)
        val_lbl.pack(anchor="w", padx=12)
        return val_lbl

    def _conn_row(self, parent, label, cfg):
        row = tk.Frame(parent, bg=PANEL)
        row.pack(fill="x", padx=14, pady=6)

        tk.Label(row, text=f"{label} :", font=FONT_H, fg=MUTED,
                 bg=PANEL, width=12, anchor="w").pack(side="left")

        host = cfg.get("host", "—")
        db   = cfg.get("database", "—")
        table = cfg.get("table", cfg.get("table_prefix", "—"))
        txt = f"{host}  /  {db}  /  {table}"

        lbl = tk.Label(row, text=txt, font=FONT_UI, fg=TEXT, bg=PANEL, anchor="w")
        lbl.pack(side="left")
        return lbl

    def _btn(self, parent, text, cmd, color):
        b = tk.Button(parent, text=text, command=cmd,
                      bg=color, fg="#000" if color in (ACCENT, WARN) else "#fff",
                      font=FONT_H, relief="flat", padx=14, pady=6,
                      activebackground=color, cursor="hand2", bd=0)
        return b

    # ── Onglet Configuration ──────────────────────────────────────────────────
    def _build_config(self, parent):
        frame = tk.Frame(parent, bg=BG)

        canvas = tk.Canvas(frame, bg=BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=BG)

        scroll_frame.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self._cfg_fields = {}
        fields = [
            ("Source", [
                ("source.host",     "Hôte source",       self.config.source["host"]),
                ("source.port",     "Port",              str(self.config.source["port"])),
                ("source.user",     "Utilisateur",       self.config.source["user"]),
                ("source.password", "Mot de passe",      self.config.source["password"], True),
                ("source.database", "Base de données",   self.config.source["database"]),
                ("source.table",    "Table source",      self.config.source["table"]),
            ]),
            ("Destination", [
                ("destination.host",          "Hôte destination",   self.config.destination["host"]),
                ("destination.port",          "Port",               str(self.config.destination["port"])),
                ("destination.user",          "Utilisateur",        self.config.destination["user"]),
                ("destination.password",      "Mot de passe",       self.config.destination["password"], True),
                ("destination.database",      "Base de données",    self.config.destination["database"]),
                ("destination.table_prefix",  "Préfixe table (ex: sync_data_V)", self.config.destination["table_prefix"]),
                ("destination.current_version","Version actuelle",  str(self.config.destination["current_version"])),
            ]),
            ("Synchronisation", [
                ("sync.interval_seconds", "Intervalle (secondes)", str(self.config.sync["interval_seconds"])),
                ("sync.polling_column",   "Colonne timestamp",     self.config.sync["polling_column"]),
            ]),
        ]

        for section, items in fields:
            sec_frame = tk.Frame(scroll_frame, bg=PANEL)
            sec_frame.pack(fill="x", padx=20, pady=(14, 0))
            tk.Label(sec_frame, text=section, font=FONT_BIG, fg=ACCENT,
                     bg=PANEL).pack(anchor="w", padx=14, pady=(10, 6))

            for item in items:
                key, label, default = item[0], item[1], item[2]
                is_pwd = len(item) > 3 and item[3]
                row = tk.Frame(sec_frame, bg=PANEL)
                row.pack(fill="x", padx=14, pady=4)
                tk.Label(row, text=label, font=FONT_UI, fg=MUTED,
                         bg=PANEL, width=28, anchor="w").pack(side="left")
                var = tk.StringVar(value=default)
                show = "*" if is_pwd else ""
                entry = tk.Entry(row, textvariable=var, font=FONT_MONO,
                                 bg=BG, fg=TEXT, insertbackground=TEXT,
                                 relief="flat", show=show,
                                 highlightthickness=1,
                                 highlightcolor=ACCENT,
                                 highlightbackground=BORDER)
                entry.pack(side="left", fill="x", expand=True, ipady=5, padx=4)
                self._cfg_fields[key] = var

            tk.Frame(sec_frame, bg=BG, height=10).pack()

        save_btn = self._btn(scroll_frame, "💾  Enregistrer la configuration", self._save_config, ACCENT)
        save_btn.pack(pady=20, padx=20, anchor="w")

        return frame

    # ── Onglet Logs ───────────────────────────────────────────────────────────
    def _build_logs(self, parent):
        frame = tk.Frame(parent, bg=BG)

        toolbar = tk.Frame(frame, bg=BG)
        toolbar.pack(fill="x", padx=20, pady=(12, 4))
        self._btn(toolbar, "🗑  Effacer", self._clear_logs, BORDER).pack(side="right")
        tk.Label(toolbar, text="Journal d'activité", font=FONT_BIG,
                 fg=TEXT, bg=BG).pack(side="left")

        self._log_text = tk.Text(frame, bg=PANEL, fg=TEXT, font=FONT_MONO,
                                  relief="flat", state="disabled",
                                  selectbackground=ACCENT, wrap="word",
                                  padx=10, pady=8)
        self._log_text.pack(fill="both", expand=True, padx=20, pady=(0, 16))

        self._log_text.tag_configure("INFO",  foreground=TEXT)
        self._log_text.tag_configure("WARN",  foreground=WARN)
        self._log_text.tag_configure("ERROR", foreground=ERROR)

        return frame

    # ── Actions ───────────────────────────────────────────────────────────────
    def _toggle_sync(self):
        if self.engine.running:
            self.engine.stop()
            self._btn_toggle.config(text="▶  Reprendre")
        else:
            self.engine.start()
            self._btn_toggle.config(text="⏸  Pause")

    def _force_sync(self):
        self.engine.stats["last_sync"] = None

    def _save_config(self):
        try:
            for key, var in self._cfg_fields.items():
                parts = key.split(".")
                section, field = parts[0], parts[1]
                value = var.get()
                if field in ("port", "interval_seconds", "current_version"):
                    value = int(value)
                self.config.set(value, section, field)
            self._refresh_conn_labels()
            messagebox.showinfo("Sauvegardé", "Configuration enregistrée.\nRedémarrez la synchronisation pour appliquer.")
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de sauvegarder :\n{e}")

    def _clear_logs(self):
        self._log_text.config(state="normal")
        self._log_text.delete("1.0", "end")
        self._log_text.config(state="disabled")

    # ── Callbacks ─────────────────────────────────────────────────────────────
    def _on_log(self, level, msg):
        self.root.after(0, lambda: self._append_log(level, msg))

    def _append_log(self, level, msg):
        self._log_text.config(state="normal")
        self._log_text.insert("end", msg + "\n", level)
        self._log_text.see("end")
        self._log_text.config(state="disabled")

    def _refresh_conn_labels(self):
        pass  # Sera actualisé via _start_refresh

    def _start_refresh(self):
        self._refresh()

    def _refresh(self):
        st = self.engine.stats
        running = self.engine.running

        self._card_rows.config(text=str(st["rows_synced"]))
        self._card_errors.config(text=str(st["errors"]),
                                   fg=ERROR if st["errors"] > 0 else MUTED)
        self._card_table.config(text=st["current_dest_table"])
        last = st["last_sync"]
        self._card_last.config(text=last.strftime("%H:%M:%S") if last else "—")

        if running:
            self._status_lbl.config(text="◉ En cours", fg=ACCENT)
            self._btn_toggle.config(text="⏸  Pause")
        else:
            self._status_lbl.config(text="◎ Arrêté", fg=MUTED)
            self._btn_toggle.config(text="▶  Reprendre")

        self.root.after(2000, self._refresh)
