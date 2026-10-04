"""Tests du référentiel matériel : base, YAML, éditeur de recette et dialogue."""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtWidgets import QMessageBox, QTabWidget
from ruamel.yaml import YAML

from pbrecipe.config import RecipeConfig
from pbrecipe.database.database import Database
from pbrecipe.export.yaml_io import YamlExport, YamlImport
from pbrecipe.models import Category, Equipment, Recipe, RecipeEquipment
from pbrecipe.ui.dialogs.equipment_dialog import EquipmentDialog
from pbrecipe.ui.equipment_list_editor import EquipmentListEditor, EquipmentRow
from pbrecipe.ui.recipe_editor import RecipeEditor


@pytest.fixture
def db(tmp_path: Path):
    d = Database(f"sqlite:///{tmp_path / 'test.db'}")
    d.connect()
    d.create_schema()
    yield d
    d.disconnect()


def _seed(db):
    cat = db.save_category(Category(name="Dessert"))
    whisk = db.save_equipment(Equipment(name="Fouet", name_plural="Fouets"))
    pan = db.save_equipment(Equipment(name="Moule à manqué"))
    return cat, whisk, pan


def _rows(*specs) -> list[RecipeEquipment]:
    return [
        RecipeEquipment(position=i, prefix=p, equipment_id=e, suffix=s)
        for i, (p, e, s) in enumerate(specs)
    ]


# ===========================================================================
# Database
# ===========================================================================


def test_equipment_crud(db):
    eq = db.save_equipment(Equipment(name="Fouet", name_plural="Fouets"))
    assert eq.id is not None
    db.save_equipment(Equipment(name="économe"))
    # Tri insensible à la casse et aux accents
    assert [e.name for e in db.list_equipment()] == ["économe", "Fouet"]
    eq.name = "Fouet électrique"
    eq.name_plural = "Fouets électriques"
    db.save_equipment(eq)
    saved = next(e for e in db.list_equipment() if e.id == eq.id)
    assert (saved.name, saved.name_plural) == ("Fouet électrique", "Fouets électriques")
    db.delete_equipment(eq.id)
    assert [e.name for e in db.list_equipment()] == ["économe"]


def test_recipe_equipment_roundtrip(db):
    cat, whisk, pan = _seed(db)
    rows = _rows(("1", pan.id, "de 24 cm"), ("2", whisk.id, ""))
    rows[1].equipment_plural = True
    db.save_recipe(Recipe(code="R", name="R", categories=[cat.id], equipment=rows))
    loaded = db.get_recipe("R").equipment
    assert [(r.position, r.prefix, r.equipment_id, r.suffix) for r in loaded] == [
        (0, "1", pan.id, "de 24 cm"),
        (1, "2", whisk.id, ""),
    ]
    assert [r.equipment_plural for r in loaded] == [False, True]
    assert all(r.id is not None and r.recipe_code == "R" for r in loaded)

    recipe = db.get_recipe("R")
    recipe.equipment = recipe.equipment[1:]
    db.save_recipe(recipe)
    assert [r.equipment_id for r in db.get_recipe("R").equipment] == [whisk.id]


def test_recipe_equipment_follows_code_rename(db):
    cat, whisk, _pan = _seed(db)
    db.save_recipe(
        Recipe(
            code="OLD",
            name="R",
            categories=[cat.id],
            equipment=_rows(("", whisk.id, "")),
        )
    )
    recipe = db.get_recipe("OLD")
    recipe.code = "NEW"
    db.save_recipe(recipe, original_code="OLD")
    assert [r.equipment_id for r in db.get_recipe("NEW").equipment] == [whisk.id]


def test_delete_equipment_keeps_row_without_reference(db):
    """Comme pour les ingrédients : la ligne reste, sans matériel (SET NULL)."""
    cat, whisk, pan = _seed(db)
    db.save_recipe(
        Recipe(
            code="R",
            name="R",
            categories=[cat.id],
            equipment=_rows(("1", whisk.id, "x"), ("", pan.id, "")),
        )
    )
    db.delete_equipment(whisk.id)
    rows = db.get_recipe("R").equipment
    assert [(r.prefix, r.equipment_id, r.suffix) for r in rows] == [
        ("1", None, "x"),
        ("", pan.id, ""),
    ]


def test_delete_recipe_cascades_equipment_rows(db):
    cat, whisk, _pan = _seed(db)
    db.save_recipe(
        Recipe(
            code="R", name="R", categories=[cat.id], equipment=_rows(("", whisk.id, ""))
        )
    )
    db.delete_recipe("R")
    with db._tx() as conn:
        assert (
            conn.exec_driver_sql("SELECT COUNT(*) FROM recipe_equipment").scalar() == 0
        )
    # Le matériel lui-même reste connu
    assert whisk.id in [e.id for e in db.list_equipment()]


