#!/usr/bin/env/python3
# This contains all the functions to find the crossover parameters for 8 SAT

import numpy as np
import math
import scipy.optimize
from scipy.stats import lognorm
from scipy.integrate import quad
# 简单版运行适配：原版需要 SciPy；当前复现只调用
# get_8_SAT_params(..., verbose=False)。未调用的原版 SciPy 路径保留在
# author_utils_original.py，避免把它们误认为已经过本适配验证。


@np.vectorize
def expected_runtime_parallel_lognormal(n, sigma, mean):
    """
    Calculate the expected runtime of a parallel process for a log-normal distribution.

    Parameters:
    n (int): The number of parallel processes (cores).
    sigma (float): The standard deviation of the underlying normal distribution.
    mean (float): The mean of the log-normal distribution.

    Returns:
    float: The expected runtime of the parallel process.
    """
    # Calculate the scale parameter for the log-normal distribution
    scale = calculate_scale_from_mean(mean, sigma)

    # Define the integrand for the expected runtime
    def integrand(t):
        fY = lognorm.pdf(t, s=sigma, scale=scale)
        FY = lognorm.cdf(t, s=sigma, scale=scale)
        return t * fY * (1 - FY) ** (n - 1)

    # Perform numerical integration from 0 to infinity
    expected_runtime, _ = quad(integrand, 0, np.inf)

    return n * expected_runtime


def calculate_scale_from_mean(mean, sigma):
    """
    Calculate the scale parameter of a log-normal distribution given its mean and sigma.

    Parameters:
    mean (float): The mean of the log-normal distribution.
    sigma (float): The standard deviation of the underlying normal distribution.

    Returns:
    float: The scale parameter of the log-normal distribution.
    """
    # Calculate mu from the mean of the log-normal distribution
    mu = np.log(mean) - (sigma**2) / 2

    # Calculate the scale parameter
    scale = np.exp(mu)

    return scale


@np.vectorize
def expected_runtime_parallel_shifted_exponential(n, lambda_, shift):
    # 作者原式计算 n 个独立运行时间的最小值期望。
    # 若每个运行时间 = shift + Exp(lambda_)，则最小值
    # = shift + Exp(n*lambda_)，故期望为 shift + 1/(n*lambda_)。
    # 与原版 quad 积分在数学上等价，不涉及拟合参数。
    return shift + 1 / (n * lambda_)


def get_classical_run_time_cores_integrand(
    xx: float, alpha: float, num_classical_cores: float
) -> float:
    """
    obtaining the integrand for the integration to find the
    minimum runtime for a given number of cores for classical algorithm,
    for a given value of number of cores and value alpha
    """
    pre_factor = num_classical_cores / scipy.special.gamma(alpha)
    factor_a = alpha * math.log(xx) - xx
    factor_g = (
        np.log(scipy.special.gammaincc(alpha, xx)) if num_classical_cores > 1 else 0
    )
    log_factor = factor_a + (num_classical_cores - 1) * factor_g
    return pre_factor * np.exp(log_factor)


def get_classical_run_time_cores(alpha: float, num_classical_cores: int) -> float():
    """
    the minimum classical runtime obtained using the numerical integration
    """
    result, error = quad(
        get_classical_run_time_cores_integrand,
        0,
        np.inf,
        args=(alpha, num_classical_cores),
    )
    return result


@np.vectorize
def get_ent_fidelity_analytical(p_D: float, p_T: float, a: float, b: float) -> float:
    """
    The analytical calculation of the entanglement fidelity
    """
    cc = (1 / 4 + 3 / 4 * (1 - p_T) ** (a * (np.log2(1 / p_D))+ b)) * (1 - p_D**2 )

    return 1 - cc

@np.vectorize
def get_optimal_infidelity(
    infid_T_gate: list, b_decomp: float, c_decomp: float
) -> float:
    """
    Find the optimal infidelity of the rotation gate for the
    a deomposition method and the given T gate infidelity
    """
    b_decomp = b_decomp / math.log(2)
    infid_rotation = np.sqrt((-3 / 8 * b_decomp * math.log(1 - infid_T_gate)))
    num_t_gate_rotation = b_decomp * math.log2(1 / infid_rotation) + c_decomp
    Infid = 1 - 1 / 4 * (1 + (3 * (1 - infid_T_gate) ** num_t_gate_rotation)) * (
        1 - infid_rotation**2
    )
    return Infid


