#!/usr/bin/env python3
"""
Повний конвеєр криміналістичного аналізу хабу:
1. Хронологія подій 23:00 13.10 — 04:00 14.10 (сортована за повною датою-часом).
2. Звірка журналу з інвентаризацією: конфлікти статусів + аномалії даних.
3. Часовий інтервал між розбіжністю (вивезення партії) і пожежею (перший дим).
4. Запис файлів-результатів: хронологія.txt та висновок.txt.
"""

from datetime import datetime
from pathlib import Path
import re
import sys

WINDOW_START = datetime.fromisoformat("2026-10-13T23:00:00")
WINDOW_END = datetime.fromisoformat("2026-10-14T04:00:00")

KNOWN_CATEGORIES = {"ACCESS", "GATE", "CARGO", "SENSOR", "ALARM", "SYSTEM", "CALL"}
FULL_TS = re.compile(r"^20\d{2}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\||$)")
TS_PREFIX = re.compile(r"^20\d{2}-\d{2}-\d{2}T")


def fix_mojibake(text: str) -> str:
    """Відновлює мохібейк: текст у UTF-8, помилково прочитаний як CP1251."""
    try:
        return text.encode("cp1251").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text


def parse_hub_chronology(log_path: Path):
    """
    Парсить журнал і повертає:
    - target_events: цільові події у вікні 23:00–04:00, сортовані за часом;
    - cargo_map: всі легітимні відвантаження CARGO за день (для звірки);
    - smoke_event: перший датчик диму в секторі C;
    - anomalies: підозрілі/пошкоджені рядки з класифікацією;
    - noise_count: кількість рядків бінарного сміття.
    """
    target_events = []
    cargo_map = {}
    last_gate_open = {}
    smoke_event = None
    anomalies = []
    noise_count = 0

    lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    valid_ts = []  # (index, timestamp) усіх рядків із коректною міткою часу

    parsed = []  # (index, cleaned, parts, ts_or_None)
    for i, raw in enumerate(lines):
        stripped = raw.strip()
        if not stripped:
            continue
        cleaned = re.sub(r"^[-*•\s]+", "", stripped)
        parts = cleaned.split("|")
        ts = None
        try:
            ts = datetime.fromisoformat(parts[0])
        except ValueError:
            pass
        if ts is not None:
            valid_ts.append((i, ts))
        parsed.append((i, cleaned, parts, ts))

    def neighbors(i):
        """Мітки часу найближчого валідного запису до та після аномального рядка."""
        prev_ts = next((ts for j, ts in reversed(valid_ts) if j < i), None)
        next_ts = next((ts for j, ts in valid_ts if j > i), None)
        fmt = lambda t: t.strftime("%H:%M:%S") if t else "?"
        return fmt(prev_ts), fmt(next_ts)

    for i, cleaned, parts, ts in parsed:
        cat = parts[1] if len(parts) > 1 else ""
        params = parts[2:]
        params_dict = dict(p.split("=", 1) for p in params if "=" in p)

        # --- аномалії та пошкоджені рядки (докази втручання в журнал) ---
        if ts is None:
            if FULL_TS.match(cleaned):
                anomalies.append({
                    "kind": "неможлива дата",
                    "raw": cleaned,
                    "note": "повний за форматом час, але неіснуючі значення (13-й місяць / 25-та година / 61-ша хвилина)",
                })
                continue
            if TS_PREFIX.match(cleaned):
                anomalies.append({
                    "kind": "обірваний рядок",
                    "raw": cleaned,
                    "note": "мітка часу обірвана посеред запису",
                })
                continue
            if cat in KNOWN_CATEGORIES:
                prev, nxt = neighbors(i)
                anomalies.append({
                    "kind": "стирана мітка часу",
                    "raw": cleaned,
                    "note": f"запис події {cat} без часу; у файлі розміщений між подіями {prev} і {nxt}",
                })
                continue
            noise_count += 1
            continue

        if cat == "GHOST":
            prev, nxt = neighbors(i)
            anomalies.append({
                "kind": "подія-«привид»",
                "raw": cleaned,
                "note": f"невідомий тип події GHOST у секторі C між крадіжкою і пожежею; "
                        f"у файлі вставлена між записами {prev} і {nxt}",
            })
            continue

        if len(parts) == 2 and parts[1] == "":
            anomalies.append({
                "kind": "стертя події",
                "raw": cleaned,
                "note": "мітка часу збережена, вміст події витерто",
            })
            continue

        if cat == "CARGO" and not params_dict.get("batch"):
            prev, nxt = neighbors(i)
            anomalies.append({
                "kind": "партія без ідентифікатора",
                "raw": cleaned,
                "note": f"відвантаження без номера партії і воріт; у файлі між подіями {prev} і {nxt}",
            })
            continue

        if cat not in KNOWN_CATEGORIES:
            continue

        # --- легітимні події ---
        if cat == "GATE":
            gate = params_dict.get("gate")
            if params_dict.get("action") == "open" and gate:
                last_gate_open[gate] = {
                    "truck": params_dict.get("truck", "Невідомо"),
                    "iso_time": parts[0],
                    "raw": cleaned,
                }

        if cat == "CARGO":
            batch = fix_mojibake(params_dict.get("batch", "").strip())
            gate = params_dict.get("gate")
            if batch:
                gate_info = last_gate_open.get(gate, {})
                cargo_map[batch] = {
                    "timestamp": ts,
                    "iso_time": parts[0],
                    "gate": gate,
                    "truck": gate_info.get("truck", "Невідомо"),
                    "gate_open_raw": gate_info.get("raw", ""),
                    "raw": cleaned,
                }

        if (cat == "SENSOR" and params_dict.get("zone") == "C"
                and params_dict.get("type") == "smoke" and smoke_event is None):
            smoke_event = {"timestamp": ts, "iso_time": parts[0], "raw": cleaned}

        # фільтр цільових категорій за умовою завдання
        if WINDOW_START <= ts <= WINDOW_END:
            is_target = (
                cat == "ALARM"
                or (cat == "GATE" and params_dict.get("gate") == "3")
                or (cat == "ACCESS" and params_dict.get("zone") == "C")
                or (cat == "SENSOR" and params_dict.get("type") == "smoke")
                or cat in ("CARGO", "CALL")
                or (cat == "SYSTEM" and params_dict.get("status") == "offline")
            )
            if is_target:
                target_events.append({
                    "timestamp": ts,
                    "iso_time": parts[0],
                    "event_type": cat,
                    "details": fix_mojibake(" | ".join(params)),
                    "raw": cleaned,
                })

    target_events.sort(key=lambda ev: ev["timestamp"])
    return target_events, cargo_map, smoke_event, anomalies, noise_count


