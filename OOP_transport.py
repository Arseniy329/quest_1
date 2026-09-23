from abc import ABC, abstractmethod


class Transport(ABC):
    def __init__(self, name: str, speed: int, capacity: int) -> None:
        if speed <= 0:
            raise ValueError(f"Швидкість має бути > 0, отримано {speed}.")
        self.name: str = name
        self.speed: int = speed
        self.capacity: int = capacity

    @abstractmethod
    def move(self, distance: float) -> float:
        pass

    @abstractmethod
    def fuel_consumption(self, distance: float) -> float | str:
        pass

    @abstractmethod
    def info(self) -> str:
        pass

    def calculate_cost(self, distance: float, price_per_unit: float) -> float | str:
        consumption = self.fuel_consumption(distance)
        if isinstance(consumption, str):
            return consumption
        return consumption * price_per_unit


class Car(Transport):
    def move(self, distance: float) -> float:
        return distance / self.speed

    def fuel_consumption(self, distance: float) -> float:
        return distance * 0.07

    def info(self) -> str:
        return f"[Car] {self.name} | Швидкість: {self.speed} км/год | Місткість: {self.capacity} пасажирів"


class Bus(Transport):
    def __init__(self, name: str, speed: int, capacity: int, passengers: int = 0) -> None:
        super().__init__(name, speed, capacity)
        self.passengers: int = passengers

    def move(self, distance: float) -> float:
        return distance / self.speed

    def fuel_consumption(self, distance: float, passengers: int | None = None) -> float | str:
        current_passengers = self.passengers if passengers is None else passengers
        if current_passengers > self.capacity:
            return "Перевантажено!"
        return distance * 0.15

    def info(self) -> str:
        return f"[Bus] {self.name} | Швидкість: {self.speed} км/год | Місткість: {self.capacity} | Пасажири: {self.passengers}"


class Bicycle(Transport):
    _MAX_SPEED: int = 20

    def __init__(self, name: str, speed: int, capacity: int = 1) -> None:
        super().__init__(name, min(speed, self._MAX_SPEED), capacity)

    @property
    def speed(self) -> int:
        return self._speed

    @speed.setter
    def speed(self, value: int) -> None:
        self._speed = min(value, self._MAX_SPEED)

    def move(self, distance: float) -> float:
        return distance / self.speed

    def fuel_consumption(self, distance: float = 0.0) -> float:
        return 0.0

    def info(self) -> str:
        return f"[Bicycle] {self.name} | Швидкість: {self.speed} км/год | Місткість: {self.capacity}"


class ElectricCar(Car):
    def battery_usage(self, distance: float) -> float:
        return distance * 0.2

    def fuel_consumption(self, distance: float = 0.0) -> float:
        return 0.0

    def calculate_cost(self, distance: float, price_per_unit: float) -> float:
        return self.battery_usage(distance) * price_per_unit

    def info(self) -> str:
        return f"[ElectricCar] {self.name} | Швидкість: {self.speed} км/год | Місткість: {self.capacity} пасажирів"


if __name__ == "__main__":
    distance = 100.0

    fleet: list[Transport] = [
        Car("Toyota Camry", 120, 5),
        Bus("Богдан А092", 60, 30, passengers=25),
        Bicycle("Trek FX3", 25, 1),
        ElectricCar("Tesla Model 3", 140, 5),
    ]

    print("Список транспорту (100 км)")
    for vehicle in fleet:
        time_spent = vehicle.move(distance)
        fuel = vehicle.fuel_consumption(distance)
        print(f"Транспорт: {vehicle.name} | Час у дорозі: {time_spent:.2f} год | Витрати пального: {fuel:.3f}")

    print("\nПеревірка перевантаженого автобуса")
    overloaded_bus = Bus("Еталон", 60, 30, passengers=35)
    print(f"{overloaded_bus.name} (пасажирів 35/30): {overloaded_bus.fuel_consumption(distance)}")
