# Sparrow 本地使用指南

## macOS

在仓库根目录用 Apple Clang 编译，然后运行 8-SAT 主实例。编译器由 Xcode Command Line Tools 提供。

```sh
./classical_solvers/sparrow/build.sh
./classical_solvers/sparrow/bin/sparrow --randomc 1 -a --runs 1 --maxflips 1000000 qaoa_aa_3sat/data/instance_8sat_n10_m176_seed20261116.cnf 1
```

找到解时，程序会打印 `s SATISFIABLE` 和赋值，退出码为 10。两个 8-SAT Notebook 会自动找到本机程序。Mac 构建时对上游源码的副本应用两处修复：为按 1 起始编号的邻居表分配最后一个元素，并在使用默认参数时初始化子句选择函数。

复测主实例并与仓库实验 CSV 比较，只需 Python 3 标准库。省略 `--output` 可仅打印统计。

```sh
python3 classical_solvers/sparrow/benchmark_8sat.py --output sparrow-local.csv
```

测试沿用 AA Notebook 的 3 次预热、种子 1–1000、每次最多 100 万次翻转和 5 秒超时。每次单独启动进程，从启动调用计时到收取输出，之后逐子句验解。不同平台的 C 库可能为同一种子生成不同的随机序列。对照数据取自 `04_sparrow_1000_runs.csv`，云端版本保存的是 Windows 测量；重跑完整 Notebook 会更新该文件。

## Windows

已编译为 Windows 64 位程序，不需要 Python、Qiskit 或 WSL 才能运行。

