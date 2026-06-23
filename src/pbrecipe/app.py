from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from pbrecipe.argparse_qt import add_qt_arguments

_log = logging.getLogger(__name__)

_LEVEL_MAP: dict[str, int] = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
}


def apply_log_level(level: int) -> None:
    """Apply level and matching format to the root logger immediately."""
    fmt = (
        "%(asctime)s %(levelname)-8s %(name)s: %(message)s"
        if level == logging.DEBUG
        else "%(levelname)s: %(message)s"
    )
    root = logging.getLogger()
    root.setLevel(level)
    if root.handlers:
        formatter = logging.Formatter(fmt)
        for handler in root.handlers:
            handler.setLevel(level)
            handler.setFormatter(formatter)
    else:
        logging.basicConfig(level=level, format=fmt)


def _load_bundled_fonts(app: object) -> None:
    """Register bundled fonts into Qt's font database (frozen builds only).

    In a PyInstaller onefile build, fontconfig uses paths hardcoded at build
    time that don't exist on the target machine.  QFontDatabase.addApplicationFont
    bypasses fontconfig entirely and guarantees that the bundled fonts (Ubuntu,
    DejaVu, …) are available regardless of the host fontconfig configuration.
    """
    if not getattr(sys, "frozen", False):
        return
    from PySide6.QtGui import QFont, QFontDatabase

    fonts_dir = Path(sys._MEIPASS) / "fonts"  # type: ignore[attr-defined]
    if not fonts_dir.is_dir():
        return

    loaded: set[str] = set()
    for ttf in sorted(fonts_dir.glob("*.ttf")):
        fid = QFontDatabase.addApplicationFont(str(ttf))
        if fid >= 0:
            loaded.update(QFontDatabase.applicationFontFamilies(fid))

    # If the desktop system font (from fontconfig/GTK theme) is not available
    # in the bundle, fall back to Ubuntu which ships with fonts-conda-ecosystem.
    if "Ubuntu" in loaded:
        current = app.font()  # type: ignore[union-attr]
        desired = QFont(
            "Ubuntu", current.pointSize() if current.pointSize() > 0 else 10
        )
        app.setFont(desired)


def main() -> None:
    # Pre-parse --config-dir avant AppConfig.load() pour rediriger la config
    # (option développement : évite d'écraser ~/.config/pbrecipe/).
    _pre = argparse.ArgumentParser(add_help=False)
    _pre.add_argument("--config-dir", dest="config_dir")
    _pre_args, _ = _pre.parse_known_args()
    if _pre_args.config_dir:
        from pbrecipe.config._config_root import set_config_dir

        set_config_dir(Path(_pre_args.config_dir))

    from pbrecipe.config import AppConfig

    app_config = AppConfig.load()
    default_level = _LEVEL_MAP.get(app_config.log_level, logging.INFO)

    parser = argparse.ArgumentParser(description="PBRecipe — gestionnaire de recettes")
    parser.add_argument(
        "config",
        nargs="?",
        metavar="FICHIER",
        help="Fichier de configuration YAML à ouvrir",
    )
    parser.add_argument(
        "--config-dir",
        metavar="RÉPERTOIRE",
        dest="config_dir",
        help=(
            "Répertoire de configuration à utiliser à la place de"
            " $XDG_CONFIG_HOME/pbrecipe. Utile en développement pour ne pas"
            " écraser la configuration réelle."
        ),
    )
    parser.add_argument(
        "--export-php",
        nargs="?",
        const="",
        metavar="RÉPERTOIRE",
        dest="export_php",
        help=(
            "Exporter les fichiers PHP sans ouvrir l'interface graphique. "
            "Si RÉPERTOIRE est omis, utilise le répertoire défini"
            " dans la configuration."
        ),
    )
    parser.add_argument(
        "--export-yaml",
        nargs="?",
        const="",
        metavar="FICHIER",
        dest="export_yaml",
        help=(
            "Exporter la base en YAML sans ouvrir l'interface graphique. "
            "Si FICHIER est omis, utilise le répertoire défini"
            " dans la configuration (nom de fichier généré automatiquement)."
        ),
    )
    parser.add_argument(
        "--check-connect",
        action="store_true",
        dest="check_connect",
        help=(
            "Tester la connexion définie dans le fichier YAML"
            " (affiche le détail de chaque étape, puis quitte)."
        ),
    )

    log_group = parser.add_mutually_exclusive_group()
    log_group.add_argument(
        "--debug",
        action="store_const",
        dest="log_level",
        const=logging.DEBUG,
        help="Afficher les messages de débogage",
    )
    log_group.add_argument(
        "--verbose",
        action="store_const",
        dest="log_level",
        const=logging.INFO,
        help="Afficher les messages d'information",
    )
    log_group.add_argument(
        "--quiet",
        action="store_const",
        dest="log_level",
        const=logging.WARNING,
        help="N'afficher que les avertissements et erreurs",
    )
    parser.set_defaults(log_level=default_level)
    add_qt_arguments(parser)

    args = parser.parse_args()
    apply_log_level(args.log_level)

    if args.check_connect:
        _check_connect(args.config)
        return

    if args.export_php is not None:
        _headless_export(args.config, args.export_php)
        return

    if args.export_yaml is not None:
        _headless_export_yaml(args.config, args.export_yaml)
        return

    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication

    from pbrecipe.ui.main_window import MainWindow

    app = QApplication([sys.argv[0]] + args.qt_args)
    _load_bundled_fonts(app)
    app.setApplicationName("PBRecipe")
    app.setOrganizationName("Cardolan")
    _icon = Path(__file__).parent / "resources" / "icons" / "pbrecipe-128x128.png"
    app.setWindowIcon(QIcon(str(_icon)))

    window = MainWindow(initial_path=args.config, app_config=app_config)
    window.show()
    sys.exit(app.exec())


