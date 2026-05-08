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
MAX_TECHNIQUE_TITLE = 40

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

# shared
MAX_MIME_TYPE = 50  # recipe_media.mime_type, difficulty_levels.mime_type

# difficulty_levels
MAX_DIFFICULTY_LABEL = 50

# globals
MAX_GLOBAL_KEY = 50

# Business rules
MIN_DIFFICULTY = 0
MAX_DIFFICULTY = 3
MIN_TIME_MINUTES = 0
MAX_TIME_MINUTES = 9999

# Config fields (stored in YAML, not in DB)
MAX_SITE_TYPE = 40
