import unittest
from reliability_engine import Quantity, lookup_curve, RuleExecutor, CurveRepository
from reliability_engine.errors import EvaluationError

class CurveTests(unittest.TestCase):
    def setUp(self):
        self.points=[(Quantity.of(0,"A"),Quantity.of(1,"Ohm")),(Quantity.of(10,"A"),Quantity.of(3,"Ohm"))]
    def test_midpoint_linear_interpolation(self): self.assertAlmostEqual(lookup_curve(Quantity.of(5,"A"),self.points).in_unit("Ohm"),2)
    def test_exact_boundary(self): self.assertAlmostEqual(lookup_curve(Quantity.of(10,"A"),self.points).in_unit("Ohm"),3)
    def test_out_of_range_rejected(self):
        with self.assertRaises(EvaluationError): lookup_curve(Quantity.of(11,"A"),self.points)
    def test_clamp(self): self.assertAlmostEqual(lookup_curve(Quantity.of(11,"A"),self.points,extrapolation="clamp").in_unit("Ohm"),3)
    def test_unsorted_rejected(self):
        with self.assertRaises(EvaluationError): lookup_curve(Quantity.of(5,"A"),list(reversed(self.points)))
    def test_expression_executor(self):
        out=RuleExecutor().execute({"rule_id":"R1","rule_type":"expression","expression":"v >= 3.7[V]"},{"v":{"value":3.8,"unit":"V"}})
        self.assertEqual(out["status"],"pass")
    def test_schema_style_lookup_curve_2d(self):
        repo=CurveRepository()
        repo.register("SOA-DEMO",x_unit="ms",y_unit="V",z_unit="A",
                      x_values=[1,10],y_values=[10,100],z_values=[[10,20],[20,40]],interpolation="log_log_linear")
        rule={"rule_id":"SOA","rule_type":"lookup_curve",
              "inputs":[{"name":"soa_curve_table","unit":"table"},{"name":"pulse_width_ms","unit":"ms"},{"name":"peak_vds","unit":"V"},{"name":"peak_id","unit":"A"}],
              "curve_eval":{"interpolation":"log_log_linear","expression":"peak_id <= lookup_max_id(soa_curve_table, pulse_width_ms, peak_vds) * safety_margin_ratio","safety_margin_ratio":0.8,"curve_out_of_bounds":"error"}}
        out=RuleExecutor(curves=repo).execute(rule,{"soa_curve_table":"SOA-DEMO","pulse_width_ms":1,"peak_vds":10,"peak_id":7})
        self.assertEqual(out["status"],"pass")
    def test_schema_style_soa_temperature_derating_and_precondition(self):
        repo=CurveRepository()
        repo.register("SOA-TEMP",x_unit="ms",y_unit="V",z_unit="A",
                      x_values=[1,10],y_values=[10,100],z_values=[[10,20],[20,40]],interpolation="log_log_linear")
        rule={"rule_id":"SOA-TEMP","rule_type":"lookup_curve",
              "preconditions":"(soa_curve_table != null)",
              "inputs":[{"name":"soa_curve_table","unit":"table"},{"name":"pulse_width_ms","unit":"ms"},{"name":"peak_vds","unit":"V"},{"name":"peak_id","unit":"A"},{"name":"case_temp","unit":"degC"}],
              "curve_eval":{"interpolation":"log_log_linear","temp_derating_factor":"1 - (case_temp - 25[degC]) / (150[degC] - 25[degC])",
                            "expression":"peak_id <= lookup_max_id(soa_curve_table, pulse_width_ms, peak_vds) * temp_derating_factor * safety_margin_ratio",
                            "safety_margin_ratio":0.8,"curve_out_of_bounds":"error"}}
        out=RuleExecutor(curves=repo).execute(rule,{"soa_curve_table":"SOA-TEMP","pulse_width_ms":1,"peak_vds":10,"peak_id":5,"case_temp":25})
        self.assertEqual(out["status"],"pass")
    def test_precondition_skip(self):
        rule={"rule_id":"PRE","rule_type":"declarative_expr","preconditions":"ambient < 70[degC]","inputs":[{"name":"ambient","unit":"degC"}],"expression":"ambient < 80[degC]"}
        out=RuleExecutor().execute(rule,{"ambient":75})
        self.assertEqual(out["status"],"skipped")
    def test_curve_executor(self):
        rule={"rule_id":"R2","rule_type":"lookup_curve","curve":{"input":"load","points":[[{"value":0,"unit":"A"},{"value":1,"unit":"Ohm"}],[{"value":10,"unit":"A"},{"value":3,"unit":"Ohm"}]]}}
        out=RuleExecutor().execute(rule,{"load":{"value":5,"unit":"A"}})
        self.assertEqual(out["status"],"pass"); self.assertAlmostEqual(out["result"]["value"],2)

if __name__=="__main__": unittest.main()