源码来自你指定的 [adrianopolus/Sparrow 仓库](https://github.com/adrianopolus/Sparrow)，版本为 **Sparrow 2014**。固定源码提交：`fcbda5127ad873ec306905b5c22cc4388d079f17`。`upstream/` 保留下载的原始源码、文档与许可；没有修改这些文件。

## 1. 先运行示例

在 PowerShell 里执行：

```powershell
cd "D:\桌面\hkust\urop\code\classical_solvers\sparrow"
.\run.ps1
```

默认运行 `examples/demo.cnf`，随机种子为 1。看到 `s SATISFIABLE` 表示找到了满足全部子句的赋值。

```text
s SATISFIABLE
v 1 -2 -3 0
```

这里 `1` 表示 x₁ = 1，`-2` 表示 x₂ = 0，`-3` 表示 x₃ = 0，最后的 `0` 是结束标记。

也可以运行准备好的 8-SAT 示例：

```powershell
.\run.ps1 -Instance .\examples\demo-8sat.cnf -Seed 1
```

这个 8-SAT 文件含 32 个变量、800 个子句，每个子句包含 8 个不同变量。生成时预先保证存在满足解，用于检查安装；它不是论文基准实验采用的随机实例分布。

如果 PowerShell 提示禁止执行脚本，用下面的命令运行即可，无需永久改变系统策略：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\run.ps1
```

## 2. 输入你自己的 SAT 实例

Sparrow 的输入是 **DIMACS CNF 文件**：

```text
c This is a comment.
p cnf 3 2
1 -2 3 0
-1 2 -3 0
```

这表示有 3 个变量、2 个子句：

\[
(x_1\lor\neg x_2\lor x_3)\land(\neg x_1\lor x_2\lor\neg x_3).
\]

- `p cnf n m`：n 是变量数，m 是子句数。
- 正整数 i 表示 xᵢ，负整数 −i 表示 ¬xᵢ；变量编号从 1 开始。
- 每个子句以 `0` 结束；所有子句通过 AND 连接。
- 这是经典求解器的文件格式，不是量子电路或量子态。

运行自己的文件，并可选保存输出：

```powershell
.\run.ps1 -Instance "D:\桌面\hkust\urop\your-instance.cnf" -Seed 1 -MaxFlips 10000000 -TimeoutSeconds 60 -OutputLog .\solver-output.txt
```

`run.ps1` 会检查 DIMACS 头、子句数量、编号与结束符，并使用临时文件处理中文路径。每个子句内应使用不同变量；重复文字和永真子句需先清理。空公式或空子句不交给此启动器处理。

## 3. 运行参数与输出

- `-Seed`：随机种子。相同程序与输入下，固定种子方便重复检查。
- `-MaxFlips`：总变量翻转预算，默认 1,000,000；这个 Windows 版本接受 1～2,147,483,647。上游程序把它作为整个搜索的总预算。
- `-Runs`：尝试次数上限，默认 1。若需在总预算内重启，可配合 `-Luby -LubyBase 262144`；仅增加 Runs 不会突破总翻转预算。
- `-TimeoutSeconds`：从启动求解器开始计算的实际经过时间上限，默认 60 秒；输入检查和临时文件准备时间不包含在内。
- `-CpuSeconds`：可选的进程 CPU 时间上限；默认 0 表示不设置，仍受上述实际时间上限约束。
- `-NoAssignment`：不打印赋值；默认会打印。
- `-OutputLog`：把输出保存到指定文本文件；所在目录须已存在。

例如带重启和 CPU 时间限制：

```powershell
.\run.ps1 -Instance .\examples\demo-8sat.cnf -Seed 2 -Luby -Runs 10 -MaxFlips 10000000 -CpuSeconds 30 -TimeoutSeconds 60
```

**Sparrow 是不完备的随机局部搜索求解器。** `SATISFIABLE` 表示已找到满足解；`UNKNOWN` 表示预算内没有找到解，不能据此判定 UNSAT。`examples/unsat-demo.cnf` 故意包含所有 3 变量符号组合，搜索结束应返回 UNKNOWN：

```powershell
.\run.ps1 -Instance .\examples\unsat-demo.cnf -MaxFlips 1000
```

原生程序找到解时退出码是 **10**，预算耗尽时是 **0**；启动脚本已按这个约定处理，不会把 10 当作失败。程序报出的 CPU 时间对极小实例可能为 0，导致 `flips/sec` 为 `inf`；这不影响满足解判断。启动脚本还会另行显示实际经过时间，两种时间不能混用。

## 4. 文件与重新编译

- `bin/sparrow.exe`：可以直接运行的程序。
- `run.ps1`：推荐的启动入口，处理中文输入路径、检查输入、设置预算并解释返回状态。
- `build.ps1`：重新编译入口。
- `platform/windows/windows_compat.h`：Windows 计时接口。
- `upstream/`：原始代码、文档和 `license.txt`。
- `examples/`：简单 SAT、8-SAT、不可满足测试文件。
- `build/`：重新编译时生成的中间文件，可重新生成。
- `results/installation-check.txt`：安装后运行 8-SAT 示例的输出记录。

本机使用已有的 MinGW-w64 GCC 15.2.0；缺失头文件和 `libgcc` 已从匹配的 [MSYS2 官方软件包](https://repo.msys2.org/mingw/mingw64/mingw-w64-x86_64-gcc-15.2.0-8-any.pkg.tar.zst) 补齐，没有覆盖原有编译器文件。重新编译：

```powershell
.\build.ps1
# 其他电脑可指定自己的 MinGW-w64 GCC：
.\build.ps1 -Compiler "C:\msys64\mingw64\bin\gcc.exe"
```

构建脚本生成单独的 Windows 源文件，替换上游 Linux 的计时、CPU 限额与信号接口；CPU 限额每 16,384 次翻转检查一次，因此可能略超预算。编译时通过临时目录避开 MinGW 链接器的中文输出路径问题，再把可执行文件复制到 `bin/`。未更换变量选择、概率或子句权重算法。启动脚本显式传入 `--randomc 1`：源码在固定子句长度且未显式设置该选项时，可能留下未初始化的子句选择函数指针，导致崩溃。

如需绕过启动器，使用 ASCII 输入路径，并显式包含该参数：

```powershell
.\bin\sparrow.exe --randomc 1 -a --runs 1 --maxflips 1000000 "C:\Temp\instance.cnf" 1
```

## 5. 与论文复现的关系

这次配置的是你提供的仓库，源码自述为 Sparrow 2014。**尚未确认它与 QAOA 论文基准实验使用的具体版本、参数和构建环境一致**，不能直接把本机运行时间当成论文的 Sparrow 数据。

Windows 的随机数实现和计时接口与 Linux 也有差别；相同种子不保证跨平台得到相同搜索轨迹。仓库对最大子句长度大于 5 的输入使用标为 “7 SAT” 的默认参数，因此 8-SAT 输入看到这个标签并不代表文件读错，也不表示参数已按论文的 8-SAT 实验优化。

本地检查已完成：简单 SAT 和 8-SAT 各用三个种子找到满足解，并独立逐子句核对；不可满足测试返回 UNKNOWN；CPU 时间限额正常退出。许可保留在 `upstream/license.txt`，使用范围以原许可为准。
