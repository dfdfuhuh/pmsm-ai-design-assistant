# Windows 免安装便携版

记录日期：2026-11-20

## 文件

```text
D:\CODES\PMSM-AI-Design-Assistant-portable.zip
```

- 大小：207,481,687 字节，约 197.9 MiB
- SHA-256：`ad2526fd162cf891994852effbb4709705b1d5ed693c9a58e819b2db5f64cd06`
- 解压后文件数：2235
- 内置模型：85.3 MiB

## 使用

1. 把 ZIP 复制到 U 盘。
2. 在 Windows 10/11 64 位电脑上解压整个 ZIP。
3. 进入 `PMSM-AI-Design-Assistant` 文件夹。
4. 双击 `PMSM-AI-Design-Assistant.exe`。

不需要安装 Python、Conda、VS Code 或 Maxwell。不要单独复制 EXE；必须保留 `_internal`、`artifacts` 和 `使用说明.txt`。

## 构建

```powershell
conda activate pmsm-ai
python -m pip install -r requirements-packaging.txt
python scripts/build_portable.py
```

构建脚本使用 PyInstaller onedir 模式，并补充 Conda 环境所需的 OpenSSL、FFI、压缩和 SQLite DLL。构建完成后会：

- 将已训练模型和指标复制到便携目录。
- 生成 `SHA256SUMS.txt` 和 `使用说明.txt`。
- 在移除 Conda/Python PATH 的环境中执行 `--smoke-test`。
- 生成便携 ZIP。

## 验证结果

- 构建目录 EXE 自检返回 0。
- ZIP 解压文件数与构建目录一致。
- 解压副本在清空 `CONDA_PREFIX`、`CONDA_DEFAULT_ENV`、`PYTHONPATH`、`PYTHONHOME` 并将 PATH 限制为 Windows 系统目录后，EXE 自检返回 0。
- 内置随机森林模型成功加载。
- 参数趋势页同时展示解析公式实线和 AI 代理虚线；不可行点与训练域外点以断点显示。
- 模型评估页提供 R²、MAE、RMSE 的中文定义、单位和适用范围说明。
- 基础参数页根据拓扑和转速自动显示电频率，不需要客户重复输入。

## 限制

- 仅支持 Windows 10/11 64 位。
- 便携版不包含 Maxwell FEA 样本构建功能，只包含 GUI 预测应用。
- 结果仍基于合成教学数据，不能替代有限元、实测或正式工程设计。
- 部分杀毒软件可能对 PyInstaller EXE 产生误报。
