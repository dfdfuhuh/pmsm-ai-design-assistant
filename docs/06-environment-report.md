# 开发环境报告

记录日期：2026-11-18

操作系统：Windows，x86-64

项目目录：`D:\CODES\pmsm-ai-design-assistant`

## 初始检查

- `D:\CODES` 初始为空，没有可复用项目或 `AGENTS.md`。
- VS Code 已安装于用户程序目录，但 `code` 命令不在初始 PATH 中。
- 初始终端没有可用的 Git、Conda 或真实 Python；只有 Windows 应用商店占位入口。
- `winget` 可用，并核实了 Git、Miniconda3、GitHub CLI 的包标识。
- PyPI 官方下载出现超时，改用清华镜像完成 Python 包安装。
- 默认 Anaconda 源要求接受新的服务条款，因此使用 `conda-forge` 创建环境。
- PowerShell 初始执行策略禁止加载 Conda 脚本；当前用户策略已调整为 `RemoteSigned`，远程脚本仍需签名。

## 最终环境

| 组件 | 配置 |
| --- | --- |
| Conda | Miniconda，环境名 `pmsm-ai` |
| Python | 3.11.18 |
| GUI | PyQt6 6.12.1，Qt 6.12.0 |
| 科学计算 | NumPy 2.4.6、Pandas 2.3.3、SciPy 1.17.1 |
| 机器学习 | scikit-learn 1.9.1、joblib 1.6.0 |
| 绘图 | Matplotlib 3.11.2 |
| 测试与质量 | pytest 9.2.0、pytest-qt 4.5.0、ruff 0.17.5 |
| Git | 2.56.0.windows.4 |
| GitHub CLI | 2.104.0 |
| 编辑器 | VS Code，安装 Python、Pylance、Ruff 扩展 |

## 复现步骤

```powershell
conda env create -f environment.yml
conda activate pmsm-ai
python -m pip install -e .
python scripts/check_environment.py
```

锁定版本见根目录 `requirements-lock.txt`。若镜像不可用，应根据机构网络环境更换索引，不应关闭依赖来源验证。

## 验收记录

最终命令结果在环境搭建完成后由仓库测试补充：

- [x] `python scripts/check_environment.py`：8/8 项通过
- [x] `python -m pytest -q`：30 项测试通过
- [x] `python -m ruff check .`：无问题
- [x] PyQt 启动页在 offscreen 模式下完成显示与事件循环，并生成预览图
