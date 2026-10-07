from abc import ABC, abstractmethod

class JunkItem():
    def __init__(self, name: str, quantity: int, value: float):
        self.name = str(name)
        self.quantity = int(quantity)
        self.value = float(value)

    def __repr__(self) -> str:
        return f"JunkItem(name='{self.name}', quantity={self.quantity}, value={self.value:.2f})"

    def __eq__(self, other) -> bool:
        if not isinstance(other, JunkItem):
            return False
        return (
            self.name == other.name and
            self.quantity == other.quantity and
            abs(self.value - other.value) < 1e-6
        )

class StorageBackend(ABC):
    @abstractmethod
    def save(self, items: list[JunkItem]) -> None:
        pass

    @abstractmethod
    def read(self) -> list[JunkItem]:
        pass

class FileJunkStorage(StorageBackend):
    def __init__(self, filename: str):
        self.filename = filename

    def serialize(self, items: list[JunkItem], filename: str | None = None) -> None:
        target_file = filename or self.filename
        with open(target_file, "w", encoding="utf-8") as file:
            for item in items:
                val_str = str(item.value).replace(".", ",")
                file.write(f"{item.name}|{item.quantity}|{val_str}\n")

    def parse(self, filename: str | None = None) -> list[JunkItem]:
        target_file = filename or self.filename
        items: list[JunkItem] = []

        try:
            with open(target_file, "r", encoding="utf-8") as file:
                lines = file.readlines()
        except FileNotFoundError:
            print(f"Файл '{target_file}' не знайдено")
            return items

        for line_num, raw_line in enumerate(lines, 1):
            line = raw_line.strip()
            if not line:
                continue

            parts = line.split("|")
            if len(parts) != 3:
                print(f"[Рядок {line_num}] Рядок пропущено: очікувалось 3 поля")
                continue

            try:
                name, qty_str, val_str = parts
                qty = int(qty_str.strip())
                val = float(val_str.strip().replace(",", "."))
                items.append(JunkItem(name.strip(), qty, val))
            except ValueError:
                print(f"[Рядок {line_num}] Помилка: невалідні числові дані")
        return items

    def save(self, items: list[JunkItem], filename: str | None = None) -> None:
        self.serialize(items, filename)

    def read(self, filename: str | None = None) -> list[JunkItem]:
        return self.parse(filename)

class JunkWarehouse:
    def __init__(self, backend: StorageBackend):
        self._backend = backend
        self._items: list[JunkItem] = []

    def add_item(self, item: JunkItem) -> None:
        for existing in self._items:
            if existing.name.lower() == item.name.lower():
                existing.quantity += item.quantity
                existing.value = item.value
                return
        self._items.append(item)

    def get_item(self, name: str) -> JunkItem | None:
        for idx, item in enumerate(self._items):
            if item.name.lower() == name.lower():
                return self._items.pop(idx)
        return None

    def find(self, query: str) -> list[JunkItem]:
        query_norm = query.lower()
        return [item for item in self._items if query_norm in item.name.lower()]

    def list_all(self) -> list[JunkItem]:
        return list(self._items)

    def persist(self) -> None:
        self._backend.save(self._items)

    def sync(self) -> None:
        self._items = self._backend.read()



if __name__ == "__main__":
    storage_file = "warehouse_data.csv"

    initial_items = [
        JunkItem("Бляшанка", 5, 2.5),
        JunkItem("Стара плата", 3, 7.8),
        JunkItem("Купка дротів", 10, 1.2),
    ]

    backend = FileJunkStorage(storage_file)
    warehouse = JunkWarehouse(backend=backend)

    for item in initial_items:
        warehouse.add_item(item)

    warehouse.persist()
    print("Дані успішно записано у файл.")


    with open(storage_file, "a", encoding="utf-8") as file:
        file.write("Бите скло|многа|1,5\n")
        file.write("Рваний черевик|2\n")
        file.write("Іржавий цвях|100|дорого\n")
        file.write("Пральний порошок|1|15,5\n")

    print("\nЗчитування даних")
    warehouse.sync()

    loaded_items = warehouse.list_all()
    print("\nКільксть товару:")
    for item in loaded_items:
        print(f"  - {item}")

    print("\nПеревірка точності відновлення початкових об'єктів")
    all_matched = True
    for original in initial_items:
        match = next((i for i in loaded_items if i == original), None)
        if match:
            print(f"  [OK] '{original.name}' збігається: {match}")
        else:
            print(f"  [ПОМИЛКА] '{original.name}' не знайдено або значення спотворені.")
            all_matched = False

    if all_matched:
        print("Всі базові об'єкти після читання повністю зберегли значення.")

    print("\nПошук та вилучення")
    found = warehouse.find("дротів")
    print(f"Пошук за 'дротів': {found}")

    taken = warehouse.get_item("Стара плата")
    print(f"Дістали зі складу: {taken}")
    print(f"Залишилось на складі позицій: {len(warehouse.list_all())}")