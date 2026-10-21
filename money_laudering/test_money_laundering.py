import pytest
from money_laudering.money_laundering import (
    parse_transaction,
    shadow,
    suspicious_counter,
    transaction_stream,
    consume_generator,
)


def test_parse_transaction_valid():
    assert parse_transaction("payment 120") == 120.0
    assert parse_transaction("refund 50") == 50.0
    assert parse_transaction("transfer 300.5") == 300.5
    assert parse_transaction("  deposit   40   ") == 40.0


def test_parse_transaction_invalid():
    assert parse_transaction("invalid") is None
    assert parse_transaction("payment not_a_number") is None
    assert parse_transaction("too many tokens 100") is None
    assert parse_transaction("payment -50") is None
    assert parse_transaction("") is None
    assert parse_transaction(None) is None
    assert parse_transaction(12345) is None


def test_generator_yields_all_items_and_returns_total(capsys):
    data = ["payment 100", "invalid", "refund 50"]
    gen = transaction_stream(data)

    items = []
    try:
        while True:
            items.append(next(gen))
    except StopIteration as e:
        total = e.value

    assert items == data
    assert total == 150.0

    captured = capsys.readouterr()
    for item in data:
        assert item in captured.out


def test_shadow_decorator_default_limit(capsys):
    @shadow()
    def sample_gen(items):
        total = 0.0
        for item in items:
            yield item
            val = parse_transaction(item)
            if val is not None:
                total += val
        return total

    items = ["payment 120", "refund 50", "transfer 40", "bonus 10"]
    gen = sample_gen(items)
    total = consume_generator(gen)

    assert total == 220.0
    captured = capsys.readouterr()
    assert "Тіньовий ліміт перевищено. Активую схему." in captured.out
    assert captured.out.count("Тіньовий ліміт перевищено. Активую схему.") == 1


def test_shadow_decorator_custom_limit(capsys):
    @shadow(limit=500)
    def sample_gen(items):
        total = 0.0
        for item in items:
            yield item
            val = parse_transaction(item)
            if val is not None:
                total += val
        return total

    items = ["payment 300", "transfer 150"]
    gen = sample_gen(items)
    total = consume_generator(gen)

    assert total == 450.0
    captured = capsys.readouterr()
    assert "Тіньовий ліміт перевищено" not in captured.out


def test_suspicious_counter_decorator(capsys):
    @suspicious_counter(threshold=100)
    def sample_gen(items):
        for item in items:
            yield item

    items = ["payment 50", "payment 150", "refund 80", "transfer 200"]
    gen = sample_gen(items)
    consume_generator(gen)

    captured = capsys.readouterr()
    assert "Транзакція перевищила ліміт 100: 150.0" in captured.out
    assert "Транзакція перевищила ліміт 100: 200.0" in captured.out
    assert captured.out.count("[suspicious_counter]") == 2


def test_stacked_decorators_independence(capsys):
    @suspicious_counter(threshold=150)
    @shadow(limit=200)
    def sample_gen(items):
        total = 0.0
        for item in items:
            yield item
            val = parse_transaction(item)
            if val is not None:
                total += val
        return total

    items = [
        "payment 120",
        "invalid",
        "refund 50",
        "transfer 300",
        "cash 10",
    ]

    gen = sample_gen(items)
    total = consume_generator(gen)

    assert total == 480.0
    captured = capsys.readouterr()

    assert "Тіньовий ліміт перевищено. Активую схему." in captured.out
    assert "Транзакція перевищила ліміт 150: 300.0" in captured.out
