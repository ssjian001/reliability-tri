import json, sys, unittest
from reliability_engine import PluginRegistry, PluginSpec
from reliability_engine.errors import PluginError

class PluginTests(unittest.TestCase):
    def test_unapproved_plugin_blocked(self):
        r=PluginRegistry(); r.register(PluginSpec("p",(sys.executable,"-c","print('{}')"),False,True))
        with self.assertRaises(PluginError): r.execute("p",{})
    def test_unsandboxed_plugin_blocked(self):
        r=PluginRegistry(); r.register(PluginSpec("p",(sys.executable,"-c","print('{}')"),True,False))
        with self.assertRaises(PluginError): r.execute("p",{})
    def test_registered_approved_sandbox_launcher(self):
        code="import sys,json; x=json.load(sys.stdin); print(json.dumps({'status':'pass','echo':x}))"
        r=PluginRegistry(); r.register(PluginSpec("test.echo",(sys.executable,"-c",code),True,True))
        self.assertEqual(r.execute("test.echo",{"x":1})["echo"],{"x":1})
    def test_plugin_output_limit(self):
        r=PluginRegistry(); r.register(PluginSpec("large",(sys.executable,"-c","print('x'*100)"),True,True,max_output_bytes=16))
        with self.assertRaises(PluginError): r.execute("large",{})
    def test_plugin_timeout(self):
        r=PluginRegistry(); r.register(PluginSpec("slow",(sys.executable,"-c","import time; time.sleep(1); print('{}')"),True,True,timeout_seconds=0.1))
        with self.assertRaises(PluginError): r.execute("slow",{})
    def test_schema_style_plugin_ref(self):
        code="import sys,json; x=json.load(sys.stdin); print(json.dumps({'status':'pass','received':x['plugin_params']['scale']}))"
        r=PluginRegistry(); r.register(PluginSpec("trusted.mod::run",(sys.executable,"-c",code),True,True))
        rule={"rule_id":"PLUG","rule_type":"script_plugin","plugin_ref":{"module":"trusted.mod","entry_func":"run","params":{"scale":1.5}}}
        out=__import__("reliability_engine").RuleExecutor(plugins=r).execute(rule,{})
        self.assertEqual(out["status"],"pass"); self.assertEqual(out["result"]["received"],1.5)
    def test_unregistered_plugin_blocked(self):
        with self.assertRaises(PluginError): PluginRegistry().execute("missing",{})

if __name__=="__main__": unittest.main()