@np.vectorize
def get_best_T_infidelity(depth: int, acc: float, b_decomp: float, c_decomp) -> float:
    """
    the function outputs the maximum infidelity required of the T gate
    requried for obtaining the given total accuracy of the whole circuit
    """
    val = np.logspace(-16, -5, 2000)
    F1 = get_optimal_infidelity(val, b_decomp, c_decomp)
    FF = (1 - F1) ** depth
    F = [v for i, v in enumerate(val) if FF[i] > acc]

    return np.max(F) if F else 10 ** (-17)  # Return None if F is empty



@np.vectorize
def get_p_for_speedup(speed_up: int, cl_exp: float, a: float, c: float) -> float:
    return (cl_exp * 2 / (a * speed_up)) ** (-1 / c)

@np.vectorize
def get_speedup_for_p(tar_speed_up:int, cl_exp:float)->int:
    return int((cl_exp * 2 / (0.69 * tar_speed_up)) ** (-1 / 0.32))

@np.vectorize
def get_optimal_p__8_SAT(
    num_qubits: float, e_ph: float, gamma_0: float, par_fac: float
) -> float:
    """Find minimum number of qubits (N) for a quantum-classical crossover."""
    res = scipy.optimize.minimize(
        wrapper_function,
        120,
        method="SLSQP",
        args=(num_qubits, e_ph, gamma_0, par_fac),
        bounds=[(100, 1000)],
    )
    return res.x, res.fun


@np.vectorize
def get_optimal_p_8_SAT_analytical(N: int, c=0.32, a=0.69) -> float:
    return (np.log(2) * a * c * N / 2) ** (1 / c)

def get_toff_count_multiqubit_toffoli(m):
    """
    the function returns the number of Toffoli gates required a
    mutiqubit Toffoli (m body), including the cost of reversibility
    """
    return np.ceil(math.log2(m))


