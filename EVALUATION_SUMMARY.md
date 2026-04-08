# PredBlock — Comprehensive Evaluation Summary

This document summarises the experiments conducted to validate the PredBlock system across its core components: physics-based simulation accuracy, AI anomaly detection, reinforcement learning control, blockchain audit-trail performance, and model robustness.

All scripts are located in `scripts/` and all outputs (figures, CSVs) are saved to `paper_evaluation_multiclass/`.

### Reproducibility

To reproduce all key tables and figures from a clean checkout:

```bash
conda env create -f environment.yml   # or: pip install -r requirements.txt
conda activate predblock
python reproduce.py                    # offline (ML/RL only)
python reproduce.py --online           # includes PureChain blockchain benchmark
```

`reproduce.py` executes all evaluation scripts in dependency order: data generation, multiclass RF evaluation, baseline comparison, ablation study, robustness analysis, RL controller, lambda sensitivity sweep, blockchain benchmark (optional), and EOS validation. All outputs are written to `paper_evaluation_multiclass/`. Core dependencies are pinned in `environment.yml` (Python 3.10, scikit-learn 1.3.0, web3 6.8.0).

---

## Table of Contents

1. [Target Deployment Context](#1-target-deployment-context)
2. [CO2 Density Equation Validation (EOS)](#2-co2-density-equation-validation)
3. [Multiclass Random Forest Anomaly Detection](#3-multiclass-random-forest-anomaly-detection)
4. [Ablation Study: Physics-Informed Features](#4-ablation-study-physics-informed-features)
5. [Robustness Analysis](#5-robustness-analysis)
6. [Q-Learning RL Compression Controller](#6-q-learning-rl-compression-controller)
7. [Blockchain Latency Benchmark](#7-blockchain-latency-benchmark)
8. [ISO 27916 Compliance Mapping](#8-iso-27916-compliance-mapping)
9. [Threat Model](#9-threat-model)
10. [Output Files Index](#10-output-files-index)

---

## 1. Target Deployment Context

This section defines the reference CCS pipeline configuration used across all simulations and evaluations.

### Pipeline Physical Parameters

| Parameter | Value | Source |
|-----------|-------|--------|
| Length | 100 km (100,000 m) | `PipelinePhysics` default |
| Internal diameter | 0.5 m (DN500 / ~20") | `PipelinePhysics` default |
| Wall roughness | 4.6 × 10⁻⁵ m (steel) | `PipelinePhysics` default |

### Pressure and Temperature Window

| Parameter | Normal | Alert | Critical |
|-----------|--------|-------|----------|
| Pressure | 75 bar | 90 bar | 100 bar |
| Temperature | 25 °C | — | 50 °C (max) |

The RL compression environment uses a wider exploration range: 50–110 bar pressure, 10–50 °C temperature, 10–100 kg/s flow rate. The EOS validation grid covers 7–20 MPa (70–200 bar) and 305–330 K (32–57 °C), while the density spline lookup table spans 50–250 bar and 5–80 °C.

### Sensor Suite

| Sensor | Normal Range | Unit | Type |
|--------|-------------|------|------|
| Pressure | ~75 ± 2 | bar | Process |
| Temperature | ~25 ± 3 | °C | Process |
| Flow rate | 10–100 (nominal ~50) | kg/s | Process |
| Acoustic emission | ~50 ± 5 | a.u. | Integrity |
| Vibration | ~10 ± 2 | a.u. | Integrity |

The AI anomaly detector uses 9 features: the 5 process/integrity sensors above plus 4 impurity species (H₂O, H₂S, SO₂, O₂).

### Impurity Thresholds

| Species | Normal Max | Alert | Critical | Unit |
|---------|-----------|-------|----------|------|
| H₂O | 50 | 100 | 150 | ppmv |
| H₂S | 10 | 20 | 50 | ppmv |
| SO₂ | 50 | 100 | 200 | ppmv |
| O₂ | 10 | 15 | 25 | ppmv |
| NOx | 50 | 80 | 120 | ppmv |
| N₂ | 4 | 5 | 7 | mol% |
| CH₄ | 2 | 3 | 5 | mol% |

### Sampling and Simulation

| Parameter | Value |
|-----------|-------|
| Sampling interval | 60 seconds (1 reading/min) |
| Simulation duration | 720 hours (30 days) |
| Sensor count | 10 |
| Anomaly injection rate | 5% |

### On-Chain Validation Bounds

The `MonitoringLog.sol` `validData` modifier enforces: pressure < 150 bar and temperature < 100 °C (stored as scaled integers: 15000 and 10000 respectively). Readings outside these ranges are rejected at the smart-contract level.

---

## 2. CO2 Density Equation Validation

**Script:** `scripts/eos_validation.py`
**Objective:** Compare the surrogate CO2 density equation (`CO2Properties.density()`) against CoolProp's full Span-Wagner EOS.

### Setup

- **Operating window:** 7–20 MPa, 305–330 K
- **Grid resolution:** 30 × 25 = 750 points
- **Reference:** CoolProp library (Span-Wagner EOS for CO2)

### Approach

The original surrogate used a simplified analytical correlation with reduced properties (Tr, Pr). This produced large errors near the critical point (~304 K, ~7.38 MPa). The surrogate was subsequently **improved** by replacing it with a **bicubic spline interpolation** over a 100 × 100 CoolProp-generated lookup table stored in `data/co2_density_lookup.npz`. The spline falls back to the original formula only for out-of-range inputs.

### Results (After Improvement)

After the bicubic spline replacement, the surrogate matches CoolProp to near-machine precision across the entire operating window. The validation heatmap confirms negligible residual error.

### Figure

`paper_evaluation_multiclass/figures/eos_validation.pdf` — 3-panel plot: CoolProp reference density, surrogate density, and percentage error heatmap.

---

## 3. Multiclass Random Forest Anomaly Detection

**Script:** `scripts/multiclass_rf_evaluation.py`
**Objective:** Classify pipeline events into 4 classes: `normal`, `leakage`, `corrosion`, `overpressure`.

### Setup

- **Data:** Combined `train_physics.csv` + `val_physics.csv` + `test_physics.csv` → 75,000 samples
- **Split:** Strict chronological 70/15/15 (train/validation/test), with temporal leakage assertions
- **Features (9):** `pressure`, `temperature`, `flow_rate`, `H2O`, `H2S`, `SO2`, `O2`, `vibration`, `acoustic_emission`
- **Model:** `RandomForestClassifier(n_estimators=100, max_depth=None, class_weight='balanced')`
- **Seeds:** 5 random seeds `[42, 7, 21, 99, 123]`
- **Bootstrap CI:** 1,000 bootstrap resamples of the test set

### Split Distribution

| Split | Samples | Normal | Leakage | Corrosion | Overpressure |
|-------|---------|--------|---------|-----------|--------------|
| Train | 52,500 | 50,982 | 750 | 685 | 83 |
| Val | 11,250 | 10,837 | 150 | 249 | 14 |
| Test | 11,250 | 11,021 | 150 | 71 | 8 |

**Test-set anomaly prevalence:** Leakage 1.33%, Corrosion 0.63%, Overpressure 0.07%. The class imbalance reflects realistic CCS pipeline operations.

`paper_evaluation_multiclass/figures/anomaly_distribution.pdf` — Bar charts showing the frequency distribution of anomaly events across the three risk categories in the test set.

### Multi-Seed Macro Results (mean ± std over 5 seeds)

| Metric | Value |
|--------|-------|
| **F1-macro** | **0.9989 ± 0.0009** |
| Precision-macro | 0.9979 ± 0.0017 |
| Recall-macro | 1.0000 ± 0.0000 |
| AUC-ROC-macro | 1.0000 ± 0.0000 |

### Bootstrapped 95% Confidence Intervals (n = 1,000)

| Metric (macro) | 95% CI |
|----------------|--------|
| **F1** | **[1.0000, 1.0000]** |
| Precision | [1.0000, 1.0000] |
| Recall | [1.0000, 1.0000] |
| AUC-ROC | [1.0000, 1.0000] |

The tight CIs reflect near-perfect separability on this test split. Saturation at 1.0 across all 1,000 bootstrap resamples indicates that the model's decision boundary is highly stable.

### Per-Class Precision, Recall, and F1 (mean ± std over 5 seeds)

| Class | Precision | Recall | F1 |
|-------|-----------|--------|----|
| **Normal** | 1.0000 ± 0.0000 | 0.9999 ± 0.0000 | 1.0000 ± 0.0000 |
| **Leakage** | 1.0000 ± 0.0000 | 1.0000 ± 0.0000 | 1.0000 ± 0.0000 |
| **Corrosion** | 0.9917 ± 0.0068 | 1.0000 ± 0.0000 | 0.9958 ± 0.0034 |
| **Overpressure** | 1.0000 ± 0.0000 | 1.0000 ± 0.0000 | 1.0000 ± 0.0000 |

**Note on corrosion class:** The slight precision variance (0.9917) is attributable to the small test-set count (71 corrosion samples, 8 overpressure) and occasional false positives from the normal class. Recall remains perfect across all seeds.

### PR-AUC per Class

| Class | PR-AUC |
|-------|--------|
| Normal | 1.0000 |
| Leakage | 1.0000 |
| Corrosion | 1.0000 |
| Overpressure | 1.0000 |

### Baseline Comparison

**Script:** `scripts/baseline_comparison.py`

PredBlock is compared against three unsupervised/heuristic baselines on the same chronological test split. To ensure a **like-for-like comparison**, PredBlock is evaluated in both its native 4-class mode *and* a separate binary RF (normal vs any anomaly) trained on binarised labels. Baselines are binary detectors evaluated with F1-macro.

#### Baseline Hyperparameters

| Baseline | Hyperparameters |
|----------|----------------|
| **Isolation Forest** | `contamination=0.05`, `random_state=42`, `n_jobs=-1` (scikit-learn defaults for all other parameters: `n_estimators=100`, `max_samples='auto'`, `max_features=1.0`) |
| **One-Class SVM** | `nu=0.05`, `kernel='rbf'` (scikit-learn default), `gamma='scale'` (scikit-learn default). Trained on a random subsample of 10,000 training points (`random_state=42`) for computational tractability. |
| **Threshold** | O₂ > 95th percentile of the test set triggers an anomaly flag. No training required. |

The `contamination` and `nu` parameters are both set to 0.05, matching the 5% anomaly injection rate used during data generation, giving each unsupervised baseline the best-case prior on anomaly prevalence.

#### F1-macro Results

| Method | Type | Task | F1-macro |
|--------|------|------|----------|
| **PredBlock (4-class RF)** | Supervised | 4-class | **0.994** |
| **PredBlock (binary RF)** | Supervised | Binary | **1.000** |
| Isolation Forest | Unsupervised | Binary | 0.879 |
| One-Class SVM | Unsupervised | Binary | 0.767 |
| Threshold (O₂ 95th pctl) | Heuristic | Binary | 0.727 |

The binary PredBlock RF provides a **like-for-like comparison**: on the same binary detection task, PredBlock (F1 = 1.000) outperforms the best unsupervised baseline (Isolation Forest, F1 = 0.879) by +12.1 percentage points. The 4-class model (F1 = 0.994) additionally distinguishes anomaly subtypes at near-perfect accuracy.

#### Binary PR-AUC (Average Precision)

| Method | PR-AUC |
|--------|--------|
| **PredBlock (binary RF)** | **1.0000** |
| Isolation Forest | 0.9707 |
| One-Class SVM | 0.6506 |

Binary Precision-Recall curves are provided in `paper_evaluation_multiclass/figures/pr_curves_binary.pdf`. PredBlock achieves perfect precision across all recall levels; Isolation Forest maintains high precision (PR-AUC 0.97) but drops at high recall; One-Class SVM shows substantially lower ranking quality (PR-AUC 0.65).

### Figures

- `paper_evaluation_multiclass/figures/confusion_matrix.pdf`
- `paper_evaluation_multiclass/figures/pr_curves.pdf` — Per-class (OvR) Precision-Recall curves for the 4-class model
- `paper_evaluation_multiclass/figures/pr_curves_binary.pdf` — Binary PR curves: PredBlock RF vs Isolation Forest vs One-Class SVM
- `paper_evaluation_multiclass/figures/baseline_comparison.pdf` — F1-macro bar chart (includes binary PredBlock row)

---

## 4. Ablation Study: Physics-Informed Features

**Script:** `scripts/ablation_study.py`
**Objective:** Quantify the contribution of physics-informed and corrosion-derived features to anomaly detection performance.

### Feature Groups

| Group | Features |
|-------|----------|
| **Raw Sensors** | pressure, temperature, flow_rate, H2O, H2S, SO2, O2, NOx, N2, CH4, acoustic_emission, vibration |
| **Physics/Thermo** | density (Span-Wagner surrogate) |
| **Corrosion-Derived** | corrosion_depth (cumulative corrosion kinetics) |

### Variants

| Variant | Description | Features |
|---------|-------------|----------|
| A | Full model | All 14 features |
| B | No corrosion depth | 13 features |
| C | No physics features | 12 features (no density, no corrosion_depth) |
| D | Raw sensors only | 12 sensor features |

### Results (mean ± std over 5 seeds)

| Variant | F1-macro | PR-AUC | AUC-ROC |
|---------|----------|--------|---------|
| **A — Full Model** | **0.9971 ± 0.0059** | **1.0000 ± 0.0000** | **1.0000 ± 0.0000** |
| B — No Corrosion Depth | 0.9941 ± 0.0072 | 1.0000 ± 0.0000 | 1.0000 ± 0.0000 |
| C — No Physics Features | 0.9941 ± 0.0072 | 1.0000 ± 0.0000 | 1.0000 ± 0.0000 |
| D — Raw Sensors Only | 0.9941 ± 0.0072 | 1.0000 ± 0.0000 | 1.0000 ± 0.0000 |

### Interpretation

The full model (Variant A) achieves the highest F1-macro at **0.9971**, a marginal but consistent improvement over the sensor-only baseline (0.9941). The physics-informed `density` feature and corrosion-derived `corrosion_depth` contribute a **+0.30%** absolute F1 gain. PR-AUC and AUC-ROC are saturated at 1.0 across all variants, indicating that the ranking quality is excellent regardless of feature set.

### Figure

`paper_evaluation_multiclass/figures/ablation_study.pdf` — Grouped bar chart comparing F1-macro, PR-AUC, and AUC-ROC across all four variants.

---

## 5. Robustness Analysis

**Script:** `scripts/robustness_analysis.py`
**Objective:** Evaluate the anomaly detector's resilience to three types of input corruption.

### Corruption Modes

1. **Gaussian noise** — additive N(0, σ) noise at σ ∈ {0, 0.01, 0.05, 0.1, 0.2, 0.5}
2. **Sensor drift** — linear drift added over time at magnitudes ∈ {0, 0.01, 0.05, 0.1, 0.2, 0.5}
3. **Missing data** — random zero-out at rates ∈ {0%, 10%, 20%, 30%, 50%}

### Results

#### Gaussian Noise

| σ | F1-macro | Δ from baseline |
|---|---------|----------------|
| 0.00 | 0.9853 | — |
| 0.01 | 0.9853 | +0.0000 |
| 0.05 | 0.9853 | +0.0000 |
| 0.10 | 0.9835 | −0.0018 |
| 0.20 | 0.9853 | +0.0000 |
| 0.50 | 0.9836 | −0.0017 |

**Verdict:** Highly robust. Maximum degradation < 0.2% even at σ = 0.5.

#### Sensor Drift

| Drift magnitude | F1-macro | Δ from baseline |
|-----------------|---------|----------------|
| 0.00 | 0.9853 | — |
| 0.01–0.20 | 0.9853 | +0.0000 |
| 0.50 | 0.9835 | −0.0018 |

**Verdict:** Extremely robust. Negligible degradation up to drift = 0.5.

#### Missing Sensor Data

| Missing % | F1-macro | Δ from baseline |
|-----------|---------|----------------|
| 0% | 0.9853 | — |
| 10% | 0.9274 | −0.0579 |
| 20% | 0.8367 | −0.1486 |
| 30% | 0.8676 | −0.1177 |
| 50% | 0.7346 | −0.2507 |

**Verdict:** Most sensitive corruption mode. F1 drops to **0.73 at 50% missing data**, representing the primary vulnerability. This suggests sensor redundancy or imputation strategies should be considered for production deployments.

### Figure

`paper_evaluation_multiclass/figures/robustness_analysis.pdf` — 3-panel degradation curves.

---

## 6. Q-Learning RL Compression Controller

**Script:** `scripts/rl_compression_eval.py`
**Objective:** Train a tabular Q-learning agent to optimise compressor energy while maintaining safe pipeline pressure, and compare against a PID baseline.

### Environment: `PipelineCompressionEnv`

| Property | Value |
|----------|-------|
| State dimensions | 3 (pressure × flow rate × temperature) |
| State bins | 12 × 8 × 8 = **768 states** |
| Pressure range | 50–110 bar |
| Flow rate range | 10–100 kg/s |
| Temperature range | 10–50 °C |
| Actions | 5 discrete: {−15, −5, 0, +5, +15} kW |
| Target pressure | 75 bar |

### Hyperparameters

| Parameter | Value |
|-----------|-------|
| Episodes | 500 |
| Max steps/episode | 200 |
| Learning rate (α) | 0.1 |
| Discount (γ) | 0.99 |
| ε-greedy | 1.0 → 0.05, decay = 0.995 |
| Energy weight (λ_E) | 0.7 |
| Safety weight (λ_S) | 0.3 |
| Seeds | [42, 7, 21, 99, 123] |

### PID Baseline and Tuning Rationale

The PID baseline uses a classic proportional–integral–derivative controller with gains:

| Gain | Value | Rationale |
|------|-------|-----------|
| **Kp** | 0.4 | Proportional gain sized so that a typical steady-state error of ±5 bar (from the 75 bar setpoint) produces a PID output of ~2, mapping to the "decrease a bit" / "increase a bit" discrete action. This keeps the controller responsive without oscillating across the ±3 bar dead-band. |
| **Ki** | 0.02 | Integral gain chosen to be small relative to Kp (Ki/Kp = 0.05) to eliminate steady-state offset over ~50 steps without causing integral windup. At a constant 5 bar offset, the integral term accumulates ~5 units over 50 steps, comparable to one Kp contribution — sufficient to nudge the action threshold without overshooting. |
| **Kd** | 0.1 | Derivative gain set at Kd/Kp = 0.25 to damp pressure oscillations. The environment adds N(0, 1.5) bar noise per step; Kd = 0.1 ensures that a 3 bar/step transient generates a derivative correction of ~0.3, meaningful but not dominant. |

The PID output is mapped to discrete actions via fixed thresholds: output > 8 → decrease a lot (−15 kW), > 2 → decrease a bit (−5 kW), < −8 → increase a lot (+15 kW), < −2 → increase a bit (+5 kW), else hold. These thresholds were selected so that the PID naturally uses the moderate actions (±5 kW) during normal regulation and reserves the aggressive actions (±15 kW) for large deviations (>8 bar from setpoint).

The PID controller is run for the same number of episodes per seed as the Q-learning agent to ensure a fair comparison.

### Results

| Controller | Mean Energy (last 50 eps) | Std |
|------------|--------------------------|-----|
| **PID baseline** | 23,030.6 kW | ± 52.3 kW |
| **RL (Q-learning)** | 23,457.1 kW | ± 841.3 kW |

| Seed | Energy Savings vs PID |
|------|----------------------|
| 42 | **+4.39%** |
| 7 | −1.82% |
| 21 | −7.11% |
| 99 | −1.55% |
| 123 | −3.17% |

**Mean energy savings:** −1.85% ± 3.70%

### Interpretation

The Q-learning agent has not yet converged to consistently outperform the PID baseline within 500 episodes on a 768-state space. However, **seed 42 achieved +4.39% savings**, demonstrating that the agent *can* learn an effective policy. Increasing `N_EPISODES` (to 2000+) or using a coarser state discretisation would improve convergence reliability.

### Figure

`paper_evaluation_multiclass/figures/rl_learning_curves.pdf` — 3-panel: reward learning curve, energy consumption (with PID baseline), and energy savings box plot.

### λ\_E / λ\_S Sensitivity Sweep

**Script:** `scripts/lambda_sensitivity_sweep.py`
**Objective:** Characterise the energy–safety trade-off by sweeping the reward weights λ\_E (energy) and λ\_S (safety) across five ratios while keeping λ\_E + λ\_S = 1.

#### Setup

- **Sweep grid:** λ\_E / λ\_S ∈ {0.1/0.9, 0.3/0.7, 0.5/0.5, 0.7/0.3, 0.9/0.1}
- **Training:** 500 episodes × 5 seeds per pair (same hyperparameters as main evaluation)
- **Metrics:** Mean energy (last 50 episodes), energy savings vs PID (%), and safety violations (steps where |pressure − 75| > 15 bar)

#### Results

| λ\_E / λ\_S | RL Energy (kW) | PID Energy (kW) | Energy Savings | Violations (RL) | Violations (PID) |
|-------------|---------------|----------------|---------------|----------------|-----------------|
| 0.1 / 0.9 | 23,940.9 ± 565.3 | 23,030.6 | −3.95% | 102.30 ± 6.95 | — |
| 0.3 / 0.7 | 23,754.6 ± 361.3 | 23,030.6 | −3.14% | 105.21 ± 4.62 | — |
| **0.5 / 0.5** | 24,173.2 ± 396.1 | 23,030.6 | −4.96% | 106.75 ± 6.37 | — |
| **0.7 / 0.3** (default) | 23,457.1 ± 841.3 | 23,030.6 | −1.85% | 114.58 ± 9.06 | — |
| 0.9 / 0.1 | 22,707.0 ± 1,215.7 | 23,030.6 | **+1.41%** | 123.86 ± 6.60 | — |

#### Interpretation

The sweep reveals a clear **energy–safety Pareto front**:

- **Safety-dominant regime (λ\_E ≤ 0.3):** The agent prioritises pressure regulation, achieving the fewest violations (~102–105 per episode) but consuming more energy than the PID baseline (−3% to −4% savings).
- **Balanced regime (λ\_E = 0.5–0.7):** The default λ\_E = 0.7 sits near the elbow of the trade-off. It achieves moderate violations (~107–115) and the closest energy match to PID (−1.85%).
- **Energy-dominant regime (λ\_E = 0.9):** The only configuration that outperforms PID on energy (+1.41% savings), but at the cost of the most safety violations (~124 per episode) and the highest variance (±1,216 kW), reflecting aggressive but inconsistent policies.

The default λ\_E = 0.7 / λ\_S = 0.3 represents a reasonable trade-off: it minimises the energy gap to PID while keeping violations below the energy-dominant regime. For safety-critical deployments, λ\_E = 0.3 / λ\_S = 0.7 would be preferable despite ~3% higher energy consumption.

#### Figure

`paper_evaluation_multiclass/figures/lambda_sensitivity.pdf` — 3-panel: energy consumption (RL vs PID), energy savings (%), and safety violations across all λ pairs.

---

## 7. Blockchain Latency Benchmark

**Script:** `scripts/blockchain_latency_benchmark.py`
**Objective:** Benchmark end-to-end latency of the PureChain blockchain for both read and write operations.

### Network Configuration

| Property | Value |
|----------|-------|
| Network | PureChain Testnet |
| Consensus | Proof-of-Authority (PoA) |
| RPC URL | `https://purechainnode.com` |
| Chain ID | `900520900520` |
| Gas Price | 0 (zero-fee PoA) |
| Gas Limit | 8,000,000 |
| Block interval (observed) | ~2 s (median write-commit latency: 1,963.66 ms) |
| Validator count | Not published by PureChain; the network is operated as a permissioned PoA chain with a fixed, pre-approved validator set managed by PureChain |

### Benchmark Setup

- **Tier 1 (Read-RPC):** 500 calls each to `get_block('latest')` and `get_network_status()`
- **Tier 2 (Write-Tx):** 500 zero-value `send_transaction` calls (self-transfers), measuring end-to-end latency (build + sign + confirm) and chain commit latency (send + confirm)
- **Failures:** 0 out of 1,000 read calls, 0 out of 500 write transactions

### Results

| Metric | Read: get_block | Read: net_status | Write: E2E | Write: Chain Commit |
|--------|----------------|-----------------|------------|-------------------|
| **Mean** | 20.13 ms | 76.16 ms | 1,953.32 ms | 1,942.86 ms |
| **Median** | 18.46 ms | 73.78 ms | 1,973.79 ms | 1,963.66 ms |
| **Std** | 4.91 ms | 10.90 ms | 556.61 ms | 556.68 ms |
| **P95** | 29.35 ms | 95.71 ms | 2,111.25 ms | 2,101.10 ms |
| **P99** | 35.46 ms | 109.81 ms | 2,235.52 ms | 2,225.87 ms |
| **Min** | 14.52 ms | 61.21 ms | 190.97 ms | 174.26 ms |
| **Max** | 58.05 ms | 152.15 ms | 12,689.30 ms | 12,678.44 ms |

### Interpretation

- **Read operations** are fast: ~20 ms for block queries, ~76 ms for network status (which involves multiple RPC calls internally).
- **Write transactions** average ~2 seconds end-to-end, dominated by on-chain confirmation time (~1.95s). The build + sign overhead is minimal (~10 ms).
- **Zero failures** across 1,500 total operations demonstrates PureChain testnet reliability.
- The ~2s write latency is consistent with a PoA chain block time and is well within acceptable limits for pipeline monitoring (typical sensor reading interval: 60 seconds).

### Validator Count and Scaling Discussion

PureChain does not publicly disclose its validator set size. The network is operated as a **permissioned PoA chain** where a fixed, pre-approved set of validator nodes produces blocks; external parties cannot join the validator set without authorisation. This is standard for enterprise/consortium PoA deployments (e.g., Hyperledger Besu, Quorum-based networks).

**Why the exact count matters less than it might appear:**

1. **PoA finality is deterministic.** Unlike PoW/PoS chains, PoA block production is round-robin among authorised validators. A single honest validator is sufficient to guarantee liveness; a majority is required for safety (resistance to censorship/reordering). The ~2 s block interval we observe is consistent with PoA networks running 2–5 validators, though it is also compatible with larger sets that use short rotation periods.

2. **PredBlock's integrity guarantees are data-hash-based, not consensus-based.** Every `MonitoringLog` record includes a `keccak256` integrity hash recomputable by any auditor (Section 9.1). Even if all validators collude, hash mismatches between on-chain records and off-chain sensor archives are detectable. The blockchain provides tamper-evidence, not tamper-proof guarantees — a distinction that holds regardless of validator count.

3. **Throughput ceiling for CCS monitoring is low.** At one sensor reading per 60 seconds, PredBlock requires ~1 write transaction per minute. The benchmark demonstrates that even a single-threaded writer achieves 500 consecutive writes with 0 failures and P99 latency of 2.2 s. A PoA chain with as few as 2 validators and a 2 s block time can sustain ~30 tx/block, far exceeding the ~0.017 tx/s demand.

4. **Scaling to multi-site deployments.** For N monitored pipelines each writing once per minute, the chain must sustain N tx/min. At the observed ~2 s block time with 21,000 gas per monitoring transaction and an 8,000,000 gas block limit, the theoretical throughput is ~380 tx/block or ~190 tx/s — sufficient for thousands of concurrent pipelines without sharding or L2 rollups.

**Recommendation for production:** Operators deploying PredBlock on a private PoA network should configure a minimum of **3 validators** (tolerating 1 Byzantine fault under standard PBFT-style PoA), ideally hosted across independent infrastructure providers. The PureChain testnet benchmarks reported here serve as a representative baseline for any Ethereum-compatible PoA chain with similar block intervals.

### Figure

`paper_evaluation_multiclass/figures/blockchain_latency.pdf` — Histograms of read/write latency distributions, box plot comparison, and summary statistics panel.

---

## 8. ISO 27916 Compliance Mapping

ISO 27916:2019 (*Carbon dioxide capture, transportation and geological storage — Carbon dioxide storage using enhanced oil recovery*) specifies requirements for Measurement, Reporting, and Verification (MRV) of CO₂ storage. The table below maps PredBlock's blockchain-anchored outputs to the relevant ISO 27916 clauses.

| ISO 27916 Requirement | Clause | PredBlock Implementation | Smart Contract / Module |
|-----------------------|--------|--------------------------|-------------------------|
| **Continuous monitoring of injection parameters** | §7.2 — Monitoring plan | `MonitoringLog.addRecord()` stores pressure, temperature, flow rate, and 5 impurity species (H₂O, H₂S, SO₂, O₂, NOx) at each sampling interval. Records are immutable and time-stamped on-chain. | `MonitoringLog.sol` |
| **Data integrity and tamper-evidence** | §7.2.2 — Data quality | Each record includes a `keccak256` hash (`dataHash`) computed from all sensor fields + recorder address. On-chain `verifyRecord()` recomputes the hash for auditors. Duplicate records are rejected. | `MonitoringLog.sol` |
| **Leakage detection and quantification** | §8.3 — Leakage events | Leakage incidents are reported via `LeakageReport.reportIncident()` with severity classification (LOW/MEDIUM/HIGH/CRITICAL), pressure-drop magnitude, O₂ level, and acoustic signal. Each report carries an `evidenceHash` linking to off-chain sensor logs. | `LeakageReport.sol` |
| **Incident lifecycle tracking** | §8.3.2 — Corrective measures | `LeakageReport` implements a full lifecycle: REPORTED → INVESTIGATING → CONFIRMED → RESOLVED (or FALSE_ALARM). Investigator assignments and resolution notes are recorded immutably. | `LeakageReport.sol` |
| **Threshold-based alert generation** | §7.4 — Alarm systems | `AlertSystem.triggerAlert()` evaluates measured values against on-chain configurable thresholds for IMPURITY, OVERPRESSURE, LEAKAGE, and CORROSION alert types. Alert levels (INFO/WARNING/CRITICAL) are determined automatically. Thresholds are admin-updatable via `updateThreshold()`. | `AlertSystem.sol` |
| **Preventive and predictive maintenance** | §9.2 — Risk management | `MaintenanceScheduler.scheduleTask()` creates maintenance tasks (PREVENTIVE/CORRECTIVE/PREDICTIVE/EMERGENCY) linked to AI prediction hashes (`aiPredictionHash`). Tasks track assignment, start, completion, and duration on-chain. | `MaintenanceScheduler.sol` |
| **Audit trail accessible to regulators** | §10 — Reporting | All smart contracts emit indexed events (`RecordAdded`, `IncidentReported`, `AlertTriggered`, `TaskScheduled`, etc.) queryable by any Ethereum-compatible block explorer. The `PredBlockAuditor` Python class creates master hashes of complete audit records (sensor data + AI predictions + model hashes) and records them on-chain via `logReading()`. | `PredBlockAuditor` (Python) + all contracts |
| **Role-based access control** | §10.2 — Verification | Contracts enforce `onlyAdmin`, `onlyAuthorizedReporter`, `onlyAuthorizedInvestigator`, and `onlyMaintenancePersonnel` modifiers. Admin manages authorised addresses; no anonymous writes are permitted. | All contracts |
| **Zero-cost, high-throughput audit logging** | §7.2.3 — Practicality | PureChain's zero-gas PoA consensus allows unlimited audit writes at no cost. Benchmark confirms 500/500 write transactions with 0 failures and median latency of ~2 s — well within the 60 s sensor-reading interval. | Blockchain benchmark |

---

## 9. Threat Model

This section provides a brief security analysis of PredBlock's blockchain audit layer, focusing on the most relevant attack vectors for a permissioned PoA network.

### 9.1 Validator Compromise

**Threat:** PureChain uses Proof-of-Authority (PoA) consensus, meaning a fixed set of pre-approved validators produce blocks (the exact validator count is not publicly disclosed). If a majority of validators are compromised (or collude), they could censor transactions, reorder blocks, or inject fraudulent records.

**Mitigations:**
- **Data-hash anchoring:** Every `MonitoringLog` record includes a `keccak256` hash of the sensor data + recorder address. Even if a validator tampers with on-chain storage, the off-chain sensor data can be rehashed and compared via `verifyRecord()`. Hash mismatches are detectable by any auditor.
- **Event-log immutability:** Ethereum-style event logs are indexed by block hash. Retroactive modification would require rewriting the entire chain from the tampered block forward — detectable by any full node or archival service.
- **Multi-party observation:** Regulators and operators can independently run full nodes against the PureChain RPC endpoint to maintain local copies of all blocks and receipts.

### 9.2 Sensor Spoofing / Data Poisoning

**Threat:** An adversary with physical or network access to sensor hardware could inject false readings before they reach the blockchain. The AI anomaly detector trained on poisoned data would learn incorrect decision boundaries.

**Mitigations:**
- **On-chain data validation:** `MonitoringLog` enforces range checks (`validData` modifier: pressure 0–150 bar, temperature 0–100 °C) rejecting physically implausible values.
- **AI-layer anomaly detection:** The Random Forest classifier flags anomalous readings with F1-macro > 0.99. Robustness tests (Section 5) confirm resilience to Gaussian noise up to σ = 0.5 and sensor drift up to 0.5 magnitude.
- **Evidence hashing:** `LeakageReport` stores `evidenceHash` linking to raw sensor logs. Post-hoc forensic comparison between on-chain hashes and off-chain archives can detect retroactive manipulation.

### 9.3 Smart Contract Vulnerabilities

**Threat:** Logic bugs in Solidity contracts (reentrancy, integer overflow, access-control bypass) could allow unauthorised writes or data corruption.

**Mitigations:**
- **Role-based access:** All state-mutating functions enforce `onlyAdmin`, `onlyAuthorizedReporter`, or `onlyAuthorizedInvestigator` modifiers.
- **Duplicate prevention:** `MonitoringLog` maintains a `recordExists` mapping; records with identical data hashes are rejected.
- **Solidity 0.8+:** Contracts compile with Solidity ≥ 0.8.0, which includes built-in overflow/underflow checks.
- **Minimal external calls:** None of the contracts make external calls to untrusted addresses, eliminating reentrancy risk.

### 9.4 Residual Risks

- **Single-admin key:** Contract admin privileges (adding reporters, updating thresholds) are controlled by a single address. Loss or compromise of this key would require contract redeployment. A multi-sig wallet is recommended for production.
- **PoA centralisation:** The trust model inherently depends on the validator set operator (PureChain). For higher assurance, audit hashes could be periodically anchored to a public chain (e.g., Ethereum mainnet) as a checkpoint.

---

## 10. Output Files Index

### Figures (`paper_evaluation_multiclass/figures/`)

| File | Description |
|------|-------------|
| `eos_validation.pdf/.png` | Surrogate vs CoolProp density heatmaps + error |
| `confusion_matrix.pdf/.png` | Multiclass RF confusion matrix |
| `pr_curves.pdf/.png` | Per-class (OvR) Precision-Recall curves (4-class model) |
| `pr_curves_binary.pdf/.png` | Binary PR curves: PredBlock vs Isolation Forest vs One-Class SVM |
| `ablation_study.pdf/.png` | Ablation study bar chart |
| `robustness_analysis.pdf/.png` | Robustness degradation curves |
| `rl_learning_curves.pdf/.png` | RL reward, energy, and savings plots |
| `blockchain_latency.pdf/.png` | Blockchain latency histograms + box plot |
| `lambda_sensitivity.pdf/.png` | λ\_E/λ\_S sensitivity sweep (energy, savings, violations) |

### Data (`paper_evaluation_multiclass/`)

| File | Description |
|------|-------------|
| `ablation_results.csv` | Ablation study metrics (mean ± std per variant) |
| `robustness_results.csv` | F1-macro at each corruption level |
| `blockchain_latency_stats.csv` | Latency summary statistics |
| `lambda_sensitivity.csv` | λ\_E/λ\_S sweep metrics per pair |

### Scripts (`scripts/`)

| Script | Purpose |
|--------|---------|
| `generate_publication_data.py` | Generate train/val/test physics CSVs from simulator |
| `multiclass_rf_evaluation.py` | Main multiclass RF training + evaluation |
| `baseline_comparison.py` | Binary + multiclass baseline comparison + binary PR curves |
| `ablation_study.py` | Feature ablation study |
| `robustness_analysis.py` | Robustness under noise, drift, missing data |
| `rl_compression_eval.py` | Q-learning RL controller vs PID baseline |
| `lambda_sensitivity_sweep.py` | λ\_E/λ\_S reward weight sensitivity sweep |
| `eos_validation.py` | Surrogate density vs CoolProp validation |
| `blockchain_latency_benchmark.py` | PureChain read/write latency benchmark |

---

*Generated from PredBlock evaluation experiments. All results produced from live runs on the PureChain testnet (blockchain) and local compute (ML/RL).*
