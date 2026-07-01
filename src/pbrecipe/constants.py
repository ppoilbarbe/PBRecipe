# SPDX-FileCopyrightText: Philippe Poilbarbe <philippe@cardolan.net>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Field length limits (kept in sync with schema.py) and shared business rules."""

# DB field length limits — kept in sync with schema.py String() sizes.
# UI editors import these for setMaxLength() to guarantee consistency.

# categories
MAX_CATEGORY_NAME = 20

# units
MAX_UNIT_NAME = 15

# ingredients
MAX_INGREDIENT_NAME = 50

# techniques
MAX_TECHNIQUE_CODE = 10
MAX_TECHNIQUE_TITLE = 200

# recipes
MAX_RECIPE_CODE = 50
MAX_RECIPE_NAME = 200
MAX_RECIPE_SERVING = 30

# recipe_ingredients
MAX_INGREDIENT_PREFIX = 20
MAX_INGREDIENT_QUANTITY = 15
MAX_INGREDIENT_SEPARATOR = 30
MAX_INGREDIENT_SUFFIX = 30

# recipe_media
MAX_MEDIA_CODE = 20
MAX_MEDIA_BYTES = 16_777_215  # MEDIUMBLOB limit on MariaDB/MySQL

# shared
MAX_MIME_TYPE = 50  # recipe_media.mime_type, difficulty_levels.mime_type

# difficulty_levels
MAX_DIFFICULTY_LABEL = 50

# globals
MAX_GLOBAL_KEY = 50

# Business rules
MIN_DIFFICULTY = 0
MAX_DIFFICULTY = 6  # max level value ever storable
MIN_DIFFICULTY_COUNT = 3  # min number of useful levels (excluding level 0)
MAX_DIFFICULTY_COUNT = 6  # max number of useful levels (excluding level 0)
MIN_TIME_MINUTES = 0
MAX_TIME_MINUTES = 9999

# Default image size limits (stored in globals, configurable per-database)
DEFAULT_DIFF_IMG_MAX_W = 512
DEFAULT_DIFF_IMG_MAX_H = 512
DEFAULT_MEDIA_MAX_W = 3072
DEFAULT_MEDIA_MAX_H = 2048
DEFAULT_MEDIA_JPEG_QUALITY = 85

# Config fields (stored in YAML, not in DB)
MAX_SITE_TYPE = 40