@np.vectorize
def get_8_SAT_params(
    num_qubits: int,
    physical_error_rate: float,
    code_cycle: float,
    tar_speed_up: float,
    alpha: float,
    logical_cycle_time: int,
    b_decomp: float,
    c_decomp: float,
    qubit_factory: int,
    lambda_value: float,
    shift: float,
    verbose: bool,
):
    if verbose:
        mean = lambda_value
        sigma = shift
    """
    Parameters:
    ----------
    num_qubits: int
         the number of variables in the 8-SAT equation
    physical_error_rate: float
          the physical error rate of the platform under
          consideration
    code_cycle: float
          the code cycle time
    tar_speed_up: int
          the target speed up for the algorithm
    alpha: float
          the classical parallization factor
    logical_cycle_time:int
          the time to have a resource state
    (b_decomp,c_decomp):defines the decomposition of the
          rotation gates
    qubit_factory:qubit footprint of the resource state
          factory

    Returns:
    ---------

    np.abs(log_T_q - log_T_c): float
           the difference of the classical to quantum runtime
    qaoa_layers: int
           the value of the qaoa layers used
    total_gates: int
           an upperbound on the total gates used
    total_depth:int
           the depth of the total algorithm
    target_distance_surface_code:int
           the distance of the code
    num_T_gate_rotation: int
           the number of T gate for rotation
    inf_T_gate:float
           the target infideltiy of the T gate
    tar_speed_up:int
           the target speed up
    log_T_c: float
           the classicla runtime
    log_T_q: float
           the quantum runtime
    num_resource_factories:int
           the number of resource state factories
    total_physical_qubits:int
           the number of physical qubits used


    """
    # the threshold for the surface code
    threshold_surface = 10 ** (-2)

    # quantum amplitude amplification ratio
    # This is to account the fact that to ovecome that the probability is not exact and
    # we need to avoid the overcouning issue
    qaa_fac = 4

    
    # the accuracy of the total circuit, which is set to be 99 %
    acc = 0.99

    # the value of the k-SAT problem of interest here which is 8
    k = 8

    # the graph coloring depth we got for the random variables
    graph_coloring_depth = 12

    # the satisfiability_threshold of the 8-SAT problem
    satisfiability_threshold = 176

    # classical exponent and constant  we got from the numerical runs
    # for the Sparrow solver
    classical_exp = 0.176
    classical_const = 19.369

    # clifford overhead for rotation gate
    n_cliff = 2
    
    # the number of layers of the qaoa required to get the given
    # speedup using PRX Quantum 5, 030348 (2024)
    qaoa_layers = int((classical_exp * 2 / (0.69 * tar_speed_up)) ** (-1 / 0.32))

    # the probability of solution from PRX Quantum 5, 030348 (2024)
    qaoa_prob_solution = 2 ** (-0.69 * qaoa_layers ** (-0.32) * num_qubits)

    aa_repetitions = int(np.pi / (4 * np.sqrt(qaoa_prob_solution)))

    total_rotation_gates = (
        2 * qaoa_layers * num_qubits * (satisfiability_threshold + 1) * aa_repetitions
    )
    # the target infidelity for the T gates
    inf_T_gate = get_best_T_infidelity(total_rotation_gates, acc, b_decomp, c_decomp)

    # the corresponding fidelity of the rotation gates
    inf_rotation = np.sqrt(-3 / 8 * b_decomp / math.log(2) * (-inf_T_gate))

    # the number of T gates required for the fidelity of the rotation
    num_T_gate_rotation = np.ceil((b_decomp * math.log2(1 / inf_rotation)) + c_decomp)

    # an upperbound on the total number of gates
    total_nc_gates = total_rotation_gates * (7 + num_T_gate_rotation)

    # the target distance
    target_distance_surface_code = (
        int(
            2
            * (math.log(1 - acc) - math.log(total_nc_gates))
            / math.log(physical_error_rate / threshold_surface)
        )
        + 1
    )

    # the number of clauses we need to run in parallel
    num_par_clauses = np.ceil(num_qubits / 12)

    # the num_T_rotation logical cycles to finish one clause for the 8-SAT,
    # we need three rounds of the TACU gadget.
    clauses_per_logical_cycle = (
        4 * np.log2(k) + num_T_gate_rotation + n_cliff
    ) / logical_cycle_time

    # number of resoucre factories is simply the num_par clauses time the
    # clauses_per_logical cycle.
    num_resource_factories = np.ceil(clauses_per_logical_cycle * num_par_clauses)

    # this is just to verify the fact the total time to solution is just
    # confirm that the crossover time does not change
    # if both classical and quantum TTS are multiplied by the same constant
    # set to 1 if we are not testing
    constant_to_test = 1

    # the number of ancilla qubits we require
    # Then one can simply multiply this with the number of resource factories to
    # get an upperbound.
    num_ancilla_qubits = int(
        13 * np.ceil(k / 2) * clauses_per_logical_cycle * num_par_clauses
    )
    
    # the number of factories we need this will be such that we need
    num_classical_cores_decoding = (
        10 * num_resource_factories + num_qubits + num_ancilla_qubits
    )

    # The ratio of the classical power we used for the classical analysis
    # versus the riverlane decoder
    ratio_power = 729 

    num_classical_cores = num_classical_cores_decoding // ratio_power

    num_ancilla_oracle = 13 / 2 * (k + 1) * num_par_clauses + 2 * np.ceil(
        np.sqrt(graph_coloring_depth * satisfiability_threshold)
    )

    if verbose:
        par_fac_classical = expected_runtime_parallel_lognormal(
            num_classical_cores, sigma, mean
        ) / expected_runtime_parallel_lognormal(1, sigma, mean)
    else:
        par_fac_classical = expected_runtime_parallel_shifted_exponential(
            num_classical_cores, lambda_value, shift
        ) / expected_runtime_parallel_shifted_exponential(1, lambda_value, shift)

    # the depth of the oracle_0 in terms of the logical cylecs
    depth_oracle_0 = 4 * get_toff_count_multiqubit_toffoli(num_qubits)



    total_physical_qubits = int(
        qubit_factory * num_resource_factories
        + 2 * int(target_distance_surface_code) ** 2 * (num_qubits + num_ancilla_qubits)
    )

    paralell_fac_oracle = np.floor(
        (total_physical_qubits)
        / ((4 * num_ancilla_oracle + 2 * num_qubits) * target_distance_surface_code**2)
    )

    num_1 = np.ceil(np.sqrt(graph_coloring_depth * satisfiability_threshold))
    num_2 = graph_coloring_depth * satisfiability_threshold / (num_1)

    depth_oracle_chi = (
        graph_coloring_depth
        * satisfiability_threshold
        * (
            4 * (4 * np.ceil(np.log2(k)) - 1)
            + 4 * (4 * np.ceil(np.log2(num_par_clauses)))
        )/paralell_fac_oracle
        + 2 * num_2 * (4 * np.ceil(np.log2(num_1)) - 1)
        + 1 * (4 * np.ceil(np.log2(num_2)) - 1)
        + (paralell_fac_oracle - 1)
    ) 

    # depth of the phase unitary in terms of logical cycle
    depth_phase_unitary = qaoa_layers * (
        graph_coloring_depth * satisfiability_threshold
        + 4 * np.log2(k)
        + num_T_gate_rotation
        + 2
    )

    # depth of the mixer unitary in terms of the logical cycle
    depth_mixer_unitary = qaoa_layers * num_T_gate_rotation

    total_depth = int(
        aa_repetitions
        * (
            depth_oracle_0
            + depth_oracle_chi
            + 2 * (depth_phase_unitary + depth_mixer_unitary)
        )
    )

    # the quantum runtime
    log_T_q = math.log(
        qaa_fac
        * total_depth
        * code_cycle
        * logical_cycle_time
        * target_distance_surface_code
        * constant_to_test
    )

    # the classical run time
    log_T_c = math.log(
        (2 ** (classical_const + classical_exp * num_qubits))
        * 10 ** (-9)
        * par_fac_classical
        * constant_to_test
    )
    num_toff_gate = aa_repetitions * (
        (num_qubits - 1)
        + 7 * satisfiability_threshold * (num_qubits) * (2 * qaoa_layers + 1)
        + satisfiability_threshold
        - 1
    )
    num_T_gate = (
        2
        * aa_repetitions
        * (
            num_T_gate_rotation
            * qaoa_layers
            * (num_qubits + num_qubits * satisfiability_threshold)
        )
    )
    # print(par_fac_classical)


    return (
        np.abs(log_T_q - log_T_c),
        qaoa_layers,
        total_nc_gates,
        total_depth,
        target_distance_surface_code,
        num_T_gate_rotation,
        inf_T_gate,
        tar_speed_up,
        log_T_c,
        log_T_q,
        num_resource_factories,
        total_physical_qubits,
        int(num_classical_cores),
        int(num_toff_gate),
        num_ancilla_qubits,
        int(num_classical_cores_decoding),
        inf_rotation,
        inf_T_gate,
        int(np.floor(par_fac_classical**(-1))),
        paralell_fac_oracle
    )


