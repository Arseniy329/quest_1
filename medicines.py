medicines = [
    ("Амоксицилін", 44, "antibiotic", 18.5),
    ("Вітамін C", 250, "vitamin", 28.0),
    ("Вакцина проти грипу", 50, "vaccine", 3.2),
    ("Зіпсований запис", 67, "vitamin", 15.0),
]

result = []

for name, quantity, category, temp in medicines:
    if not isinstance(quantity, int) or not isinstance(temp, (int, float)):
        print(f"Помилка: неправильний тип даних для '{name}'")
        continue

    if temp < 5:
        temp_stat = "занадто холодно"
    elif temp > 25:
        temp_stat = "занадто жарко"
    else:
        temp_stat = "норма"

    match category:
        case "antibiotic":
            cat_status = "Рецептурний препарат"
        case "vitamin":
            cat_status = "Вільний продаж"
        case "vaccine":
            cat_status = "Потребує спецзберігання"
        case _:
            cat_status = "Невідома категорія"

    result.append(f"Назва: {name} | Категорія: {cat_status} | Температурні умови: {temp_stat} ({temp}°C) | Кількість: {quantity}")

print(*result, sep="\n")