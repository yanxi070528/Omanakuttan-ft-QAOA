---
title: QAOA 电路与原文对照
tags: [QAOA, 论文复现, 电路, 资源估算]
paper: arXiv:2504.01897v1
---

# QAOA 电路、时间预算与原文对照


本笔记由已保存 Notebook 的图下正文生成。功能电路按式 (6) 字面执行；原文约定问题和实现差异在各节及末尾标明。


## 1. 初态制备与式 (6) 的一轮迭代

![[obsidian_assets/01_full_QAOA_AA.png|1100]]

初态制备只在开头执行一次：

$$|0^n\rangle\xrightarrow{H^{\otimes n}}|+\rangle^{\otimes n}\xrightarrow{U}|\psi\rangle.$$

这里 $U$ 是式 (3) 的 QAOA 演化，不含初始 H。每轮直接按式 (6) 从左到右执行：

$$O_C\longrightarrow U^\dagger\longrightarrow O_0\longrightarrow U,\qquad Q=UO_0U^\dagger O_C.$$

本版本保留初始 H，$O_0$ 前后没有全寄存器 H 层。经过 $O_C$ 标记后，$U^\dagger$ 一般不会将整个态还原为均匀叠加态；$O_0$ 只翻转当时的全零分量。

> **[原文内部约定问题，p.3–4]** 式 (2) 的初态与式 (6) 的零态反射定义并未显式匹配。当前代码忠实于式 (6) 字面顺序，未补 H，也不声称因此已证明标准 AA 的概率公式。详细解释见末尾原文对照第 1 项。

初始演化预算与每轮主体预算分别为

$$T_U=p(T_{\mathrm{phaser}}+T_{\mathrm{mixer}}),\qquad T_Q=2T_U+T_{O_C}+T_{O_0}.$$

图中四根线表示一般的数据寄存器，方框是不可直接模拟的压缩模块；实际演示另有清零辅助位。重复的是最后四个模块，初始 H 和第一次 U 不在重复段内。


## 2. 一层正向 QAOA

![[obsidian_assets/02_QAOA_layer.png|1100]]

论文公式 (3) 的一层算符为

$$
U_l=e^{-i\beta_l H_M}e^{-i\gamma_l H_C}.
$$

矩阵右侧先作用，因此从左到右执行 $e^{-i\gamma_l H_C}$，再执行 $e^{-i\beta_l H_M}$。正向电路按 $l=1,\ldots,p$ 逐层加入这两段。

整段 phaser 的时间来自公式 (9)：

$$
T_{\mathrm{phaser}}
=\left(c+n_P+4\left\lceil\log_2 k\right\rceil\right)T_{\mathrm{LC}}.
\tag{9}
$$

整段 mixer 的时间来自公式 (8)：

$$
T_{\mathrm{mixer}}=n_P T_{\mathrm{LC}}.
\tag{8}
$$

对 $k=8$，$4\lceil\log_2 k\rceil=12$，因此

$$
T_{\mathrm{layer}}=(c+2n_P+12)T_{\mathrm{LC}},
\qquad T_U=pT_{\mathrm{layer}}.
$$

这里 $p$ 是 QAOA 层数；$n_P$ 是单比特相位门分解的逻辑周期数。Phaser 后辅助位复原为 $|0\rangle$，mixer 只操作数据位。


## 3. 逆 QAOA

![[obsidian_assets/03_inverse_QAOA.png|1100]]

设 $P_l=e^{-i\gamma_l H_C}$、$M_l=e^{-i\beta_l H_M}$。正向单层的时间顺序是 $P_l\to M_l$；逆向单层是

$$
M_l^\dagger\to P_l^\dagger,
\qquad
M_l^\dagger=e^{+i\beta_l H_M},\quad
P_l^\dagger=e^{+i\gamma_l H_C}.
$$

按层来看，逆电路从 $p$ 层撤销到第 $1$ 层：

