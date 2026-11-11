#!/usr/bin/env python3
"""
Головна точка входу для запуску програми складського обліку товарів.

Використання:
    python3 accounting_app.py
    python3 accounting_app.py [шлях_до_файлу.csv]
"""

import os
import sys

# Додаємо поточну директорію до sys.path для підтримки імпортів
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)

for p in (PARENT_DIR, CURRENT_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from gui import AccountingApp
    from repository import CSVProductRepository
except (ImportError, ModuleNotFoundError):
    from accounting_app.gui import AccountingApp
    from accounting_app.repository import CSVProductRepository


def main() -> None:
    # За замовчуванням база даних зберігається у файлі inventory.csv
    default_csv = os.path.join(CURRENT_DIR, "inventory.csv")
    candidates = [
        os.path.join(CURRENT_DIR, "sample_inventory.csv"),
        os.path.join(PARENT_DIR, "sample_inventory.csv"),
        os.path.join(CURRENT_DIR, "accounting_app", "sample_inventory.csv"),
    ]
    sample_csv = next((c for c in candidates if os.path.exists(c)), candidates[0])

    initial_file = None
    if len(sys.argv) > 1:
        arg_file = sys.argv[1]
        if os.path.exists(arg_file):
            initial_file = os.path.abspath(arg_file)
        else:
            print(f"Попередження: вказаний файл '{arg_file}' не знайдено.")

    if initial_file is None:
        # Якщо файл не задано явно, створюємо або відкриваємо inventory.csv
        if not os.path.exists(default_csv) and os.path.exists(sample_csv):
            import shutil
            try:
                shutil.copyfile(sample_csv, default_csv)
            except Exception as e:
                print(f"Не вдалося скопіювати зразок бази: {e}")

        initial_file = default_csv

    # 1. Ініціалізація репозиторію (сховища)
    # Зверніть увагу: GUI знає лише про інтерфейс ProductRepository
    repository = CSVProductRepository(initial_filepath=initial_file if os.path.exists(initial_file) else None)
    if not repository.current_filepath:
        repository.current_filepath = initial_file

    # 2. Запуск графічного інтерфейсу із впровадженням залежності
    app = AccountingApp(repository=repository)
    app.mainloop()


if __name__ == "__main__":
    main()

