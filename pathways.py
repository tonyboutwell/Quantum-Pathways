# Copyright (C) 2024  Tony Boutwell/Mark Stevens  12/30/24 tonyboutwell@gmail.com
# This program is free software: you can redistribute it and/or modify it under the terms of the 
# GNU General Public License as published by the Free Software Foundation, either version 3 of the License, 
# or (at your option) any later version.

import numpy as np
import matplotlib.pyplot as plt
from scipy.linalg import expm
from dataclasses import dataclass
from typing import List
from qiskit_aer.noise import NoiseModel, depolarizing_error, amplitude_damping_error

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

    def refined_hamiltonian(self, config: SystemConfig) -> np.ndarray:
        """Builds a refined Hamiltonian."""
        H = np.zeros((config.N, config.N), dtype=complex)
        for i in range(config.N):
            H[i, i] = config.V0 * np.cos(2 * np.pi * i / config.N)
            if i < config.N - 1:
                coupling = config.g
                H[i, i + 1] = coupling
                H[i + 1, i] = coupling
        return H

    def evaluate_with_qiskit_noise(self, config: SystemConfig, noise_model: NoiseModel) -> float:
        """Evaluates the system using Qiskit noise."""
        H = self.refined_hamiltonian(config)

        # Evolution Operators
        U = expm(-1j * H * config.dt)
        Uinv = expm(1j * H * config.dt)

        # Forward Evolution
        wf_forward = [np.ones(config.N, dtype=complex) / np.sqrt(config.N)]
        for _ in range(config.T):
            wf_next = U @ wf_forward[-1]
            wf_forward.append(wf_next)

        # Backward Reconstruction
        final_probs = np.abs(wf_forward[-1]) ** 2
        wf_backward = [None] * (config.T + 1)
        wf_backward[-1] = np.sqrt(final_probs)
        for t in range(config.T - 1, -1, -1):
            wf_temp = Uinv @ wf_backward[t + 1]
            wf_backward[t] = wf_temp / np.linalg.norm(wf_temp)

        # Compute Total Error
        total_error = 0.0
        for t in range(config.T + 1):
            P_fwd = np.abs(wf_forward[t]) ** 2
            P_bwd = np.abs(wf_backward[t]) ** 2
            total_error += np.sum((P_fwd - P_bwd) ** 2)
        return total_error

# Define noise model
noise_model = NoiseModel()
noise_model.add_all_qubit_quantum_error(depolarizing_error(0.001, 1), ["id", "rz"])
noise_model.add_all_qubit_quantum_error(amplitude_damping_error(0.002), ["id", "rz"])

# Configurations to test
configurations = [
    SystemConfig(N=25, T=4, dt=0.8, V0=0.8, g=0.15, noise=0.005, phase_precision=10),
    SystemConfig(N=50, T=4, dt=0.8, V0=0.8, g=0.15, noise=0.005, phase_precision=7),
    SystemConfig(N=100, T=4, dt=0.8, V0=1.0, g=0.15, noise=0.005, phase_precision=7),
    SystemConfig(N=200, T=4, dt=0.8, V0=1.0, g=0.2, noise=0.005, phase_precision=10),
]

# Run evaluations
framework = QuantumFramework()
results = []
for config in configurations:
    error = framework.evaluate_with_qiskit_noise(config, noise_model)
    results.append((config.N, error))

# Print results table
print("\nValidation Results with Qiskit Noise")
print(f"{'System Size (N)':<15}{'Validation Error':<20}")
for N, error in results:
    print(f"{N:<15}{error:<20.6f}")

# Calculate and print percentage reductions
print("\nPercentage Reduction in Error:")
percent_reductions = []
for i in range(1, len(results)):
    reduction = 100 * (results[i - 1][1] - results[i][1]) / results[i - 1][1]
    percent_reductions.append(reduction)
    print(f"Reduction from N={results[i - 1][0]} to N={results[i][0]}: {reduction:.2f}%")

# Plot results with annotations
Ns, errors = zip(*results)
plt.figure(figsize=(10, 6))
plt.plot(Ns, errors, marker='o', label="Validation Errors")
for N, error in zip(Ns, errors):
    plt.text(N, error, f"{error:.6f}", fontsize=8, ha='right')
plt.xlabel("System Size (N)")
plt.ylabel("Validation Error")
plt.title("Validation Errors with Qiskit Noise vs System Size")
plt.grid(True)
plt.legend()
plt.show()
