"""
Модуль перевірки та валідації введених користувачем даних.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional, Tuple

from .models import Product
from .repository import ProductRepository


@dataclass
class ValidationResult:
    """Результат валідації форми товару."""

    is_valid: bool
    product: Optional[Product] = None
    errors: Dict[str, str] = field(default_factory=dict)

    @property
    def first_error_message(self) -> str:
        """Повертає перше повідомлення про помилку для виведення у status bar."""
        if not self.errors:
            return ""
        return next(iter(self.errors.values()))


class ProductValidator:
    """
    Валідатор для полів форми введення товару.
    Забезпечує коректність типів даних, числових меж та унікальності ID.
    """

    @staticmethod
    def validate(
        raw_id: str,
        name: str,
        category: str,
        quantity_str: str,
        price_str: str,
        location: str,
        repository: ProductRepository,
        is_new: bool = True,
        original_id: Optional[str] = None,
        created_at: Optional[str] = None,
    ) -> ValidationResult:
        """
        Перевіряє всі поля форми.

        Параметри:
            raw_id: Введений ID (може бути порожнім для автогенерації).
            name: Назва товару.
            category: Категорія товару.
            quantity_str: Рядкове значення кількості.
            price_str: Рядкове значення ціни.
            location: Місцезнаходження на складі.
            repository: Сховище для перевірки унікальності ID.
            is_new: Чи додається новий товар (True) або оновлюється існуючий (False).
            original_id: Початковий ID при редагуванні (дозволяє зберегти власний ID).
            created_at: Час створення (зберігається при оновленні).

        Повертає:
            ValidationResult із валідованим об'єктом Product або переліком помилок по полях.
        """
        errors: Dict[str, str] = {}

        # 1. Валідація назви
        clean_name = name.strip()
        if not clean_name:
            errors["name"] = "Назва товару не може бути порожньою."

        # 2. Валідація категорії
        clean_category = category.strip()
        if not clean_category:
            errors["category"] = "Категорія товару не може бути порожньою."

        # 3. Валідація кількості (int >= 0)
        clean_qty_str = quantity_str.strip()
        quantity_val = 0
        if not clean_qty_str:
            errors["quantity"] = "Вкажіть кількість товару (ціле число >= 0)."
        else:
            try:
                # Перевірка на ціле число (без десяткової крапки)
                if "." in clean_qty_str or "," in clean_qty_str:
                    raise ValueError("Десяткові дроби не дозволені для кількості.")
                quantity_val = int(clean_qty_str)
                if quantity_val < 0:
                    errors["quantity"] = "Кількість не може бути від'ємною."
            except ValueError:
                errors["quantity"] = "Кількість має бути цілим невід'ємним числом (наприклад: 0, 5, 100)."

        # 4. Валідація ціни (float >= 0, коми нормалізуються у крапки)
        clean_price_str = price_str.strip().replace(",", ".")
        price_val = 0.0
        if not clean_price_str:
            errors["price"] = "Вкажіть ціну товару (число >= 0)."
        else:
            try:
                price_val = float(clean_price_str)
                if price_val < 0.0:
                    errors["price"] = "Ціна не може бути від'ємною."
                else:
                    price_val = round(price_val, 2)
            except ValueError:
                errors["price"] = "Ціна має бути додатним числом (наприклад: 120.50 або 0)."

        # 5. Валідація / генерація ID
        clean_id = raw_id.strip()
        if not clean_id:
            if is_new:
                clean_id = repository.generate_id()
            else:
                clean_id = original_id or repository.generate_id()
        else:
            # Перевірка унікальності ID
            existing = repository.get_by_id(clean_id)
            if existing is not None:
                if is_new or (original_id and clean_id != original_id):
                    errors["id"] = f"Товар з ID '{clean_id}' вже існує. Оберіть інший ID."

        clean_location = location.strip()
        if not clean_location:
            clean_location = "Основний склад"

        if errors:
            return ValidationResult(is_valid=False, product=None, errors=errors)

        valid_created_at = created_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        product = Product(
            id=clean_id,
            name=clean_name,
            category=clean_category,
            quantity=quantity_val,
            price=price_val,
            location=clean_location,
            created_at=valid_created_at,
        )

        return ValidationResult(is_valid=True, product=product, errors={})

