"""Ideal circuit semantics and the separate, approximate paper resource model.

The notebook embeds these definitions so it remains independently executable.
This module does not implement TACU, lattice surgery, or resource factories.
"""
import math
import numbers
import numpy as np
import qiskit
from qiskit import QuantumCircuit
from qiskit.circuit import ParameterExpression
from qiskit.circuit.library import PhaseGate
from qiskit.quantum_info import Statevector, Operator

PAPER = 'Omanakuttan et al., arXiv:2504.01897v1 (2025)'


def _positive_integer(value, name):
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, numbers.Integral) or value < 1:
        raise ValueError(f'{name} must be a positive integer.')
    return int(value)


def _validate_angle(angle, name):
    if isinstance(angle, ParameterExpression):
        return angle
    if isinstance(angle, (bool, np.bool_)) or not isinstance(angle, numbers.Real) or not math.isfinite(angle):
        raise ValueError(f'{name} must be a finite real angle or a Qiskit parameter.')
    return float(angle)


def _normalize_clause(n, clause):
    """Deduplicate literals; None means a tautology, [] means constant false.

    The paper samples variables with replacement (Sec. IV.F). Repeated controls
    cannot be passed directly to MCX, but OR semantics can be normalized exactly.
    """
    _positive_integer(n, 'n')
    literals = {}
    tautology = False
    for literal in clause:
        if not isinstance(literal, (tuple, list)) or len(literal) != 2:
            raise ValueError('Each literal must be (variable_index, positive_bool).')
        index, positive = literal
        if isinstance(index, (bool, np.bool_)) or not isinstance(index, numbers.Integral) or not 0 <= index < n:
            raise ValueError(f'Variable index must be an integer in [0, {n}).')
        if not isinstance(positive, (bool, np.bool_)):
            raise ValueError('Literal sign must be True or False.')
        index, positive = int(index), bool(positive)
        if index in literals and literals[index] != positive:
            tautology = True
        literals[index] = positive
    return None if tautology else list(literals.items())


def clause_compute(n, clause):
    """Reversibly XOR the OR of literals into flag n; never repeat controls."""
    literals = _normalize_clause(n, clause)
    qc = QuantumCircuit(n + 1, name='OR_clause')
    if literals is None:
        qc.x(n)  # A clause containing x and NOT x is always true.
        return qc
    if not literals:
        return qc  # An empty OR is false.
    positive = [i for i, sign in literals if sign]
    if positive:
        qc.x(positive)
    qc.mcx([i for i, _ in literals], n)
    if positive:
        qc.x(positive)
    qc.x(n)  # Complement UNSAT to obtain SAT.
    return qc


def evaluate(n, clause, x):
    """Classical OR evaluation; x_i is bit i (Qiskit little-endian convention)."""
    _normalize_clause(n, clause)  # Validate, while evaluating the original OR.
    if isinstance(x, (bool, np.bool_)) or not isinstance(x, numbers.Integral) or not 0 <= x < 2**n:
        raise ValueError('Assignment x must be an integer in [0, 2**n).')
    return int(any(((x >> i) & 1) if sign else 1 - ((x >> i) & 1) for i, sign in clause))


def phaser(n, clauses, gamma):
    """Eqs. (3)-(4): positive phase on satisfied clauses; ideal MCX circuit.

    Eq. (20) prints the opposite sign. We explicitly follow H_C in Eq. (4).
    """
    _positive_integer(n, 'n')
    gamma = _validate_angle(gamma, 'gamma')
    qc = QuantumCircuit(n + 1, name='phaser')
    for clause in clauses:
        compute = clause_compute(n, clause)
        qc.compose(compute, inplace=True)
        qc.p(gamma, n)
        qc.compose(compute.inverse(), inplace=True)
    return qc


def mixer(n, beta):
    """H_M = (1/2) sum X_i implies Rx(beta), with exact ideal rotations."""
    n = _positive_integer(n, 'n')
    beta = _validate_angle(beta, 'beta')
    qc = QuantumCircuit(n, name='mixer')
    qc.rx(beta, range(n))
    return qc


