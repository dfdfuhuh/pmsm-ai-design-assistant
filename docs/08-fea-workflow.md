# Maxwell FEA 参考库工作流

记录日期：2026-11-18

## 目标

建立一个适度的离线参考库，用于校准现有解析模型，而不是把完整 Maxwell 求解放进客户端。最终客户端仍只加载本地模型并快速预测。

## 已验证环境

- `D:\ANSYS\ANSYS Inc\v252\AnsysEM\ansysedt.exe`
- AEDT 2025 R2
- PyAEDT 1.10.0
- Ansys PLE Licensing 2025 R2 服务运行正常
- AEDT 可在 non-graphical 模式下启动
- 官方 RMxprt PMSG 模板可读取、修改、求解并导出 Maxwell 2D
- 一个 8 极 12 槽 Maxwell 2D 瞬态设计可完成求解
- `Moving1.Torque`、`CoreLoss`、`StrandedLoss` 和三相电流波形可读取

## 已验证的方法

1. 复制官方 PMSG 模板，避免修改安装目录。
2. 修改极数、槽数、定转子直径、铁芯长度、气隙、磁钢厚度和 NdFe35 材料。
3. 设置电机绕组节距、两层绕组和几何种子。
4. 求解 RMxprt，并从结果创建 Maxwell 2D Transient。
5. 在 Maxwell 中显式设置三相电流、转速、两个电周期、每周期 120 点。
6. 使用稳定后的最后一个电周期计算平均转矩、转矩脉动和铁耗。

## 当前阻塞

- 4 极 6 槽自动槽型在部分几何上报 `Slot design error`。
- PMSG 模板改造成 8 极 12 槽后曾出现三相电流不平衡。
- 官方 BLDC 模板只导出 A/B 两相绕组组，不适合作为三相对称 PMSM 数据源。
- 因此不能把当前试算结果伪装成 100 点 FEA 库。

## 已完成工具

```powershell
python scripts/build_fea_library.py --dry-run
python scripts/build_fea_library.py --pilot
python scripts/build_fea_library.py --limit 1
python scripts/calibrate_from_fea.py
```

- `data/fea/pmsm_fea_plan.csv`：100 点、每拓扑 15 校准 + 5 保留。
- 每个样本有独立项目目录和失败日志。
- 已完成样本会被跳过，支持中断后继续。
- FEA 结果不足时，应用自动回退到合成数据模型，并显示“尚未 FEA 校准”。

## 继续条件

要让批量任务可靠运行，需要一套经过验证的三相表面式 PMSM Maxwell 2D 参数化模板。最直接的方式是先用 AEDT GUI 为任一拓扑完成一个可正常求解、每相电流平衡的模板，再按该模板固定槽型、绕组相带和运动方向。

在模板通过以下检查前，不应启动 100 点批量任务：

- 三相绕组组均为 A/B/C。
- 三相 RMS 电流偏差小于 5%。
- 平均转矩不为零且符号一致。
- 两个电周期后转矩波形稳定。
- 定转子铁耗单位与数量级合理。

## 数据使用边界

即使 100 点 FEA 库完成，也只能证明模型在该通用教学模板的采样范围内得到改善。实测样机、温度、制造误差和真实材料仍需单独验证。
