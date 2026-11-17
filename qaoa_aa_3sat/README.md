# 8-SAT：Pretrain QAOA、AA 与 Sparrow

当前主实例为 **n=10、m=176、k=8**，密度 m/n=17.6。每条子句含 8 个不同变量，随机种子 20261116。两个当前 Notebook 共用同一份 DIMACS 文件，并重新训练全部参数。

## 运行顺序

1. [Pretrain_Sparrow.ipynb](notebooks/Pretrain_Sparrow.ipynb)：训练 p=1、2、3，主 p=3，并核验 Sparrow 的真实输出。
2. [AA_QAOA_Expanded_No_FT.ipynb](notebooks/AA_QAOA_Expanded_No_FT.ipynb)：同一输入的 QAOA+AA、电路核验、1000 shots、振幅和四种方法的时间比较。

aa-fixed 固定 R=1，aa-adjusted 扫描 R=0…12。A / A† 包含完整制备及其逆，O0 两侧不单独画两排 H。无容错或纠错。

## 每条子句一个辅助位

沿用原 3-SAT 的 compute–mark–uncompute 方法：a1 存 C1，a2 存 C2，直到 a176 存 C176。每位 0 表示子句不满足、1 表示满足；只有所有辅助位为 1 时翻相位，再逆计算将它们全部清零。没有加法器或计数器。

完整理想电路有 **10 数据位 + 176 子句辅助位 = 186 位**。Notebook 展开实际前三条子句的辅助位计算；完整 Qiskit 门序保存在 `results/8sat_n10_m176/circuits/02_QAOA_AA.svg` 和 `.txt`，未封装 OC 门逻辑。Notebook 的第 2 部分直接构建 `compute`、`OC`、`full` 和带测量的 `measured` 电路对象。

逐条核验全部局部输入，再用大整数基态编号和稀疏振幅检查全部 1024 个数据输入、实际 H–MCX–H 标记及辅助位清零。数据位上的 oracle 与之前完全相同，因此训练角度、统计和计时保持原值。186 是理想电路线数，不含纠错或特定 MCX 分解的额外资源；计时仍是等价 10 数据位模拟，不是 186 位硬件运行时间。

## 当前文件

- 输入：`data/instance_8sat_n10_m176_seed20261116.cnf`。
- 生成说明与校验：`data/instance_8sat_n10_m176_seed20261116.cnf.json`。
- 本次参数、图表与原始计时：`results/8sat_n10_m176/`，分别放在 `pretrain/`、`circuits/`、`experiments/`。
- [迁移说明](notes/8SAT_n10_m176_说明.md)。

旧 3-SAT 数据和旧报告仍保留，供历史报告引用。`results/report_only`、`results/meeting_experiments`、`results/pretrain_aa_integrated` 中的旧数字不属于当前 8-SAT 实验。项目目录名 `qaoa_aa_3sat` 暂沿用，避免 IDE 路径失效。

时间比较采用精确编译 CPU 态矢量与原生 Sparrow，按实际毫秒显示，包含一次测量/求解。预编译、训练、R 选择分别说明，没有将其解释为真实量子硬件速度。规模扫描已扩大为 n=8…17，每个规模三份 8-SAT 实例，m≈17.6n；观察不到交点时如实报告。


最新 [crossover 扩展与交点说明](notes/crossover_扩展规模与交点说明.md)：第 10 节四种方法统一在 Windows 实测，第 9 节保留新拉取的 Mac M2 主实例参考值。
