# Copyright (C) 2024  Tony Boutwell/Mark Stevens  12/30/24 tonyboutwell@gmail.com
# This program is free software: you can redistribute it and/or modify it under the terms of the 
# GNU General Public License as published by the Free Software Foundation, either version 3 of the License, 
# or (at your option) any later version.

import numpy as np
from scipy.linalg import expm
import matplotlib.pyplot as plt
from dataclasses import dataclass
from typing import Dict, Tuple, List


@dataclass
class SystemConfig:
    N: int
    T: int
    dt: float
    V0: float
    g: float
    noise: float
    phase_precision: int


class QuantumFramework:
    def __init__(self):
        self.error_history = []
        self.scaling_results = []

    def refined_hamiltonian(self, config: SystemConfig) -> np.ndarray:
        """Builds a refined Hamiltonian with quasi-periodic perturbations."""
        H = np.zeros((config.N, config.N), dtype=complex)
        for i in range(config.N):
            H[i, i] = config.V0 * np.cos(2 * np.pi * i / config.N) + config.noise * np.random.normal()
            if i < config.N - 1:
                coupling = config.g + config.noise * np.random.normal()
                H[i, i + 1] = coupling
                H[i + 1, i] = coupling
        return H

    def phase_realignment(self, wavefunction: np.ndarray, config: SystemConfig) -> np.ndarray:
        """
        Applies an adaptive phase realignment to the wavefunction.
        
        This step shifts the phase of each basis component by a small, index-dependent
        amount to better align forward and backward evolutions. This is inspired by
        phase estimation ideas but does not implement the traditional QPE protocol 
        (no ancillas, no measurement-based eigenvalue extraction).
        """
        corrected_wf = wavefunction.copy()
        for state in range(config.N):
            phase = 2 * np.pi * state / config.phase_precision
            corrected_wf[state] *= np.exp(1j * phase)
        return corrected_wf / np.linalg.norm(corrected_wf)

    def evaluate_system(self, config: SystemConfig) -> float:
        """Evaluates the system for a given configuration and returns the total error."""
        H = self.refined_hamiltonian(config)

        # Forward Evolution
        U = expm(-1j * H * config.dt)
        wf_forward = [np.ones(config.N, dtype=complex) / np.sqrt(config.N)]
        for t in range(config.T):
            wf_forward.append(U @ wf_forward[-1])

        # Backward Reconstruction
        Uinv = expm(1j * H * config.dt)
        final_probs = np.abs(wf_forward[-1]) ** 2
        wf_backward = [None] * (config.T + 1)
        wf_backward[-1] = np.sqrt(final_probs)

        for t in range(config.T - 1, -1, -1):
            wf_temp = Uinv @ wf_backward[t + 1]
            # Replace the old "adaptive_qpe_correction" call:
            wf_backward[t] = self.phase_realignment(wf_temp, config)

        # Compute Total Error
        total_error = 0.0
        for t in range(config.T + 1):
            P_fwd = np.abs(wf_forward[t]) ** 2
            P_bwd = np.abs(wf_backward[t]) ** 2
            total_error += np.sum((P_fwd - P_bwd) ** 2)

        return total_error

    def analyze_energy_gaps(self, config: SystemConfig) -> float:
        """Analyzes energy gap uniformity for a given Hamiltonian."""
        H = self.refined_hamiltonian(config)
        eigenvalues = np.linalg.eigvalsh(H)
        energy_gaps = np.diff(np.sort(eigenvalues))
        gap_uniformity = np.std(energy_gaps)
        return gap_uniformity

    def scale_system(self, N_values: List[int], param_ranges: Dict) -> None:
        """Scales the system by testing different N values and re-optimizing parameters."""
        for N in N_values:
            param_ranges['N'] = [N]  # Fix N for this round
            best_config, best_error = self.parameter_sweep(param_ranges)
            gap_uniformity = self.analyze_energy_gaps(best_config)
            self.scaling_results.append((N, best_error, gap_uniformity))
            print(f"\nScaling Complete for N={N}: Best Error={best_error:.6f}, Gap Uniformity={gap_uniformity:.6f}")
            print(f"Best Config={best_config}\n")

    def parameter_sweep(self, param_ranges: Dict) -> Tuple[SystemConfig, float]:
        """Performs a parameter sweep to identify the best configuration."""
        best_config = None
        best_error = float('inf')
        total_combinations = np.prod([len(v) for v in param_ranges.values()])
        print(f"Testing {total_combinations} parameter combinations...")

        combinations_tested = 0
        for N in param_ranges['N']:
            for T in param_ranges['T']:
                for dt in param_ranges['dt']:
                    for V0 in param_ranges['V0']:
                        for g in param_ranges['g']:
                            for noise in param_ranges['noise']:
                                for phase_precision in param_ranges['phase_precision']:
                                    config = SystemConfig(N=N, T=T, dt=dt, V0=V0, g=g,
                                                          noise=noise, phase_precision=phase_precision)
                                    error = self.evaluate_system(config)
                                    self.error_history.append(error)

                                    if error < best_error:
                                        best_error = error
                                        best_config = config
                                        print(f"New best error: {error:.6f} for config: {config}")

                                    combinations_tested += 1
                                    if combinations_tested % 100 == 0:
                                        print(f"Tested {combinations_tested}/{total_combinations} combinations...")

        return best_config, best_error

    def plot_scaling_results(self):
        """Plots error and gap uniformity vs system size (N)."""
        N_values, errors, gap_uniformities = zip(*self.scaling_results)
        fig, ax1 = plt.subplots(figsize=(10, 6))

        color = 'tab:blue'
        ax1.set_xlabel("System Size (N)")
        ax1.set_ylabel("Best Error", color=color)
        ax1.plot(N_values, errors, marker='o', color=color, label="Best Error")
        ax1.tick_params(axis='y', labelcolor=color)
        ax1.grid(True)

        ax2 = ax1.twinx()
        color = 'tab:orange'
        ax2.set_ylabel("Gap Uniformity", color=color)
        ax2.plot(N_values, gap_uniformities, marker='x', linestyle='--', color=color, label="Gap Uniformity")
        ax2.tick_params(axis='y', labelcolor=color)

        fig.tight_layout()
        plt.title("Error and Gap Uniformity Scaling with System Size")
        plt.show()


# Example Usage
if __name__ == "__main__":
    param_ranges = {
        'N': [3],  # This will be overridden in scale_system()
        'T': [4, 5],
        'dt': [0.8, 1.0],
        'V0': [0.8, 1.0],
        'g': [0.15, 0.2],
        'noise': [0.005, 0.01],
        'phase_precision': [5, 7, 10]
    }

    framework = QuantumFramework()
    framework.scale_system(N_values=[25, 50, 100, 200], param_ranges=param_ranges)

    print("\nScaling Results:")
    for N, error, gap_uniformity in framework.scaling_results:
        print(f"N={N}, Best Error={error:.6f}, Gap Uniformity={gap_uniformity:.6f}")

    framework.plot_scaling_results()