def test_search_recipes_by_equipment(db):
    cat, whisk, pan = _seed(db)
    db.save_recipe(
        Recipe(
            code="A", name="A", categories=[cat.id], equipment=_rows(("", whisk.id, ""))
        )
    )
    db.save_recipe(
        Recipe(
            code="B", name="B", categories=[cat.id], equipment=_rows(("", pan.id, ""))
        )
    )
    assert [r.code for r in db.search_recipes(equipment_id=pan.id)] == ["B"]


def test_clear_all_data_clears_equipment(db):
    cat, whisk, _pan = _seed(db)
    db.save_recipe(
        Recipe(
            code="R", name="R", categories=[cat.id], equipment=_rows(("", whisk.id, ""))
        )
    )
    db.clear_all_data()
    assert db.list_equipment() == []


def test_schema_without_equipment_tables_is_upgraded(tmp_path):
    """Une base antérieure (sans tables matériel) reste reconnue puis complétée."""
    path = tmp_path / "old.db"
    d = Database(f"sqlite:///{path}")
    d.connect()
    d.create_schema()
    with d._tx() as conn:
        conn.exec_driver_sql("DROP TABLE recipe_equipment")
        conn.exec_driver_sql("DROP TABLE equipment")
    assert d.check_schema() == "ok"
    d.create_schema()
    d.save_equipment(Equipment(name="Fouet"))
    assert len(d.list_equipment()) == 1
    d.disconnect()


def test_incompatible_schema_is_refused(first_version_db):
    from pbrecipe.database import SchemaMismatchError

    db_path, _ = first_version_db
    d = Database(f"sqlite:///{db_path}")
    d.connect()
    with pytest.raises(SchemaMismatchError) as info:
        d.create_schema()
    missing = info.value.missing
    assert "equipment.name_plural" in missing
    assert {"recipe_equipment.id", "recipe_equipment.prefix"} <= set(missing)
    assert "recipe_equipment.position" not in missing
    assert "equipment.name_plural" in str(info.value)
    assert d.missing_columns() == missing
    d.disconnect()


def test_current_schema_has_no_missing_columns(db):
    assert db.missing_columns() == []


# ===========================================================================
# YAML
# ===========================================================================


def test_yaml_roundtrip_equipment(db, tmp_path):
    cat, whisk, pan = _seed(db)
    rows = _rows(("1", pan.id, "de 24 cm"), ("2", whisk.id, ""))
    rows[1].equipment_plural = True
    db.save_recipe(Recipe(code="R", name="R", categories=[cat.id], equipment=rows))
    out = tmp_path / "export.yaml"
    YamlExport(db).run(str(out))
    doc = YAML().load(out.read_text(encoding="utf-8"))
    assert doc["equipment"] == [
        {"name": "Fouet", "name_plural": "Fouets"},
        {"name": "Moule à manqué", "name_plural": ""},
    ]
    assert doc["recipes"][0]["equipment"][1] == {
        "position": 1,
        "prefix": "2",
        "equipment": "Fouet",
        "equipment_plural": True,
        "suffix": "",
    }

    db2 = Database(f"sqlite:///{tmp_path / 'dest.db'}")
    db2.connect()
    db2.create_schema()
    stats = YamlImport(db2).run(str(out))
    assert stats["equipment"] == 2
    by_id = {e.id: e for e in db2.list_equipment()}
    loaded = db2.get_recipe("R").equipment
    assert [(r.prefix, by_id[r.equipment_id].name, r.suffix) for r in loaded] == [
        ("1", "Moule à manqué", "de 24 cm"),
        ("2", "Fouet", ""),
    ]
    assert loaded[1].equipment_plural is True
    assert by_id[loaded[1].equipment_id].name_plural == "Fouets"
    db2.disconnect()


def _write_yaml(path: Path, doc: dict) -> None:
    yaml = YAML()
    with open(path, "w", encoding="utf-8") as fh:
        yaml.dump(doc, fh)


def test_yaml_import_equipment_plural_update_and_on_the_fly(db, tmp_path):
    db.save_equipment(Equipment(name="Fouet"))
    path = tmp_path / "in.yaml"
    _write_yaml(
        path,
        {
            "equipment": [{"name": "Fouet", "name_plural": "Fouets"}],
            "recipes": [
                {
                    "code": "R",
                    "name": "R",
                    "categories": ["Plat"],
                    "equipment": [
                        {"equipment": "Cocotte", "prefix": "1"},
                        {"prefix": "du papier sulfurisé"},  # ligne sans matériel
                        "invalide",
                    ],
                }
            ],
        },
    )
    YamlImport(db).run(str(path))
    by_name = {e.name: e for e in db.list_equipment()}
    assert by_name["Fouet"].name_plural == "Fouets"  # mis à jour
    assert "Cocotte" in by_name  # créé à la volée
    rows = db.get_recipe("R").equipment
    assert [(r.prefix, r.equipment_id) for r in rows] == [
        ("1", by_name["Cocotte"].id),
        ("du papier sulfurisé", None),
    ]


