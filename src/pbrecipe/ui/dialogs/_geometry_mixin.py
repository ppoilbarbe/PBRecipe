"""Mixin for persisting dialog geometry (position + size) via AppConfig."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


class GeometryMixin:
    def _init_geometry(self, key: str) -> None:
        """Restaure la géométrie depuis le fichier de config."""
        self._geo_key = key
        from pbrecipe.config.app_config import AppConfig

        geom = AppConfig.load().dialog_geometries.get(key, {})
        if geom.get("width") and geom.get("height"):
            self.resize(int(geom["width"]), int(geom["height"]))
        if geom.get("x") is not None and geom.get("y") is not None:
            self.move(int(geom["x"]), int(geom["y"]))

    def _save_geometry(self) -> None:
        key = getattr(self, "_geo_key", None)
        if not key:
            return
        # Recharger depuis le disque pour ne pas écraser d'autres valeurs
        # sauvegardées entretemps (autres dialogues, fichiers récents…).
        from pbrecipe.config.app_config import AppConfig

        cfg = AppConfig.load()
        pos = self.pos()
        size = self.size()
        cfg.dialog_geometries[key] = {
            "x": pos.x(),
            "y": pos.y(),
            "width": size.width(),
            "height": size.height(),
        }
        cfg.save()

    def closeEvent(self, event) -> None:
        self._save_geometry()
        super().closeEvent(event)

    def done(self, result: int) -> None:
        self._save_geometry()
        super().done(result)
