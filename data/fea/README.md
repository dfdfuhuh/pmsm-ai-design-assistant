# Maxwell FEA 参考数据

本目录保存一次性离线 FEA 样本计划和后续经过验证的参考结果。

- `pmsm_fea_plan.csv`：100 个固定设计点；每种拓扑 15 个校准点和 5 个独立保留点。
- `pmsm_fea_reference.csv`：只有在 Maxwell 模板通过几何、三相电流、转矩和损耗校验后才会生成。
- `pmsm_fea_manifest.json`：参考库行数、划分和 SHA-256。
- `pmsm_fea_calibration.json`：只使用校准集拟合的 Ridge 修正参数。

当前计划已生成，但五拓扑参考库尚未完成。应用不能把计划数据当作 FEA 结果，也不能在缺少参考库时宣称已完成 FEA 校准。
