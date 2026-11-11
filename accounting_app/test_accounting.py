"""
Модульні та інтеграційні тести для системи складського обліку товарів.
"""

import os
import tempfile
import pytest

from accounting_app.models import Product
from accounting_app.repository import (
    CSVProductRepository,
    StorageError,
    StorageFormatError,
)
from accounting_app.validator import ProductValidator


# =============================================================================
# Тести моделі Product
# =============================================================================

def test_product_creation_and_attributes():
    prod = Product(
        id="PRD-001",
        name="Папір А4",
        category="Канцтовари",
        quantity=25,
        price=180.50,
        location="Склад 1",
    )
    assert prod.id == "PRD-001"
    assert prod.name == "Папір А4"
    assert prod.category == "Канцтовари"
    assert prod.quantity == 25
    assert prod.price == 180.50
    assert prod.location == "Склад 1"
    assert prod.total_value() == 25 * 180.50
    assert prod.created_at != ""


def test_product_serialization():
    prod = Product(
        id="PRD-002",
        name="Ручка",
        category="Канцтовари",
        quantity=10,
        price=15.0,
        location="Стелаж 2",
        created_at="2026-11-11 10:00:00",
    )
    data = prod.to_dict()
    assert data["id"] == "PRD-002"
    assert data["name"] == "Ручка"
    assert data["quantity"] == "10"
    assert data["price"] == "15.00"

    # Десеріалізація
    restored = Product.from_dict(data)
    assert restored.id == prod.id
    assert restored.name == prod.name
    assert restored.quantity == 10
    assert restored.price == 15.0


def test_product_from_dict_with_commas_and_spaces():
    raw_data = {
        "id": " PRD-003 ",
        "name": " Олівець ",
        "category": " Канцтовари ",
        "quantity": " 5 ",
        "price": " 12,75 ",
        "location": " Полиця 1 ",
        "created_at": "2026-11-11 12:00:00",
    }
    prod = Product.from_dict(raw_data)
    assert prod.id == "PRD-003"
    assert prod.price == 12.75
    assert prod.quantity == 5


def test_product_invalid_data_raises():
    with pytest.raises(ValueError):
        Product.from_dict({"id": "", "name": "Тест", "category": "Кат", "quantity": "1", "price": "10"})

    with pytest.raises(ValueError):
        Product.from_dict({"id": "1", "name": "", "category": "Кат", "quantity": "1", "price": "10"})

    with pytest.raises(ValueError):
        Product.from_dict({"id": "1", "name": "Тест", "category": "Кат", "quantity": "-5", "price": "10"})

    with pytest.raises(ValueError):
        Product.from_dict({"id": "1", "name": "Тест", "category": "Кат", "quantity": "abc", "price": "10"})


# =============================================================================
# Тести репозиторію CSVProductRepository
# =============================================================================

@pytest.fixture
def empty_repo():
    return CSVProductRepository()


def test_repo_crud_operations(empty_repo):
    repo = empty_repo
    assert len(repo.get_all()) == 0

    p1 = Product(id="P1", name="Товар 1", category="Кат 1", quantity=10, price=100.0, location="Склад А")
    p2 = Product(id="P2", name="Товар 2", category="Кат 2", quantity=20, price=200.0, location="Склад Б")

    # Add
    repo.add(p1)
    repo.add(p2)
    assert len(repo.get_all()) == 2
    assert repo.get_by_id("P1") == p1
    assert repo.get_by_id("P2") == p2
    assert repo.is_dirty is True

    # Duplicate add
    with pytest.raises(ValueError):
        repo.add(Product(id="P1", name="Дублікат", category="Кат", quantity=1, price=1, location=""))

    # Update
    updated_p1 = Product(id="P1", name="Товар 1 Оновлений", category="Кат 1", quantity=15, price=120.0, location="Склад А")
    repo.update(updated_p1)
    assert repo.get_by_id("P1").name == "Товар 1 Оновлений"
    assert repo.get_by_id("P1").quantity == 15

    # Update non-existing
    with pytest.raises(KeyError):
        repo.update(Product(id="NON_EXISTENT", name="Немає", category="Кат", quantity=1, price=1, location=""))

    # Delete
    repo.delete("P2")
    assert len(repo.get_all()) == 1
    assert repo.get_by_id("P2") is None

    # Delete non-existing
    with pytest.raises(KeyError):
        repo.delete("P2")

    # Clear
    repo.clear()
    assert len(repo.get_all()) == 0
    assert repo.is_dirty is False


