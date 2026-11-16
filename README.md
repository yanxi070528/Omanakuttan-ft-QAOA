# QAOA、Amplitude Amplification 与 Sparrow 论文复现

当前主实验：**8-SAT，10 个变量、176 条子句，每条包含 8 个文字**。普通理想电路，无纠错；主深度 p=3，aa-fixed 固定 R=1，aa-adjusted 扫描 R=0…12，每组 1000 shots。

## 当前版本入口

1. [Pretrain_Sparrow.ipynb](qaoa_aa_3sat/notebooks/Pretrain_Sparrow.ipynb)：训练 p=1、2、3 的 QAOA 参数，检查同一 CNF 的 Sparrow 输出。
2. [AA_QAOA_Expanded_No_FT.ipynb](qaoa_aa_3sat/notebooks/AA_QAOA_Expanded_No_FT.ipynb)：接续训练参数，构建 QAOA+AA，展示成功概率、输出分布、振幅与四种方法的运行时间。
3. [当前实验说明](qaoa_aa_3sat/notes/8SAT_n10_m176_说明.md)与[任务 README](qaoa_aa_3sat/README.md)。

Oracle 沿用每条子句一个辅助位的方法：a1 存 C1，直到 a176 存 C176；全部为 1 时翻相位，再逆计算清零。完整理想电路有 **10 数据位 + 176 子句辅助位 = 186 位**，没有加法器。Notebook 展开实际前三条的计算片段，并提供[完整电路 SVG](qaoa_aa_3sat/results/8sat_n10_m176/circuits/02_QAOA_AA.svg)和[文本门序](qaoa_aa_3sat/results/8sat_n10_m176/circuits/02_QAOA_AA.txt)。

输入位于 [data/](qaoa_aa_3sat/data/instance_8sat_n10_m176_seed20261116.cnf)，当前训练、图表、原始统计与核验记录位于 [results/8sat_n10_m176/](qaoa_aa_3sat/results/8sat_n10_m176/)。时间图比较本机等价数据位态矢量模拟与原生 Sparrow 的墙钟时间；不代表真实量子硬件速度，训练和单次执行分列。

## 本地运行

在仓库根目录安装依赖：

```powershell
python -m pip install -r qaoa_aa_3sat/requirements.txt
$env:SPARROW_EXE = (Resolve-Path './classical_solvers/sparrow/bin/sparrow.exe').Path
python -m jupyter lab
```

先从上到下运行 Pretrain，再运行 AA Notebook。更换 CNF 后需重新训练；AA Notebook 会核验输入哈希和参数来源。Sparrow 的 Windows 程序、源码、许可及使用方法见 [classical_solvers/sparrow/](classical_solvers/sparrow/README.md)。

## 其他任务与历史实验

- [simulation/](simulation/README.md)：Figure 3A、Table III 及容错资源估算。
- [circuit with corresponding time estimation/](circuit%20with%20corresponding%20time%20estimation/README.md)：Qiskit 电路、分块时间公式和 Obsidian 图文笔记。
- [QAOA_AA_3SAT_No_QEC.ipynb](qaoa_aa_3sat/notebooks/QAOA_AA_3SAT_No_QEC.ipynb)：早期 3-SAT 与 QUBO 实验。旧结果、说明与历史汇报按原目录保留，与当前 8-SAT 结果分开使用。

原论文：[arXiv:2504.01897](https://arxiv.org/abs/2504.01897)。本仓库的局部优化、有限 shots 和 CPU 计时采用 Notebook 中注明的实验配置。
