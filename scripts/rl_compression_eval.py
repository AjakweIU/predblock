"""
Q-Learning RL Controller for CO2 Pipeline Compression Optimization
===================================================================
1. Train Q-learning agent across 5 random seeds for N_EPISODES each
2. Record cumulative reward and energy consumption per episode
3. Plot learning curves (mean +/- std shaded band) across seeds
4. Compare final energy savings vs PID baseline (box plot)
5. Report mean +/- std energy reduction percentage

The environment discretises the state/action space of the existing
PipelinePressureEnv for tabular Q-learning.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from loguru import logger

# ── Hyperparameters ────────────────────────────────────────────────────────
N_EPISODES    = 500
MAX_STEPS     = 200
ALPHA         = 0.1        # learning rate
GAMMA         = 0.99       # discount factor
EPSILON_START = 1.0
EPSILON_END   = 0.05
EPSILON_DECAY = 0.995
LAMBDA_E      = 0.7        # energy weight in reward
LAMBDA_S      = 0.3        # safety weight in reward
SEEDS         = [42, 7, 21, 99, 123]
OUTPUT_DIR    = os.path.join(os.path.dirname(__file__), '..', 'paper_evaluation_multiclass')


# ═══════════════════════════════════════════════════════════════════════════
#  Discrete Pipeline Compression Environment
# ═══════════════════════════════════════════════════════════════════════════
class PipelineCompressionEnv:
    """
    Discrete-space environment for CO2 pipeline compression optimisation.

    State  (3 discrete dims, flattened to a single int):
      - pressure_bin   : 0..N_P-1  (bins over 50-110 bar)
      - flow_rate_bin  : 0..N_F-1  (bins over 10-100 kg/s)
      - temperature_bin: 0..N_T-1  (bins over 10-50 °C)

    Actions (5 discrete):
      0 = decrease compressor power a lot  (-15 kW)
      1 = decrease compressor power a bit  (-5 kW)
      2 = hold
      3 = increase compressor power a bit  (+5 kW)
      4 = increase compressor power a lot  (+15 kW)

    Reward:
      - LAMBDA_E * (−energy_kw / max_energy)  penalises energy use
      - LAMBDA_S * safety_bonus                rewards staying in target band
      - Large penalty for overpressure / underpressure
    """

    N_P, N_F, N_T = 12, 8, 8          # bin counts
    N_ACTIONS = 5

    # Physical bounds
    P_LO, P_HI = 50.0, 110.0          # bar
    F_LO, F_HI = 10.0, 100.0          # kg/s
    T_LO, T_HI = 10.0, 50.0           # °C

    TARGET_PRESSURE = 75.0             # bar – operational setpoint
    ALERT_PRESSURE  = 90.0
    CRITICAL_PRESSURE = 100.0
    BASE_COMPRESSOR_KW = 120.0         # kW at equilibrium
    MAX_COMPRESSOR_KW  = 250.0

    def __init__(self, seed=42):
        self.rng = np.random.RandomState(seed)
        self.n_states = self.N_P * self.N_F * self.N_T
        self.n_actions = self.N_ACTIONS

        # Bin edges
        self._p_edges = np.linspace(self.P_LO, self.P_HI, self.N_P + 1)
        self._f_edges = np.linspace(self.F_LO, self.F_HI, self.N_F + 1)
        self._t_edges = np.linspace(self.T_LO, self.T_HI, self.N_T + 1)

        self.state_cont = None        # (pressure, flow, temp)
        self.compressor_kw = self.BASE_COMPRESSOR_KW
        self.steps = 0

    # ── helpers ────────────────────────────────────────────────────────
    def _digitise(self, p, f, t):
        pb = int(np.clip(np.digitize(p, self._p_edges) - 1, 0, self.N_P - 1))
        fb = int(np.clip(np.digitize(f, self._f_edges) - 1, 0, self.N_F - 1))
        tb = int(np.clip(np.digitize(t, self._t_edges) - 1, 0, self.N_T - 1))
        return pb * (self.N_F * self.N_T) + fb * self.N_T + tb

    def _action_delta(self, action):
        return {0: -15.0, 1: -5.0, 2: 0.0, 3: 5.0, 4: 15.0}[action]

    # ── gym-like interface ─────────────────────────────────────────────
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

        # Apply compressor change
        delta = self._action_delta(action)
        self.compressor_kw = np.clip(self.compressor_kw + delta,
                                     20.0, self.MAX_COMPRESSOR_KW)

        # Physics: higher compressor power → higher downstream pressure
        dp = 0.08 * (self.compressor_kw - self.BASE_COMPRESSOR_KW)
        p_new = p + dp + self.rng.normal(0, 1.5)

        # Flow rate drift + noise
        f_new = 0.95 * f + 0.05 * 50.0 + self.rng.normal(0, 2)

        # Temperature: compressor heats CO2
        t_new = t + 0.01 * self.compressor_kw - 1.2 + self.rng.normal(0, 0.5)

        # Clip
        p_new = np.clip(p_new, self.P_LO, self.P_HI)
        f_new = np.clip(f_new, self.F_LO, self.F_HI)
        t_new = np.clip(t_new, self.T_LO, self.T_HI)

        self.state_cont = np.array([p_new, f_new, t_new])

        # ── Reward ────────────────────────────────────────────────────
        energy_kw = self.compressor_kw
        energy_penalty = -LAMBDA_E * (energy_kw / self.MAX_COMPRESSOR_KW)

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
            safety_bonus -= 1.5          # underpressure penalty

        reward = energy_penalty + LAMBDA_S * safety_bonus

        self.steps += 1
        done = self.steps >= MAX_STEPS

        info = {'energy_kw': energy_kw, 'pressure': p_new}

        return self._digitise(p_new, f_new, t_new), reward, done, info

    def sample_action(self):
        return self.rng.randint(self.n_actions)


# ═══════════════════════════════════════════════════════════════════════════
#  PID Baseline Controller
# ═══════════════════════════════════════════════════════════════════════════
def run_pid_episode(seed):
    """Run one episode with a simple PID-style controller (no learning)."""
    env = PipelineCompressionEnv(seed=seed)
    state = env.reset()
    total_reward = 0.0
    total_energy = 0.0

    # PID params
    integral = 0.0
    prev_err = 0.0
    Kp, Ki, Kd = 0.4, 0.02, 0.1

    for _ in range(MAX_STEPS):
        p = env.state_cont[0]
        err = p - env.TARGET_PRESSURE     # positive → too high
        integral += err
        derivative = err - prev_err
        prev_err = err

        pid_out = Kp * err + Ki * integral + Kd * derivative

        # Map PID output to discrete action
        if pid_out > 8:
            action = 0      # decrease power a lot
        elif pid_out > 2:
            action = 1      # decrease power a bit
        elif pid_out < -8:
            action = 4      # increase power a lot
        elif pid_out < -2:
            action = 3      # increase power a bit
        else:
            action = 2      # hold

        state, reward, done, info = env.step(action)
        total_reward += reward
        total_energy += info['energy_kw']
        if done:
            break

    return total_reward, total_energy


# ═══════════════════════════════════════════════════════════════════════════
#  Q-Learning Training
# ═══════════════════════════════════════════════════════════════════════════
def run_rl_experiment(seed):
    """Train Q-learning agent for one seed; return per-episode metrics."""
    env = PipelineCompressionEnv(seed=seed)
    Q = np.zeros((env.n_states, env.n_actions))

    episode_rewards  = np.zeros(N_EPISODES)
    episode_energies = np.zeros(N_EPISODES)
    epsilon = EPSILON_START

    for ep in range(N_EPISODES):
        state = env.reset()
        total_reward = 0.0
        total_energy = 0.0

        for _ in range(MAX_STEPS):
            # Epsilon-greedy
            if env.rng.rand() < epsilon:
                action = env.sample_action()
            else:
                action = int(np.argmax(Q[state]))

            next_state, reward, done, info = env.step(action)
            total_energy += info['energy_kw']

            # Q-update (off-policy TD(0))
            best_next = np.max(Q[next_state])
            Q[state, action] += ALPHA * (reward + GAMMA * best_next - Q[state, action])

            state = next_state
            total_reward += reward
            if done:
                break

        epsilon = max(EPSILON_END, epsilon * EPSILON_DECAY)
        episode_rewards[ep] = total_reward
        episode_energies[ep] = total_energy

    return episode_rewards, episode_energies


# ═══════════════════════════════════════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════════════════════════════════════
def main():
    os.makedirs(os.path.join(OUTPUT_DIR, 'figures'), exist_ok=True)

    # ── 1. PID baseline (run N_EPISODES per seed for fair comparison) ──
    logger.info("Running PID baseline episodes...")
    pid_energies_per_seed = []
    for seed in SEEDS:
        energies = []
        for ep in range(N_EPISODES):
            _, e = run_pid_episode(seed + ep)
            energies.append(e)
        pid_energies_per_seed.append(np.array(energies))
    pid_energies_per_seed = np.array(pid_energies_per_seed)  # (5, N_EPISODES)
    pid_mean_energy = pid_energies_per_seed[:, -50:].mean()  # scalar baseline
    logger.info(f"PID mean energy (last 50 eps, all seeds): {pid_mean_energy:.1f} kW")

    # ── 2. Train Q-learning across 5 seeds ─────────────────────────────
    logger.info("Training Q-learning agents (5 seeds)...")
    all_rewards  = []
    all_energies = []
    for seed in SEEDS:
        logger.info(f"  Seed {seed}...")
        rewards, energies = run_rl_experiment(seed)
        all_rewards.append(rewards)
        all_energies.append(energies)

    all_rewards  = np.array(all_rewards)    # (5, N_EPISODES)
    all_energies = np.array(all_energies)

    # ── 3. Compute energy savings vs PID ───────────────────────────────
    rl_final_energy = all_energies[:, -50:].mean(axis=1)    # per seed
    pid_final_energy = pid_energies_per_seed[:, -50:].mean(axis=1)
    energy_savings_pct = (pid_final_energy - rl_final_energy) / pid_final_energy * 100

    print("\n" + "=" * 65)
    print("  RL Energy Savings vs PID Baseline")
    print("=" * 65)
    print(f"  PID  mean energy (last 50 eps): {pid_final_energy.mean():.1f} "
          f"+/- {pid_final_energy.std():.1f} kW")
    print(f"  RL   mean energy (last 50 eps): {rl_final_energy.mean():.1f} "
          f"+/- {rl_final_energy.std():.1f} kW")
    print(f"  Energy savings: {np.mean(energy_savings_pct):.2f}% "
          f"+/- {np.std(energy_savings_pct):.2f}%")
    print(f"  Per-seed savings: {np.round(energy_savings_pct, 2)}")

    # ── 4. Learning curves (reward + energy) ───────────────────────────
    episodes = np.arange(N_EPISODES)
    mean_r = all_rewards.mean(axis=0)
    std_r  = all_rewards.std(axis=0)
    mean_e = all_energies.mean(axis=0)
    std_e  = all_energies.std(axis=0)

    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    # Panel 1: Reward learning curve
    axes[0].plot(episodes, mean_r, color='#2196F3', linewidth=1.5, label='Mean reward')
    axes[0].fill_between(episodes, mean_r - std_r, mean_r + std_r,
                         alpha=0.25, color='#2196F3')
    axes[0].set_xlabel("Episode")
    axes[0].set_ylabel("Cumulative Reward")
    axes[0].set_title("Reward Learning Curve (5 Seeds)")
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    # Panel 2: Energy learning curve
    axes[1].plot(episodes, mean_e, color='#FF9800', linewidth=1.5, label='Mean energy (RL)')
    axes[1].fill_between(episodes, mean_e - std_e, mean_e + std_e,
                         alpha=0.25, color='#FF9800')
    # PID reference line
    axes[1].axhline(y=pid_mean_energy, color='red', linestyle='--', linewidth=1.5,
                    label=f'PID baseline ({pid_mean_energy:.0f} kW)')
    axes[1].set_xlabel("Episode")
    axes[1].set_ylabel("Total Energy (kW)")
    axes[1].set_title("Energy Consumption per Episode")
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    # Panel 3: Energy savings box plot
    bp = axes[2].boxplot(energy_savings_pct, vert=True, patch_artist=True,
                         boxprops=dict(facecolor='#4CAF50', alpha=0.7),
                         medianprops=dict(color='black', linewidth=2))
    axes[2].axhline(y=np.mean(energy_savings_pct), color='red', linestyle='--',
                    linewidth=1.5,
                    label=f'Mean: {np.mean(energy_savings_pct):.2f}%')
    for i, val in enumerate(energy_savings_pct):
        axes[2].plot(1, val, 'ko', markersize=6, alpha=0.6)
    axes[2].set_ylabel("Energy Savings (%)")
    axes[2].set_title("RL vs PID — Energy Reduction")
    axes[2].set_xticks([1])
    axes[2].set_xticklabels(['RL Controller'])
    axes[2].legend()
    axes[2].grid(axis='y', alpha=0.3)

    fig.suptitle("Q-Learning RL Controller — CO2 Pipeline Compression Optimisation",
                 fontsize=13, fontweight='bold')
    plt.tight_layout()

    for ext in ('pdf', 'png'):
        path = os.path.join(OUTPUT_DIR, 'figures', f'rl_learning_curves.{ext}')
        fig.savefig(path, dpi=300, bbox_inches='tight')
    plt.close(fig)
    logger.info(f"Plots saved → {os.path.join(OUTPUT_DIR, 'figures', 'rl_learning_curves.pdf')}")

    print("\n" + "=" * 65)
    print("  RL evaluation complete.  Outputs in:", OUTPUT_DIR)
    print("=" * 65)


if __name__ == "__main__":
    main()