def test_repo_id_autogeneration(empty_repo):
    repo = empty_repo
    # Перший ID
    first_id = repo.generate_id(prefix="PRD-")
    assert first_id == "PRD-0001"

    repo.add(Product(id=first_id, name="А", category="Б", quantity=1, price=1.0, location=""))
    second_id = repo.generate_id(prefix="PRD-")
    assert second_id == "PRD-0002"


def test_repo_csv_save_and_load():
    repo = CSVProductRepository()
    p1 = Product(id="PRD-001", name="Папір офісний", category="Канцелярія", quantity=100, price=210.50, location="Склад 1")
    p2 = Product(id="PRD-002", name="Картридж HP", category="Витратні матеріали", quantity=5, price=1450.00, location="Склад 2")

    repo.add(p1)
    repo.add(p2)

    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        # Save
        saved_count = repo.save_to_file(tmp_path)
        assert saved_count == 2
        assert repo.is_dirty is False

        # Load into fresh repo
        new_repo = CSVProductRepository()
        loaded_count = new_repo.load_from_file(tmp_path)
        assert loaded_count == 2
        assert len(new_repo.get_all()) == 2

        restored_p1 = new_repo.get_by_id("PRD-001")
        assert restored_p1 is not None
        assert restored_p1.name == "Папір офісний"
        assert restored_p1.category == "Канцелярія"
        assert restored_p1.quantity == 100
        assert restored_p1.price == 210.50

        # Categories
        cats = new_repo.get_categories()
        assert "Канцелярія" in cats
        assert "Витратні матеріали" in cats
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_repo_load_missing_file_raises():
    repo = CSVProductRepository()
    with pytest.raises(StorageError):
        repo.load_from_file("non_existent_file_xyz_123.csv")


def test_repo_load_corrupted_csv_headers():
    repo = CSVProductRepository()
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as tmp:
        tmp.write("some,invalid,header,without,required,columns\n1,2,3,4,5,6\n")
        tmp_path = tmp.name

    try:
        with pytest.raises(StorageFormatError) as exc_info:
            repo.load_from_file(tmp_path)
        assert "відсутній обов'язковий стовпець" in str(exc_info.value)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


# =============================================================================
# Тести валідатора ProductValidator
# =============================================================================

def test_validator_valid_product(empty_repo):
    repo = empty_repo
    res = ProductValidator.validate(
        raw_id="PRD-0100",
        name="Ножиці канцелярські",
        category="Канцтовари",
        quantity_str="15",
        price_str="65,50",
        location="Стелаж 1",
        repository=repo,
        is_new=True,
    )
    assert res.is_valid is True
    assert res.product is not None
    assert res.product.id == "PRD-0100"
    assert res.product.price == 65.50
    assert res.product.quantity == 15
    assert not res.errors


def test_validator_autogenerates_id_when_empty(empty_repo):
    repo = empty_repo
    res = ProductValidator.validate(
        raw_id="",  # Порожній ID
        name="Степлер",
        category="Канцтовари",
        quantity_str="5",
        price_str="120.00",
        location="",
        repository=repo,
        is_new=True,
    )
    assert res.is_valid is True
    assert res.product is not None
    assert res.product.id.startswith("PRD-")
    assert res.product.location == "Основний склад"


def test_validator_detects_empty_name_and_category(empty_repo):
    repo = empty_repo
    res = ProductValidator.validate(
        raw_id="",
        name="   ",
        category="",
        quantity_str="10",
        price_str="100",
        location="",
        repository=repo,
        is_new=True,
    )
    assert res.is_valid is False
    assert "name" in res.errors
    assert "category" in res.errors


def test_validator_detects_invalid_quantity(empty_repo):
    repo = empty_repo

    # Негативне число
    res1 = ProductValidator.validate(
        raw_id="",
        name="Тест",
        category="Кат",
        quantity_str="-5",
        price_str="10",
        location="",
        repository=repo,
    )
    assert res1.is_valid is False
    assert "quantity" in res1.errors

    # Неціле число
    res2 = ProductValidator.validate(
        raw_id="",
        name="Тест",
        category="Кат",
        quantity_str="5.5",
        price_str="10",
        location="",
        repository=repo,
    )
    assert res2.is_valid is False
    assert "quantity" in res2.errors


def test_validator_detects_invalid_price(empty_repo):
    repo = empty_repo

    # Не число
    res1 = ProductValidator.validate(
        raw_id="",
        name="Тест",
        category="Кат",
        quantity_str="5",
        price_str="безкоштовно",
        location="",
        repository=repo,
    )
    assert res1.is_valid is False
    assert "price" in res1.errors

    # Від'ємна ціна
    res2 = ProductValidator.validate(
        raw_id="",
        name="Тест",
        category="Кат",
        quantity_str="5",
        price_str="-10.50",
        location="",
        repository=repo,
    )
    assert res2.is_valid is False
    assert "price" in res2.errors


