# QAOA 8-SAT reproduction

This repository contains a small, formula-level reproduction of the classical baseline from:

> Omanakuttan et al., *Threshold for Fault-tolerant Quantum Advantage with the Quantum Approximate Optimization Algorithm*, arXiv:2504.01897.

The current notebook focuses on Obsidian note 01:

- random 8-SAT instance generation with `k = 8` and `r = m/n = 176`
- Sparrow median time-to-solution scaling
- Rand-9 parallelization model used for the classical baseline

## File

- `ft-QAOA.ipynb`: main reproduction notebook.

## Kernel

The notebook is configured for the local `phys1007` kernel:

```text
D:\miniconda\envs\phys1007\python.exe
```

Required packages in that kernel:

- `numpy`
- `matplotlib`
- `qiskit`

## Run

Open `ft-QAOA.ipynb` in Jupyter or VS Code, select the `phys1007` kernel, and run the cells in order.

The plotting cell saves:

```text
paper_figures_repro.png
```

This generated PNG is ignored by Git.

## Scope

This repository is intentionally limited to the classical baseline in note 01.

It does not yet contain:

- a real Sparrow benchmark run
- a Qiskit QAOA circuit simulation
- the fault-tolerant resource model from the later notes
