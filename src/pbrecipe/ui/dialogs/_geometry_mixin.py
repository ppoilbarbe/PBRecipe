"""Mixin for persisting dialog geometry (position + size) via AppConfig."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pbrecipe.config.app_config import AppConfig


class GeometryMixin:
    def _init_geometry(self, app_config: AppConfig | None, key: str) -> None:
        self._geo_app_config = app_config
        self._geo_key = key
        if app_config is None:
            return
        geom = app_config.dialog_geometries.get(key, {})
        if geom.get("width") and geom.get("height"):
            self.resize(int(geom["width"]), int(geom["height"]))
        if geom.get("x") is not None and geom.get("y") is not None:
            self.move(int(geom["x"]), int(geom["y"]))

    def done(self, result: int) -> None:
        cfg = getattr(self, "_geo_app_config", None)
        key = getattr(self, "_geo_key", None)
        if cfg is not None and key:
            pos = self.pos()
            size = self.size()
            cfg.dialog_geometries[key] = {
                "x": pos.x(),
                "y": pos.y(),
                "width": size.width(),
                "height": size.height(),
            }
            cfg.save()
        super().done(result)
