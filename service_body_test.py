class Order:
    def __init__(self, id, items):
        self.id = id
        self.items = items

    def total(self):
        return sum(item['price'] * item['quantity'] for item in self.items)

    def most_expensive(self):
        return max(self.items, key=lambda x: x['price'])

    def apply_discount(self, percent):
        if not 0 <= percent <= 100:
            raise ValueError("Invalid discount")
        for item in self.items:
            item['price'] -= item['price'] * (percent / 100)

    def __repr__(self):
        return f"<Order {self.id}: {len(self.items)} items>"