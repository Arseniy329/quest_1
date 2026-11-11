#!/usr/bin/env python3
"""
Точка входу для запуску програми складського обліку з кореневої папки.
"""
import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from accounting_app.accounting_app import main

if __name__ == "__main__":
    main()

