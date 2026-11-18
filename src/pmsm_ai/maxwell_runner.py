"""PyAEDT execution of one PMSM FEA sample from the official RMxprt template."""

from __future__ import annotations

import contextlib
import json
import math
import os
import shutil
import time
from pathlib import Path

import numpy as np

from pmsm_ai.analytical import AnalyticalPMSMModel
from pmsm_ai.domain import PMSMDesign, get_topology
from pmsm_ai.fea import FEAPlanSample, FEASampleRecord

DEFAULT_TEMPLATE_CANDIDATES = (
    Path(
        r"D:\ANSYS\ANSYS Inc\v252\AnsysEM\Examples\RMxprt\pmsg\pmsg-1.aedt"
    ),
    Path(
        r"C:\Program Files\ANSYS Inc\v252\AnsysEM\Examples\RMxprt\pmsg\pmsg-1.aedt"
    ),
)


def find_maxwell_template() -> Path:
    """Resolve the official surface-PM RMxprt template."""

    configured = os.environ.get("PMSM_MAXWELL_TEMPLATE")
    candidates = (
        (Path(configured),) if configured else ()
    ) + DEFAULT_TEMPLATE_CANDIDATES
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(
        "找不到 Maxwell PMSG 模板。请设置 PMSM_MAXWELL_TEMPLATE 指向 pmsg-1.aedt。"
    )


