import tkinter as tk
from tkinter import ttk, messagebox

BG      = "#0f1117"
PANEL   = "#1a1d27"
BORDER  = "#2a2d3a"
ACCENT  = "#00c47a"
ACCENT2 = "#0099ff"
WARN    = "#ffaa00"
ERROR   = "#ff4455"
TEXT    = "#e8eaf0"
MUTED   = "#6b7080"
FONT_UI = ("Segoe UI", 10)
FONT_MONO=("Consolas", 9)
FONT_BIG= ("Segoe UI Semibold", 12)
FONT_H  = ("Segoe UI Semibold", 10)


class SupervisionWindow:
    def __init__(self, config, engine):
        self.config = config
        self.engine = engine

        self.root = tk.Tk()
        self.root.title("MySQLSync — Supervision")
        self.root.geometry("960x660")
        self.root.minsize(800, 500)
        self.root.configure(bg=BG)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        engine.add_log_callback(self._on_log)
        self._build_ui()
        self._start_refresh()

    def _on_close(self):
        self.root.withdraw()

    def show_window(self):
        self.root.after(0, lambda: (self.root.deiconify(), self.root.lift(), self.root.focus_force()))

    def _build_ui(self):
        # Header
        header = tk.Frame(self.root, bg=PANEL, height=54)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="● MySQLSync", font=("Segoe UI Semibold", 14),
                 fg=ACCENT, bg=PANEL).pack(side="left", padx=18, pady=14)
        self._status_lbl = tk.Label(header, text="◉ En cours", font=FONT_UI, fg=ACCENT, bg=PANEL)
        self._status_lbl.pack(side="right", padx=18)
        tk.Frame(self.root, bg=BORDER, height=1).pack(fill="x")

        # Notebook
        style = ttk.Style()
        style.theme_use("default")
        style.configure("D.TNotebook", background=BG, borderwidth=0)
        style.configure("D.TNotebook.Tab", background=PANEL, foreground=MUTED,
                        font=FONT_H, padding=[16, 8])
        style.map("D.TNotebook.Tab",
                  background=[("selected", BG)], foreground=[("selected", TEXT)])

        nb = ttk.Notebook(self.root, style="D.TNotebook")
        nb.pack(fill="both", expand=True)

        nb.add(self._build_dashboard(nb), text="  Tableau de bord  ")
        nb.add(self._build_pairs(nb),     text="  Paires de sync  ")
        nb.add(self._build_history(nb),   text="  Historique  ")
        nb.add(self._build_config(nb),    text="  Configuration  ")
        nb.add(self._build_logs(nb),      text="  Logs  ")

    # ── Dashboard ─────────────────────────────────────────────────────────────
    def _build_dashboard(self, parent):
        frame = tk.Frame(parent, bg=BG)

        cards = tk.Frame(frame, bg=BG)
        cards.pack(fill="x", padx=20, pady=20)
        self._card_rows   = self._stat_card(cards, "Lignes ajoutées", "0", ACCENT)
        self._card_errors = self._stat_card(cards, "Erreurs", "0", ERROR)
        self._card_pairs  = self._stat_card(cards, "Paires actives",
                                             str(len(self.config.pairs)), ACCENT2)

        btns = tk.Frame(frame, bg=BG)
        btns.pack(fill="x", padx=20)
        self._btn_toggle = self._btn(btns, "⏸  Pause", self._toggle_sync, WARN)
        self._btn_toggle.pack(side="left", padx=(0, 10))
        self._btn(btns, "↺  Forcer synchro", self._force_sync, ACCENT2).pack(side="left")

        # Tableau des paires
        self._pairs_frame = tk.Frame(frame, bg=BG)
        self._pairs_frame.pack(fill="both", expand=True, padx=20, pady=16)
        self._refresh_pairs_table()

        return frame

    def _refresh_pairs_table(self):
        for w in self._pairs_frame.winfo_children():
            w.destroy()

        headers = ["Nom", "Table source", "Table destination", "Lignes", "Dernière synchro", "Statut"]
        widths   = [160, 140, 160, 80, 130, 80]

        hrow = tk.Frame(self._pairs_frame, bg=PANEL)
        hrow.pack(fill="x")
        for h, w in zip(headers, widths):
            tk.Label(hrow, text=h, font=FONT_H, fg=MUTED, bg=PANEL,
                     width=w//8, anchor="w").pack(side="left", padx=8, pady=6)

        tk.Frame(self._pairs_frame, bg=BORDER, height=1).pack(fill="x")

        for pair in self.config.pairs:
            pid  = pair["id"]
            pst  = self.engine.stats["pairs"].get(pid, {})
            last = pst.get("last_sync")
            last_str = last.strftime("%H:%M:%S") if last else "—"
            status = pst.get("status", "—")
            status_color = ACCENT if status == "OK" else ERROR if status == "Erreur" else MUTED

            row = tk.Frame(self._pairs_frame, bg=BG)
            row.pack(fill="x")
            vals = [
                pair["name"],
                pair["source"].get("table", "—"),
                pst.get("dest_table", "—"),
                str(pst.get("rows_synced", 0)),
                last_str,
                status
            ]
            colors = [TEXT, TEXT, TEXT, ACCENT, MUTED, status_color]
            for v, w, c in zip(vals, widths, colors):
                tk.Label(row, text=v, font=FONT_UI, fg=c, bg=BG,
                         width=w//8, anchor="w").pack(side="left", padx=8, pady=5)
            tk.Frame(self._pairs_frame, bg=BORDER, height=1).pack(fill="x")

    # ── Paires ────────────────────────────────────────────────────────────────
    def _build_pairs(self, parent):
        frame = tk.Frame(parent, bg=BG)

        toolbar = tk.Frame(frame, bg=BG)
        toolbar.pack(fill="x", padx=20, pady=12)
        tk.Label(toolbar, text="Paires de synchronisation", font=FONT_BIG,
                 fg=TEXT, bg=BG).pack(side="left")
        self._btn(toolbar, "+ Ajouter une paire", self._add_pair, ACCENT).pack(side="right")

        self._pairs_list_frame = tk.Frame(frame, bg=BG)
        self._pairs_list_frame.pack(fill="both", expand=True, padx=20)
        self._refresh_pairs_list()

        return frame

    def _refresh_pairs_list(self):
        for w in self._pairs_list_frame.winfo_children():
            w.destroy()

        for pair in self.config.pairs:
            self._pair_card(self._pairs_list_frame, pair)

    def _pair_card(self, parent, pair):
        card = tk.Frame(parent, bg=PANEL, bd=0)
        card.pack(fill="x", pady=6)

        top = tk.Frame(card, bg=PANEL)
        top.pack(fill="x", padx=14, pady=8)

        enabled_var = tk.BooleanVar(value=pair.get("enabled", True))
        tk.Checkbutton(top, variable=enabled_var, bg=PANEL, activebackground=PANEL,
                       fg=ACCENT, selectcolor=BG,
                       command=lambda pid=pair["id"], v=enabled_var: self.config.set_pair_enabled(pid, v.get())
                       ).pack(side="left")

        tk.Label(top, text=pair["name"], font=FONT_BIG, fg=TEXT, bg=PANEL).pack(side="left", padx=6)

        self._btn(top, "✎ Modifier", lambda p=pair: self._edit_pair(p), ACCENT2).pack(side="right", padx=(4, 0))
        self._btn(top, "✕ Supprimer", lambda pid=pair["id"]: self._delete_pair(pid), ERROR).pack(side="right")

        info = tk.Frame(card, bg=PANEL)
        info.pack(fill="x", padx=14, pady=(0, 10))

        src  = pair["source"]
        dst  = pair["destination"]
        dest_table = self.config.get_dest_table_name(pair["id"])

        tk.Label(info, text=f"Source : {src['host']} / {src['database']} / {src['table']}",
                 font=FONT_UI, fg=MUTED, bg=PANEL).pack(anchor="w")
        tk.Label(info, text=f"Destination : {dst['host']} / {dst['database']} / {dest_table}",
                 font=FONT_UI, fg=MUTED, bg=PANEL).pack(anchor="w")

    def _add_pair(self):
        pair = self.config.add_pair()
        self.engine.stats["pairs"][pair["id"]] = {
            "name": pair["name"], "rows_synced": 0, "errors": 0,
            "last_sync": None, "dest_table": self.config.get_dest_table_name(pair["id"]),
            "status": "En attente"
        }
        self._edit_pair(pair)

    def _delete_pair(self, pair_id):
        if messagebox.askyesno("Supprimer", "Supprimer cette paire ?"):
            self.config.remove_pair(pair_id)
            self._refresh_pairs_list()

    def _edit_pair(self, pair):
        win = tk.Toplevel(self.root)
        win.title(f"Modifier — {pair['name']}")
        win.geometry("500x580")
        win.configure(bg=BG)

        fields = {}

        def row(parent, label, value, is_pwd=False):
            f = tk.Frame(parent, bg=BG)
            f.pack(fill="x", pady=4)
            tk.Label(f, text=label, font=FONT_UI, fg=MUTED, bg=BG, width=22, anchor="w").pack(side="left")
            var = tk.StringVar(value=str(value))
            e = tk.Entry(f, textvariable=var, font=FONT_MONO, bg=PANEL, fg=TEXT,
                         insertbackground=TEXT, relief="flat", show="*" if is_pwd else "",
                         highlightthickness=1, highlightcolor=ACCENT, highlightbackground=BORDER)
            e.pack(side="left", fill="x", expand=True, ipady=5)
            return var

        src = pair["source"]
        dst = pair["destination"]

        tk.Label(win, text="Nom de la paire", font=FONT_H, fg=MUTED, bg=BG).pack(anchor="w", padx=16, pady=(14, 0))
        fields["name"] = row(tk.Frame(win, bg=BG), "Nom", pair["name"])
        fields["name"].master = win

        tk.Label(win, text="Source", font=FONT_BIG, fg=ACCENT, bg=BG).pack(anchor="w", padx=16, pady=(12, 4))
        src_frame = tk.Frame(win, bg=BG)
        src_frame.pack(fill="x", padx=16)
        fields["src_host"]     = row(src_frame, "Hôte", src["host"])
        fields["src_port"]     = row(src_frame, "Port", src["port"])
        fields["src_user"]     = row(src_frame, "Utilisateur", src["user"])
        fields["src_password"] = row(src_frame, "Mot de passe", src["password"], True)
        fields["src_database"] = row(src_frame, "Base de données", src["database"])
        fields["src_table"]    = row(src_frame, "Table", src["table"])
        fields["src_pk"]       = row(src_frame, "Clé primaire", src.get("primary_key", "id"))

        tk.Label(win, text="Destination", font=FONT_BIG, fg=ACCENT2, bg=BG).pack(anchor="w", padx=16, pady=(12, 4))
        dst_frame = tk.Frame(win, bg=BG)
        dst_frame.pack(fill="x", padx=16)
        fields["dst_host"]     = row(dst_frame, "Hôte", dst["host"])
        fields["dst_port"]     = row(dst_frame, "Port", dst["port"])
        fields["dst_user"]     = row(dst_frame, "Utilisateur", dst["user"])
        fields["dst_password"] = row(dst_frame, "Mot de passe", dst["password"], True)
        fields["dst_database"] = row(dst_frame, "Base de données", dst["database"])
        fields["dst_prefix"]   = row(dst_frame, "Préfixe table (ex: sync_V)", dst["table_prefix"])

        def save():
            updated = {
                "id": pair["id"],
                "name": fields["name"].get(),
                "enabled": pair.get("enabled", True),
                "source": {
                    "host": fields["src_host"].get(),
                    "port": int(fields["src_port"].get()),
                    "user": fields["src_user"].get(),
                    "password": fields["src_password"].get(),
                    "database": fields["src_database"].get(),
                    "table": fields["src_table"].get(),
                    "primary_key": fields["src_pk"].get()
                },
                "destination": {
                    "host": fields["dst_host"].get(),
                    "port": int(fields["dst_port"].get()),
                    "user": fields["dst_user"].get(),
                    "password": fields["dst_password"].get(),
                    "database": fields["dst_database"].get(),
                    "table_prefix": fields["dst_prefix"].get(),
                    "current_version": dst["current_version"]
                }
            }
            self.config.update_pair(pair["id"], updated)
            self._refresh_pairs_list()
            win.destroy()

        self._btn(win, "💾  Enregistrer", save, ACCENT).pack(pady=16)

    # ── Historique ────────────────────────────────────────────────────────────
    def _build_history(self, parent):
        frame = tk.Frame(parent, bg=BG)

        toolbar = tk.Frame(frame, bg=BG)
        toolbar.pack(fill="x", padx=20, pady=12)
        tk.Label(toolbar, text="Historique des synchronisations", font=FONT_BIG,
                 fg=TEXT, bg=BG).pack(side="left")
        self._btn(toolbar, "↺ Actualiser", self._refresh_history, ACCENT2).pack(side="right")

        cols = ("Heure", "Paire", "Table src", "Table dst", "Ajoutées", "Vérifiées")
        self._hist_tree = ttk.Treeview(frame, columns=cols, show="headings", height=20)
        widths = [130, 140, 140, 160, 80, 80]
        for col, w in zip(cols, widths):
            self._hist_tree.heading(col, text=col)
            self._hist_tree.column(col, width=w, anchor="w")

        style = ttk.Style()
        style.configure("Treeview", background=PANEL, foreground=TEXT,
                        fieldbackground=PANEL, font=FONT_UI, rowheight=28)
        style.configure("Treeview.Heading", background=BG, foreground=MUTED, font=FONT_H)

        self._hist_tree.pack(fill="both", expand=True, padx=20, pady=(0, 16))
        return frame

    def _refresh_history(self):
        for row in self._hist_tree.get_children():
            self._hist_tree.delete(row)
        try:
            from core.history_manager import HistoryManager
            hm = HistoryManager(self.config, lambda *a: None)
            hm.connect()
            rows = hm.fetch_recent(200)
            hm.disconnect()
            for r in rows:
                self._hist_tree.insert("", "end", values=(
                    str(r.get("synced_at", ""))[:19],
                    r.get("pair_name", ""),
                    r.get("src_table", ""),
                    r.get("dest_table", ""),
                    r.get("rows_added", 0),
                    r.get("rows_updated", 0),
                ))
        except Exception as e:
            self._hist_tree.insert("", "end", values=(str(e), "", "", "", "", ""))

    # ── Configuration globale ─────────────────────────────────────────────────
    def _build_config(self, parent):
        frame = tk.Frame(parent, bg=BG)

        tk.Label(frame, text="Base d'historique", font=FONT_BIG, fg=ACCENT,
                 bg=BG).pack(anchor="w", padx=20, pady=(16, 6))

        hist_frame = tk.Frame(frame, bg=PANEL)
        hist_frame.pack(fill="x", padx=20)

        self._hist_fields = {}
        hist = self.config.history
        for label, key, val, pwd in [
            ("Hôte", "host", hist.get("host",""), False),
            ("Port", "port", str(hist.get("port", 3306)), False),
            ("Utilisateur", "user", hist.get("user",""), False),
            ("Mot de passe", "password", hist.get("password",""), True),
            ("Base historique", "database", hist.get("database","mysqlsync_history"), False),
        ]:
            row = tk.Frame(hist_frame, bg=PANEL)
            row.pack(fill="x", padx=14, pady=4)
            tk.Label(row, text=label, font=FONT_UI, fg=MUTED, bg=PANEL,
                     width=20, anchor="w").pack(side="left")
            var = tk.StringVar(value=val)
            tk.Entry(row, textvariable=var, font=FONT_MONO, bg=BG, fg=TEXT,
                     insertbackground=TEXT, relief="flat", show="*" if pwd else "",
                     highlightthickness=1, highlightcolor=ACCENT,
                     highlightbackground=BORDER).pack(side="left", fill="x", expand=True, ipady=5)
            self._hist_fields[key] = var

        tk.Label(frame, text="Synchronisation", font=FONT_BIG, fg=ACCENT,
                 bg=BG).pack(anchor="w", padx=20, pady=(16, 6))

        sync_frame = tk.Frame(frame, bg=PANEL)
        sync_frame.pack(fill="x", padx=20)
        row = tk.Frame(sync_frame, bg=PANEL)
        row.pack(fill="x", padx=14, pady=4)
        tk.Label(row, text="Intervalle (secondes)", font=FONT_UI, fg=MUTED,
                 bg=PANEL, width=20, anchor="w").pack(side="left")
        self._interval_var = tk.StringVar(value=str(self.config.sync.get("interval_seconds", 5)))
        tk.Entry(row, textvariable=self._interval_var, font=FONT_MONO, bg=BG, fg=TEXT,
                 insertbackground=TEXT, relief="flat",
                 highlightthickness=1, highlightcolor=ACCENT,
                 highlightbackground=BORDER).pack(side="left", fill="x", expand=True, ipady=5)

        self._btn(frame, "💾  Enregistrer", self._save_global_config, ACCENT).pack(pady=16, padx=20, anchor="w")
        return frame

    def _save_global_config(self):
        try:
            self.config._data["history"] = {
                "host": self._hist_fields["host"].get(),
                "port": int(self._hist_fields["port"].get()),
                "user": self._hist_fields["user"].get(),
                "password": self._hist_fields["password"].get(),
                "database": self._hist_fields["database"].get()
            }
            self.config._data["sync"]["interval_seconds"] = int(self._interval_var.get())
            self.config.save()
            messagebox.showinfo("Sauvegardé", "Configuration enregistrée.")
        except Exception as e:
            messagebox.showerror("Erreur", str(e))

    # ── Logs ──────────────────────────────────────────────────────────────────
    def _build_logs(self, parent):
        frame = tk.Frame(parent, bg=BG)
        toolbar = tk.Frame(frame, bg=BG)
        toolbar.pack(fill="x", padx=20, pady=(12, 4))
        tk.Label(toolbar, text="Journal d'activité", font=FONT_BIG, fg=TEXT, bg=BG).pack(side="left")
        self._btn(toolbar, "🗑  Effacer", self._clear_logs, BORDER).pack(side="right")

        self._log_text = tk.Text(frame, bg=PANEL, fg=TEXT, font=FONT_MONO,
                                  relief="flat", state="disabled",
                                  selectbackground=ACCENT, wrap="word", padx=10, pady=8)
        self._log_text.pack(fill="both", expand=True, padx=20, pady=(0, 16))
        self._log_text.tag_configure("INFO",  foreground=TEXT)
        self._log_text.tag_configure("WARN",  foreground=WARN)
        self._log_text.tag_configure("ERROR", foreground=ERROR)
        return frame

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _stat_card(self, parent, label, value, color):
        card = tk.Frame(parent, bg=PANEL, width=160, height=80)
        card.pack(side="left", padx=(0, 12))
        card.pack_propagate(False)
        tk.Label(card, text=label, font=("Segoe UI", 8), fg=MUTED, bg=PANEL).pack(anchor="w", padx=12, pady=(12, 0))
        lbl = tk.Label(card, text=value, font=("Segoe UI Semibold", 18), fg=color, bg=PANEL)
        lbl.pack(anchor="w", padx=12)
        return lbl

    def _btn(self, parent, text, cmd, color):
        return tk.Button(parent, text=text, command=cmd,
                         bg=color, fg="#000" if color in (ACCENT, WARN) else "#fff",
                         font=FONT_H, relief="flat", padx=14, pady=6,
                         activebackground=color, cursor="hand2", bd=0)

    def _toggle_sync(self):
        if self.engine.running:
            self.engine.stop()
        else:
            self.engine.start()

    def _force_sync(self):
        pass

    def _clear_logs(self):
        self._log_text.config(state="normal")
        self._log_text.delete("1.0", "end")
        self._log_text.config(state="disabled")

    def _on_log(self, level, msg):
        self.root.after(0, lambda: self._append_log(level, msg))

    def _append_log(self, level, msg):
        self._log_text.config(state="normal")
        self._log_text.insert("end", msg + "\n", level)
        self._log_text.see("end")
        self._log_text.config(state="disabled")

    def _start_refresh(self):
        self._refresh()

    def _refresh(self):
        st = self.engine.stats
        self._card_rows.config(text=str(st["total_rows_synced"]))
        self._card_errors.config(text=str(st["total_errors"]),
                                   fg=ERROR if st["total_errors"] > 0 else MUTED)
        active = sum(1 for p in self.config.pairs if p.get("enabled", True))
        self._card_pairs.config(text=str(active))

        if self.engine.running:
            self._status_lbl.config(text="◉ En cours", fg=ACCENT)
            self._btn_toggle.config(text="⏸  Pause")
        else:
            self._status_lbl.config(text="◎ Arrêté", fg=MUTED)
            self._btn_toggle.config(text="▶  Reprendre")

        self._refresh_pairs_table()
        self.root.after(3000, self._refresh)
