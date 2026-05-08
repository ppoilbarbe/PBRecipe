from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Integer,
    LargeBinary,
    MetaData,
    SmallInteger,
    String,
    Table,
    Text,
)

from pbrecipe.constants import (
    MAX_CATEGORY_NAME,
    MAX_DIFFICULTY_LABEL,
    MAX_GLOBAL_KEY,
    MAX_INGREDIENT_NAME,
    MAX_INGREDIENT_PREFIX,
    MAX_INGREDIENT_QUANTITY,
    MAX_INGREDIENT_SEPARATOR,
    MAX_INGREDIENT_SUFFIX,
    MAX_MEDIA_CODE,
    MAX_MIME_TYPE,
    MAX_RECIPE_CODE,
    MAX_RECIPE_NAME,
    MAX_RECIPE_SERVING,
    MAX_TECHNIQUE_CODE,
    MAX_TECHNIQUE_TITLE,
    MAX_UNIT_NAME,
)

metadata = MetaData()

t_categories = Table(
    "categories",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("name", String(MAX_CATEGORY_NAME), nullable=False),
)

t_units = Table(
    "units",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("name", String(MAX_UNIT_NAME), nullable=False, default=""),
    Column("name_plural", String(MAX_UNIT_NAME), nullable=False, default=""),
)

t_ingredients = Table(
    "ingredients",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("name", String(MAX_INGREDIENT_NAME), nullable=False),
    Column("name_plural", String(MAX_INGREDIENT_NAME), nullable=False, default=""),
)

t_sources = Table(
    "sources",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("name", Text, nullable=False),
)

t_techniques = Table(
    "techniques",
    metadata,
    Column("code", String(MAX_TECHNIQUE_CODE), primary_key=True),
    Column("title", String(MAX_TECHNIQUE_TITLE), nullable=False),
    Column("description", Text, nullable=False, default=""),
)

t_recipes = Table(
    "recipes",
    metadata,
    Column("code", String(MAX_RECIPE_CODE), primary_key=True),
    Column("name", String(MAX_RECIPE_NAME), nullable=False),
    Column("difficulty", SmallInteger, nullable=False, default=0),
    Column("serving", String(MAX_RECIPE_SERVING), nullable=False, default=""),
    Column("prep_time", Integer),
    Column("wait_time", Integer),
    Column("cook_time", Integer),
    Column("description", Text, nullable=False, default=""),
    Column("comments", Text, nullable=False, default=""),
    Column("source_id", Integer, ForeignKey("sources.id", ondelete="SET NULL")),
)

t_recipe_categories = Table(
    "recipe_categories",
    metadata,
    Column(
        "recipe_code",
        String(MAX_RECIPE_CODE),
        ForeignKey("recipes.code", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "category_id",
        Integer,
        ForeignKey("categories.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

t_recipe_ingredients = Table(
    "recipe_ingredients",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column(
        "recipe_code",
        String(MAX_RECIPE_CODE),
        ForeignKey("recipes.code", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("position", Integer, nullable=False, default=0),
    Column("prefix", String(MAX_INGREDIENT_PREFIX), nullable=False, default=""),
    Column("quantity", String(MAX_INGREDIENT_QUANTITY), nullable=False, default="1"),
    Column("unit_id", Integer, ForeignKey("units.id", ondelete="SET NULL")),
    Column("separator", String(MAX_INGREDIENT_SEPARATOR), nullable=False, default=""),
    Column("ingredient_id", Integer, ForeignKey("ingredients.id", ondelete="SET NULL")),
    Column("suffix", String(MAX_INGREDIENT_SUFFIX), nullable=False, default=""),
    Column("unit_plural", Boolean, nullable=False, default=False),
    Column("ingredient_plural", Boolean, nullable=False, default=False),
)

t_recipe_media = Table(
    "recipe_media",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column(
        "recipe_code",
        String(MAX_RECIPE_CODE),
        ForeignKey("recipes.code", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("position", Integer, nullable=False, default=0),
    Column(
        "code", String(MAX_MEDIA_CODE), nullable=False
    ),  # référence dans [IMG:RECIPE:CODE]
    Column("mime_type", String(MAX_MIME_TYPE), nullable=False, default="image/jpeg"),
    Column("data", LargeBinary, nullable=False),
)

t_difficulty_levels = Table(
    "difficulty_levels",
    metadata,
    Column("level", SmallInteger, primary_key=True, autoincrement=False),
    Column("label", String(MAX_DIFFICULTY_LABEL), nullable=False, default=""),
    Column("mime_type", String(MAX_MIME_TYPE), nullable=False, default="image/jpeg"),
    Column("data", LargeBinary, nullable=True),  # icône bitmap, None si non définie
)

t_globals = Table(
    "globals",
    metadata,
    Column("key", String(MAX_GLOBAL_KEY), primary_key=True),
    Column("value", Text, nullable=False, default=""),
)