$$
\mathrm{Mixer}(-\beta_p)
\to\mathrm{Phaser}(-\gamma_p)
\to\cdots\to
\mathrm{Mixer}(-\beta_1)
\to\mathrm{Phaser}(-\gamma_1).
$$

代码中的 `.inverse()` 同时完成门的逆序与取逆。只改变角度符号却保留顺序，通常不会得到逆算符。图中省略了中间的逆向层。

论文模型给出

$$
T_{U^\dagger}=T_U
=p\left(T_{\mathrm{phaser}}+T_{\mathrm{mixer}}\right).
$$

每轮 AA 同时含 $U$ 和 $U^\dagger$，所以共有 $2p$ 个 phaser 和 $2p$ 个 mixer。


## 4. 8-SAT 子句 Phaser

![[obsidian_assets/04_8SAT_clause_phaser.png|1100]]

图示子句为

$$
C_j(x)=x_0\lor\neg x_1\lor x_2\lor\cdots\lor x_7.
$$

正文公式 (4)–(5) 用子句满足数定义 cost Hamiltonian：

$$
H_C=-\sum_{j=1}^{m}\sum_{x\in\{0,1\}^n}
C_j(x)|x\rangle\langle x|.
$$

因此 phaser 的目标相位是

$$
e^{-i\gamma_l H_C}|x\rangle
=\exp\!\left(i\gamma_l\sum_j C_j(x)\right)|x\rangle.
$$

用一个清零辅助位 $f$ 搭建单子句相位：

$$
|x\rangle|0\rangle_f
\xrightarrow{\mathrm{compute}}
|x\rangle|C_j(x)\rangle_f
\xrightarrow{P(\gamma_l)}
e^{i\gamma_l C_j(x)}|x\rangle|C_j(x)\rangle_f
\xrightarrow{\mathrm{uncompute}}
e^{i\gamma_l C_j(x)}|x\rangle|0\rangle_f.
$$

这里 $P(\gamma)=\operatorname{diag}(1,e^{i\gamma})$。正相位来自 $H_C$ 的负号。

代码先对正文字对应的数据位施加 $X$，让所有文字均为假的模式映射成全 $1$ 控制条件；MCX 得到 UNSAT 标记，再用 $X_f$ 转成 SAT 标记。恢复数据位并在施加相位后反计算，辅助位复原。

> [!note] 功能电路与论文编译
> MCX 图解释可逆功能。论文 Fig.2C、Sec.IV.C 和 Appendix B 用 CCZ 资源态、测量及反馈构建 TACU。$k=8$ 的单个相位 gadget 使用 $7$ 个 CCZ 态和 $52$ 个 $|0\rangle$ 辅助位，延迟为 $(n_P+12)T_{\mathrm{LC}}$。公式 (9) 给的是所有子句组成的完整 phaser，不能直接由图里的 MCX 深度替代。
> **[原文内部约定问题，p.4 与 p.10]** 式 (4) 的负号与式 (3) 推出正相位 $e^{+i\gamma C_j(x)}$，式 (20) 印刷为负相位 $e^{-i\gamma C_j(x)}$。本实现明确选式 (3)–(4) 的约定，即 `p(+gamma)`。

> **[功能等价简化]** 用 SAT 标记而非唯一 UNSAT 模式实现子句相位。等价关系是 $e^{i\gamma C_j}=e^{i\gamma}e^{-i\gamma(1-C_j)}$；对控制文字的 X 位置、相位号和全局相位必须一起核对，不能只比较两张图的 X 门位置。


## 5. Mixer 的相位实现

![[obsidian_assets/05_mixer_phase_basis.png|1100]]

论文采用

$$
H_M=\frac12\sum_{j=1}^{n}X_j,
\qquad
e^{-i\beta_l H_M}=\bigotimes_{j=1}^{n}R_x(\beta_l),
$$

其中

$$
R_x(\theta)=e^{-i\theta X/2}.
$$

因此 Qiskit 应使用 `rx(beta)`。X 基底相位实现为