def _check_connect(config_path: str | None) -> None:
    from pbrecipe.config import AppConfig, RecipeConfig
    from pbrecipe.database import create_database

    ok = "[OK]"
    ko = "[ERREUR]"

    # --- Étape 1 : résolution du fichier de configuration ---
    if config_path:
        yaml_path = Path(config_path).expanduser()
    else:
        app_config = AppConfig.load()
        last = app_config.last_file
        if not last:
            print(
                f"{ko} Aucun fichier de configuration spécifié"
                " et aucun fichier récent trouvé."
            )
            sys.exit(1)
        yaml_path = Path(last).expanduser()
        print(f"      Dernier fichier utilisé : {yaml_path}")

    print(f"      Fichier de configuration : {yaml_path}")
    if not yaml_path.exists():
        print(f"{ko} Fichier introuvable : {yaml_path}")
        sys.exit(1)
    print(f"{ok} Fichier trouvé")

    # --- Étape 2 : chargement de la configuration ---
    try:
        config = RecipeConfig.from_file(yaml_path)
    except Exception as exc:  # noqa: BLE001
        print(f"{ko} Impossible de lire la configuration : {exc}")
        sys.exit(1)
    print(f"{ok} Configuration chargée (base : {config.name!r})")

    # --- Étape 3 : paramètres de connexion ---
    db_cfg = config.db
    print(f"      Type        : {db_cfg.type}")
    if db_cfg.type == "sqlite":
        resolved = Path(db_cfg.path).expanduser().resolve()
        print(f"      Fichier     : {resolved}")
        if not resolved.exists():
            print(
                "      (le fichier n'existe pas encore"
                " — il sera créé à la première ouverture)"
            )
    else:
        print(f"      Hôte        : {db_cfg.host}:{db_cfg.port}")
        print(f"      Base        : {db_cfg.database}")
        print(f"      Utilisateur : {db_cfg.user or '(aucun)'}")
        print(f"      Mot de passe: {'(défini)' if db_cfg.password else '(vide)'}")

    # --- Étape 4 : construction de l'URL ---
    try:
        db = create_database(config)
    except ValueError as exc:
        print(f"{ko} Type de base non supporté : {exc}")
        sys.exit(1)
    print(f"{ok} URL de connexion construite")

    # --- Étape 5 : connexion ---
    try:
        db.connect()
    except Exception as exc:  # noqa: BLE001
        print(f"{ko} Connexion échouée : {exc}")
        sys.exit(1)
    print(f"{ok} Connexion établie")

    # --- Étape 6 : état du schéma ---
    try:
        status = db.check_schema()
    except Exception as exc:  # noqa: BLE001
        print(f"{ko} Vérification du schéma échouée : {exc}")
        sys.exit(1)
    finally:
        db.disconnect()

    schema_labels = {
        "empty": "base vide (aucune table)",
        "ok": "schéma valide",
        "foreign": "tables présentes mais schéma incompatible",
    }
    print(f"{ok} Schéma : {schema_labels.get(status, status)}")
    print(f"{ok} Connexion opérationnelle.")