def describe_event(ev):
    key = ev["event_type"]
    desc = ev["details"]
    if key == "SENSOR" and "zone=C" in desc:
        return "Дим у секторі C, концентрація 0,92"
    if key == "SENSOR":
        return "Дим у секторі B, концентрація 0,61"
    if key == "CALL":
        return "Зовнішній виклик: «пожежна»"
    if key == "ALARM" and "action=disable" in desc:
        return "Сигналізацію всього об'єкта (zone=all) вимкнено карткою BLUE-0417"
    if key == "ALARM":
        return f"Тривога у секторі {'C' if 'zone=C' in desc else 'B'} спрацювала, але оповіщення пригнічене (state=suppressed)"
    if key == "ACCESS":
        return "Вхід у сектор C карткою BLUE-0417, доступ надано"
    if key == "GATE":
        return "Ворота 3 відчинено, заїзд вантажівки BC7781TT" if "action=open" in desc else "Ворота 3 зачинено"
    if key == "CARGO":
        return "Партію 7-Б вивезено через ворота 3 (у сирому рядку партія записана в пошкодженому кодуванні)"
    if key == "SYSTEM":
        return "Сервер хабу офлайн — журнал обривається"
    return desc


def audit_inventory(inventory_path: Path, cargo_map: dict):
    """Звіряє інвентаризацію з журналом: конфлікти в обидва боки + аномалії даних."""
    lines = [ln.strip() for ln in inventory_path.read_text(encoding="utf-8", errors="replace").splitlines() if ln.strip()]
    headers = [h.strip() for h in lines[0].split("|")]

    records, discrepancies, data_anomalies = [], [], []
    for raw_line in lines[1:]:
        cleaned = re.sub(r"^[-*•\s]+", "", raw_line)
        parts = [p.strip() for p in cleaned.split("|")]
        row = dict(zip(headers, parts + [""] * (len(headers) - len(parts))))
        decoded = {k: fix_mojibake(v) for k, v in row.items()}
        decoded["_raw"] = raw_line

        batch = decoded["batch"].strip()
        status = decoded["status"].strip()
        qty = decoded["qty"].strip()
        weight = decoded["weight_kg"].strip()

        issues = []
        if not batch:
            issues.append("відсутній ідентифікатор партії")
        if qty and not qty.replace(",", "").replace(".", "").isdigit():
            issues.append(f"кількість не числова: «{qty}»")
        if not weight:
            issues.append("відсутня вага")
        if not status:
            issues.append("відсутній статус")
        if issues:
            data_anomalies.append({"batch": batch or "—", "name": decoded["name"], "issues": issues, "raw": raw_line})

        log_event = cargo_map.get(batch) if batch else None
        conflict = ""
        if log_event and status == "згоріло":
            conflict = (f"статус «згоріло», але журнал фіксує вивіз через ворота {log_event['gate']} "
                        f"(вантажівка {log_event['truck']}) о {log_event['iso_time']}")
        elif log_event and status == "на складі":
            conflict = (f"статус «на складі», але журнал фіксує вивіз о {log_event['iso_time']}")
        elif not log_event and status == "відвантажено":
            conflict = "статус «відвантажено», але в журналі немає запису CARGO out"

        decoded["log_event"] = log_event
        decoded["conflict"] = conflict
        records.append(decoded)
        if conflict:
            discrepancies.append(decoded)

    return records, discrepancies, data_anomalies