$$
H P(-\beta_l)H=e^{-i\beta_l/2}R_x(\beta_l).
$$

对全部 $n$ 根线，差异是整体相位 $e^{-in\beta_l/2}$，不改变测量概率。

在足够资源态工厂供应的假设下，所有单比特相位分解并行执行：

$$
T_{\mathrm{mixer}}=n_P T_{\mathrm{LC}}.
$$

因此不用乘 $n$。$n_P$ 近似与相位合成的 T 门消耗数相关，但不能未经核对直接用 Table III 的 $N_T$ 列替换。


## 6. SAT Oracle

![[obsidian_assets/06_SAT_oracle.png|1100]]

整份 SAT 公式的满足标记是

$$
C(x)=\bigwedge_{j=1}^{m}C_j(x),
\qquad
O_C|x\rangle=(-1)^{C(x)}|x\rangle.
$$

依次计算各条子句 OR，把标记经 AND 树汇总，对总标记施加 $Z$，然后反计算 AND 和所有子句。所有辅助位最终回到 $|0\rangle$。

图中 $m=2$，单个 Toffoli 就能汇总两个标记；Notebook 的紧凑版本直接对两个标记使用受控 $P(\pi)$，功能等价。

正文公式 (10) 给出整个 oracle 的近似时间：

$$
T_{O_C}=4c\log_2\!\left(\frac{km}{c}\right)T_{\mathrm{LC}}.
\tag{10}
$$

这一项已经含正算和反算，不再乘 $2$。Appendix C 的实现通过有意延迟与辅助位回收，使空间和资源态需求受 phaser 的预算约束。正文没有把公式 (10) 逐框分摊，所以图中不自行指定每个 compute/AND 框的微秒数。


## 7. 全零态 Oracle

![[obsidian_assets/07_zero_oracle.png|1100]]

全零态 oracle 的功能是

$$O_0=I-2|0^n\rangle\langle0^n|=X^{\otimes n}(I-2|1^n\rangle\langle1^n|)X^{\otimes n}.$$

它只将全零基态的振幅乘 -1，其余基态不变。代码先 X 全部数据位，再通过目标位 H–MCX–H 实现全 1 模式受控 Z，最后恢复 X。

> **[H 门位置说明]** 此处两个 H 仅作用在 MCX 的目标位上，用于实现受控 Z；不是此前移除的、夹在整个 O_0 模块前后的两组全寄存器 H。整体迭代直接调用 O_0。n=1 的实现使用 -Z，避免调用没有控制位的 MCX。

正文式 (11) 给出 $T_{O_0}=4\log_2(n)T_{\mathrm{LC}}$。这是原文 TACU 实现的近似预算，不是此 MCX 电路的准确整数深度；原文资源计数为最多 n-1 个 CCZ 态。


## 8. Phaser 流水线预算

![[obsidian_assets/08_phaser_timing_schedule.png|1100]]

染色在量子执行前产生 c 批，同批子句访问的数据位互不重叠。论文 TACU 每个任务只需一个逻辑周期访问原始数据位，之后可在各自辅助位上继续处理。因此可以每个逻辑周期派发一批，而不必等前一批全部完成；Pauli-Z 修正推迟到 phaser 末尾。

令 $L=\lceil\log_2k\rceil$。p.23 Appendix B 给出的单任务延迟预算为

$$\tau_{\mathrm{task}}=(3L+n_P+L)T_{\mathrm{LC}}=(n_P+4L)T_{\mathrm{LC}}.$$

三项分别为树形 AND 写入、单比特相位合成、逐层测量清除。p.11 Corollary IV.1 给出

$$\mathrm{LogicalDepth}(V_C)\le c+n_P+4L.$$

> **[更正旧说明]** 额外的 $n_P+4L$ 同时预算了首次派发前准备和末次派发后收尾，不是仅在全部派发后发生的等待。图中「Startup」与「Finish」合计使用该预算，未给两者各自编造周期数。

