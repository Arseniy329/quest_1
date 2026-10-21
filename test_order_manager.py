import pytest
from service_body_test import Order


@pytest.fixture
def empty_order():
    return Order(id=1, items=[])


@pytest.fixture
def sample_order():
    return Order(
        id=42,
        items=[
            {"name": "Клавіатура", "price": 100.0, "quantity": 1},
            {"name": "Мишка", "price": 50.0, "quantity": 2},
            {"name": "Килимок", "price": 20.0, "quantity": 3},
        ],
    )


# total tests

def test_total_empty_items(empty_order):
    assert empty_order.total() == 0


def test_total_single_item():
    order = Order(id=2, items=[{"name": "Ноутбук", "price": 1500.0, "quantity": 2}])
    assert order.total() == 3000.0


def test_total_multiple_items(sample_order):
    assert sample_order.total() == 260.0


def test_total_with_zero_price_or_quantity():
    order = Order(
        id=3,
        items=[
            {"name": "Безкоштовний бонус", "price": 0.0, "quantity": 5},
            {"name": "Товар із нульовою кількістю", "price": 100.0, "quantity": 0},
        ],
    )
    assert order.total() == 0.0


def test_total_float_precision():
    order = Order(
        id=4,
        items=[
            {"name": "Кава", "price": 19.99, "quantity": 3},
            {"name": "Цукор", "price": 2.49, "quantity": 2},
        ],
    )
    expected = 19.99 * 3 + 2.49 * 2
    assert order.total() == pytest.approx(expected)


# most_expensive tests

def test_most_expensive_multiple_items(sample_order):
    most_exp = sample_order.most_expensive()
    assert most_exp["name"] == "Клавіатура"
    assert most_exp["price"] == 100.0


def test_most_expensive_single_item():
    single_item = {"name": "Монітор", "price": 500.0, "quantity": 1}
    order = Order(id=5, items=[single_item])
    assert order.most_expensive() == single_item


def test_most_expensive_same_prices():
    item1 = {"name": "Товар 1", "price": 100.0, "quantity": 1}
    item2 = {"name": "Товар 2", "price": 100.0, "quantity": 1}
    order = Order(id=6, items=[item1, item2])
    assert order.most_expensive() == item1


def test_most_expensive_empty_items_value_error(empty_order):
    with pytest.raises(ValueError):
        empty_order.most_expensive()


# apply_discount tests

@pytest.mark.parametrize("valid_percent", [0, 0.0, 15.5, 50, 100, 100.0])

def test_apply_discount_valid_range(valid_percent):
    order = Order(id=7, items=[{"name": "Товар", "price": 100.0, "quantity": 1}])
    order.apply_discount(valid_percent)


@pytest.mark.parametrize("invalid_percent", [-100, -1, -0.01, 100.01, 101, 250])

def test_apply_discount_invalid_range_raises_value_error(invalid_percent):
    order = Order(id=8, items=[{"name": "Товар", "price": 100.0, "quantity": 1}])

    with pytest.raises(ValueError, match="Invalid discount"):
        order.apply_discount(invalid_percent)


# test prices after discount

def test_apply_discount_updates_all_items_prices(sample_order):
    initial_prices = [item["price"] for item in sample_order.items]
    sample_order.apply_discount(20)

    expected_prices = [price * 0.8 for price in initial_prices]
    actual_prices = [item["price"] for item in sample_order.items]

    assert actual_prices == pytest.approx(expected_prices)
    assert sample_order.items[0]["price"] == pytest.approx(80.0)
    assert sample_order.items[1]["price"] == pytest.approx(40.0)
    assert sample_order.items[2]["price"] == pytest.approx(16.0)


def test_apply_discount_boundary_zero_percent(sample_order):
    sample_order.apply_discount(0)
    assert sample_order.items[0]["price"] == 100.0
    assert sample_order.items[1]["price"] == 50.0
    assert sample_order.items[2]["price"] == 20.0


def test_apply_discount_boundary_hundred_percent(sample_order):
    sample_order.apply_discount(100)
    for item in sample_order.items:
        assert item["price"] == pytest.approx(0.0)


def test_apply_discount_empty_items(empty_order):
    empty_order.apply_discount(50)
    assert empty_order.items == []


def test_apply_discount_affects_total(sample_order):
    sample_order.apply_discount(50)
    assert sample_order.total() == pytest.approx(130.0)


# __repr__ tests

def test_repr_empty_order(empty_order):
    assert repr(empty_order) == "<Order 1: 0 items>"
    assert str(empty_order) == "<Order 1: 0 items>"


def test_repr_with_items(sample_order):
    assert repr(sample_order) == "<Order 42: 3 items>"


def test_repr_with_string_id():
    order = Order(id="ORD-999", items=[{"name": "A", "price": 10, "quantity": 1}])
    assert repr(order) == "<Order ORD-999: 1 items>"
