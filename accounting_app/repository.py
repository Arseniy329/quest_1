"""
Рівень збереження даних (Data Access Layer / Repository Pattern).
Повністю ізолює бізнес-логіку та GUI від деталей збереження у CSV.
"""

from abc import ABC, abstractmethod
import csv
from datetime import datetime
import os
import re
from typing import Dict, List, Optional
import uuid

from .models import Product


class StorageError(Exception):
    """Базовий виняток для помилок сховища."""
    pass


class StorageFormatError(StorageError):
    """Виникає при порушенні формату файлу або заголовків."""
    pass


class ProductRepository(ABC):
    """
    Абстрактний інтерфейс сховища товарів (Repository Pattern).
    GUI-компоненти взаємодіють виключно з цим інтерфейсом.
    """

    @abstractmethod
    def get_all(self) -> List[Product]:
        """Отримати повний список усіх товарів."""
        pass

    @abstractmethod
    def get_by_id(self, product_id: str) -> Optional[Product]:
        """Знайти товар за унікальним ідентифікатором."""
        pass

    @abstractmethod
    def add(self, product: Product) -> None:
        """Додати новий товар до сховища."""
        pass

    @abstractmethod
    def update(self, product: Product) -> None:
        """Оновити існуючий товар."""
        pass

    @abstractmethod
    def delete(self, product_id: str) -> None:
        """Видалити товар за його ID."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Очистити всі записи в пам'яті."""
        pass

    @abstractmethod
    def load_from_file(self, filepath: str) -> int:
        """Завантажити дані з файлу. Повертає кількість завантажених записів."""
        pass

    @abstractmethod
    def save_to_file(self, filepath: str) -> int:
        """Зберегти поточні дані у файл. Повертає кількість збережених записів."""
        pass

    @abstractmethod
    def save_current(self) -> int:
        """Зберегти поточні дані у відкритий файл."""
        pass

    @abstractmethod
    def generate_id(self, prefix: str = "PRD-") -> str:
        """Згенерувати новий унікальний ID, гарантовано відсутній у поточному сховищі."""
        pass


