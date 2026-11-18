# 永磁同步电机 AI 设计助手

> 当前状态：课程项目预研与开发环境准备阶段。

本项目围绕永磁同步电机（PMSM）设计，规划一个基于 PyQt6 的交互式设计分析工具。后续核心算法采用随机森林代理模型，根据电机几何、材料与工况参数预测转矩、转矩脉动和效率。

当前仓库只验证工具链、工程结构和图形界面启动链路，**尚未实现电磁计算、数据生成、模型训练或性能预测**。规划中的合成数据只能用于教学方法验证，不能替代有限元计算、样机测试或工程设计结论。

![PyQt6 预研启动页](docs/images/launch-page.png)

## 当前交付

- Python 3.11 Conda 环境配置
- PyQt6 最小启动页
- 环境自检脚本
- 面向对象的基础 UI 结构
- GUI 与自检逻辑的自动化测试
- 课程要求、技术路线和风险预研文档

## 快速开始

```powershell
conda env create -f environment.yml
conda activate pmsm-ai
python -m pip install -e .
python scripts/check_environment.py
python -m pmsm_ai
```

如果环境已经存在，可更新后安装项目：

```powershell
conda env update -f environment.yml --prune
conda activate pmsm-ai
python -m pip install -e .
```

## 验证

```powershell
python -m pytest -q
python -m ruff check .
python scripts/check_environment.py
```

自动化 GUI 测试通过 `QT_QPA_PLATFORM=offscreen` 运行，不要求桌面显示服务。

## 后续技术路线

1. 建立物理约束的 PMSM 降阶解析模型，并明确其适用边界。
2. 生成可复现的合成设计数据集，记录采样方法、随机种子和参数范围。
3. 训练并验证随机森林多目标代理模型。
4. 将参数输入、性能预测、敏感性和模型评估接入 PyQt6 界面。
5. 使用独立样本、解析基准和可获得的有限元/实验数据交叉验证。

## 文档

- [课程要求映射](docs/01-course-requirements.md)
- [项目说明](docs/02-project-brief.md)
- [技术可行性](docs/03-technical-feasibility.md)
- [风险清单](docs/04-risk-register.md)
- [大模型协作记录](docs/05-ai-collaboration-log.md)
- [环境报告](docs/06-environment-report.md)
- [参考资料](docs/references.md)

## 使用边界

- 这是课程学习与研究准备项目，不是经过认证的电机设计软件。
- 合成数据不能作为有限元或实验精度的证据。
- 后续报告必须披露数据来源、模型假设、参数范围、评价指标和误差。
- 不提交账号令牌、个人数据、商业软件许可文件或受版权保护的工程数据。
