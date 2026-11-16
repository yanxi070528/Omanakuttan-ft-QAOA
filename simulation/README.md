# Figure 3A 与 Table III 复现

## 内容

- `notebooks/01 - Figure 3A 与 Table III.ipynb`：主要计算流程，附公式与论文参数核对。
- `notebooks/ft-QAOA.ipynb`：随机 8-SAT、Sparrow 指数拟合及并行搜索的演示。
- `src/author_utils_notebook.py`：主 Notebook 导入的运行模型，必须保留。
- `data/optimized_parameters.txt`：经典搜索拟合参数，必须保留。
- `reference/author_utils_original.py`：保留的作者模型参考副本。
- `results/notebook_table_III.csv`：未圆整的 Notebook 计算结果。
- `results/notebook_figure_3A.png`、`results/notebook_G_surface.png`：Notebook 绘制的结果。
- `notes/table_III_comparison.md`：源码与论文 Table III 的逐列比较及差异说明。

从主 Notebook 第 1 个代码格开始顺序运行。结果写入 `results/`。

计算得到交叉规模 n=242、191、179。当前源码的码距 d=(34,28,27)、每次旋转 T 门数 NT=(26,23,22) 与论文各小 1；比较笔记保留这些差异。作者模型的 qaa_fac=4 已计入运行时间，不重复乘 4。

运行副本对并行移位指数分布使用等价解析期望 shift+1/(n*lambda)。完整参考模型保存在 `reference/`；本整理没有改动科学计算公式。
