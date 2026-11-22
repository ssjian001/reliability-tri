"""受控白名单插件：铝电解电容 Arrhenius 寿命评估（ecap_arrhenius_v1）。

模型（02 模板 3）：芯温 = 环温 + I²·ESR·Rth；寿命 = 额定寿命 × 2^((T_rated - T_core)/doubling)。
输出：core_temp_est（degC）、predicted_life_hours（h）。
数值口径：确定性（同输入同版本结果一致）；回归容差 ≤0.1%（03 §5.1）。
"""
from __future__ import annotations


def evaluate_ecap_lifetime(values: dict, params: dict) -> dict:
    i_rms = float(values["ripple_current_rms"])
    esr = float(values["esr_at_freq"])
    rth = float(values["thermal_resistance_ca"])
    ta = float(values["local_ambient_temp"])
    t_rated = float(values["rated_max_temp"])
    rated_life = float(values["rated_endurance_hours"])
    doubling = float(params.get("doubling_temp_delta", 10.0))

    p_heat = i_rms * i_rms * esr
    delta_t = p_heat * rth
    core = ta + delta_t
    if core > t_rated:
        life = 0.0  # 超额定芯温：寿命按 0 处理（前置条件已挡大部分）
    else:
        life = rated_life * (2 ** ((t_rated - core) / doubling))
    return {"core_temp_est": core, "predicted_life_hours": life,
            "delta_t": delta_t, "p_heat_w": p_heat}
