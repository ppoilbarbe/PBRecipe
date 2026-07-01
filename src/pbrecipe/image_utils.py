# SPDX-FileCopyrightText: Philippe Poilbarbe <philippe@cardolan.net>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Image scaling: resize to fit dimensions while preserving aspect ratio and alpha."""

from __future__ import annotations

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, Qt
from PySide6.QtGui import QImage

_MIME_TO_QT: dict[str, str] = {
    "image/jpeg": "JPEG",
    "image/png": "PNG",
    "image/gif": "GIF",
    "image/webp": "WEBP",
    "image/bmp": "BMP",
}


def scale_to_fit(
    data: bytes, max_w: int, max_h: int, mime_type: str = "image/jpeg"
) -> bytes:
    """Return bytes of the image scaled to fit within max_w × max_h.

    Returns original bytes unchanged if already within bounds or if encoding fails.
    Aspect ratio and alpha channel are preserved.
    """
    img = QImage()
    img.loadFromData(QByteArray(data))
    if img.isNull() or (img.width() <= max_w and img.height() <= max_h):
        return data

    target_fmt = (
        QImage.Format.Format_ARGB32
        if img.hasAlphaChannel()
        else QImage.Format.Format_RGB32
    )
    if img.format() != target_fmt:
        img = img.convertToFormat(target_fmt)

    scaled = img.scaled(
        max_w,
        max_h,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )

    qt_fmt = _MIME_TO_QT.get(mime_type, "PNG")
    buf = QBuffer()
    buf.open(QIODevice.OpenMode.WriteOnly)
    scaled.save(buf, qt_fmt)
    buf.close()
    result = bytes(buf.data())
    return result if result else data
