# AA + QAOA 电路与运行时间

本版本已按项目保存的论文 v1 核对。初始 H 保留，迭代按式 (6) 字面执行，不在 O_0 前后添加全寄存器 H。Notebook 各节及末尾的九项「原文对照」注明原文内部约定问题、功能等价简化和资源估算假设。

- `notebooks/AA_QAOA_Qiskit.ipynb`：完整分段代码、图形和已保存的执行结果；不依赖旧 `.py`。
- `notes/AA_QAOA_电路与时间估算_Obsidian.md`：中文图文讲解、可编辑数学公式。
- `notes/obsidian_assets/`：笔记需要的 9 张 PNG 和可缩放 SVG。
- `figures/QAOA_AA_circuit_atlas.pdf`：带时间与来源注释的 9 页图册。
- `data/time_estimates.csv`：默认参数的组件预算。
- `src/circuit_logic.py`、`src/build_circuits.py`：同版独立脚本；Notebook 内已包含功能函数，不依赖这两个文件。
- `notes/电路搭建与时间估算说明.md`、`notes/阅读说明.html`：对应的说明与离线阅读版。

此目录保留当前修订后的正式版本。`notebooks/` 放代码，`notes/` 放说明，`figures/` 放图册，`data/` 放数据。独立脚本新生成的图册写入 `results/atlas/`。

Notebook 顺序运行后，重新生成的图、笔记和数据集中写入 `results/`。它不会覆盖 `notes/` 中的阅读笔记。

修改说明后先保存 Notebook 再运行导出格。导出直接读取已保存的图下正文，不再维护第二份内嵌解释。`results/data/verification.json` 保存理想功能检查，`results/data/audit_checks.json` 记录本次正文同步与源码核对结果；PASS 不代表完成 TACU、资源态工厂、实际染色或论文完整交叉点复现。

导入 Obsidian 时，将 `notes/` 内的笔记和 `obsidian_assets/` 一起复制到 vault。当前已修好的 UROP vault 仍可正常读图。

时间使用论文公式 (7)–(11) 的容错模型。数值例子的 c=2112、nP=27 是明示假设，未声称完整复现论文交叉点。