def _headless_export_yaml(config_path: str | None, export_file: str) -> None:
    from pbrecipe.config import AppConfig, RecipeConfig
    from pbrecipe.database import create_database
    from pbrecipe.export.yaml_io import YamlExport

    if config_path:
        yaml_path = Path(config_path).expanduser()
    else:
        app_config = AppConfig.load()
        last = app_config.last_file
        if not last:
            _log.error(
                "Aucun fichier de configuration spécifié"
                " et aucun fichier récent trouvé."
            )
            sys.exit(1)
        yaml_path = Path(last).expanduser()
        _log.debug("Utilisation du dernier fichier : %s", yaml_path)

    if not yaml_path.exists():
        _log.error("Fichier de configuration introuvable : %s", yaml_path)
        sys.exit(1)

    try:
        config = RecipeConfig.from_file(yaml_path)
        _log.debug("Configuration chargée : %s", yaml_path)
    except Exception as exc:  # noqa: BLE001
        _log.error("Impossible de lire la configuration : %s", exc)
        sys.exit(1)

    if export_file:
        target = Path(export_file).expanduser()
        if not target.suffix:
            target = target.with_suffix(".yaml")
    elif config.yaml_export_dir:
        export_dir = Path(config.yaml_export_dir).expanduser()
        target = export_dir / f"{yaml_path.stem}.yaml"
        _log.debug("Répertoire d'export depuis la configuration : %s", export_dir)
    else:
        _log.error(
            "Aucun fichier d'export spécifié et aucun répertoire défini"
            " dans la configuration. Utilisez --export-yaml=FICHIER"
            " ou définissez le répertoire dans les paramètres de la base."
        )
        sys.exit(1)

    db = create_database(config)
    try:
        db.connect()
        _log.info("Export YAML vers %s…", target)
        YamlExport(db).run(str(target))
        _log.info("Export YAML terminé → %s", target)
    except Exception as exc:  # noqa: BLE001
        _log.error("Erreur lors de l'export YAML : %s", exc)
        sys.exit(1)
    finally:
        db.disconnect()


def _headless_export(config_path: str | None, export_dir: str) -> None:
    from pbrecipe.config import AppConfig, RecipeConfig
    from pbrecipe.database import create_database
    from pbrecipe.export.php_export import PhpExport

    app_config = AppConfig.load()

    # Résolution du fichier de configuration
    if config_path:
        yaml_path = Path(config_path).expanduser()
    else:
        last = app_config.last_file
        if not last:
            _log.error(
                "Aucun fichier de configuration spécifié"
                " et aucun fichier récent trouvé."
            )
            sys.exit(1)
        yaml_path = Path(last).expanduser()
        _log.debug("Utilisation du dernier fichier : %s", yaml_path)

    if not yaml_path.exists():
        _log.error("Fichier de configuration introuvable : %s", yaml_path)
        sys.exit(1)

    try:
        config = RecipeConfig.from_file(yaml_path)
        _log.debug("Configuration chargée : %s", yaml_path)
    except Exception as exc:  # noqa: BLE001
        _log.error("Impossible de lire la configuration : %s", exc)
        sys.exit(1)

    # Résolution du répertoire d'export
    if export_dir:
        target = Path(export_dir).expanduser()
    elif config.php_export_dir:
        target = Path(config.php_export_dir).expanduser()
        _log.debug("Répertoire d'export depuis la configuration : %s", target)
    else:
        _log.error(
            "Aucun répertoire d'export spécifié et aucun répertoire défini"
            " dans la configuration. Utilisez --export-php=RÉPERTOIRE"
            " ou définissez le répertoire dans les paramètres de la base."
        )
        sys.exit(1)

    db = create_database(config)
    try:
        db.connect()
        _log.info("Export PHP vers %s…", target)
        exporter = PhpExport(config, db, target, php_debug=app_config.php_debug)
        exporter.run()
        _log.info("Export PHP terminé → %s", target)
    except Exception as exc:  # noqa: BLE001
        _log.error("Erreur lors de l'export PHP : %s", exc)
        sys.exit(1)
    finally:
        db.disconnect()
