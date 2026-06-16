# MySQLSync

Outil de synchronisation one-way entre deux bases MySQL,
avec détection automatique de changement de schéma.

---

## Installation

```bash
pip install -r requirements.txt
```

## Lancement (développement)

```bash
python main.py
```

## Packaging en .exe

```bash
pip install pyinstaller
pyinstaller build.spec
```
L'exécutable sera dans `dist/MySQLSync.exe`.

## Démarrage automatique Windows

```bash
# Enregistrer
python install_startup.py

# Désinstaller
python install_startup.py --uninstall
```

---

## Logique de versionnement de table

Le moteur compare à chaque cycle le **schéma de la table source**
(colonnes + types via `INFORMATION_SCHEMA`) avec la signature mise en cache
dans `schema_cache.json`.

- **Aucun changement** → sync normale vers `<prefix>V<N>`
- **Changement détecté** → `current_version` s'incrémente automatiquement,
  une nouvelle table `<prefix>V<N+1>` est créée, la synchronisation repart de zéro.

La version peut aussi être modifiée manuellement depuis l'onglet **Configuration**.

---

## Structure des fichiers

```
mysqlsync/
├── main.py                  # Point d'entrée + systray
├── config.json              # Configuration (auto-généré)
├── schema_cache.json        # Signature de schéma (auto-généré)
├── requirements.txt
├── build.spec               # PyInstaller
├── install_startup.py       # Démarrage Windows
├── core/
│   ├── config_manager.py
│   ├── db_connector.py
│   ├── schema_manager.py
│   └── sync_engine.py
└── ui/
    └── supervision_window.py
```
