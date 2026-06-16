import tkinter as tk
from tkinter import ttk, messagebox
from core.local_db import VERSION

BG      = "#0f1117"
PANEL   = "#1a1d27"
BORDER  = "#2a2d3a"
ACCENT  = "#00c47a"
ACCENT2 = "#0099ff"
WARN    = "#ffaa00"
ERROR   = "#ff4455"
TEXT    = "#e8eaf0"
MUTED   = "#6b7080"
FONT_UI  = ("Segoe UI", 10)
FONT_MONO= ("Consolas", 9)
FONT_BIG = ("Segoe UI Semibold", 12)
FONT_H   = ("Segoe UI Semibold", 10)


class SupervisionWindow:
    def __init__(self, config, engine, root):
        self.config = config
        self.engine = engine
        self.root = root

        self.root.deiconify()
        self.root.title(f"MySQLSync v{VERSION} — Supervision")
        self.root.geometry("980x680")
        self.root.minsize(800, 520)
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
        tk.Label(header, text=f"v{VERSION}", font=("Segoe UI", 9),
                 fg=MUTED, bg=PANEL).pack(side="left", pady=14)
        self._status_lbl = tk.Label(header, text="◉ En cours", font=FONT_UI, fg=ACCENT, bg=PANEL)
        self._status_lbl.pack(side="right", padx=18)
        tk.Frame(self.root, bg=BORDER, height=1).pack(fill="x")

        style = ttk.Style()
        style.theme_use("default")
        style.configure("D.TNotebook", background=BG, borderwidth=0)
        style.configure("D.TNotebook.Tab", background=PANEL, foreground=MUTED,
                        font=FONT_H, padding=[16, 8])
        style.map("D.TNotebook.Tab",
                  background=[("selected", BG)], foreground=[("selected", TEXT)])
        style.configure("Treeview", background=PANEL, foreground=TEXT,
                        fieldbackground=PANEL, font=FONT_UI, rowheight=28)
        style.configure("Treeview.Heading", background=BG, foreground=MUTED, font=FONT_H)

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

        self._pairs_frame = tk.Frame(frame, bg=BG)
        self._pairs_frame.pack(fill="both", expand=True, padx=20, pady=16)
        self._refresh_pairs_table()
        return frame

    def _refresh_pairs_table(self):
        for w in self._pairs_frame.winfo_children():
            w.destroy()

        headers = ["Nom", "Table source", "Table destination", "Ajoutées", "Dernière synchro", "Statut"]
        widths   = [18, 16, 18, 8, 14, 8]

        hrow = tk.Frame(self._pairs_frame, bg=PANEL)
        hrow.pack(fill="x")
        for h, w in zip(headers, widths):
            tk.Label(hrow, text=h, font=FONT_H, fg=MUTED, bg=PANEL,
                     width=w, anchor="w").pack(side="left", padx=8, pady=6)
        tk.Frame(self._pairs_frame, bg=BORDER, height=1).pack(fill="x")

        for pair in self.config.pairs:
            pid  = pair["id"]
            pst  = self.engine.stats["pairs"].get(pid, {})
            last = pst.get("last_sync")
            status = pst.get("status", "—")
            status_color = ACCENT if status == "OK" else ERROR if status == "Erreur" else MUTED

            row = tk.Frame(self._pairs_frame, bg=BG)
            row.pack(fill="x")
            vals = [
                pair["name"],
                pair["source"].get("table", "—"),
                pst.get("dest_table", self.config.get_dest_table_name(pid) or "—"),
                str(pst.get("rows_synced", 0)),
                last.strftime("%H:%M:%S") if last else "—",
                status
            ]
            colors = [TEXT, TEXT, TEXT, ACCENT, MUTED, status_color]
            widths2 = [18, 16, 18, 8, 14, 8]
            for v, w, c in zip(vals, widths2, colors):
                tk.Label(row, text=v, font=FONT_UI, fg=c, bg=BG,
                         width=w, anchor="w").pack(side="left", padx=8, pady=5)
            tk.Frame(self._pairs_frame, bg=BORDER, height=1).pack(fill="x")

    # ── Paires ────────────────────────────────────────────────────────────────
    def _build_pairs(self, parent):
        frame = tk.Frame(parent, bg=BG)

        toolbar = tk.Frame(frame, bg=BG)
        toolbar.pack(fill="x", padx=20, pady=12)
        tk.Label(toolbar, text="Paires de synchronisation", font=FONT_BIG,
                 fg=TEXT, bg=BG).pack(side="left")
        self._btn(toolbar, "+ Ajouter une paire", self._add_pair, ACCENT).pack(side="right")

        # Zone scrollable
        canvas = tk.Canvas(frame, bg=BG, highlightthickness=0)
        sb = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        self._pairs_list_frame = tk.Frame(canvas, bg=BG)
        self._pairs_list_frame.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self._pairs_list_frame, anchor="nw")
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        self._refresh_pairs_list()
        return frame

    def _refresh_pairs_list(self):
        for w in self._pairs_list_frame.winfo_children():
            w.destroy()
        for pair in self.config.pairs:
            self._pair_card(self._pairs_list_frame, pair)

    def _pair_card(self, parent, pair):
        card = tk.Frame(parent, bg=PANEL)
        card.pack(fill="x", pady=6, padx=4)

        top = tk.Frame(card, bg=PANEL)
        top.pack(fill="x", padx=14, pady=8)

        enabled_var = tk.BooleanVar(value=pair.get("enabled", True))
        tk.Checkbutton(top, variable=enabled_var, bg=PANEL, activebackground=PANEL,
                       fg=ACCENT, selectcolor=BG,
                       command=lambda pid=pair["id"], v=enabled_var:
                           self.config.set_pair_enabled(pid, v.get())
                       ).pack(side="left")

        tk.Label(top, text=pair["name"], font=FONT_BIG, fg=TEXT, bg=PANEL).pack(side="left", padx=6)
        self._btn(top, "✎ Modifier", lambda p=pair: self._edit_pair(p), ACCENT2).pack(side="right", padx=(4, 0))
        self._btn(top, "✕", lambda pid=pair["id"]: self._delete_pair(pid), ERROR).pack(side="right")

        info = tk.Frame(card, bg=PANEL)
        info.pack(fill="x", padx=14, pady=(0, 10))
        src = pair["source"]
        dst = pair["destination"]
        dest_table = self.config.get_dest_table_name(pair["id"])
        tk.Label(info, text=f"Source : {src.get('host','')} / {src.get('database','')} / {src.get('table','')}",
                 font=FONT_UI, fg=MUTED, bg=PANEL).pack(anchor="w")
        tk.Label(info, text=f"Destination : {dst.get('host','')} / {dst.get('database','')} / {dest_table}",
                 font=FONT_UI, fg=MUTED, bg=PANEL).pack(anchor="w")

    def _add_pair(self):
        pair = self.config.add_pair()
        self.engine.stats["pairs"][pair["id"]] = {
            "name": pair["name"], "rows_synced": 0, "errors": 0,
            "last_sync": None,
            "dest_table": self.config.get_dest_table_name(pair["id"]),
            "status": "En attente"
        }
        self._edit_pair(pair, new=True)

    def _delete_pair(self, pair_id):
        if messagebox.askyesno("Supprimer", "Supprimer cette paire ?"):
            self.config.remove_pair(pair_id)
            self._refresh_pairs_list()

    def _edit_pair(self, pair, new=False):
        win = tk.Toplevel(self.root)
        win.title(f"{'Nouvelle paire' if new else pair['name']}")
        win.geometry("520x640")
        win.minsize(480, 600)
        win.configure(bg=BG)
        win.grab_set()

        # Zone scrollable
        canvas = tk.Canvas(win, bg=BG, highlightthickness=0)
        sb = ttk.Scrollbar(win, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas, bg=BG)
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        fields = {}

        def field_row(parent, label, value, is_pwd=False):
            f = tk.Frame(parent, bg=BG)
            f.pack(fill="x", pady=4, padx=16)
            tk.Label(f, text=label, font=FONT_UI, fg=MUTED, bg=BG,
                     width=24, anchor="w").pack(side="left")
            var = tk.StringVar(value=str(value))
            e = tk.Entry(f, textvariable=var, font=FONT_MONO, bg=PANEL, fg=TEXT,
                         insertbackground=TEXT, relief="flat",
                         show="*" if is_pwd else "",
                         highlightthickness=1, highlightcolor=ACCENT,
                         highlightbackground=BORDER)
            e.pack(side="left", fill="x", expand=True, ipady=6)
            return var

        def section(text, color=ACCENT):
            tk.Label(inner, text=text, font=FONT_BIG, fg=color,
                     bg=BG).pack(anchor="w", padx=16, pady=(16, 4))

        src = pair["source"]
        dst = pair["destination"]

        section("Général")
        fields["name"] = field_row(inner, "Nom de la paire", pair["name"])

        section("Source")
        fields["src_host"]     = field_row(inner, "Hôte", src.get("host", ""))
        fields["src_port"]     = field_row(inner, "Port", src.get("port", 3306))
        fields["src_user"]     = field_row(inner, "Utilisateur", src.get("user", "root"))
        fields["src_password"] = field_row(inner, "Mot de passe", src.get("password", ""), True)
        fields["src_database"] = field_row(inner, "Base de données", src.get("database", ""))
        fields["src_table"]    = field_row(inner, "Table", src.get("table", ""))
        fields["src_pk"]       = field_row(inner, "Clé primaire", src.get("primary_key", "id"))

        section("Destination", ACCENT2)
        fields["dst_host"]     = field_row(inner, "Hôte", dst.get("host", ""))
        fields["dst_port"]     = field_row(inner, "Port", dst.get("port", 3306))
        fields["dst_user"]     = field_row(inner, "Utilisateur", dst.get("user", "root"))
        fields["dst_password"] = field_row(inner, "Mot de passe", dst.get("password", ""), True)
        fields["dst_database"] = field_row(inner, "Base de données", dst.get("database", ""))
        fields["dst_prefix"]   = field_row(inner, "Préfixe table (ex: sync_V)", dst.get("table_prefix", "sync_V"))

        def save():
            try:
                new_db     = fields["dst_database"].get()
                new_prefix = fields["dst_prefix"].get()
                old_db     = dst.get("database", "")
                old_prefix = dst.get("table_prefix", "")

                db_changed     = new_db     != old_db
                prefix_changed = new_prefix != old_prefix
                dest_changed   = db_changed or prefix_changed

                new_version = dst.get("current_version", 1)

                if dest_changed and old_db and old_prefix:
                    action = self._ask_dest_change(win, old_db, old_prefix,
                                                   new_db, new_prefix,
                                                   pair["id"], dst, db_changed)
                    if action is None:
                        return
                    new_version = action["version"]

                updated = {
                    "id": pair["id"],
                    "name": fields["name"].get(),
                    "enabled": pair.get("enabled", True),
                    "source": {
                        "host":        fields["src_host"].get(),
                        "port":        int(fields["src_port"].get()),
                        "user":        fields["src_user"].get(),
                        "password":    fields["src_password"].get(),
                        "database":    fields["src_database"].get(),
                        "table":       fields["src_table"].get(),
                        "primary_key": fields["src_pk"].get()
                    },
                    "destination": {
                        "host":          fields["dst_host"].get(),
                        "port":          int(fields["dst_port"].get()),
                        "user":          fields["dst_user"].get(),
                        "password":      fields["dst_password"].get(),
                        "database":      new_db,
                        "table_prefix":  new_prefix,
                        "current_version": new_version
                    }
                }
                self.config.update_pair(pair["id"], updated)
                self._refresh_pairs_list()
                win.destroy()
            except Exception as e:
                messagebox.showerror("Erreur", str(e), parent=win)

        btn_frame = tk.Frame(inner, bg=BG)
        btn_frame.pack(fill="x", pady=20, padx=16)
        self._btn(btn_frame, "💾  Enregistrer", save, ACCENT).pack(side="left")
        self._btn(btn_frame, "Annuler", win.destroy, BORDER).pack(side="left", padx=8)

    # ── Historique ────────────────────────────────────────────────────────────
    def _build_history(self, parent):
        frame = tk.Frame(parent, bg=BG)

        toolbar = tk.Frame(frame, bg=BG)
        toolbar.pack(fill="x", padx=20, pady=12)
        tk.Label(toolbar, text="Historique des synchronisations", font=FONT_BIG,
                 fg=TEXT, bg=BG).pack(side="left")
        self._btn(toolbar, "↺ Actualiser", self._refresh_history, ACCENT2).pack(side="right")

        cols = ("Heure", "Paire", "Table src", "Table dst", "Ajoutées", "Vérifiées")
        self._hist_tree = ttk.Treeview(frame, columns=cols, show="headings", height=22)
        for col, w in zip(cols, [140, 160, 140, 160, 80, 80]):
            self._hist_tree.heading(col, text=col)
            self._hist_tree.column(col, width=w, anchor="w")

        sb = ttk.Scrollbar(frame, orient="vertical", command=self._hist_tree.yview)
        self._hist_tree.configure(yscrollcommand=sb.set)
        self._hist_tree.pack(side="left", fill="both", expand=True, padx=(20, 0), pady=(0, 16))
        sb.pack(side="right", fill="y", pady=(0, 16), padx=(0, 8))

        self._refresh_history()
        return frame

    def _refresh_history(self):
        for row in self._hist_tree.get_children():
            self._hist_tree.delete(row)
        try:
            rows = self.config.fetch_history(200)
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

    # ── Configuration ─────────────────────────────────────────────────────────
    def _build_config(self, parent):
        frame = tk.Frame(parent, bg=BG)

        tk.Label(frame, text="Synchronisation", font=FONT_BIG, fg=ACCENT,
                 bg=BG).pack(anchor="w", padx=20, pady=(16, 6))

        sync_frame = tk.Frame(frame, bg=PANEL)
        sync_frame.pack(fill="x", padx=20)
        row = tk.Frame(sync_frame, bg=PANEL)
        row.pack(fill="x", padx=14, pady=8)
        tk.Label(row, text="Intervalle (secondes)", font=FONT_UI, fg=MUTED,
                 bg=PANEL, width=24, anchor="w").pack(side="left")
        self._interval_var = tk.StringVar(
            value=str(self.config.sync.get("interval_seconds", 5)))
        tk.Entry(row, textvariable=self._interval_var, font=FONT_MONO,
                 bg=BG, fg=TEXT, insertbackground=TEXT, relief="flat",
                 highlightthickness=1, highlightcolor=ACCENT,
                 highlightbackground=BORDER, width=10).pack(side="left", ipady=5)

        tk.Label(frame, text=f"Version : {VERSION}", font=FONT_UI,
                 fg=MUTED, bg=BG).pack(anchor="w", padx=20, pady=(20, 4))

        self._btn(frame, "💾  Enregistrer", self._save_config, ACCENT).pack(pady=12, padx=20, anchor="w")
        return frame

    def _save_config(self):
        try:
            self.config.save_settings({"interval_seconds": self._interval_var.get()})
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
        tk.Label(card, text=label, font=("Segoe UI", 8), fg=MUTED,
                 bg=PANEL).pack(anchor="w", padx=12, pady=(12, 0))
        lbl = tk.Label(card, text=value, font=("Segoe UI Semibold", 18),
                        fg=color, bg=PANEL)
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

    def _ask_dest_change(self, parent_win, old_db, old_prefix, new_db, new_prefix, pair_id, dst, db_changed):
        """
        Popup affichée quand la BDD ou le préfixe de table destination change.
        Retourne un dict {"version": int} ou None si annulé.
        """
        result = {"action": None, "version": dst.get("current_version", 1), "from_id": None}

        dlg = tk.Toplevel(parent_win)
        dlg.title("Changement de destination")
        dlg.geometry("480x400")
        dlg.minsize(440, 380)
        dlg.configure(bg=BG)
        dlg.grab_set()
        dlg.resizable(False, False)

        old_table = f"{old_prefix}{dst.get('current_version', 1)}"
        new_table = f"{new_prefix}{dst.get('current_version', 1)}"

        tk.Label(dlg, text="Changement de destination détecté",
                 font=FONT_BIG, fg=WARN, bg=BG).pack(pady=(20, 4))

        info_frame = tk.Frame(dlg, bg=PANEL)
        info_frame.pack(fill="x", padx=20, pady=8)
        tk.Label(info_frame, text=f"Ancien : {old_db} / {old_table}",
                 font=FONT_UI, fg=MUTED, bg=PANEL).pack(anchor="w", padx=12, pady=4)
        tk.Label(info_frame, text=f"Nouveau : {new_db} / {new_table}",
                 font=FONT_UI, fg=TEXT, bg=PANEL).pack(anchor="w", padx=12, pady=4)

        tk.Frame(dlg, bg=BORDER, height=1).pack(fill="x", padx=20, pady=8)

        # Option 1 : Renommer
        rename_frame = tk.Frame(dlg, bg=BG)
        rename_frame.pack(fill="x", padx=20, pady=4)
        tk.Label(rename_frame, text="↩  Renommer", font=FONT_H, fg=ACCENT, bg=BG).pack(anchor="w")
        tk.Label(rename_frame,
                 text=f"Renomme {old_prefix} → {new_prefix} (et la BDD si changée).\nGarde la version actuelle V{dst.get('current_version',1)}.",
                 font=("Segoe UI", 9), fg=MUTED, bg=BG, justify="left").pack(anchor="w", padx=12)

        def do_rename():
            try:
                from core.db_connector import DBConnector
                d = DBConnector(dst)
                d.connect()
                if db_changed:
                    d.rename_database(old_db, new_db)
                elif old_prefix != new_prefix:
                    d.rename_table(old_table, new_table)
                d.disconnect()
            except Exception as e:
                messagebox.showerror("Erreur renommage", str(e), parent=dlg)
                return
            result["action"] = "rename"
            result["version"] = dst.get("current_version", 1)
            dlg.destroy()

        self._btn(rename_frame, "Renommer", do_rename, ACCENT).pack(anchor="w", padx=12, pady=(4, 0))

        tk.Frame(dlg, bg=BORDER, height=1).pack(fill="x", padx=20, pady=8)

        # Option 2 : Nouvelle table
        new_frame = tk.Frame(dlg, bg=BG)
        new_frame.pack(fill="x", padx=20, pady=4)
        tk.Label(new_frame, text="✦  Nouvelle table", font=FONT_H, fg=ACCENT2, bg=BG).pack(anchor="w")
        tk.Label(new_frame, text="Crée une nouvelle table. L'ancienne est conservée.",
                 font=("Segoe UI", 9), fg=MUTED, bg=BG, justify="left").pack(anchor="w", padx=12)

        from_frame = tk.Frame(new_frame, bg=BG)
        from_frame.pack(fill="x", padx=12, pady=4)
        tk.Label(from_frame, text="À partir de l'ID :", font=FONT_UI, fg=TEXT,
                 bg=BG).pack(side="left")
        from_id_var = tk.StringVar(value="")
        tk.Entry(from_frame, textvariable=from_id_var, font=FONT_MONO,
                 bg=PANEL, fg=TEXT, insertbackground=TEXT, relief="flat",
                 highlightthickness=1, highlightcolor=ACCENT2,
                 highlightbackground=BORDER, width=12).pack(side="left", padx=8, ipady=4)
        tk.Label(from_frame, text="(vide = depuis le début)", font=("Segoe UI", 8),
                 fg=MUTED, bg=BG).pack(side="left")

        def do_new():
            raw = from_id_var.get().strip()
            fid = int(raw) if raw else None
            self.config.set_from_id(pair_id, fid)
            result["action"] = "new"
            result["version"] = 1
            dlg.destroy()

        self._btn(new_frame, "Créer nouvelle table", do_new, ACCENT2).pack(anchor="w", padx=12, pady=(4, 0))

        tk.Frame(dlg, bg=BORDER, height=1).pack(fill="x", padx=20, pady=8)

        # Annuler
        self._btn(dlg, "Annuler", dlg.destroy, BORDER).pack(pady=4)

        dlg.wait_window()

        if result["action"] is None:
            return None
        return result
