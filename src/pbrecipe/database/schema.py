from sqlalchemy import (
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

metadata = MetaData()

t_categories = Table(
    "categories",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("name", String(20), nullable=False),
)

t_units = Table(
    "units",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("name", String(15), nullable=False, default=""),
)

t_ingredients = Table(
    "ingredients",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("name", String(50), nullable=False),
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
    Column("code", String(10), primary_key=True),
    Column("title", String(40), nullable=False),
    Column("description", Text, nullable=False, default=""),
)

t_recipes = Table(
    "recipes",
    metadata,
    Column("code", String(50), primary_key=True),
    Column("name", String(200), nullable=False),
    Column("difficulty", SmallInteger, nullable=False, default=0),
    Column("serving", String(30), nullable=False, default=""),
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
        String(50),
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
        String(50),
        ForeignKey("recipes.code", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("position", Integer, nullable=False, default=0),
    Column("prefix", String(10), nullable=False, default=""),
    Column("quantity", String(10), nullable=False, default="1"),
    Column("unit_id", Integer, ForeignKey("units.id", ondelete="SET NULL")),
    Column("separator", String(20), nullable=False, default=""),
    Column("ingredient_id", Integer, ForeignKey("ingredients.id", ondelete="SET NULL")),
    Column("suffix", String(20), nullable=False, default=""),
)

t_recipe_media = Table(
    "recipe_media",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column(
        "recipe_code",
        String(50),
        ForeignKey("recipes.code", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("position", Integer, nullable=False, default=0),
    Column("code", String(20), nullable=False),  # référence dans [IMG:CODE]
    Column("mime_type", String(50), nullable=False, default="image/jpeg"),
    Column("data", LargeBinary, nullable=False),
)

t_difficulty_levels = Table(
    "difficulty_levels",
    metadata,
    Column("level", SmallInteger, primary_key=True, autoincrement=False),
    Column("label", String(50), nullable=False, default=""),
    Column("mime_type", String(50), nullable=False, default="image/jpeg"),
    Column("data", LargeBinary, nullable=True),  # icône bitmap, None si non définie
)