def zero_oracle(n):
    """I - 2|0^n><0^n|, including n=1 without an invalid zero-control MCX."""
    n = _positive_integer(n, 'n')
    qc = QuantumCircuit(n, name='O0')
    if n == 1:
        qc.global_phase = math.pi
        qc.z(0)  # -Z = diag(-1, +1).
        return qc
    qc.x(range(n))
    # These TWO target-wire H gates implement controlled-Z; they are not the
    # removed full-register basis conversion layers around O0.
    qc.h(n - 1)
    qc.mcx(list(range(n - 1)), n - 1)
    qc.h(n - 1)
    qc.x(range(n))
    return qc


def sat_oracle(n, clauses):
    """Flag all clauses, apply phase pi on all-true flags, then uncompute.

    Functional simplification: this is not Appendix C's timed AND-tree schedule.
    A formula must contain at least one clause; individual empty ORs are allowed.
    """
    n = _positive_integer(n, 'n')
    clauses = list(clauses)
    m = len(clauses)
    if not m:
        raise ValueError('The SAT instance must contain at least one clause.')
    qc = QuantumCircuit(n + m, name='OC')
    for j, clause in enumerate(clauses):
        qc.compose(clause_compute(n, clause), list(range(n)) + [n + j], inplace=True)
    phase = PhaseGate(math.pi)
    qc.append(phase if m == 1 else phase.control(m - 1), list(range(n, n + m)))
    for j in reversed(range(m)):
        qc.compose(clause_compute(n, clauses[j]).inverse(), list(range(n)) + [n + j], inplace=True)
    return qc


def qaoa(n, clauses, betas, gammas):
    """QAOA evolution U; initial H preparation is excluded, as in Eq. (3)."""
    n = _positive_integer(n, 'n')
    clauses, betas, gammas = list(clauses), list(betas), list(gammas)
    if not clauses:
        raise ValueError('The SAT instance must contain at least one clause.')
    for clause in clauses:
        _normalize_clause(n, clause)
    if len(betas) != len(gammas):
        raise ValueError('betas and gammas must have equal lengths; no layer may be silently dropped.')
    qc = QuantumCircuit(n + len(clauses), name='U_QAOA')
    for beta, gamma in zip(betas, gammas):
        qc.compose(phaser(n, clauses, gamma), list(range(n)) + [n], inplace=True)
        qc.compose(mixer(n, beta), range(n), inplace=True)
    return qc


def paper_iteration(n, clauses, betas, gammas):
    """Literal Eq. (6): U O0 U-dagger OC; no full-register H around O0.

    Following Eq. (6) literally does not resolve its preparation convention
    mismatch with Eqs. (2)-(3); this function claims no standard-AA probability law.
    """
    clauses = list(clauses)
    u = qaoa(n, clauses, betas, gammas)
    qc = sat_oracle(n, clauses)
    qc.name = 'Q_paper_Eq6'
    qc.compose(u.inverse(), inplace=True)
    qc.compose(zero_oracle(n), range(n), inplace=True)
    qc.compose(u, inplace=True)
    return qc


def qaoa_data_operator(n, clauses, betas, gammas):
    """Independent mathematical reference on data only, for small numeric cases."""
    n = _positive_integer(n, 'n')
    if len(betas) != len(gammas):
        raise ValueError('betas and gammas must have equal lengths.')
    size = 2**n
    counts = np.array([sum(evaluate(n, clause, x) for clause in clauses) for x in range(size)])
    matrix = np.eye(size, dtype=complex)
    for beta, gamma in zip(betas, gammas):
        beta, gamma = float(beta), float(gamma)
        rx = np.array([[math.cos(beta/2), -1j*math.sin(beta/2)],
                       [-1j*math.sin(beta/2), math.cos(beta/2)]])
        parallel_rx = np.array([[1.0 + 0j]])
        for _ in range(n):
            parallel_rx = np.kron(parallel_rx, rx)
        matrix = parallel_rx @ (np.exp(1j*gamma*counts)[:, None] * matrix)
    return matrix