@np.vectorize
def wrapper_function(
    num_qubits: int,
    physical_error_rate: float,
    code_cycle: float,
    target_speed_up: float,
    alpha: float,
    logical_cycle_time: float,
    b_decomp: float,
    c_decomp: float,
    qubit_factory: float,
    lambda_value: float,
    shift: float,
    verbose: bool,
) -> float:
    """
    This function is just used as a wrapper function such that we can use the
    difference between the classical and runtime which then can be used for
    finding the crossover.
    """
    cross_over_time, *_ = get_8_SAT_params(
        num_qubits,
        physical_error_rate,
        code_cycle,
        target_speed_up,
        alpha,
        logical_cycle_time,
        b_decomp,
        c_decomp,
        qubit_factory,
        lambda_value,
        shift,
        verbose,
    )

    return cross_over_time


@np.vectorize
def get_crossover_point_8_SAT(
    physical_error_rate: float,
    code_cycle: float,
    target_speed_up: float,
    alpha: float,
    logical_cycle_time: float,
    b_decomp: float,
    c_decomp: float,
    qubit_factory: float,
    lambda_value: float,
    shift: float,
    verbose: bool,
) -> float:
    """Find minimum number of qubits (N) for a quantum-classical crossover."""
    res = scipy.optimize.minimize(
        wrapper_function,
        40,
        method="SLSQP",
        args=(
            physical_error_rate,
            code_cycle,
            target_speed_up,
            alpha,
            logical_cycle_time,
            b_decomp,
            c_decomp,
            qubit_factory,
            lambda_value,
            shift,
            verbose,
        ),
        bounds=[(40, 1000)],
    )
    # print(res.x)
    if res.fun > 10 ** (-2):
        print(res.fun)
        print()
        print("too bad of input")
        exit()
    return res.x