def run_fea_sample(
    sample: FEAPlanSample,
    work_root: Path,
    template_path: Path | None = None,
) -> FEASampleRecord:
    """Build, solve and extract one 2D transient FEA sample."""

    try:
        from ansys.aedt.core import Rmxprt
    except ImportError as exc:
        raise RuntimeError("未安装 PyAEDT；请安装项目的 fea 可选依赖") from exc

    template = template_path or find_maxwell_template()
    design = sample.design
    topology = get_topology(design.topology)
    sample_root = work_root / sample.sample_id
    sample_root.mkdir(parents=True, exist_ok=True)
    project_path = sample_root / f"{sample.sample_id.replace('-', '_')}.aedt"
    results_path = project_path.with_suffix(".aedtresults")
    lock_path = project_path.with_name(project_path.name + ".lock")
    if project_path.exists():
        project_path.unlink()
    if results_path.exists():
        shutil.rmtree(results_path)
    if lock_path.exists():
        lock_path.unlink()
    shutil.copy2(template, project_path)

    started = time.perf_counter()
    previous_directory = Path.cwd()
    rmxprt = None
    try:
        os.chdir(sample_root)
        rmxprt = Rmxprt(
            project=str(project_path),
            design="pmsg-1",
            non_graphical=True,
            new_desktop=True,
            close_on_exit=True,
        )
        config_path = sample_root / "rmxprt_config.json"
        rmxprt.export_configuration(config_path)
        config = json.loads(config_path.read_text(encoding="utf-8"))
        _apply_rmxprt_config(config, design)
        config_path.write_text(
            json.dumps(config, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        rmxprt.import_configuration(str(config_path))

        coil_pitch = 2 if design.topology == "spm_8p18s" else 1
        rmxprt.stator["Coil Pitch"] = coil_pitch
        rmxprt.stator["Winding Layers"] = 2
        rmxprt.stator["Parallel Branches"] = 1
        rmxprt.stator["Conductors per Slot"] = 20
        _configure_rmxprt_setup(rmxprt, design)
        if not rmxprt.validate_simple():
            raise RuntimeError("RMxprt 模板参数校验失败")
        if not rmxprt.analyze_setup("Setup1"):
            raise RuntimeError(_solver_messages(rmxprt, project_path, "pmsg-1"))
        rmxprt.save_project()

        maxwell = rmxprt.create_maxwell_design("Setup1", maxwell_2d=True)
        if isinstance(maxwell, bool) or not hasattr(maxwell, "boundaries"):
            raise RuntimeError("RMxprt 未生成 Maxwell 2D 设计")
        _configure_maxwell(maxwell, design, topology.pole_pairs)
        if not maxwell.analyze_setup("Setup1"):
            raise RuntimeError(
                _solver_messages(maxwell, project_path, maxwell.design_name)
            )
        maxwell.save_project()
        return _extract_record(sample, maxwell, started)
    finally:
        if rmxprt is not None:
            with contextlib.suppress(Exception):
                rmxprt.release_desktop()
        os.chdir(previous_directory)


def _apply_rmxprt_config(config: dict, design: PMSMDesign) -> None:
    topology = get_topology(design.topology)
    rotor_outer = design.stator_inner_diameter_mm - 2.0 * design.air_gap_mm
    rotor_inner = rotor_outer - 2.0 * design.rotor_yoke_thickness_mm
    general = config["General"]
    general["Number of Poles"] = topology.poles
    general["Reference Speed"] = f"{design.speed_rpm:g}rpm"
    general["Frictional Loss"] = "0W"
    stator = config["Stator"]
    stator["Outer Diameter"] = f"{design.stator_outer_diameter_mm:g}mm"
    stator["Inner Diameter"] = f"{design.stator_inner_diameter_mm:g}mm"
    stator["Length"] = f"{design.stack_length_mm:g}mm"
    stator["Number of Slots"] = topology.slots
    stator["Slot Type"] = [1]
    stator["Slot Type/SlotType"] = 1
    rotor = config["Rotor"]
    rotor["Outer Diameter"] = f"{rotor_outer:g}mm"
    rotor["Inner Diameter"] = f"{rotor_inner:g}mm"
    rotor["Length"] = f"{design.stack_length_mm:g}mm"
    pole = config["Pole"]
    pole["Magnet Thickness"] = f"{design.magnet_thickness_mm:g}mm"
    pole["Embrace"] = 0.82
    pole["Magnet Type"] = ["NdFe35"]
    pole["Magnet Type/Material"] = "NdFe35"
    slot = config["Slot"]
    slot.update(
        {
            "Auto Design": True,
            "Hs0": "0.5mm",
            "Bs0": f"{design.slot_opening_mm:g}mm",
            "Rs": "0mm",
        }
    )
    winding = config["Winding"]
    winding["Winding Layers"] = 2
    winding["Parallel Branches"] = 1
    winding["Conductors per Slot"] = 20


def _configure_rmxprt_setup(rmxprt: object, design: PMSMDesign) -> None:
    setup = rmxprt.get_setup("Setup1")
    analytical = AnalyticalPMSMModel().evaluate(design)
    setup.props["OperationType"] = "Motor"
    setup.props["RatedOutputPower"] = f"{max(analytical.shaft_power_w, 1.0) / 1000:g}kW"
    setup.props["RatedVoltage"] = (
        f"{analytical.maximum_phase_voltage_v * math.sqrt(3):g}V"
    )
    setup.props["RatedSpeed"] = f"{design.speed_rpm:g}rpm"
    setup.props["RatedPowerFactor"] = 0.9
    setup.update()


def _configure_maxwell(
    maxwell: object,
    design: PMSMDesign,
    pole_pairs: int,
) -> None:
    winding_groups = [item for item in maxwell.boundaries if item.type == "Winding Group"]
    if {item.name for item in winding_groups} != {"PhaseA", "PhaseB", "PhaseC"}:
        raise RuntimeError("Maxwell 模型未生成三相绕组")

    group_by_name = {item.name: item for item in winding_groups}
    coil_groups: dict[str, list[object]] = {name: [] for name in group_by_name}
    for coil in (item for item in maxwell.boundaries if item.type == "Coil"):
        parent = int(coil.props["ParentBndID"])
        for name, group in group_by_name.items():
            if int(group.props["ID"]) == parent:
                coil_groups[name].append(coil)
                break

    for name, coils in coil_groups.items():
        if not coils:
            raise RuntimeError(f"{name} 没有线圈")
        turns_per_coil = max(1, round(design.turns_per_phase / len(coils)))
        for coil in coils:
            coil.auto_update = False
            coil.props["Conductor number"] = str(turns_per_coil)
            coil.auto_update = True
            coil.update()
        group = group_by_name[name]
        group.auto_update = False
        group.props["ParallelBranchesNum"] = "1"
        group.auto_update = True
        group.update()

    electrical_frequency = pole_pairs * design.speed_rpm / 60.0
    current_peak = design.rated_current_a * math.sqrt(2.0)
    phase_a = -228.0 + design.current_angle_deg
    for name, delta in (("PhaseA", 0.0), ("PhaseB", -120.0), ("PhaseC", -240.0)):
        group = group_by_name[name]
        group.auto_update = False
        group.props["Type"] = "Current"
        group.props["Voltage"] = "0V"
        group.props["Current"] = (
            f"{current_peak:.9g}*cos(2*pi*{electrical_frequency:.9g}*time"
            f"+({phase_a + delta:.9g})*pi/180)"
        )
        group.auto_update = True
        group.update()

    motion = next(item for item in maxwell.boundaries if item.type == "Band")
    motion.props["InitPos"] = "0deg"
    motion.props["Angular Velocity"] = f"{design.speed_rpm:g}rpm"
    maxwell.set_core_losses(["Stator", "Rotor"], core_loss_on_field=True)

    setup = maxwell.get_setup("Setup1")
    stop_time = 2.0 / electrical_frequency
    time_step = 1.0 / (120.0 * electrical_frequency)
    setup.props["StopTime"] = f"{stop_time:.9g}s"
    setup.props["TimeStep"] = f"{time_step:.9g}s"
    setup.props["RangeEnd"] = f"{stop_time:.9g}s"
    setup.props["SaveFieldsType"] = "None"
    setup.update()
    maxwell.save_project()


def _extract_record(
    sample: FEAPlanSample,
    maxwell: object,
    started: float,
) -> FEASampleRecord:
    data = maxwell.post.get_solution_data_per_variation(
        solution_type="Transient",
        setup_sweep_name="Setup1 : Transient",
        context=None,
        sweeps={"Time": "All"},
        expressions=["Moving1.Torque", "CoreLoss", "StrandedLoss"],
    )
    if not data:
        raise RuntimeError("Maxwell 没有返回转矩数据")

    torque = np.asarray(
        data.get_expression_data("Moving1.Torque", convert_to_si=True)[1],
        dtype=float,
    )
    core_loss = np.asarray(
        data.get_expression_data("CoreLoss", convert_to_si=True)[1],
        dtype=float,
    )
    stranded_loss = np.asarray(
        data.get_expression_data("StrandedLoss", convert_to_si=True)[1],
        dtype=float,
    )
    count = min(len(torque), len(core_loss), len(stranded_loss))
    steady = slice(count // 2, count)
    torque_cycle = torque[steady]
    mean_torque = float(np.mean(torque_cycle))
    if abs(mean_torque) < 1e-3:
        raise RuntimeError("FEA 平均转矩接近零，电流相位或绕组配置无效")
    ripple = 100.0 * float(np.ptp(torque_cycle)) / abs(mean_torque)
    core_loss_w = float(np.mean(core_loss[steady]))
    stranded_loss_w = float(np.mean(stranded_loss[steady]))
    mechanical_loss_w = AnalyticalPMSMModel().evaluate(sample.design).mechanical_loss_w
    shaft_power_w = abs(mean_torque) * 2.0 * math.pi * sample.design.speed_rpm / 60.0
    denominator = shaft_power_w + core_loss_w + stranded_loss_w + mechanical_loss_w
    efficiency = 100.0 * shaft_power_w / denominator if denominator > 0 else 0.0
    if not 0.0 < efficiency < 100.0:
        raise RuntimeError(f"FEA 效率不合理：{efficiency:.2f}%")
    return FEASampleRecord(
        sample_id=sample.sample_id,
        topology=sample.topology,
        split=sample.split,
        design=sample.design,
        torque_nm=abs(mean_torque),
        torque_ripple_pct=ripple,
        efficiency_pct=efficiency,
        core_loss_w=core_loss_w,
        stranded_loss_w=stranded_loss_w,
        mechanical_loss_w=mechanical_loss_w,
        solver_seconds=time.perf_counter() - started,
    )


def _conductors_per_slot(design: PMSMDesign) -> int:
    slots = get_topology(design.topology).slots
    return max(2, round(design.turns_per_phase * 6 / slots))


def _solver_messages(app: object, project_path: Path, design_name: str) -> str:
    try:
        messages = app.odesktop.GetMessages(project_path.stem, design_name, 0)
    except Exception:
        messages = []
    return "\n".join(messages) or "Maxwell 求解失败，未返回诊断消息"