正文式 (9) 采用上述预算写作

$$T_{\mathrm{phaser}}=(c+n_P+4L)T_{\mathrm{LC}},\qquad k=8\Rightarrow L=3.$$

> **[与原文实现不同]** 代码中的普通 MCX phaser 没有实现这一流水线；c 也是手动提供，没有实际执行染色。图 8 仅解释论文的资源预算，不能作为所画功能电路的实测运行轨迹。


## 9. 数值资源预算

![[obsidian_assets/09_numerical_timing.png|1100]]

数值输入来自第 9 节 RESOURCE_INPUTS，当前输出会随参数重新计算。

$$T_{\mathrm{LC}}=d\times1\,\mu\mathrm{s},\quad T_U=p(T_{\mathrm{phaser}}+T_{\mathrm{mixer}}),\quad T_Q=2T_U+T_{O_C}+T_{O_0}.$$

$$P_{\mathrm{model}}=2^{-0.69p^{-0.32}n},\quad R_{\mathrm{Eq7}}\simeq\frac{\pi}{4\sqrt{P_{\mathrm{model}}}},\quad T_{\mathrm{Eq7}}=R_{\mathrm{Eq7}}T_Q.$$

只额外计一次初始演化的组件预算为 $T_U+T_{\mathrm{Eq7}}$；正文稳健协议预算约为 $4T_{\mathrm{Eq7}}$。后者不是在此小例子中执行了四次迭代。

> **[资源估算假设]** 默认 n=191,p=253,d=29 与 Table III cubic 行相同，但 c=2112 是经验值，nP=27 是演示输入；表中的 N_T=24 不能在未核对编译方法时直接替代 nP。因此没有复现 64.57 h 交叉点。模型成功率不是小例子的成功率，模型时间也不是对字面式 (6) 电路的成功保证。

初始 H、重置、测量、经典验证、训练与布线没有单独数值；c 未经实际染色计算。式 (10)–(11) 是正文近似，而非附录中的完整整数调度。


### 本次模型计算结果

$$n=191,\quad m=33616,\quad p=253,\quad c=2112,\quad n_P=27,\quad d=29.$$

$$T_{\mathrm{mixer}}=0.783000\,\mathrm{ms},\quad T_{\mathrm{phaser}}=62.379000\,\mathrm{ms}.$$

$$T_{O_C}=1.713098\,\mathrm{s},\quad T_{O_0}=0.878982\,\mathrm{ms}.$$

$$T_U=15.979986\,\mathrm{s},\quad T_Q=33.673949\,\mathrm{s}.$$

模型成功率：1.76623e-07；连续轮数预算：1868.813。

式 (7) 预算：17.4806 h；加一次初始 U：17.4851 h；正文稳健协议预算：69.9226 h。


## 原文对照：当前实现的约定、差异和未实现部分

以下以项目保存的 arXiv:2504.01897v1 PDF 为准，页码为印刷页码。差异分为「原文内部约定问题」「功能等价简化」「资源估算假设」；不将推断写成作者的明确说明。