@np.vectorize
def get_8_SAT_function_p(
    num_qubits: int,
    physical_error_rate: float,
    code_cycle: float,
    p:int,
    alpha: float,
    logical_cycle_time: int,
    b_decomp: float,
    c_decomp: float,
    qubit_factory: int,
    lambda_value: float,
    shift: float,
    verbose: bool,
):
    if verbose:
        mean = lambda_value
        sigma = shift
    """
    Parameters:
    ----------
    log_p: float
         the value of p for the QAOA in log scale
    N: int
         the number of variables in the 8-SAT equation
    e_ph: float
          the physical error rate of the platform under
          consideration
    gamma_0: float
          the logical cycle time

    """
    # the threshold for the surface code
    threshold_surface = 10 ** (-2)

    # quantum amplitude amplification ratio
    # This is to account the fact that to ovecome that the probability is not exact and
    # we need to avoid the overcouning issue
    qaa_fac = 4


    # the accuracy of the total circuit, which is set to be
    # 99 %
    acc = 0.99

    # the value of the k-SAT problem of interest here which is 8
    k = 8

    # the graph coloring depth we got for the random variables
    graph_coloring_depth = 12

    # the satisfiability_threshold of the 8-SAT problem of interest here
    satisfiability_threshold = 176

    # classical exponent and constant  we got from the numerical runs for the dimetheus solver
    classical_exp = 0.176
    classical_const = 19.369

    # clifford overhead for rotation gate
    n_cliff = 2
    
    # the number of layers of the qaoa required to get the given speedup using PRX Quantum 5, 030348 (2024)
    qaoa_layers = int(p)

    # the probability of solution from PRX Quantum 5, 030348 (2024)
    qaoa_prob_solution = 2 ** (-0.69 * qaoa_layers ** (-0.32) * num_qubits)

    aa_repetitions = int(np.pi / (4 * np.sqrt(qaoa_prob_solution)))

    total_rotation_gates = (
        2 * qaoa_layers * num_qubits * (satisfiability_threshold + 1) * aa_repetitions
    )
    # the target infidelity for the T gates
    inf_T_gate = get_best_T_infidelity(total_rotation_gates, acc, b_decomp, c_decomp)

    # the corresponding fidelity of the rotation gates
    inf_rotation = np.sqrt(-3 / 8 * b_decomp / math.log(2) * (-inf_T_gate))

    # the number of T gates required for the fidelity of the rotation
    num_T_gate_rotation = np.ceil((b_decomp * math.log2(1 / inf_rotation)) + c_decomp)

    # an upperbound on the total number of gates
    total_nc_gates = total_rotation_gates * (7 + num_T_gate_rotation)

    # the target distance
    target_distance_surface_code = (
        int(
            2
            * (math.log(1 - acc) - math.log(total_nc_gates))
            / math.log(physical_error_rate / threshold_surface)
        )
        + 1
    )

    # the number of clauses we need to run in parallel
    num_par_clauses = np.ceil(num_qubits / 12)

    # the num_T_rotation logical cycles to finish one clause for the 8-SAT,
    # we need three rounds of the TACU gadget.
    clauses_per_logical_cycle = (
        4 * np.log2(k) + num_T_gate_rotation + n_cliff
    ) / logical_cycle_time

    # number of resoucre factories is simply the num_par clauses time the
    # clauses_per_logical cycle.
    num_resource_factories = np.ceil(clauses_per_logical_cycle * num_par_clauses)

    # this is just to verify the fact the total time to solution is just
    # confirm that the crossover time does not change
    # if both classical and quantum TTS are multiplied by the same constant
    # set to 1 if we are not testing
    constant_to_test = 1

    # the number of ancilla qubits we require to find the number of ancilla qubits
    # an upperbound can be estimated from the fact that we need 7 ancilla qubits for
    # a TACU gadget and we need 7 of these to finish a clause.
    # Then one can simply multiply this with the number of resource factories to
    # get an upperbound.
    num_ancilla_qubits = int(
        13 * np.ceil(k / 2) * clauses_per_logical_cycle * num_par_clauses
    )
    
    # the number of the classical cores need for decoding
    num_classical_cores_decoding = (
        10 * num_resource_factories + num_qubits + num_ancilla_qubits
    )

    # The ratio of the classical power we used for the classical analysis
    # versus the riverlane decoder
    ratio_power = 729

    # the total classical cores accounting the energy cost
    num_classical_cores = num_classical_cores_decoding // ratio_power

    num_ancilla_oracle = 13 / 2 * (k + 1) * num_par_clauses + 2 * np.ceil(
        np.sqrt(graph_coloring_depth * satisfiability_threshold)
    )

    if verbose:
        par_fac_classical = expected_runtime_parallel_lognormal(
            num_classical_cores, sigma, mean
        ) / expected_runtime_parallel_lognormal(1, sigma, mean)
    else:
        par_fac_classical = expected_runtime_parallel_shifted_exponential(
            num_classical_cores, lambda_value, shift
        ) / expected_runtime_parallel_shifted_exponential(1, lambda_value, shift)


    # the depth of the oracle_0 in terms of the logical cylecs
    depth_oracle_0 = 4 * get_toff_count_multiqubit_toffoli(num_qubits)

    total_physical_qubits = int(
        qubit_factory * num_resource_factories
        + 2 * int(target_distance_surface_code) ** 2 * (num_qubits + num_ancilla_qubits)
    )
    paralell_fac_oracle = np.floor(
        (total_physical_qubits)
        / ((4 * num_ancilla_oracle + 2 * num_qubits) * target_distance_surface_code**2)
    )

    num_1 = np.ceil(np.sqrt(graph_coloring_depth * satisfiability_threshold))
    num_2 = graph_coloring_depth * satisfiability_threshold / (num_1)

    depth_oracle_chi = (
        graph_coloring_depth
        * satisfiability_threshold
        * (
            4 * (4 * np.ceil(np.log2(k)) - 1)
            + 4 * (4 * np.ceil(np.log2(num_par_clauses)))
        )/paralell_fac_oracle
        + 2 * num_2 * (4 * np.ceil(np.log2(num_1)) - 1)
        + 1 * (4 * np.ceil(np.log2(num_2)) - 1)
        + (paralell_fac_oracle - 1)
    ) 

    # depth of the phase unitary in terms of logical cycle
    depth_phase_unitary = qaoa_layers * (
        graph_coloring_depth * satisfiability_threshold
        + 4 * np.log2(k)
        + num_T_gate_rotation
        + 2
    )

    # depth of the mixer unitary in terms of the logical cycle
    depth_mixer_unitary = qaoa_layers * num_T_gate_rotation

    total_depth = int(
        aa_repetitions
        * (
            depth_oracle_0
            + depth_oracle_chi
            + 2 * (depth_phase_unitary + depth_mixer_unitary)
        )
    )

    # the quantum runtime
    log_T_q = math.log(
        qaa_fac
        * total_depth
        * code_cycle
        * logical_cycle_time
        * target_distance_surface_code
        * constant_to_test
    )
    

    return log_T_q



