"""
Пакет системи обліку товарів.
"""

from .models import Product
from .repository import CSVProductRepository, ProductRepository, StorageError, StorageFormatError
from .validator import ProductValidator, ValidationResult
from .gui import AccountingApp

__all__ = [
    "Product",
    "ProductRepository",
    "CSVProductRepository",
    "StorageError",
    "StorageFormatError",
    "ProductValidator",
    "ValidationResult",
    "AccountingApp",
]

