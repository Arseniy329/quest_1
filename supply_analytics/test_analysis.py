import os
import subprocess
import tempfile
import pandas as pd
import numpy as np
import pytest
from pathlib import Path


def test_analysis_script_execution():
    analytics_dir = Path(__file__).resolve().parent
    script_path = analytics_dir / "analysis.py"
    csv_path = analytics_dir / "supplies.csv"

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        low_supply_file = tmp_path / "test_low_supply.csv"
        report_file = tmp_path / "test_report.txt"
        chart_file = tmp_path / "test_chart.png"

        cmd = [
            "python3",
            str(script_path),
            str(csv_path),
            "--output-low",
            str(low_supply_file),
            "--report",
            str(report_file),
            "--chart",
            str(chart_file),
            "--no-show"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(tmp_path))
        assert result.returncode == 0, f"Script failed: {result.stderr}"

        # Перевірка створення файлів
        assert low_supply_file.exists()
        assert report_file.exists()
        assert chart_file.exists()

        # Перевірка вмісту low_supply.csv
        low_df = pd.read_csv(low_supply_file)
        assert len(low_df) == 7
        assert (low_df["quantity"] < 100).all()

        # Перевірка вмісту звіту
        report_text = report_file.read_text(encoding="utf-8")
        assert "4.52" in report_text
        assert "100.0" in report_text
        assert "2.95" in report_text
        assert "BioPharm" in report_text
        assert "test_low_supply.csv" in report_text