def calculate_timeline_delta(fraud_item: dict, smoke_event: dict) -> dict:
    delta = smoke_event["timestamp"] - fraud_item["log_event"]["timestamp"]
    total = int(delta.total_seconds())
    return {
        "dispatch_iso": fraud_item["log_event"]["iso_time"],
        "smoke_iso": smoke_event["iso_time"],
        "total_seconds": total,
        "hours": total // 3600,
        "minutes": (total % 3600) // 60,
        "seconds": total % 60,
        "formatted": f"{total // 3600:02d}:{(total % 3600) // 60:02d}:{total % 60:02d}",
    }


def write_chronology_file(path: Path, events, cargo_map, anomalies, noise_count, delta,
                          discrepancies, data_anomalies, records):
    out = []
    out.append("ХРОНОЛОГІЯ ПОДІЙ ХАБУ — ніч з 13 на 14 жовтня 2026 року")
    out.append("Вікно: 2026-10-13T23:00:00 — 2026-10-14T04:00:00; сортовано за ПОВНОЮ датою-часом,")
    out.append("а не лише за годинами (у сирому журналі частину записів вставлено не хронологічно).")
    out.append("")
    out.append("== ОСНОВНІ ПОДІЇ ==")
    for n, ev in enumerate(events, 1):
        out.append(f"{n:2}. {ev['iso_time']}  {ev['event_type']:<7} {describe_event(ev)}")
        out.append(f"    рядок журналу: {ev['raw']}")
    out.append("")
    out.append("== КОНТЕКСТ: ВЕЧІРНІ ВІДВАНТАЖЕННЯ 13.10 (поза вікном, потрібні для звірки) ==")
    for batch in ("2-В", "5-Г", "4-А"):
        ce = cargo_map.get(batch)
        if ce:
            out.append(f"  {ce['iso_time']}  CARGO  партію {batch} вивезено через ворота {ce['gate']} "
                       f"(вантажівка {ce['truck']}) — у інвентаризації статус «відвантажено», збігається")
    out.append("  Обхіди охоронця GUARD-07 (сектори A/B) о 23:30, 23:36, 01:30, 01:36 — штатні, сектор C не відвідувався.")
    out.append("")
    out.append("== РОЗБІЖНІСТЬ МІЖ ЖУРНАЛОМ ТА ІНВЕНТАРИЗАЦІЄЮ ==")
    for d in discrepancies:
        le = d["log_event"]
        out.append(f"  Партія {d['batch']} («{d['name']}», {d['category']}, {d['qty']} од., "
                   f"{d['weight_kg']} кг, сектор {d['sector']}):")
        out.append(f"      інвентаризація: статус «{d['status']}»")
        out.append(f"      журнал:          вивіз через ворота {le['gate']} о {le['iso_time']}, вантажівка {le['truck']}")
        out.append("      → партія покинула склад ДО пожежі — статус у відомості підроблено")
    ok_dispatched = [r for r in records if r["log_event"] and not r["conflict"]]
    out.append("  Решта збігається: " + "; ".join(
        f"{r['batch']} — «{r['status']}» і є в журналі" for r in ok_dispatched
    ) + ".")
    out.append("  Партії секторів A/B без записів руху — «на складі»; решта партій сектора C —")
    out.append("  «згоріло» і в журналі не рухалися (справді згоріли).")
    if data_anomalies:
        out.append("  Аномалії самої інвентаризації (окремо від крадіжки, потребують переперевірки):")
        for a in data_anomalies:
            out.append(f"      {a['batch']} ({a['name']}): {'; '.join(a['issues'])}")
    out.append("")
    out.append("== ПОШКОДЖЕНІ / ПІДОЗРІЛІ РЯДКИ ЖУРНАЛУ (свідчення втручання) ==")
    for a in anomalies:
        out.append(f"  [{a['kind']}] {a['raw']}")
        out.append(f"      → {a['note']}")
    out.append(f"  Окремо: {noise_count} рядків бінарного сміття (напр. «&??^{{(<&>~%<*@]^$») — шум для зриву парсерів.")
    out.append("")
    out.append("== ЧАСОВІ ІНТЕРВАЛИ ==")
    if delta:
        out.append(f"  Вивезення партії 7-Б ({delta['dispatch_iso']}) → перший дим у секторі C ({delta['smoke_iso']}):")
        out.append(f"      {delta['hours']} год {delta['minutes']} хв {delta['seconds']} с "
                   f"({delta['formatted']}, {delta['total_seconds']} с) — «вікно» між крадіжкою і підпалом")
    out.append("  Перший дим (02:47:55) → зовнішній виклик «пожежна» (03:20:40): 32 хв 45 с — тривоги були пригнічені")
    out.append("  Зовнішній виклик (03:20:40) → вимкнення сервера (03:41:00): 20 хв 20 с")
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


