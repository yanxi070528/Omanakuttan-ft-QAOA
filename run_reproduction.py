"""基于作者 Zenodo 源码的 Figure 3A / Table III 简单复现。

运行：在本目录中执行 `python run_reproduction.py`。
只需 numpy、matplotlib；详细来源、公式和差异见 README.md。
"""

from __future__ import annotations

import csv
import math
import os
from pathlib import Path

# 把 matplotlib 字体缓存放在本项目，避免系统用户目录没有写权限。
os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parent / ".mpl_cache"))
import matplotlib

matplotlib.use("Agg")  # 运行脚本时直接保存图片，无需弹出绘图窗口。
import matplotlib.pyplot as plt

import author_utils_runtime as author


HERE = Path(__file__).resolve().parent
OUT = HERE / "results"
OUT.mkdir(exist_ok=True)

# Figure 3A / Table III 的三种渐进加速。n_paper 只用于对照；
# 实际交叉点 n 是下文逐个整数搜索得到的，并非直接抄入计算结果。
CASES = [
    {"name": "quadratic", "speedup": 2, "n_paper": 242, "n_range": range(220, 260),
     "paper": {"d": 35, "qubits_m": 152.43, "depth_1e8": 6750.25,
               "G_1e12": 419.0, "jobs": 840, "ancilla": 43680, "NT": 27,
               "eps_rot": 1.76e-9, "eps_T": 1e-17,
               "decoder": 52320, "cores": 71, "hours": 3 * 365 * 24}},
    {"name": "cubic", "speedup": 3, "n_paper": 191, "n_range": range(175, 210),
     "paper": {"d": 29, "qubits_m": 84.43, "depth_1e8": 20.76,
               "G_1e12": 0.96, "jobs": 592, "ancilla": 30784, "NT": 24,
               "eps_rot": 6.65e-8, "eps_T": 1.44e-14,
               "decoder": 36900, "cores": 50, "hours": 64.57}},
    {"name": "quartic", "speedup": 4, "n_paper": 179, "n_range": range(165, 195),
     "paper": {"d": 28, "qubits_m": 73.91, "depth_1e8": 5.0,
               "G_1e12": 0.21, "jobs": 540, "ancilla": 28080, "NT": 23,
               "eps_rot": 1.41e-7, "eps_T": 6.48e-14,
               "decoder": 33660, "cores": 46, "hours": 14.99}},
]


def classical_fit():
    """读取作者的 Rand-9 拟合参数；源 notebook 以零起始下标 val=2 选它。"""
    line = (HERE / "optimized_parameters.txt").read_text(encoding="utf-8").splitlines()[2]
    shift = float(line.split(",")[0].split(":")[-1])
    lam = float(line.split(",")[1].split(":")[-1])
    return lam, shift


LAMBDA, SHIFT = classical_fit()


def calculate(n: int, speedup: int) -> dict:
    """调用作者的主函数，给位置式返回值加上容易理解的中文字段。"""
    x = author.get_8_SAT_params(
        n,                         # 8-SAT 变量个数
        1e-3,                      # 物理错误率 p_ph
        1e-6,                      # 一个表面码纠错周期：1 微秒
        speedup,                   # 渐进加速目标，函数内部由此选 QAOA 层数 p
        2,                         # 作者 notebook 的 alpha；主函数此路径未使用
        1,                         # 每次派发间隔 τ=1 个逻辑周期
        0.57, 9,                   # 旋转门分解的 (b,c)
        46800 * (157 / 30) / 4,    # 单个资源态工厂的物理量子比特占用
        LAMBDA, SHIFT, False,      # Rand-9 经典运行时间分布；False=移位指数
    )
    # 返回顺序逐项核对自作者 utils.py 的 return 元组。
    return {
        "n": n, "p": int(x[1]), "G": float(x[2]), "depth": int(x[3]),
        "d": int(x[4]), "NT": int(x[5]), "eps_T": float(x[6]),
        "log_Tc": float(x[8]), "log_Tq": float(x[9]),
        "jobs": int(x[10]), "qubits": int(x[11]), "cores": int(x[12]),
        "ancilla": int(x[14]), "decoder": int(x[15]),
        "eps_rot": float(x[16]), "oracle_parallel": int(x[19]),
        "speedup": speedup,
    }