def test_yaml_import_without_equipment_key(db, tmp_path):
    """Un export antérieur (sans clé equipment) s'importe sans erreur."""
    path = tmp_path / "in.yaml"
    _write_yaml(path, {"recipes": [{"code": "R", "name": "R", "categories": ["P"]}]})
    YamlImport(db).run(str(path))
    assert db.get_recipe("R").equipment == []


# ===========================================================================
# EquipmentRow / EquipmentListEditor
# ===========================================================================


def test_equipment_row_get_data(qtbot, db):
    _cat, whisk, _pan = _seed(db)
    row = EquipmentRow(
        RecipeEquipment(
            id=7, prefix="2", equipment_id=whisk.id, suffix="", equipment_plural=True
        ),
        db.list_equipment(),
    )
    qtbot.addWidget(row)
    data = row.get_data("REC", 3)
    assert (data.id, data.recipe_code, data.position) == (7, "REC", 3)
    assert (data.prefix, data.equipment_id, data.equipment_plural) == (
        "2",
        whisk.id,
        True,
    )


def test_equipment_editor_load_insert_remove(qtbot, db):
    _cat, whisk, pan = _seed(db)
    editor = EquipmentListEditor()
    qtbot.addWidget(editor)
    editor.load([], db)
    assert not editor._empty_btn.isHidden()
    changes = []
    editor.changed.connect(lambda: changes.append(1))
    editor._insert_at(0)
    assert editor._empty_btn.isHidden()
    assert editor.get_equipment("R")[0].equipment_id is None
    editor._remove_row(editor._rows[0])
    assert editor._rows == []
    assert len(changes) == 2

    editor.load(_rows(("1", pan.id, ""), ("", whisk.id, "")), db)
    editor._move_row_to(editor._rows[0], 1)
    assert [r.equipment_id for r in editor.get_equipment("R")] == [whisk.id, pan.id]
    assert [r.position for r in editor.get_equipment("R")] == [0, 1]


def test_equipment_editor_reload_keeps_selection(qtbot, db):
    _cat, whisk, _pan = _seed(db)
    editor = EquipmentListEditor()
    qtbot.addWidget(editor)
    editor.load(_rows(("", whisk.id, "")), db)
    db.save_equipment(Equipment(name="Saladier"))
    editor.reload(db)
    combo = editor._rows[0]._equipment
    assert combo.count() == 4  # aucun + 3
    assert combo.currentData() == whisk.id


def test_recipe_editor_tab_order_and_save(qtbot, db):
    cat, whisk, pan = _seed(db)
    editor = RecipeEditor()
    qtbot.addWidget(editor)
    tabs = editor.findChild(QTabWidget)
    labels = [tabs.tabText(i) for i in range(tabs.count())]
    assert labels.index("Matériel") == labels.index("Ingrédients") + 1
    assert labels.index("Réalisation") == labels.index("Matériel") + 1

    recipe = Recipe(
        code="R", name="R", categories=[cat.id], equipment=_rows(("", pan.id, ""))
    )
    editor.load(recipe, db, RecipeConfig())
    assert editor.has_unsaved_changes() is False
    editor._equipment_editor._rows[0]._suffix.setText("de 24 cm")
    assert editor.has_unsaved_changes() is True

    saved = []
    editor.saved.connect(saved.append)
    editor._save()
    (row,) = saved[0].equipment
    assert (row.recipe_code, row.equipment_id, row.suffix) == ("R", pan.id, "de 24 cm")


# ===========================================================================
# EquipmentDialog
# ===========================================================================


def test_equipment_dialog_add_edit_delete(qtbot, db, monkeypatch):
    dlg = EquipmentDialog(db)
    qtbot.addWidget(dlg)
    assert dlg.windowTitle() == "Matériel"
    target = "pbrecipe.ui.dialogs._plural_list_dialog.plural_name_dialog"

    monkeypatch.setattr(target, lambda *a, **k: ("Fouet", "Fouets", True))
    dlg._add()
    assert [(e.name, e.name_plural) for e in db.list_equipment()] == [
        ("Fouet", "Fouets")
    ]
    assert dlg._list.item(0).text() == "Fouet / Fouets"

    dlg._list.setCurrentRow(0)
    monkeypatch.setattr(target, lambda *a, **k: ("Batteur", "", True))
    dlg._edit()
    assert [(e.name, e.name_plural) for e in db.list_equipment()] == [("Batteur", "")]
    assert dlg._list.item(0).text() == "Batteur"

    monkeypatch.setattr(
        QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes
    )
    dlg._list.setCurrentRow(0)
    dlg._delete()
    assert db.list_equipment() == []