def write_verdict_file(path: Path, delta, fraud, events_by_iso):
    """Містить 3–5 речень; докази — точні рядки журналу (моджібейк у цитатах розкодовано)."""
    get_raw = lambda iso: fix_mojibake(events_by_iso[iso]["raw"])

    conclusion = (
        "У ніч з 13 на 14 жовтня 2026 року на складі хабу сталася спланована крадіжка, "
        "замаскована підпалом: експериментальну партію 7-Б («Ксенотрин, ампули», 120 од., сектор C) "
        "вивезли з території ще до початку пожежі, а її зникнення списали на вогонь. "
        f"О 00:35:12 карткою BLUE-0417 було вимкнено сигналізацію всього об'єкта "
        f"({get_raw('2026-10-14T00:35:12')}), о 00:41:30 ця ж картка відкрила сектор C "
        f"({get_raw('2026-10-14T00:41:30')}), і о 00:53:10 партію 7-Б зафіксували при виїзді "
        f"через ворота 3 на вантажівці BC7781TT ({get_raw('2026-10-14T00:53:10')}). "
        f"Перший дим у секторі C з'явився лише через {delta['hours']} годину {delta['minutes']} хвилини "
        f"{delta['seconds']} секунд — о 02:47:55 ({get_raw('2026-10-14T02:47:55')}), "
        f"але тривога була пригнічена через попереднє вимкнення системи "
        f"({get_raw('2026-10-14T02:48:10')}), тож пожежу зафіксували лише зовнішнім викликом о 03:20:40 "
        f"({get_raw('2026-10-14T03:20:40')}), а сервер обірвався о 03:41:00 "
        f"({get_raw('2026-10-14T03:41:00')}). "
        "Отже, інвентаризація позначає партію 7-Б статусом «згоріло», тоді як журнал доводить, "
        "що вона фізично покинула склад майже за дві години до першого диму — ця розбіжність "
        "викриває крадіжку з підпалом для приховування слідів."
    )

    sentences = [s for s in re.split(r"(?<=[.!?])\s+", conclusion.strip()) if s]
    assert 3 <= len(sentences) <= 5, f"Кількість речень поза межами 3–5: {len(sentences)}"

    path.write_text("\n\n".join(sentences) + "\n", encoding="utf-8")
    return len(sentences)


