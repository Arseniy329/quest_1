import argparse
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Аналітика даних щодо поставок медичних препаратів"
    )
    parser.add_argument(
        "csv_path",
        nargs="?",
        default="supplies.csv",
        help="Шлях до вхідного файлу CSV (за замовчуванням: supplies.csv)"
    )
    parser.add_argument(
        "-f", "--file",
        dest="csv_file_flag",
        help="Альтернативний прапорець для передачі вхідного файлу CSV"
    )
    parser.add_argument(
        "--output-low",
        default="low_supply.csv",
        help="Ім'я або шлях для збереження файлу дефіцитних поставок (за замовчуванням: low_supply.csv)"
    )
    parser.add_argument(
        "--report",
        default="report.txt",
        help="Ім'я або шлях для збереження текстового звіту (за замовчуванням: report.txt)"
    )
    parser.add_argument(
        "--chart",
        default="category_distribution.png",
        help="Ім'я або шлях для збереження графіка (за замовчуванням: category_distribution.png)"
    )
    parser.add_argument(
        "--no-show",
        action="store_true",
        help="Не відкривати графічне вікно matplotlib (тільки зберегти у файл)"
    )
    return parser.parse_args()


def resolve_path(input_path_str: str, base_dir: Path) -> Path:
    path = Path(input_path_str)
    if path.is_file() or path.is_absolute():
        return path
    if (base_dir / path).is_file():
        return base_dir / path
    return base_dir / path


