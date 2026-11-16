# Non-fault-tolerant QAOA + AA: independent convention review

These notes distinguish the supplied paper's definitions, exact deductions, and implementation choices. The experimental default is 3-SAT with **n = 10 variables and m = 8 clauses**. The paper's fitted random-8-SAT scaling laws must not be reused as 3-SAT predictions.

## 1. The paper's cost and angle conventions

Omanakuttan et al., [arXiv:2504.01897v1](https://arxiv.org/pdf/2504.01897v1), Eqs. (2)–(5):

$$
|\psi\rangle=U_{\rm QAOA}|+\rangle^{\otimes n},\qquad
U_{\rm QAOA}=\prod_{\ell=1}^{p}e^{-i\beta_\ell H_M}e^{-i\gamma_\ell H_C},
$$

$$
H_M=\frac12\sum_{i=1}^{n}X_i,\qquad
H_C|x\rangle=-\left(\sum_{j=1}^{m}C_j(x)\right)|x\rangle.
$$

Here C_j(x) is 1 when clause j is satisfied, and 0 when violated. The mixer is exactly `rx(beta)` because H_M=(1/2) sum X. A circuit layer applies the phaser first and mixer second.

Define the number of violations V(x)=sum_j[1-C_j(x)]. The paper's Eq. (4) gives $H_C|x\rangle=[V(x)-m]|x\rangle$, hence

$$
e^{-i\gamma H_C}=\sum_x e^{-i\gamma[V(x)-m]}|x\rangle\langle x|.
$$

The direct SAT circuit applies angle **-gamma** to each unique failed clause pattern, and adds global phase **+gamma*m**. No product replacement, degree reduction or penalty optimization variables are used. Positive-literal wires receive X before and after the controlled phase. The gamma parameters reported in the notebook and slides all use this convention. Reversing every gamma converts to the opposite cost-sign convention, but the two parameter conventions must not be mixed.

The v1 paper's Methods Eq. (20) writes the opposite clause sign from Eq. (4). This implementation consistently follows Eq. (4), matching the negative satisfied-clause cost in the Results section. The notebook explicitly checks all 1024 basis-state phases, including global phase. It also verifies the native SAT oracle on a superposition over every data assignment, checking every phase and the return of all eight work flags to zero. The QAOA register contains 10 data qubits; work flags are used only to compute and uncompute the SAT predicate.

Pretraining minimizes the expectation of the paper's H_C from Eq. (4); mean violations are a diagnostic equal to this cost plus m. Minimizing expected cost and maximizing the SAT success probability are different optimization objectives: lower mean violations need not imply a larger probability of satisfying *every* clause. Explain the selected objective. The small-statevector simulator can compute this expectation exactly during training; this is classical simulation, not a claim that training used a real quantum device.

## 2. Correct reflection and state preparation

The complete preparation from zero is

$$
A=U_{\rm QAOA}H^{\otimes n},\qquad A|0^n\rangle=|\psi\rangle.
$$

Let S_0=I-2|0^n><0^n|, and S_chi=I-2 Pi_SAT. Standard amplitude amplification is

$$
Q=-A S_0 A^\dagger S_\chi.
$$

Source: Brassard, Hoyer, Mosca and Tapp, [arXiv:quant-ph/0005055v1](https://arxiv.org/pdf/quant-ph/0005055), Eq. (1). This source defines A as preparation from the zero state.

Written in the supplied paper's U_QAOA convention, this gives

$$
Q=-U_{\rm QAOA}H^{\otimes n}S_0H^{\otimes n}U_{\rm QAOA}^{\dagger}S_\chi.
$$

The supplied paper's Eq. (6) writes U S_0 U-dagger S_chi despite defining U as only the layer product in Eq. (3). A working implementation must either use A rather than that U, or put H gates around S_0. Explicitly label this as the standard AA basis correction. The overall minus is optional for measurement probabilities: removing it multiplies the state after R rounds by (-1)^R.

The SAT oracle must compute the original CNF satisfaction logic, or equivalently implement the phase predicate V(x)=0. It must **not** use an enumerated list of satisfying assignments to build the algorithm; enumeration is appropriate for independent correctness checking only. Clean work qubits must be uncomputed before reflection. A data-only zero reflection is sufficient on the reachable subspace when every module restores clean work qubits; test that this condition holds.

## 3. Fixed R and its actual success probability

Let

$$
P=\sum_{x:\,V(x)=0}|\langle x|\psi\rangle|^2,\qquad
\theta=\arcsin\sqrt P.
$$

Then

$$
P_R=\sin^2[(2R+1)\theta].
$$

Source: Brassard et al., Eq. (5) defines theta and Eq. (8) gives the amplified state. This equation also appears unnumbered in the proof of Omanakuttan et al., Theorem IV.1.

The paper's small-P approximation is R approximately pi/(4 sqrt P). To turn it into a discrete experimental rule, specify the rounding (for example floor). Do not describe that approximate choice as optimal when P is large.

The real-valued location of the first maximum is

$$
R_{\rm peak}=\frac{\pi}{4\arcsin\sqrt P}-\frac12.
$$

An exact first-peak integer choice evaluates the nonnegative floor/ceiling candidates and takes the one with larger P_R, with smaller R breaking ties. Include R=0. This is an **informed simulator choice** because it uses the exact P; it is not an unknown-P adaptive algorithm. At P=0 no R helps; at P=1 R=0 already succeeds.

For n=10,m=8 the formula is sparse, so the original QAOA state may already have high success. R=0 may be the best choice. Preserve and explain that result rather than changing the instance merely to force a speedup.

## 4. Fixed 1000-shot measurements

Each fixed QAOA/QAOA+AA circuit is sampled 1000 times. Report exact statevector SAT probability separately from empirical frequency and Wilson confidence intervals. Sparrow uses 1000 independent seeded solver runs. The experiment compares these three methods only.

## 5. Amplitude spectrum

Plot the basis index / bitstring against magnitude |alpha_x|, phase arg(alpha_x), and probability |alpha_x|^2 (or at minimum label clearly which quantity the figure shows). Mark satisfying outcomes independently from the CNF evaluator. For fixed R and 0<P<1,

$$
|\psi_R\rangle=
\frac{\sin[(2R+1)\theta]}{\sqrt P}\,\Pi_{\rm SAT}|\psi\rangle+
\frac{\cos[(2R+1)\theta]}{\sqrt{1-P}}\,(I-\Pi_{\rm SAT})|\psi\rangle.
$$

This closed form is useful as an independent oracle for tests. The executed result should still come from Qiskit gates, and spectrum amplitudes should be labelled exact simulator state amplitudes, not quantities reconstructed from 1000 computational-basis measurements. Such measurements do not reveal amplitude phases.

## 6. Time-to-solution and crossover

Keep measured classical simulator wall time separate from hypothetical hardware circuit time. A no-error-correction hardware model may use compiled gates with stated gate durations and scheduling constraints; it cannot use T-state factories, surface-code cycles, or TACU logical-cycle times.

For a prepared circuit A and one AA iterate Q,

$$
t_R=t_A+R\,t_Q+t_{\rm meas}+t_{\rm verify},
\quad t_Q=2t_A+t_{S_0}+t_{S_\chi}.
$$

This explicitly includes first state preparation omitted as a small overhead in the paper's Eq. (7). For fixed R with success P_R, independent retries give expected online TTS t_R/P_R. If training takes t_train on the CPU, show both cold-start t_train+t_R/P_R and already-trained online time. For a target success q, the fixed-shot budget is ceil(log(1-q)/log(1-P_R)); handle P_R=0 or 1 separately.

Sparrow measurements should distinguish process wall time, solver-reported search time, and executable startup overhead. Tiny CNFs can finish below the resolution of solver time reporting, so retain repeated wall measurements and distributions rather than replacing zero with an arbitrary positive number.

Crossover curves require a declared varying axis (instance size, p, or assumed gate duration), matched instances, and matched success targets/time definitions. Draw the curves and report **no measured crossover** if none occurs; do not fit the paper's 8-SAT exponent to n=10,m=8, and do not extrapolate a claim of practical quantum advantage from this toy statevector experiment.
