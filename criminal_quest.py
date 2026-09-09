result = []
deals = [
    ("Маша", 0, "fraud"),
    ("Олег", 50, "clean"),
    ("Ігор", 500, "suspicious"),
    ("Артем", 1500, "fraud"),
    ("Жора", 3500, "fraud"),
    ("Фантом", 500, "clean")
]

for name, sum, level in deals:
    if not isinstance(name, (str)) or not isinstance(sum, (float, int)):
        name_stat = "Фальшиві дані"
        print("Помила вводу, перевірте дані")
        break

    if sum < 100:
        sum_stat = "Дрібнота"
    elif 100 <= sum <= 999:
        sum_stat = "Срєднячок"
    else:
        sum_stat = "Крупняк"

    match level:
        case "fraud":
            level_stat = "Чорний список"
        case "suspicious":
            level_stat = "Перевірити документи"
        case "clean":
            level_stat = "Працювати без питань"
        case _:
            level_stat = "Невідомий статус"

    result.append((name, sum_stat, level_stat))
print(*result, sep="\n")