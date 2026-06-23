"""Runtime hook PyInstaller — fontconfig portable sur Linux.

Sur Linux, Qt utilise fontconfig pour trouver les polices. Le fonts.conf bundlé
par PyInstaller contient des chemins absolus vers l'environnement conda de la
machine de build (ex. /home/runner/…) qui n'existent pas sur la machine cible.

Ce hook s'exécute au démarrage du binaire frozen, avant l'init Qt. Il :
  1. Écrit un fonts.conf minimal dans sys._MEIPASS pointant vers les polices
     bundlées (fonts/) et les polices système (/usr/share/fonts).
  2. Positionne FONTCONFIG_FILE pour que fontconfig utilise ce fichier.
"""

import os
import sys

if sys.platform != "linux" or not getattr(sys, "frozen", False):
    pass
else:
    _meipass = sys._MEIPASS
    _fonts_dir = os.path.join(_meipass, "fonts")
    if os.path.isdir(_fonts_dir):
        _conf_path = os.path.join(_meipass, "fonts.conf")
        # Include the system fonts.conf so that all rendering settings
        # (anti-aliasing, hinting, subpixel, …) are inherited.  Only the
        # bundled fonts directory needs to be added explicitly; system font
        # directories and rendering rules come from the included system config.
        _conf = f"""<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd">
<fontconfig>
  <dir>{_fonts_dir}</dir>
  <include ignore_missing="yes">/etc/fonts/fonts.conf</include>
</fontconfig>
"""
        with open(_conf_path, "w", encoding="utf-8") as _f:
            _f.write(_conf)
        os.environ["FONTCONFIG_FILE"] = _conf_path

        # Force fontconfig to (re-)initialize with the new FONTCONFIG_FILE.
        # libfontconfig may have already been dlopen'd and self-initialized with
        # its compile-time defaults (hardcoded to the build machine's conda path)
        # before this hook ran.  FcFini() + FcInit() resets it so it re-reads
        # FONTCONFIG_FILE before Qt's QFontDatabase is populated.
        try:
            import ctypes

            _fc = ctypes.CDLL("libfontconfig.so.1")
            _fc.FcFini()
            _fc.FcInit()
        except OSError:
            pass