def test_validator_detects_duplicate_id(empty_repo):
    repo = empty_repo
    repo.add(Product(id="DUPL-1", name="Перший", category="Кат", quantity=1, price=1.0, location=""))

    res = ProductValidator.validate(
        raw_id="DUPL-1",
        name="Другий",
        category="Кат",
        quantity_str="2",
        price_str="2.0",
        location="",
        repository=repo,
        is_new=True,
    )
    assert res.is_valid is False
    assert "id" in res.errors


def test_validator_allows_same_id_on_update(empty_repo):
    repo = empty_repo
    repo.add(Product(id="EXIST-1", name="Початковий", category="Кат", quantity=1, price=1.0, location=""))

    res = ProductValidator.validate(
        raw_id="EXIST-1",
        name="Змінений",
        category="Кат",
        quantity_str="2",
        price_str="2.0",
        location="",
        repository=repo,
        is_new=False,
        original_id="EXIST-1",
    )
    assert res.is_valid is True
    assert res.product is not None
    assert res.product.name == "Змінений"


# =============================================================================
# Тест GUI (без запуску mainloop)
# =============================================================================

def test_gui_initialization_with_sample_data():
    candidates = [
        os.path.join(os.path.dirname(__file__), "sample_inventory.csv"),
        os.path.join(os.path.dirname(__file__), "accounting_app", "sample_inventory.csv"),
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "sample_inventory.csv"),
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "accounting_app", "sample_inventory.csv"),
    ]
    sample_file = next((c for c in candidates if os.path.exists(c)), candidates[0])
    repo = CSVProductRepository(initial_filepath=sample_file)
    assert len(repo.get_all()) == 15

    from accounting_app.gui import AccountingApp

    app = AccountingApp(repository=repo)
    app.withdraw()  # Не відображати вікно на екрані

    try:
        # Перевірка що таблиця заповнилася
        children = app.tree.get_children()
        assert len(children) == 15

        # Перевірка фільтрації пошуку
        app.search_var.set("Миша")
        app.on_search_changed()
        filtered = app.tree.get_children()
        assert len(filtered) == 1
        assert "Миша" in app.repository.get_by_id(filtered[0]).name

        # Очищення пошуку
        app.search_var.set("")
        app.on_search_changed()
        assert len(app.tree.get_children()) == 15
    finally:
        app.destroy()


def test_gui_auto_save_and_persistence(tmp_path):
    csv_file = str(tmp_path / "test_inventory.csv")
    repo = CSVProductRepository(initial_filepath=csv_file)

    from accounting_app.gui import AccountingApp

    app = AccountingApp(repository=repo)
    app.withdraw()

    try:
        # Заповнення полів форми
        app.field_entries["id"].insert(0, "TEST-99")
        app.field_entries["name"].insert(0, "Тестовий Товар")
        app.field_entries["category"].set("ТестКат")
        app.field_entries["quantity"].insert(0, "42")
        app.field_entries["price"].insert(0, "150.50")
        app.field_entries["location"].insert(0, "Стелаж 1")

        # Виклик додавання товару
        app.on_add_product()

        # Товар має з'явитися у сховищі
        assert repo.get_by_id("TEST-99") is not None

        # Файл має існувати на диску (автозбереження)
        assert os.path.exists(csv_file)

        # Перевірка що після створення нового репозиторію (імітація перезапуску) товар завантажується
        reloaded_repo = CSVProductRepository(initial_filepath=csv_file)
        saved_prod = reloaded_repo.get_by_id("TEST-99")
        assert saved_prod is not None
        assert saved_prod.name == "Тестовий Товар"
        assert saved_prod.quantity == 42
        assert saved_prod.price == 150.50

        # Тестуємо оновлення товару через вибір у таблиці
        app.tree.selection_set("TEST-99")
        app.on_tree_select()
        app.field_entries["quantity"].delete(0, "end")
        app.field_entries["quantity"].insert(0, "99")
        app.on_update_product()

        # Перевірка збереження оновлення в CSV
        reloaded_repo2 = CSVProductRepository(initial_filepath=csv_file)
        assert reloaded_repo2.get_by_id("TEST-99").quantity == 99

        # Тестуємо видалення товару
        from unittest.mock import patch
        with patch("tkinter.messagebox.askyesno", return_value=True):
            app.tree.selection_set("TEST-99")
            app.on_tree_select()
            app.on_delete_product()

        assert repo.get_by_id("TEST-99") is None
        reloaded_repo3 = CSVProductRepository(initial_filepath=csv_file)
        assert reloaded_repo3.get_by_id("TEST-99") is None
    finally:
        app.destroy()