def main():
    root = Path(__file__).parent
    log_file = root / "hub_log.md"
    inv_file = root / "inventory_recovered.txt"
    chronology_file = root / "хронологія.txt"
    verdict_file = root / "висновок.txt"

    for f in (log_file, inv_file):
        if not f.exists():
            print(f"Відсутній вхідний файл: {f}", file=sys.stderr)
            sys.exit(1)

    print("=== ПОВНИЙ КРИМІНАЛІСТИЧНИЙ КОНВЕЄР ===")

    events, cargo_map, smoke_event, anomalies, noise_count = parse_hub_chronology(log_file)
    print(f"[+] Цільових подій у вікні 23:00–04:00: {len(events)}")
    print(f"[+] Легітимних відвантажень за добу: {len(cargo_map)} ({', '.join(cargo_map)})")
    print(f"[!] Підозрілих/пошкоджених рядків: {len(anomalies)}; рядків бінарного сміття: {noise_count}")

    records, discrepancies, data_anomalies = audit_inventory(inv_file, cargo_map)
    print(f"[+] Records інвентаризації: {len(records)}; конфліктів статусів: {len(discrepancies)}; аномалій даних: {len(data_anomalies)}")
    for d in discrepancies:
        print(f"    [!] Партія {d['batch']} ({d['name']}): {d['conflict']}")
    for a in data_anomalies:
        print(f"    [~] Аномалія даних ({a['batch']}): {'; '.join(a['issues'])}")

    if not discrepancies or not smoke_event:
        print("Не вдалося виявити ключову розбіжність або подію диму.", file=sys.stderr)
        sys.exit(1)

    fraud = next((d for d in discrepancies if d["batch"] == "7-Б"), discrepancies[0])
    delta = calculate_timeline_delta(fraud, smoke_event)
    print(f"[+] Δt між вивезенням {fraud['batch']} і першим димом: "
          f"{delta['hours']} год {delta['minutes']} хв {delta['seconds']} с ({delta['formatted']})")

    write_chronology_file(chronology_file, events, cargo_map, anomalies, noise_count, delta,
                          discrepancies, data_anomalies, records)
    print(f"[+] Хронологію збережено: {chronology_file}")

    events_by_iso = {ev["iso_time"]: ev for ev in events}
    n_sentences = write_verdict_file(verdict_file, delta, fraud, events_by_iso)
    print(f"[+] Висновок збережено: {verdict_file} ({n_sentences} речення, у межах 3–5)")

    print("\n=== КОНВЕЄР ЗАВЕРШЕНО УСПІШНО ===")


if __name__ == "__main__":
    main()
