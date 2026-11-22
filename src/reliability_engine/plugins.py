"""Fail-closed external plugin adapter.

This module never evaluates plugin source code. Production execution requires an
operator-configured OS sandbox launcher (e.g. a locked-down container/runtime).
The launcher must enforce filesystem, network, CPU, memory and process limits.
"""
from __future__ import annotations
import json, os, selectors, subprocess, threading, time
from dataclasses import dataclass
from .errors import PluginError

@dataclass(frozen=True)
class PluginSpec:
    plugin_id: str
    executable: tuple[str, ...]
    approved: bool
    sandboxed: bool
    timeout_seconds: float = 3.0
    max_input_bytes: int = 65536
    max_output_bytes: int = 65536

class PluginRegistry:
    def __init__(self): self._specs={}
    def register(self,spec: PluginSpec):
        if not spec.plugin_id or spec.plugin_id in self._specs: raise PluginError("Plugin ID missing or duplicate")
        if not spec.executable: raise PluginError("Plugin executable is required")
        if spec.timeout_seconds<=0 or spec.max_input_bytes<=0 or spec.max_output_bytes<=0:
            raise PluginError("Plugin resource limits must be positive")
        self._specs[spec.plugin_id]=spec
    def execute(self,plugin_id: str, payload: dict):
        spec=self._specs.get(plugin_id)
        if not spec: raise PluginError("PLUGIN_NOT_REGISTERED")
        if not spec.approved: raise PluginError("PLUGIN_NOT_APPROVED")
        if not spec.sandboxed: raise PluginError("PLUGIN_SANDBOX_REQUIRED")
        try: raw=json.dumps(payload,allow_nan=False,separators=(",",":" )).encode()
        except (TypeError,ValueError) as e: raise PluginError("PLUGIN_INPUT_NOT_JSON") from e
        if len(raw)>spec.max_input_bytes: raise PluginError("PLUGIN_INPUT_TOO_LARGE")
        env={"PATH":os.environ.get("PATH",""),"LANG":"C.UTF-8","LC_ALL":"C.UTF-8"}
        try:
            proc=subprocess.Popen(list(spec.executable),stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                                  stderr=subprocess.DEVNULL,env=env,cwd="/",shell=False,close_fds=True)
        except OSError as e: raise PluginError(f"PLUGIN_LAUNCH_FAILED: {e}") from e
        def write_input():
            try:
                proc.stdin.write(raw); proc.stdin.close()
            except (BrokenPipeError,OSError): pass
        writer=threading.Thread(target=write_input,daemon=True); writer.start()
        output=bytearray(); deadline=time.monotonic()+spec.timeout_seconds
        try:
            with selectors.DefaultSelector() as selector:
                selector.register(proc.stdout,selectors.EVENT_READ)
                eof=False
                while not eof:
                    remaining=deadline-time.monotonic()
                    if remaining<=0: raise PluginError("PLUGIN_TIMEOUT")
                    events=selector.select(remaining)
                    if not events: raise PluginError("PLUGIN_TIMEOUT")
                    chunk=os.read(proc.stdout.fileno(),min(8192,spec.max_output_bytes-len(output)+1))
                    if not chunk: eof=True; break
                    output.extend(chunk)
                    if len(output)>spec.max_output_bytes: raise PluginError("PLUGIN_OUTPUT_TOO_LARGE")
            remaining=deadline-time.monotonic()
            if remaining<=0: raise PluginError("PLUGIN_TIMEOUT")
            try: code=proc.wait(timeout=remaining)
            except subprocess.TimeoutExpired as e: raise PluginError("PLUGIN_TIMEOUT") from e
            writer.join(timeout=max(0,deadline-time.monotonic()))
            if code!=0: raise PluginError(f"PLUGIN_EXIT_{code}")
        except PluginError:
            proc.kill(); proc.wait(); raise
        finally:
            if proc.poll() is None: proc.kill(); proc.wait()
            writer.join(timeout=0.1)
            if proc.stdout: proc.stdout.close()
        try: result=json.loads(output.decode("utf-8"))
        except Exception as e: raise PluginError("PLUGIN_INVALID_JSON") from e
        if not isinstance(result,dict): raise PluginError("PLUGIN_RESPONSE_MUST_BE_OBJECT")
        return result
