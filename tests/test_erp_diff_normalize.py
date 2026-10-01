"""Tests unitarios de normalización: fechas, importes PYG y detección de tipo."""

from __future__ import annotations

import datetime
import unittest
from decimal import Decimal

from src.erp_diff_engine.normalize import (
    detect_type,
    normalize_for_compare,
    raw_type_label,
    try_parse_date,
    try_parse_pyg_amount,
)


class DateParsingTests(unittest.TestCase):
    def test_parses_dd_mm_yyyy(self) -> None:
        self.assertEqual(try_parse_date("15/03/2024"), datetime.date(2024, 3, 15))

    def test_datetime_object_normalizes_to_date(self) -> None:
        self.assertEqual(
            try_parse_date(datetime.datetime(2024, 3, 15, 8, 30)), datetime.date(2024, 3, 15)
        )

    def test_non_date_text_returns_none(self) -> None:
        self.assertIsNone(try_parse_date("no es una fecha"))

    def test_plain_number_is_not_treated_as_date(self) -> None:
        self.assertIsNone(try_parse_date("1234567"))


class PygAmountParsingTests(unittest.TestCase):
    def test_thousands_dot_format(self) -> None:
        self.assertEqual(try_parse_pyg_amount("1.234.567"), Decimal("1234567"))

    def test_currency_prefix_gs(self) -> None:
        self.assertEqual(try_parse_pyg_amount("Gs. 1.234.567"), Decimal("1234567"))

    def test_currency_symbol(self) -> None:
        self.assertEqual(try_parse_pyg_amount("₲1.234.567"), Decimal("1234567"))

    def test_numeric_value_passthrough(self) -> None:
        self.assertEqual(try_parse_pyg_amount(1234567), Decimal("1234567"))

    def test_non_amount_text_returns_none(self) -> None:
        self.assertIsNone(try_parse_pyg_amount("no es un importe"))

    def test_bool_is_not_an_amount(self) -> None:
        self.assertIsNone(try_parse_pyg_amount(True))


class DetectTypeTests(unittest.TestCase):
    def test_empty_values(self) -> None:
        self.assertEqual(detect_type(None), "empty")
        self.assertEqual(detect_type(""), "empty")
        self.assertEqual(detect_type("   "), "empty")

    def test_bool_before_int(self) -> None:
        self.assertEqual(detect_type(True), "bool")

    def test_date_text_vs_amount_text(self) -> None:
        self.assertEqual(detect_type("15/03/2024"), "date_text")
        self.assertEqual(detect_type("1.234.567"), "amount_text")
        self.assertEqual(detect_type("hola"), "text")


class NormalizeForCompareTests(unittest.TestCase):
    def test_date_text_equals_date_object(self) -> None:
        a = normalize_for_compare(datetime.date(2024, 3, 15))
        b = normalize_for_compare("15/03/2024")
        self.assertEqual(a, b)

    def test_amount_text_equals_number(self) -> None:
        a = normalize_for_compare(1234567)
        b = normalize_for_compare("1.234.567")
        self.assertEqual(a, b)

    def test_different_amounts_are_not_equal(self) -> None:
        a = normalize_for_compare("1.234.567")
        b = normalize_for_compare("1.235.000")
        self.assertNotEqual(a, b)

    def test_text_is_stripped(self) -> None:
        self.assertEqual(normalize_for_compare("  hola  "), "hola")


class RawTypeLabelTests(unittest.TestCase):
    def test_none_label(self) -> None:
        self.assertEqual(raw_type_label(None), "NoneType")

    def test_int_vs_str_label(self) -> None:
        self.assertEqual(raw_type_label(1), "int")
        self.assertEqual(raw_type_label("1"), "str")


if __name__ == "__main__":
    unittest.main()