class CSVProductRepository(ProductRepository):
    """
    Конкретна реалізація сховища товарів у форматі CSV.

    Особливості:
    - Зберігає дані в оперативній пам'яті (словник id -> Product) для швидкого доступу O(1).
    - Використовує кодування 'utf-8-sig', що запобігає «кракозябрам» в Excel на Windows.
    - Атомарне зчитування: якщо файл пошкоджений, попередній стан сховища зберігається.
    """

    CSV_HEADERS: List[str] = [
        "id",
        "name",
        "category",
        "quantity",
        "price",
        "location",
        "created_at",
    ]

    def __init__(self, initial_filepath: Optional[str] = None):
        self._items: Dict[str, Product] = {}
        self.current_filepath: Optional[str] = initial_filepath
        self.is_dirty: bool = False

        if initial_filepath and os.path.exists(initial_filepath):
            self.load_from_file(initial_filepath)

    def get_all(self) -> List[Product]:
        """Повертає список копій об'єктів для запобігання мутаціям ззовні."""
        return list(self._items.values())

    def get_by_id(self, product_id: str) -> Optional[Product]:
        """Повертає товар або None, якщо не знайдено."""
        return self._items.get(product_id)

    def add(self, product: Product) -> None:
        """
        Додає товар.
        Викликає ValueError, якщо товар із таким ID вже існує.
        """
        if product.id in self._items:
            raise ValueError(f"Товар з ідентифікатором '{product.id}' вже існує.")
        self._items[product.id] = product
        self.is_dirty = True

    def update(self, product: Product) -> None:
        """
        Оновлює товар.
        Викликає KeyError, якщо товар не знайдено.
        """
        if product.id not in self._items:
            raise KeyError(f"Товар з ID '{product.id}' не знайдено для оновлення.")
        self._items[product.id] = product
        self.is_dirty = True

    def delete(self, product_id: str) -> None:
        """
        Видаляє товар за ID.
        Викликає KeyError, якщо товар відсутній.
        """
        if product_id not in self._items:
            raise KeyError(f"Товар з ID '{product_id}' не знайдено для видалення.")
        del self._items[product_id]
        self.is_dirty = True

    def clear(self) -> None:
        """Повністю скидає записи сховища."""
        self._items.clear()
        self.current_filepath = None
        self.is_dirty = False

    def get_categories(self) -> List[str]:
        """Повертає відсортований перелік унікальних категорій."""
        cats = {p.category for p in self._items.values() if p.category}
        return sorted(cats)

    def generate_id(self, prefix: str = "PRD-") -> str:
        """
        Генерує зручний числовий автоінкремент або короткий унікальний ідентифікатор.
        Шукає максимальне число серед ID з префіксом 'PRD-', інкрементує його.
        """
        max_num = 0
        pattern = re.compile(rf"^{re.escape(prefix)}(\d+)$", re.IGNORECASE)
        for pid in self._items:
            match = pattern.match(pid)
            if match:
                try:
                    num = int(match.group(1))
                    if num > max_num:
                        max_num = num
                except ValueError:
                    pass

        if max_num > 0 or not self._items:
            candidate = f"{prefix}{max_num + 1:04d}"
            if candidate not in self._items:
                return candidate

        # Запасний варіант: короткий UUID
        while True:
            candidate = f"{prefix}{uuid.uuid4().hex[:6].upper()}"
            if candidate not in self._items:
                return candidate

    def load_from_file(self, filepath: str) -> int:
        """
        Завантажує дані з CSV-файлу.

        Повертає кількість успішно завантажених товарів.
        Викликає StorageError або StorageFormatError при виникненні проблем.
        """
        if not os.path.exists(filepath):
            raise StorageError(f"Файл '{filepath}' не існує.")

        # Спробуємо utf-8-sig (охоплює utf-8 та BOM), а за потреби cp1251
        encodings_to_try = ["utf-8-sig", "utf-8", "cp1251"]
        last_error: Optional[Exception] = None
        loaded_items: Dict[str, Product] = {}

        for encoding in encodings_to_try:
            try:
                with open(filepath, mode="r", encoding=encoding, newline="") as csvfile:
                    reader = csv.reader(csvfile)
                    try:
                        header = next(reader)
                    except StopIteration:
                        # Порожній файл
                        self._items = {}
                        self.current_filepath = filepath
                        self.is_dirty = False
                        return 0

                    clean_header = [h.strip().lower() for h in header]
                    for required in ["id", "name", "category", "quantity", "price"]:
                        if required not in clean_header:
                            raise StorageFormatError(
                                f"У файлі відсутній обов'язковий стовпець '{required}'. "
                                f"Знайдено стовпці: {', '.join(header)}"
                            )

                    # Повертаємося до читання зі словником
                    csvfile.seek(0)
                    dict_reader = csv.DictReader(csvfile)
                    line_num = 1
                    for row in dict_reader:
                        line_num += 1
                        try:
                            # Нормалізація ключів
                            norm_row = {
                                (k.strip().lower() if k else ""): (v.strip() if v else "")
                                for k, v in row.items()
                            }
                            product = Product.from_dict(norm_row)
                            if product.id in loaded_items:
                                raise StorageFormatError(
                                    f"Рядок {line_num}: дублікат ID '{product.id}' у файлі."
                                )
                            loaded_items[product.id] = product
                        except ValueError as err:
                            raise StorageFormatError(
                                f"Помилка в рядку {line_num}: {err}"
                            ) from err

                # Якщо дійшли сюди — кодування успішне
                last_error = None
                break
            except (UnicodeDecodeError, UnicodeError) as err:
                last_error = err
                continue
            except PermissionError as err:
                raise StorageError(
                    f"Немає прав на читання файлу '{filepath}': {err}"
                ) from err
            except StorageFormatError:
                raise
            except Exception as err:
                raise StorageError(f"Помилка при читанні файлу: {err}") from err

        if last_error is not None:
            raise StorageError(
                f"Не вдалося розпізнати кодування файлу '{filepath}'. Перевірте формат UTF-8/Windows-1251."
            )

        self._items = loaded_items
        self.current_filepath = filepath
        self.is_dirty = False
        return len(self._items)

    def save_to_file(self, filepath: str) -> int:
        """
        Зберігає поточні дані у вказаний CSV-файл.

        Використовує атомарне записування через тимчасовий файл поруч,
        щоб у разі раптового збою живлення старий файл не пошкодився.
        """
        dir_name = os.path.dirname(filepath) or "."
        temp_filepath = os.path.join(dir_name, f".tmp_{os.path.basename(filepath)}")

        try:
            with open(
                temp_filepath, mode="w", encoding="utf-8-sig", newline=""
            ) as csvfile:
                writer = csv.DictWriter(
                    csvfile,
                    fieldnames=self.CSV_HEADERS,
                    quoting=csv.QUOTE_MINIMAL,
                )
                writer.writeheader()
                for product in self._items.values():
                    writer.writerow(product.to_dict())

            # Атомарна заміна файлу
            if os.path.exists(filepath):
                os.replace(temp_filepath, filepath)
            else:
                os.rename(temp_filepath, filepath)

            self.current_filepath = filepath
            self.is_dirty = False
            return len(self._items)

        except PermissionError as err:
            if os.path.exists(temp_filepath):
                try:
                    os.remove(temp_filepath)
                except OSError:
                    pass
            raise StorageError(
                f"Немає прав на запис у файл '{filepath}'. Перевірте доступ."
            ) from err
        except Exception as err:
            if os.path.exists(temp_filepath):
                try:
                    os.remove(temp_filepath)
                except OSError:
                    pass
            raise StorageError(f"Помилка при збереженні файлу: {err}") from err

    def save_current(self) -> int:
        """Зберігає дані у поточний прив'язаний файл, якщо він заданий."""
        if self.current_filepath:
            return self.save_to_file(self.current_filepath)
        return 0


