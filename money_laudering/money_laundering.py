from functools import wraps
from typing import Any, Callable, Generator, Iterable, Optional


def parse_transaction(tx: Any) -> Optional[float]:
    if not isinstance(tx, str):
        return None

    parts = tx.strip().split()
    if len(parts) != 2:
        return None

    try:
        amount = float(parts[1])
        return amount if amount >= 0 else None
    except ValueError:
        return None


def shadow(limit: float = 200):
    def decorator(gen_func: Callable[..., Generator[str, None, Any]]):
        @wraps(gen_func)
        def wrapper(*args, **kwargs) -> Generator[str, None, Any]:
            gen = gen_func(*args, **kwargs)
            accumulated = 0.0
            triggered = False

            try:
                while True:
                    item = next(gen)
                    amount = parse_transaction(item)
                    if amount is not None:
                        accumulated += amount
                        if accumulated > limit and not triggered:
                            print("Тіньовий ліміт перевищено. Активую схему.")
                            triggered = True
                    yield item
            except StopIteration as e:
                return e.value

        return wrapper

    if callable(limit):
        func = limit
        limit = 200
        return decorator(func)

    return decorator


def suspicious_counter(threshold: float = 100):
    def decorator(gen_func: Callable[..., Generator[str, None, Any]]):
        @wraps(gen_func)
        def wrapper(*args, **kwargs) -> Generator[str, None, Any]:
            gen = gen_func(*args, **kwargs)
            suspicious_total = 0.0
            suspicious_count = 0

            try:
                while True:
                    item = next(gen)
                    amount = parse_transaction(item)
                    if amount is not None and amount > threshold:
                        suspicious_total += amount
                        suspicious_count += 1
                        print(
                            f"[suspicious_counter] Увага! Транзакція перевищила ліміт {threshold}: "
                            f"{amount}. Всього підозрілих операцій: {suspicious_count} "
                            f"(на суму: {suspicious_total})"
                        )
                    yield item
            except StopIteration as e:
                return e.value

        return wrapper

    if callable(threshold):
        func = threshold
        threshold = 100
        return decorator(func)

    return decorator


@suspicious_counter(threshold=150)
@shadow(limit=200)
def transaction_stream(transactions: Iterable[Any]) -> Generator[str, None, float]:
    total_sum = 0.0

    for tx in transactions:
        print(tx)
        yield tx

        amount = parse_transaction(tx)
        if amount is not None:
            total_sum += amount

    return total_sum


def consume_generator(gen: Generator[Any, None, Any]) -> Any:
    try:
        while True:
            next(gen)
    except StopIteration as e:
        return e.value


if __name__ == "__main__":
    sample_data = [
        "payment 120",
        "invalid_format_string",
        "refund 50",
        "corrupted 9999 extra",
        "transfer 300",
        "payment not_a_number",
        "cash 80",
    ]

    gen = transaction_stream(sample_data)
    final_amount = consume_generator(gen)
    print(f"\nФінальна сума: {final_amount}")
