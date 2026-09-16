from abc import ABC, abstractmethod

class Medicine(ABC):
    def __init__(self, name: str, quantity: int, price: float):
        if not isinstance(name, (str)):
            raise TypeError("Імʼя має містити лише букви!")
        if not isinstance(quantity, (int)) or quantity < 0:
            raise TypeError("Кількість повинна бути додатнім числом!")
        if not isinstance(price, (float, int)) or price < 0:
            raise TypeError("Ціна повинна бути додатнім числом")

        self.name = name
        self.quantity = quantity
        self.price = float(price)

    @abstractmethod
    def requires_prescription(self) -> bool:
        pass

    @abstractmethod
    def storage_requirements(self) -> str:
        pass

    def total_price(self) -> float:
        return self.quantity * self.price

    def info(self) -> str:
        permit_text = "Потрібен рецепт" if self.requires_prescription() else "Рецепт не потрібен"
        return (
            f"[{self.name}] Вимоги зберігання: {self.storage_requirements()} | "
            f"Рецепт: {permit_text} | Вартість: {self.total_price():.2f} грн"
        )

class Antibiotic(Medicine):
    def requires_prescription(self) -> bool:
        return True

    def storage_requirements(self) -> str:
        return "8–15°C, темне місце"


class Vitamin(Medicine):
    def requires_prescription(self) -> bool:
        return False

    def storage_requirements(self) -> str:
        return "15–25°C, сухе місце"


class Vaccine(Medicine):
    def requires_prescription(self) -> bool:
        return True

    def storage_requirements(self) -> str:
        return "2-8°C, холодильник"

    def total_price(self) -> float:
        cost = super().total_price()
        return cost * 1.1


def print_medicines_summary(medicines: list[Medicine]) -> None:
    for medicine in medicines:
        print(medicine.info())

if __name__ == "__main__":
    medicines: list[Medicine] = [
        Antibiotic("Амоксицилін", 44, 18.5),
        Vitamin("Вітамін C", 250, 28.0),
        Vaccine("Вакцина проти грипу", 50, 3.2),
    ]
    print_medicines_summary(medicines)