def main() -> None:
    args = parse_arguments()
    script_dir = Path(__file__).resolve().parent

    input_file_str = args.csv_file_flag or args.csv_path
    csv_file_path = resolve_path(input_file_str, script_dir)

    if not csv_file_path.is_file():
        print(f"Помилка: файл '{csv_file_path}' не знайдено!", file=sys.stderr)
        sys.exit(1)

    output_dir = csv_file_path.parent

    print("=" * 60)
    print("1. ЗАВАНТАЖЕННЯ ДАНИХ")
    print("=" * 60)
    print(f"Читання файлу: {csv_file_path.name}")
    df = pd.read_csv(csv_file_path)
    print(f"Завантажено записів: {len(df)}")
    print(df.to_string(index=False))

    print("\n" + "=" * 60)
    print("2. СТАТИСТИЧНІ ОБЧИСЛЕННЯ (NUMPY)")
    print("=" * 60)
    mean_price = float(np.mean(df["price_per_unit"]))
    median_quantity = float(np.median(df["quantity"]))
    std_price = float(np.std(df["price_per_unit"]))

    print(f"• Середня ціна препаратів (price_per_unit): {mean_price:.2f}")
    print(f"• Медіана кількості (quantity): {median_quantity:.1f}")
    print(f"• Стандартне відхилення ціни (price_per_unit): {std_price:.2f}")

    print("\n" + "=" * 60)
    print("3. ОБРОБКА ДАНИХ (PANDAS)")
    print("=" * 60)

    low_supply_file = output_dir / args.output_low
    low_supply_df = df[df["quantity"] < 100].copy()
    low_supply_df.to_csv(low_supply_file, index=False)
    print(f"• Відфільтровано {len(low_supply_df)} дефіцитних записів (quantity < 100)")
    print(f"• Збережено у файл: {low_supply_file.name}")

    print("\n" + "=" * 60)
    print("4. ДОДАВАННЯ ПОЛЯ total_price")
    print("=" * 60)
    df["total_price"] = df["quantity"] * df["price_per_unit"]
    print("Поле total_price успішно додано:")
    print(df[["supplier", "category", "quantity", "price_per_unit", "total_price"]].head())

    supplier_revenue = df.groupby("supplier")["total_price"].sum()
    top_supplier = str(supplier_revenue.idxmax())
    top_supplier_revenue = float(supplier_revenue.max())

    category_quantities = df.groupby("category")["quantity"].sum()

    print(f"\n• Постачальник з найбільшим прибутком: {top_supplier} ({top_supplier_revenue:.2f})")
    print("\n• Сумарна кількість препаратів за категоріями (groupby):")
    for category, qty in category_quantities.items():
        print(f"  - {category}: {qty}")

    print("\n" + "=" * 60)
    print("5. ТОП-3 ПОСТАВКИ ЗА TOTAL_PRICE (СПАДАННЯ)")
    print("=" * 60)
    sorted_df = df.sort_values(by="total_price", ascending=False)
    top_3_df = sorted_df.head(3)
    print(top_3_df.to_string(index=False))

    print("\n" + "=" * 60)
    print("6. ГЕНЕРАЦІЯ ЗВІТУ (.TXT)")
    print("=" * 60)
    report_file = output_dir / args.report
    report_content = f"""ЗВІТ: АНАЛІТИКА ПОСТАЧАНЬ
==================================================

1. СЕРЕДНІ СТАТИСТИЧНІ ПОКАЗНИКИ (NumPy):
   - Середня ціна препаратів (price_per_unit): {mean_price:.2f}
   - Медіана кількості препаратів (quantity): {median_quantity:.1f}
   - Стандартне відхилення ціни (price_per_unit): {std_price:.2f}

2. ФІНАНСОВІ ПОКАЗНИКИ:
   - Постачальник з найбільшим загальним прибутком: {top_supplier}
   - Загальний прибуток постачальника: {top_supplier_revenue:.2f}

3. ДЕФІЦИТНІ ПОСТАВКИ:
   - Назва створеного файлу з дефіцитними поставками: {low_supply_file.name}
   - Кількість виявлених дефіцитних записів (quantity < 100): {len(low_supply_df)}

4. ДОДАТКОВІ ДАНІ:
   - Сумарна кількість препаратів за категоріями:
{chr(10).join(f"     * {cat}: {q}" for cat, q in category_quantities.items())}

   - Топ-3 поставки за сумою (total_price):
{top_3_df[['supplier', 'category', 'quantity', 'price_per_unit', 'total_price']].to_string(index=False)}
==================================================
"""
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report_content)
    print(f"• Звіт збережено у: {report_file.name}")

    print("\n" + "=" * 60)
    print("7. ПОБУДОВА ГРАФІКА (MATPLOTLIB)")
    print("=" * 60)
    chart_file = output_dir / args.chart

    plt.figure(figsize=(8, 5))
    categories = list(category_quantities.index)
    quantities = list(category_quantities.values)

    colors = ["#2b5c8f", "#3caea3", "#ed553b"]
    bars = plt.bar(categories, quantities, color=colors[:len(categories)], width=0.55, edgecolor="#1f2d3d", linewidth=1.2)

    for bar in bars:
        height = bar.get_height()
        plt.text(
            bar.get_x() + bar.get_width() / 2.0,
            height + 25,
            f"{int(height)}",
            ha="center",
            va="bottom",
            fontsize=11,
            fontweight="bold"
        )

    plt.title("Розподіл сумарної кількості препаратів за категоріями", fontsize=13, fontweight="bold", pad=15)
    plt.xlabel("Категорія препаратів", fontsize=11, labelpad=10)
    plt.ylabel("Сумарна кількість (од.)", fontsize=11, labelpad=10)
    plt.ylim(0, max(quantities) * 1.15)
    plt.grid(axis="y", linestyle="--", alpha=0.6)
    plt.tight_layout()

    plt.savefig(chart_file, dpi=300)
    print(f"• Графік успішно збережено у файл: {chart_file.name}")

    if not args.no_show:
        try:
            plt.show()
        except Exception as e:
            print(f"(Графічне вікно не відкрилося у поточному середовищі: {e}. Графік збережено у файл)")

    print("\n" + "=" * 60)
    print("ВСІ ЗАВДАННЯ УСПІШНО ВИКОНАНО!")
    print("=" * 60)


if __name__ == "__main__":
    main()