def resource_estimate(a):
    """Eqs. (7)-(11) paper budget; independent of ideal circuit gate/depth counts."""
    n, p = _positive_integer(a.n, 'n'), _positive_integer(a.p, 'p')
    d, np_cycles = _positive_integer(a.d, 'd'), _positive_integer(a.np, 'nP')
    m = 176*n if a.m is None else _positive_integer(a.m, 'm')
    c = _positive_integer(a.c, 'c')
    if n < 8 or c > m:
        raise ValueError('This resource model requires n>=8 and 1<=c<=m (fixed k=8).')
    tlc = d * 1e-6
    counts = dict(mixer=np_cycles, phaser=c+np_cycles+4*math.ceil(math.log2(8)),
                  OC=4*c*math.log2(8*m/c), O0=4*math.log2(n))
    times = {key: value*tlc for key, value in counts.items()}
    tu = p*(times['mixer'] + times['phaser'])
    tround = 2*tu + times['OC'] + times['O0']
    log2_probability = -.69*p**(-.32)*n
    probability = 2**log2_probability
    try:
        rounds = math.pi/4 * 2**(-log2_probability/2)
    except OverflowError as error:
        raise ValueError('The modeled runtime exceeds floating-point range.') from error
    if probability == 0 or not math.isfinite(4*rounds*tround):
        raise ValueError('The modeled probability/runtime exceeds floating-point range.')
    return dict(source=PAPER, k=8, n=n, m=m, p=p, c=c, nP=np_cycles, d=d,
                TLC_seconds=tlc, component_logical_cycles=counts, component_seconds=times,
                T_U_seconds=tu, T_AA_round_seconds=tround, success_model=probability,
                R_eq7_continuous=rounds, T_eq7_seconds=rounds*tround,
                T_with_initial_U_seconds=tu+rounds*tround,
                T_robust_main_text_approx_seconds=4*rounds*tround,
                robust_delta=1/16, robust_factor=4,
                model_scope='Paper Eq.(7) budget, not a runtime or success guarantee for the simulated circuit.',
                implemented_ft_schedule=False, coloring_computed=False,
                assumptions={'c': 'Manually supplied color count; default 2112 is empirical 12r.',
                             'nP': 'Manually supplied phase-synthesis cycles; default 27 is illustrative, not Table III cubic NT=24.',
                             'TLC': 'd QEC rounds at the paper-assumed 1 microsecond per round.',
                             'success': 'Instance-average 8-SAT model from the cited study; not the toy circuit probability.'},
                note='Eqs.(10)-(11) are main-text approximations, not exact integer schedules. '
                     'TACU, phase synthesis, factories, routing, training, resets and readout are not simulated. '
                     'The robust factor is a paper protocol budget; the protocol is not implemented.')


