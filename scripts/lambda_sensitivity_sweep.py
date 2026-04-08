"""
Lambda Sensitivity Sweep for RL Compression Controller
=======================================================
Sweeps lam_E (energy weight) and lam_S (safety weight) across a range of ratios
to characterise the trade-off between energy efficiency and safety compliance.

For each (lam_E, lam_S) pair the Q-learning agent is trained across 5 seeds
for N_EPISODES episodes.  The last 50 episodes are used to compute:
  - Mean energy consumption (kW)
  - Mean safety violations (steps where |pressure - 75| > 15 bar)
  - Mean energy savings vs PID baseline (%)

Outputs:
  paper_evaluation_multiclass/lambda_sensitivity.csv
  paper_evaluation_multiclass/figures/lambda_sensitivity.pdf/.png
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from loguru import logger

# -- Import environment & PID from the main RL script ---------------------
# We re-implement locally so that LAMBDA_E / LAMBDA_S can be injected per run.

N_EPISODES    = 500
MAX_STEPS     = 200
ALPHA         = 0.1
GAMMA         = 0.99
EPSILON_START = 1.0
EPSILON_END   = 0.05
EPSILON_DECAY = 0.995
SEEDS         = [42, 7, 21, 99, 123]
OUTPUT_DIR    = os.path.join(os.path.dirname(__file__), '..', 'paper_evaluation_multiclass')

# Sweep grid: (lam_E, lam_S) pairs that sum to 1.0
LAMBDA_PAIRS = [
    (0.1, 0.9),
    (0.3, 0.7),
    (0.5, 0.5),
    (0.7, 0.3),   # default used in main evaluation
    (0.9, 0.1),
]


# =========================================================================
#  Environment (parameterised λ)
# =========================================================================
class PipelineCompressionEnv:
    N_P, N_F, N_T = 12, 8, 8
    N_ACTIONS = 5
    P_LO, P_HI = 50.0, 110.0
    F_LO, F_HI = 10.0, 100.0
    T_LO, T_HI = 10.0, 50.0
    TARGET_PRESSURE = 75.0
    ALERT_PRESSURE  = 90.0
    CRITICAL_PRESSURE = 100.0
    BASE_COMPRESSOR_KW = 120.0
    MAX_COMPRESSOR_KW  = 250.0

    def __init__(self, seed, lambda_e, lambda_s):
        self.rng = np.random.RandomState(seed)
        self.n_states = self.N_P * self.N_F * self.N_T
        self.n_actions = self.N_ACTIONS
        self.lambda_e = lambda_e
        self.lambda_s = lambda_s
        self._p_edges = np.linspace(self.P_LO, self.P_HI, self.N_P + 1)
        self._f_edges = np.linspace(self.F_LO, self.F_HI, self.N_F + 1)
        self._t_edges = np.linspace(self.T_LO, self.T_HI, self.N_T + 1)
        self.state_cont = None
        self.compressor_kw = self.BASE_COMPRESSOR_KW
        self.steps = 0

    def _digitise(self, p, f, t):
        pb = int(np.clip(np.digitize(p, self._p_edges) - 1, 0, self.N_P - 1))
        fb = int(np.clip(np.digitize(f, self._f_edges) - 1, 0, self.N_F - 1))
        tb = int(np.clip(np.digitize(t, self._t_edges) - 1, 0, self.N_T - 1))
        return pb * (self.N_F * self.N_T) + fb * self.N_T + tb

    def _action_delta(self, action):
        return {0: -15.0, 1: -5.0, 2: 0.0, 3: 5.0, 4: 15.0}[action]

    def reset(self):
        p = self.rng.uniform(70, 80)
        f = self.rng.uniform(40, 60)
        t = self.rng.uniform(20, 30)
        self.state_cont = np.array([p, f, t])
        self.compressor_kw = self.BASE_COMPRESSOR_KW
        self.steps = 0
        return self._digitise(p, f, t)

    def step(self, action):
        p, f, t = self.state_cont
        delta = self._action_delta(action)
        self.compressor_kw = np.clip(self.compressor_kw + delta,
                                     20.0, self.MAX_COMPRESSOR_KW)
        dp = 0.08 * (self.compressor_kw - self.BASE_COMPRESSOR_KW)
        p_new = p + dp + self.rng.normal(0, 1.5)
        f_new = 0.95 * f + 0.05 * 50.0 + self.rng.normal(0, 2)
        t_new = t + 0.01 * self.compressor_kw - 1.2 + self.rng.normal(0, 0.5)
        p_new = np.clip(p_new, self.P_LO, self.P_HI)
        f_new = np.clip(f_new, self.F_LO, self.F_HI)
        t_new = np.clip(t_new, self.T_LO, self.T_HI)
        self.state_cont = np.array([p_new, f_new, t_new])

        energy_kw = self.compressor_kw
        energy_penalty = -self.lambda_e * (energy_kw / self.MAX_COMPRESSOR_KW)

        pressure_err = abs(p_new - self.TARGET_PRESSURE)
        if pressure_err < 3:
            safety_bonus = 1.0
        elif pressure_err < 8:
            safety_bonus = 0.3
        else:
            safety_bonus = -0.5
        if p_new > self.ALERT_PRESSURE:
            safety_bonus -= 2.0
        if p_new > self.CRITICAL_PRESSURE:
            safety_bonus -= 5.0
        if p_new < 55:
            safety_bonus -= 1.5

        reward = energy_penalty + self.lambda_s * safety_bonus

        # Track safety violation
        violation = 1 if pressure_err > 15 else 0

        self.steps += 1
        done = self.steps >= MAX_STEPS
        info = {'energy_kw': energy_kw, 'pressure': p_new, 'violation': violation}
        return self._digitise(p_new, f_new, t_new), reward, done, info

    def sample_action(self):
        return self.rng.randint(self.n_actions)


# =========================================================================
#  PID baseline (lambda-independent -uses same environment physics)
# =========================================================================
def run_pid_episode(seed, lambda_e, lambda_s):
    env = PipelineCompressionEnv(seed=seed, lambda_e=lambda_e, lambda_s=lambda_s)
    env.reset()
    total_energy = 0.0
    violations = 0
    integral = 0.0
    prev_err = 0.0
    Kp, Ki, Kd = 0.4, 0.02, 0.1

    for _ in range(MAX_STEPS):
        p = env.state_cont[0]
        err = p - env.TARGET_PRESSURE
        integral += err
        derivative = err - prev_err
        prev_err = err
        pid_out = Kp * err + Ki * integral + Kd * derivative
        if pid_out > 8:
            action = 0
        elif pid_out > 2:
            action = 1
        elif pid_out < -8:
            action = 4
        elif pid_out < -2:
            action = 3
        else:
            action = 2
        _, _, done, info = env.step(action)
        total_energy += info['energy_kw']
        violations += info['violation']
        if done:
            break
    return total_energy, violations


# =========================================================================
#  Q-Learning (parameterised λ)
# =========================================================================
def run_rl_experiment(seed, lambda_e, lambda_s):
    env = PipelineCompressionEnv(seed=seed, lambda_e=lambda_e, lambda_s=lambda_s)
    Q = np.zeros((env.n_states, env.n_actions))
    episode_energies = np.zeros(N_EPISODES)
    episode_violations = np.zeros(N_EPISODES)
    epsilon = EPSILON_START

    for ep in range(N_EPISODES):
        state = env.reset()
        total_energy = 0.0
        total_violations = 0
        for _ in range(MAX_STEPS):
            if env.rng.rand() < epsilon:
                action = env.sample_action()
            else:
                action = int(np.argmax(Q[state]))
            next_state, reward, done, info = env.step(action)
            total_energy += info['energy_kw']
            total_violations += info['violation']
            best_next = np.max(Q[next_state])
            Q[state, action] += ALPHA * (reward + GAMMA * best_next - Q[state, action])
            state = next_state
            if done:
                break
        epsilon = max(EPSILON_END, epsilon * EPSILON_DECAY)
        episode_energies[ep] = total_energy
        episode_violations[ep] = total_violations

    return episode_energies, episode_violations


# =========================================================================
#  Main
# =========================================================================
def main():
    os.makedirs(os.path.join(OUTPUT_DIR, 'figures'), exist_ok=True)

    rows = []

    for lambda_e, lambda_s in LAMBDA_PAIRS:
        tag = f"lam_E={lambda_e:.1f}, lam_S={lambda_s:.1f}"
        logger.info(f"-- Sweep: {tag} --")

        # PID baseline for this pair (physics is identical, but we need
        # per-seed energy for fair savings computation)
        pid_energies = []
        pid_violations = []
        for seed in SEEDS:
            energies = []
            viols = []
            for ep in range(N_EPISODES):
                e, v = run_pid_episode(seed + ep, lambda_e, lambda_s)
                energies.append(e)
                viols.append(v)
            pid_energies.append(np.mean(energies[-50:]))
            pid_violations.append(np.mean(viols[-50:]))
        pid_mean_energy = np.mean(pid_energies)
        pid_mean_violations = np.mean(pid_violations)

        # RL across seeds
        rl_energies_per_seed = []
        rl_violations_per_seed = []
        for seed in SEEDS:
            energies, violations = run_rl_experiment(seed, lambda_e, lambda_s)
            rl_energies_per_seed.append(np.mean(energies[-50:]))
            rl_violations_per_seed.append(np.mean(violations[-50:]))

        rl_mean_energy = np.mean(rl_energies_per_seed)
        rl_std_energy = np.std(rl_energies_per_seed)
        rl_mean_violations = np.mean(rl_violations_per_seed)
        rl_std_violations = np.std(rl_violations_per_seed)
        savings = (pid_mean_energy - rl_mean_energy) / pid_mean_energy * 100

        rows.append({
            'lambda_E': lambda_e,
            'lambda_S': lambda_s,
            'ratio': f"{lambda_e:.1f}/{lambda_s:.1f}",
            'RL_energy_mean_kW': round(rl_mean_energy, 1),
            'RL_energy_std_kW': round(rl_std_energy, 1),
            'PID_energy_mean_kW': round(pid_mean_energy, 1),
            'energy_savings_pct': round(savings, 2),
            'RL_violations_mean': round(rl_mean_violations, 2),
            'RL_violations_std': round(rl_std_violations, 2),
            'PID_violations_mean': round(pid_mean_violations, 2),
        })

        logger.info(f"  RL energy: {rl_mean_energy:.1f} ± {rl_std_energy:.1f} kW  |  "
                     f"PID: {pid_mean_energy:.1f} kW  |  "
                     f"Savings: {savings:+.2f}%  |  "
                     f"Violations: {rl_mean_violations:.2f}")

    # -- Save CSV ----------------------------------------------------------
    df = pd.DataFrame(rows)
    csv_path = os.path.join(OUTPUT_DIR, 'lambda_sensitivity.csv')
    df.to_csv(csv_path, index=False)
    logger.info(f"CSV saved -> {csv_path}")

    # -- Print summary -----------------------------------------------------
    print("\n" + "=" * 80)
    print("  L_E / L_S Sensitivity Sweep -Q-Learning RL Controller")
    print("=" * 80)
    print(f"  {'lam_E/lam_S':>8}  {'RL Energy (kW)':>18}  {'PID (kW)':>10}  "
          f"{'Savings':>10}  {'Violations':>12}")
    print("-" * 80)
    for r in rows:
        print(f"  {r['ratio']:>8}  "
              f"{r['RL_energy_mean_kW']:>10.1f} ± {r['RL_energy_std_kW']:<6.1f}  "
              f"{r['PID_energy_mean_kW']:>10.1f}  "
              f"{r['energy_savings_pct']:>+9.2f}%  "
              f"{r['RL_violations_mean']:>8.2f} ± {r['RL_violations_std']:<4.2f}")
    print("=" * 80)

    # -- Plot --------------------------------------------------------------
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    ratios = [r['ratio'] for r in rows]
    x = np.arange(len(ratios))

    # Panel 1: Energy consumption (RL vs PID)
    rl_e = [r['RL_energy_mean_kW'] for r in rows]
    rl_e_err = [r['RL_energy_std_kW'] for r in rows]
    pid_e = [r['PID_energy_mean_kW'] for r in rows]
    axes[0].bar(x - 0.18, rl_e, 0.35, yerr=rl_e_err, label='RL (Q-learning)',
                color='#2196F3', alpha=0.85, capsize=4)
    axes[0].bar(x + 0.18, pid_e, 0.35, label='PID baseline',
                color='#FF9800', alpha=0.85)
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(ratios, fontsize=9)
    axes[0].set_xlabel('L_E / L_S')
    axes[0].set_ylabel('Mean Energy (kW, last 50 eps)')
    axes[0].set_title('Energy Consumption')
    axes[0].legend()
    axes[0].grid(axis='y', alpha=0.3)

    # Panel 2: Energy savings %
    savings = [r['energy_savings_pct'] for r in rows]
    colors = ['#4CAF50' if s > 0 else '#E91E63' for s in savings]
    axes[1].bar(x, savings, color=colors, alpha=0.85, width=0.5)
    axes[1].axhline(0, color='black', linewidth=0.8)
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(ratios, fontsize=9)
    axes[1].set_xlabel('L_E / L_S')
    axes[1].set_ylabel('Energy Savings vs PID (%)')
    axes[1].set_title('Energy Savings')
    axes[1].grid(axis='y', alpha=0.3)
    for i, s in enumerate(savings):
        axes[1].text(i, s + (0.3 if s >= 0 else -0.6), f'{s:+.1f}%',
                     ha='center', fontsize=9, fontweight='bold')

    # Panel 3: Safety violations
    viol_rl = [r['RL_violations_mean'] for r in rows]
    viol_rl_err = [r['RL_violations_std'] for r in rows]
    viol_pid = [r['PID_violations_mean'] for r in rows]
    axes[2].bar(x - 0.18, viol_rl, 0.35, yerr=viol_rl_err, label='RL',
                color='#E91E63', alpha=0.85, capsize=4)
    axes[2].bar(x + 0.18, viol_pid, 0.35, label='PID',
                color='#9E9E9E', alpha=0.85)
    axes[2].set_xticks(x)
    axes[2].set_xticklabels(ratios, fontsize=9)
    axes[2].set_xlabel('L_E / L_S')
    axes[2].set_ylabel('Mean Violations (|Δp| > 15 bar)')
    axes[2].set_title('Safety Violations')
    axes[2].legend()
    axes[2].grid(axis='y', alpha=0.3)

    fig.suptitle('L_E / L_S Sensitivity Sweep -Q-Learning RL Controller',
                 fontsize=13, fontweight='bold')
    plt.tight_layout()

    for ext in ('pdf', 'png'):
        path = os.path.join(OUTPUT_DIR, 'figures', f'lambda_sensitivity.{ext}')
        fig.savefig(path, dpi=300, bbox_inches='tight')
    plt.close(fig)
    logger.info(f"Plots saved -> {os.path.join(OUTPUT_DIR, 'figures', 'lambda_sensitivity.pdf')}")

    print(f"\n  Outputs: {csv_path}")
    print(f"           {os.path.join(OUTPUT_DIR, 'figures', 'lambda_sensitivity.pdf')}")


if __name__ == "__main__":
    main()
