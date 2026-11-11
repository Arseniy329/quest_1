"""
Моделі даних для системи обліку товарів.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict


@dataclass
class Product:
    """
    Сутність товару на складі.

    Атрибути:
        id: Унікальний ідентифікатор товару (наприклад, PRD-0001).
        name: Назва товару.
        category: Категорія або товарна група.
        quantity: Кількість на складі (ціле невід'ємне число >= 0).
        price: Ціна за одиницю у гривнях (дійсне невід'ємне число >= 0.0).
        location: Місце зберігання (склад, стелаж, полиця тощо).
        created_at: Час реєстрації запису у форматі YYYY-MM-DD HH:MM:SS.
    """

    id: str
    name: str
    category: str
    quantity: int
    price: float
    location: str
    created_at: str = field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )

    def total_value(self) -> float:
        """Повертає загальну вартість залишку (кількість * ціна)."""
        return round(self.quantity * self.price, 2)

    def to_dict(self) -> Dict[str, str]:
        """Серіалізація у словник для збереження у CSV."""
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "quantity": str(self.quantity),
            "price": f"{self.price:.2f}",
            "location": self.location,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Product":
        """
        Десеріалізація зі словника (рядка CSV) з нормалізацією типів.

        Викликає ValueError, якщо дані пошкоджені або не відповідають типу.
        """
        raw_id = str(data.get("id", "")).strip()
        raw_name = str(data.get("name", "")).strip()
        raw_category = str(data.get("category", "")).strip()
        raw_quantity = str(data.get("quantity", "0")).strip()
        raw_price = str(data.get("price", "0")).strip().replace(",", ".")
        raw_location = str(data.get("location", "")).strip()
        raw_created_at = str(data.get("created_at", "")).strip()

        if not raw_id:
            raise ValueError("Поле 'id' не може бути порожнім.")
        if not raw_name:
            raise ValueError("Поле 'name' не може бути порожнім.")
        if not raw_category:
            raise ValueError("Поле 'category' не може бути порожнім.")

        try:
            quantity = int(raw_quantity)
        except ValueError as err:
            raise ValueError(
                f"Некоректне значення кількості: '{raw_quantity}'. Має бути ціле число."
            ) from err

        if quantity < 0:
            raise ValueError("Кількість не може бути від'ємною.")

        try:
            price = float(raw_price)
        except ValueError as err:
            raise ValueError(
                f"Некоректне значення ціни: '{raw_price}'. Має бути числом."
            ) from err

        if price < 0:
            raise ValueError("Ціна не може бути від'ємною.")

        if not raw_created_at:
            raw_created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return cls(
            id=raw_id,
            name=raw_name,
            category=raw_category,
            quantity=quantity,
            price=round(price, 2),
            location=raw_location,
            created_at=raw_created_at,
        )

