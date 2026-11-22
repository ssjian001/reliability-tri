import unittest
from reliability_engine import Quantity, evaluate_expression, parse
from reliability_engine.errors import ParseError, DimensionMismatch, UnitError, MissingInput

class DSLTests(unittest.TestCase):
    def test_temperature_threshold(self):
        self.assertTrue(evaluate_expression("local_ambient_temp <= 70[degC]", {"local_ambient_temp":{"value":65,"unit":"degC"}}))
    def test_unit_conversion(self):
        self.assertTrue(evaluate_expression("input_voltage >= 3.7[V]", {"input_voltage":{"value":3700,"unit":"mV"}}))
    def test_compound_dimension_algebra(self):
        self.assertEqual(evaluate_expression("v * i > 0[W]", {"v":{"value":5,"unit":"V"},"i":{"value":1,"unit":"A"}}),True)
        self.assertEqual(evaluate_expression("v / i > 0[Ohm]", {"v":{"value":5,"unit":"V"},"i":{"value":1,"unit":"A"}}),True)
        self.assertEqual(evaluate_expression("rth * p > 0[deltaK]", {"rth":{"value":10,"unit":"K/W"},"p":{"value":2,"unit":"W"}}),True)
    def test_explicit_text_aliases(self):
        self.assertAlmostEqual(Quantity.of(1,"millivolt").in_unit("V"),0.001)
        self.assertAlmostEqual(Quantity.of(1,"°C").in_unit("K"),274.15)
    def test_charge_coulomb_is_not_celsius(self):
        self.assertEqual(Quantity.of(1,"C").dimension,"capacity_charge")
        self.assertEqual(Quantity.of(1,"degC").dimension,"temperature")
    def test_case_sensitive_prefix(self):
        self.assertAlmostEqual(Quantity.of(1,"mW").value, .001)
        with self.assertRaises(Exception): Quantity.of(1,"MW")
    def test_fahrenheit_to_celsius_comparison(self):
        self.assertTrue(evaluate_expression("t < 100[degC]", {"t":{"value":200,"unit":"degF"}}))
    def test_boolean_is_not_numeric(self):
        with self.assertRaises(UnitError): Quantity.of(True,"V")
    def test_expression_size_limit(self):
        with self.assertRaises(ParseError): parse("a+" * 260 + "1")
    def test_non_finite_rejected(self):
        with self.assertRaises(UnitError): Quantity.of(float("inf"), "V")
    def test_dimension_mismatch(self):
        with self.assertRaises(DimensionMismatch): evaluate_expression("voltage > current", {"voltage":{"value":5,"unit":"V"},"current":{"value":1,"unit":"A"}})
    def test_absolute_temperature_cannot_add(self):
        with self.assertRaises(UnitError): evaluate_expression("a + b > 0[K]", {"a":{"value":20,"unit":"degC"},"b":{"value":30,"unit":"degC"}})
    def test_missing_input(self):
        with self.assertRaises(MissingInput): evaluate_expression("x > 1[V]", {})
    def test_safe_function(self):
        self.assertTrue(evaluate_expression("max(a, b) >= 4[V]", {"a":{"value":3,"unit":"V"},"b":{"value":4,"unit":"V"}}))
    def test_forbidden_attribute_or_function(self):
        for s in ("x.__class__", "__import__('os')", "x[0]", "x = 1"):
            with self.assertRaises(ParseError): parse(s)
    def test_boolean_logic(self):
        self.assertTrue(evaluate_expression("a > 2[V] and b < 10[V]", {"a":{"value":3,"unit":"V"},"b":{"value":4,"unit":"V"}}))

if __name__=="__main__": unittest.main()