def verify():
    """Check independent ideal-unitary semantics and actual input failure cases."""
    n = 3
    clauses = [[(0, True), (1, False)], [(1, True), (2, True)]]
    beta, gamma = .613, .371
    error = 0.0
    for x in range(2**n):
        actual = Statevector.from_int(x, 2**(n+1)).evolve(phaser(n, clauses, gamma)).data
        expected = np.zeros_like(actual)
        expected[x] = np.exp(1j*gamma*sum(evaluate(n, c, x) for c in clauses))
        error = max(error, float(np.max(np.abs(actual-expected))))
        actual = Statevector.from_int(x, 2**(n+len(clauses))).evolve(sat_oracle(n, clauses)).data
        expected = np.zeros_like(actual)
        expected[x] = (-1)**int(all(evaluate(n, c, x) for c in clauses))
        error = max(error, float(np.max(np.abs(actual-expected))))
    assert error < 1e-10
    for size in (1, 2, 3):
        assert np.allclose(Operator(zero_oracle(size)).data, np.diag([-1]+[1]*(2**size-1)))
    assert np.allclose(Operator(mixer(1, beta)).data,
                       [[math.cos(beta/2), -1j*math.sin(beta/2)],
                        [-1j*math.sin(beta/2), math.cos(beta/2)]])
    betas, gammas = [.41, .72], [.32, -.59]
    u = qaoa(n, clauses, betas, gammas)
    u_full = Operator(u).data
    reference_u = qaoa_data_operator(n, clauses, betas, gammas)
    size = 2**n
    u_error = float(np.max(np.abs(u_full[:size, :size]-reference_u)))
    assert u_error < 1e-10 and np.max(np.abs(u_full[size:, :size])) < 1e-10
    inverse_error = float(np.max(np.abs(Operator(u.inverse()).data @ u_full - np.eye(2**u.num_qubits))))
    assert inverse_error < 1e-10
    good = [x for x in range(size) if all(evaluate(n, c, x) for c in clauses)]
    o0 = np.diag([-1]+[1]*(size-1))
    oc = np.diag([-1 if x in good else 1 for x in range(size)])
    reference_q = reference_u @ o0 @ reference_u.conj().T @ oc
    q = paper_iteration(n, clauses, betas, gammas)
    q_full = Operator(q).data
    q_error = float(np.max(np.abs(q_full[:size, :size]-reference_q)))
    assert q_error < 1e-10 and np.max(np.abs(q_full[size:, :size])) < 1e-10
    assert q.count_ops().get('h', 0) == 2  # Only target-wire O0 decomposition.
    prep = QuantumCircuit(u.num_qubits)
    prep.h(range(n)); prep.compose(u, inplace=True)
    state = Statevector.from_instruction(prep)
    p_before = float(sum(abs(state.data[x])**2 for x in good))
    result = state.evolve(q)
    p_after = float(sum(abs(result.data[x])**2 for x in good))
    # Complex arbitrary input, several rounds, and ancilla cleanup.
    rng = np.random.default_rng(20261009)
    vector = rng.normal(size=size) + 1j*rng.normal(size=size)
    vector /= np.linalg.norm(vector)
    extended = np.zeros(2**u.num_qubits, dtype=complex); extended[:size] = vector
    actual, expected = Statevector(extended), vector
    for _ in range(3):
        actual, expected = actual.evolve(q), reference_q @ expected
        assert np.max(np.abs(actual.data[:size]-expected)) < 1e-10
        assert np.linalg.norm(actual.data[size:]) < 1e-10
    # Literal repetition, tautology, empty OR, and one-literal clauses.
    edge_clauses = [[(0, True), (0, True)], [(1, True), (1, False)], [], [(2, False)]]
    for clause in edge_clauses:
        gate = clause_compute(n, clause)
        for x in range(size):
            for flag in (0, 1):
                actual = Statevector.from_int(x + flag*size, 2**(n+1)).evolve(gate).data
                expected_index = x + size*(flag ^ evaluate(n, clause, x))
                assert abs(actual[expected_index]-1) < 1e-10
    for x in range(2):
        actual = Statevector.from_int(x, 4).evolve(sat_oracle(1, [[(0, True)]])).data
        assert abs(actual[x]-(-1)**x) < 1e-10 and np.linalg.norm(actual[2:]) < 1e-10
    invalid = [lambda: qaoa(n, clauses, [1, 2], [1]),
               lambda: zero_oracle(0), lambda: zero_oracle(1.5),
               lambda: mixer(1, float('nan')),
               lambda: clause_compute(2, [(2, True)]),
               lambda: sat_oracle(2, [])]
    for call in invalid:
        try:
            call()
        except ValueError:
            continue
        raise AssertionError('Invalid input was accepted.')
    c8 = [(i, i != 1) for i in range(8)]
    for x in range(256):
        actual = Statevector.from_int(x, 512).evolve(clause_compute(8, c8)).data
        assert abs(actual[x + 256*evaluate(8, c8, x)]-1) < 1e-10
    return dict(status='PASS', qiskit_version=qiskit.__version__,
                maximum_truth_table_error=error, qaoa_reference_error=u_error,
                iteration_reference_error=q_error, inverse_error=inverse_error,
                p_before=p_before, p_after=p_after,
                checked='256-input 8-SAT clause; repeated literals and constants; phase sign; O0 n=1,2,3; '
                        'single-clause OC; inverse; independent U and Eq.(6) matrices; three-round complex-state evolution; '
                        'clean ancillas; unequal-angle and invalid-input rejection.',
                scope='Ideal circuit semantics only; PASS does not validate FT compilation or standard-AA success scaling.')