1. **[原文内部约定问题：初态与式 (6)]** p.3 式 (2)–(3) 定义 $|\psi\rangle=U|+\rangle^{\otimes n}$，且 $U$ 只含演化；p.4 式 (6) 使用 $UO_0U^\dagger O_C$，并将 $O_0$ 定义为全零态翻相。当前代码按式 (6) 字面执行，不在 $O_0$ 前后补全寄存器 H。由定义推得 $UO_0U^\dagger$ 针对 $U|0^n\rangle$，与式 (2) 的初态一般不同。原文未在此明确说明是否改用了完整制备器的约定，因此不能仅据字面电路宣称标准 AA 的成功概率规律成立。
2. **[原文内部约定问题：相位正负号]** p.4 式 (4) 的 $H_C=-\sum_jC_j$ 与式 (3) 给出 $e^{+i\gamma\sum_j C_j(x)}$；p.10 式 (20) 却打印 $e^{-i\gamma C_j(x)}$。当前代码遵循式 (3)–(4)，对 SAT 标记施加 `p(+gamma)`，不是逐字照抄式 (20)。如果使用另一套角度符号约定，必须同时转换参数，不能仅换一个符号。
3. **[功能等价简化：相位 gadget]** `phaser()` 使用理想 MCX、精确 `p()` 和普通反计算；原文 Fig.2C、Sec.IV.C、Appendix B 使用 CCZ 资源态、Pauli 测量和反馈构建 TACU。当前代码没有实现 TACU，也没有将任意角度门分解为 Clifford+T。功能门图的深度不是式 (9) 的容错逻辑周期数。
4. **[功能等价简化：Oracle]** `sat_oracle()` 直接给全真子句标记施加受控相位，与 compute–AND–Z–uncompute 在清零辅助位的输入上功能相同；它不是 Appendix C 的有意延迟、回收辅助位和资源态调度实现。`zero_oracle()` 的目标位 H–MCX–H 用于实现受控 Z，是 oracle 内部的门，与已移除的两组全寄存器 H 不同。
5. **[更正旧说明：流水线]** p.11 Corollary IV.1 给出深度上界 $c+n_P+4\lceil\log_2k\rceil$。其中额外项覆盖首次派发前准备和末次派发后收尾；不是说派发结束后必定再等完整的 $n_P+4\lceil\log_2k\rceil$。p.23 Appendix B 将单个任务延迟分为 AND 写入 $3L$、单比特相位 $n_P$、测量清除 $L$，$L=\lceil\log_2k\rceil$。图 8 是预算示意，不是串行执行轨迹。
6. **[资源估算假设：颜色与相位成本]** `c` 和 `nP` 都是手动输入，代码未生成随机大实例、冲突图或实际染色。默认 $c=2112\approx12r$ 来自经验选取；$n_P=27$ 是演示值。Table III 的 cubic 行为 $n=191,p=253,d=29,N_T=24$；$N_T$ 是 T 门数量，不自动等于任意实现中的 $n_P$。当前输入不构成该表的完整重现。
7. **[资源估算假设：成功率与总时间]** 式 (7) 使用的 $P=2^{-0.69p^{-0.32}n}$ 是所引用研究给出的随机 8-SAT 实例平均模型；它不是小例子的测量成功率。`T_eq7_seconds` 是原文预算模型，不是对字面式 (6) 仿真成功率的保证。式 (10)–(11) 是正文近似，未实施附录中完整的取整、调度与空间约束。
8. **[资源估算假设：稳健协议与未计开销]** p.9 设置 $\delta=1/2^4=1/16$，对应约 4 倍协议预算。代码报告 $4T_q$，未实现 Theorem IV.1 的逐阶段尝试、失败后重新制备及测量停止条件。初始 H、重置、读出、经典验证、训练和布线开销未单列；资源态工厂、物理噪声和译码器未模拟。
9. **[实例与输入边界]** 演示是固定 $n=8,m=2,p=2,R=1$，不是 $m/n=176$ 的随机阈值实例。原文 Sec.IV.F 允许有放回变量抽样；代码对重复文字、恒真子句作精确布尔化简，避免 MCX 重复控制位。空 OR 为假；空整份公式不在本代码支持范围内。`x_i` 对应整数赋值的第 i 位，Qiskit ket 字符串按 $|x_{n-1}\cdots x_0\rangle$ 显示。

**验证范围。** PASS 表示理想功能电路与独立数学参考一致，包括相位符号、辅助位清零、逆电路和多轮式 (6) 的演化；不表示复现了完整容错编译、论文交叉点或标准 AA 成功率定理。

[原文 v1](https://arxiv.org/abs/2504.01897v1)


## 文件使用

将本笔记与同目录 obsidian_assets 文件夹一起复制到 vault。Notebook 的重新生成文件写入 results/；notes/ 保存用于阅读的正式笔记。原始参考文件 sources/ 不修改。