def first_crossover(case: dict) -> dict:
    """找最小整数 n，使经典预计时间 Tc 不短于量子预计时间 Tq。"""
    for n in case["n_range"]:
        row = calculate(n, case["speedup"])
        if row["log_Tc"] >= row["log_Tq"]:
            return row
    raise RuntimeError(f"{case['name']} 的搜索范围没有交叉点")


def save_csv(rows: list[dict]) -> None:
    fields = ["case", "n", "p", "d", "G", "depth", "jobs", "ancilla", "NT",
              "eps_rot", "eps_T", "decoder", "cores", "qubits", "Tq_hours",
              "Tc_hours", "Tc_over_Tq", "surface_failure_bound"]
    with (OUT / "table_III_author_output.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row[k] for k in fields})


def plot_figure_3a(rows: list[dict]) -> None:
    """重绘 Figure 3A 的资源摘要；是数据重绘，不是原论文的排版复制。"""
    labels = [r["case"] for r in rows]
    fig, axs = plt.subplots(2, 2, figsize=(10, 6), layout="constrained")
    panels = [
        ("QAOA depth p", "p", None),
        ("Crossover problem size n", "n", None),
        ("Physical qubits (millions)", "qubits", 1e6),
        ("Crossover time (hours)", "Tq_hours", None),
    ]
    for ax, (title, key, divisor) in zip(axs.flat, panels):
        actual = [r[key] / divisor if divisor else r[key] for r in rows]
        paper = [
            [71, 253, 623][i] if key == "p" else
            c["n_paper"] if key == "n" else
            c["paper"]["qubits_m"] if key == "qubits" else
            c["paper"]["hours"]
            for i, c in enumerate(CASES)
        ]
        xs = list(range(len(rows)))
        ax.bar([i - .18 for i in xs], actual, width=.36, label="Author code")
        ax.bar([i + .18 for i in xs], paper, width=.36, label="Paper", alpha=.65)
        ax.set_xticks(xs, labels)
        ax.set_title(title)
        ax.grid(axis="y", alpha=.2)
        if key == "Tq_hours":
            ax.set_yscale("log")  # 二次加速对应数年，其余是小时；对数轴可同时看清。
    axs[0, 0].legend(fontsize=8)
    fig.suptitle("Figure 3A: crossover resources (author code vs paper)")
    fig.savefig(OUT / "figure_3A_reproduction.png", dpi=180)
    plt.close(fig)


def plot_g_and_surface_code(rows: list[dict]) -> None:
    """把用户特别关心的 G 和码距 d 单独画出来。"""
    labels = [r["case"] for r in rows]
    xs = list(range(len(rows)))
    fig, axs = plt.subplots(1, 2, figsize=(10, 3.5), layout="constrained")
    axs[0].bar(xs, [r["G"] for r in rows], color="tab:purple")
    axs[0].set_xticks(xs, labels)
    axs[0].set_yscale("log")
    axs[0].set_ylabel("Total non-Clifford gates G")
    axs[0].set_title("G counts (whole algorithm)")
    axs[1].bar([i - .18 for i in xs], [r["d"] for r in rows],
               width=.36, label="Author code")
    axs[1].bar([i + .18 for i in xs], [c["paper"]["d"] for c in CASES],
               width=.36, label="Paper", alpha=.65)
    axs[1].set_xticks(xs, labels)
    axs[1].set_ylabel("Surface-code distance d")
    axs[1].set_title("Code distance: source vs Table III")
    axs[1].legend(fontsize=8)
    for ax in axs:
        ax.grid(axis="y", alpha=.2)
    fig.savefig(OUT / "G_and_surface_code.png", dpi=180)
    plt.close(fig)


def save_comparison(rows: list[dict]) -> None:
    # 直接给出源码值与论文值；不要把相差 1 的 d 或 NT 偷偷修正。
    cols = [
        ("n", lambda r: r["n"], lambda p: p["n_paper"]),
        ("p", lambda r: r["p"], lambda p: {2: 71, 3: 253, 4: 623}[p["speedup"]]),
        ("d", lambda r: r["d"], lambda p: p["paper"]["d"]),
        ("G / 10^12", lambda r: r["G"] / 1e12, lambda p: p["paper"]["G_1e12"]),
        ("depth / 10^8", lambda r: r["depth"] / 1e8, lambda p: p["paper"]["depth_1e8"]),
        ("qubits / 10^6", lambda r: r["qubits"] / 1e6, lambda p: p["paper"]["qubits_m"]),
        ("jobs", lambda r: r["jobs"], lambda p: p["paper"]["jobs"]),
        ("ancilla", lambda r: r["ancilla"], lambda p: p["paper"]["ancilla"]),
        ("N_T", lambda r: r["NT"], lambda p: p["paper"]["NT"]),
        ("rotation error", lambda r: r["eps_rot"], lambda p: p["paper"]["eps_rot"]),
        ("T infidelity", lambda r: r["eps_T"], lambda p: p["paper"]["eps_T"]),
        ("decoder", lambda r: r["decoder"], lambda p: p["paper"]["decoder"]),
        ("cores", lambda r: r["cores"], lambda p: p["paper"]["cores"]),
        ("Tq / h", lambda r: r["Tq_hours"], lambda p: p["paper"]["hours"]),
    ]
    lines = ["# Table III：作者源码输出与论文对照", "",
             "| 指标 | quadratic：源码 / 论文 | cubic：源码 / 论文 | quartic：源码 / 论文 |",
             "|---|---:|---:|---:|"]
    for title, calc, ref in cols:
        values = []
        for row, case in zip(rows, CASES):
            a, b = calc(row), ref(case)
            values.append(f"{a:.4g} / {b:.4g}" if isinstance(a, float) else f"{a} / {b}")
        lines.append(f"| {title} | " + " | ".join(values) + " |")
    lines += [
        "", "## 表面码与 G 的计算", "",
        "作者源码取 $p_{ph}=10^{-3}$、$p_{th}=10^{-2}$、目标电路保真度 $F=0.99$。",
        "总非 Clifford 门数：$G=N_{rot}(7+N_T)$，其中 "
        r"$N_{rot}=2pn(176+1)\lfloor\pi/(4\sqrt{P_{QAOA}})\rfloor$。",
        r"码距使用 $d=\operatorname{int}[2(\ln(1-F)-\ln G)/\ln(p_{ph}/p_{th})]+1$；"
        "这里 `int` 是向零截断，正值时相当于取整后加 1。",
        "联合界 $G(p_{ph}/p_{th})^{d/2}$ 是该码距下的表面码失败概率上界。",
        "", "| 加速 | G | 源码 d | 联合界 | 源码 $T_q/T_c$ |",
        "|---|---:|---:|---:|---:|",
    ]
    for r in rows:
        lines.append(f"| {r['case']} | {r['G']:.6g} | {r['d']} | "
                     f"{r['surface_failure_bound']:.4g} | "
                     f"{r['Tq_hours']/r['Tc_hours']:.4g} |")
    lines += [
        "", "## 阅读结果时注意", "",
        r"- 交叉点按整数 $n$ 搜索：选最小满足 $T_c\ge T_q$ 的 $n$，所以两时间不必完全相等。",
        "- 作者源码的 `qaa_fac=4` 只乘在运行时间 $T_q$ 上；表内的 $G$ 与 `depth` 未乘该 4。",
        "- 源码算出的 $d$ 和 $N_T$ 分别比 Table III 每行小 1；不要把表中的值覆盖源码结果。",
        "- 物理量子比特列也略有差异，说明当前 Zenodo 文件与论文表格的取整或参数版本并非逐列完全一致。",
        "- `author_utils_runtime.py` 的唯一数值路径改动是把 SciPy 积分换成移位指数分布的等价解析期望。",
    ]
    (OUT / "table_III_comparison.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    rows = []
    for case in CASES:
        row = first_crossover(case)
        row["case"] = case["name"]
        row["Tq_hours"] = math.exp(row["log_Tq"]) / 3600
        row["Tc_hours"] = math.exp(row["log_Tc"]) / 3600
        row["Tc_over_Tq"] = math.exp(row["log_Tc"] - row["log_Tq"])
        row["surface_failure_bound"] = row["G"] * .1 ** (row["d"] / 2)
        rows.append(row)
        print(f"{row['case']:9s}: n={row['n']}, p={row['p']}, d={row['d']}, "
              f"G={row['G']:.3g}, Tq={row['Tq_hours']:.3f} h")
    save_csv(rows)
    save_comparison(rows)
    plot_figure_3a(rows)
    plot_g_and_surface_code(rows)
    print(f"结果已保存到：{OUT}")


if __name__ == "__main__":
    main()
