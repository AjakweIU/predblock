"""
Robustness Analysis: PredBlock Anomaly Detector
=================================================
Tests the trained Random Forest classifier under three corruption modes:
  1. Gaussian noise at increasing sigma levels
  2. Linear sensor drift over time
  3. Missing sensor data (random zero-out)

Reports F1-macro degradation for each corruption level and plots curves.
Uses the same data pipeline and time-based split as the main evaluation.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import f1_score
from loguru import logger

from multiclass_rf_evaluation import (
    load_and_combine_data, time_based_split,
    derive_multiclass_label, FEATURE_COLS, CLASSES
)

# ── Configuration ─────────────────────────────────────────────────────────
SEED         = 42
MAX_TRAIN    = 15000          # subsample to avoid memory issues
OUTPUT_DIR   = os.path.join(os.path.dirname(__file__), '..', 'paper_evaluation_multiclass')

NOISE_LEVELS    = [0.0, 0.01, 0.05, 0.1, 0.2, 0.5]
DRIFT_MAGNITUDES = [0.0, 0.01, 0.05, 0.1, 0.2, 0.5]
MISSING_RATES   = [0.0, 0.10, 0.20, 0.30, 0.50]


# ── Helpers ───────────────────────────────────────────────────────────────
def get_feature_cols(df: pd.DataFrame) -> list:
    """Return available feature columns from the dataset."""
    cols = list(FEATURE_COLS)
    for extra in ('acoustic', 'vibration', 'acoustic_emission'):
        if extra in df.columns and extra not in cols:
            cols.append(extra)
    return cols


def subsample_stratified(df: pd.DataFrame, labels: np.ndarray,
                         max_n: int, seed: int) -> pd.DataFrame:
    """Stratified subsample to keep memory manageable."""
    if len(df) <= max_n:
        return df
    rng = np.random.RandomState(seed)
    idx_all = []
    for c in np.unique(labels):
        c_idx = np.where(labels == c)[0]
        frac = len(c_idx) / len(labels)
        n_keep = max(int(max_n * frac), min(len(c_idx), 10))
        chosen = rng.choice(c_idx, size=min(n_keep, len(c_idx)), replace=False)
        idx_all.append(chosen)
    idx_all = np.concatenate(idx_all)
    rng.shuffle(idx_all)
    return df.iloc[idx_all].reset_index(drop=True)


# ── Main ──────────────────────────────────────────────────────────────────
def main():
    os.makedirs(os.path.join(OUTPUT_DIR, 'figures'), exist_ok=True)

    # ── Load data & split ──────────────────────────────────────────────
    logger.info("Loading data...")
    df = load_and_combine_data()
    train_df, _, test_df = time_based_split(df)

    feat_cols = get_feature_cols(train_df)
    logger.info(f"Feature columns ({len(feat_cols)}): {feat_cols}")

    y_train = derive_multiclass_label(train_df)
    y_test  = derive_multiclass_label(test_df)

    # Subsample training data
    train_df = subsample_stratified(train_df, y_train, MAX_TRAIN, SEED)
    y_train  = derive_multiclass_label(train_df)

    X_train = train_df[feat_cols].values.astype(float)
    X_test  = test_df[feat_cols].values.astype(float)

    logger.info(f"Train: {X_train.shape[0]} samples | Test: {X_test.shape[0]} samples")

    # ── Train best model ───────────────────────────────────────────────
    logger.info("Training Random Forest (clf_best)...")
    clf_best = RandomForestClassifier(
        n_estimators=50,
        max_depth=20,
        random_state=SEED,
        class_weight='balanced',
        n_jobs=1,
    )
    clf_best.fit(X_train, y_train)

    baseline_f1 = f1_score(y_test, clf_best.predict(X_test), average='macro')
    logger.info(f"Baseline F1-macro on clean test set: {baseline_f1:.4f}")

    rng = np.random.RandomState(SEED)

    # ── 1. Gaussian Noise Robustness ───────────────────────────────────
    logger.info("Running Gaussian noise robustness test...")
    noise_f1 = []
    for sigma in NOISE_LEVELS:
        X_noisy = X_test + rng.normal(0, sigma, X_test.shape)
        y_pred  = clf_best.predict(X_noisy)
        noise_f1.append(f1_score(y_test, y_pred, average='macro'))

    # ── 2. Sensor Drift Robustness ─────────────────────────────────────
    logger.info("Running sensor drift robustness test...")
    drift_f1 = []
    for drift_rate in DRIFT_MAGNITUDES:
        X_drifted = X_test.copy()
        n_samples = X_test.shape[0]
        drift_vec = np.linspace(0, drift_rate, n_samples).reshape(-1, 1)
        X_drifted = X_drifted + drift_vec  # linear drift over time
        y_pred = clf_best.predict(X_drifted)
        drift_f1.append(f1_score(y_test, y_pred, average='macro'))

    # ── 3. Missing Sensor Data Robustness ──────────────────────────────
    logger.info("Running missing sensor data robustness test...")
    missing_f1 = []
    for miss_rate in MISSING_RATES:
        X_missing = X_test.copy()
        mask = rng.rand(*X_missing.shape) < miss_rate
        X_missing[mask] = 0.0  # zero-imputation for missing values
        y_pred = clf_best.predict(X_missing)
        missing_f1.append(f1_score(y_test, y_pred, average='macro'))

    # ── Print summary ──────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  PredBlock Anomaly Detector — Robustness Results")
    print("=" * 60)

    print("\n  Gaussian Noise (sigma → F1-macro):")
    for s, f in zip(NOISE_LEVELS, noise_f1):
        delta = f - baseline_f1
        print(f"    σ = {s:<6.2f}  F1 = {f:.4f}  (Δ = {delta:+.4f})")

    print("\n  Sensor Drift (magnitude → F1-macro):")
    for d, f in zip(DRIFT_MAGNITUDES, drift_f1):
        delta = f - baseline_f1
        print(f"    drift = {d:<6.2f}  F1 = {f:.4f}  (Δ = {delta:+.4f})")

    print("\n  Missing Sensors (rate → F1-macro):")
    for m, f in zip(MISSING_RATES, missing_f1):
        delta = f - baseline_f1
        print(f"    missing = {int(m*100):>3}%    F1 = {f:.4f}  (Δ = {delta:+.4f})")

    # ── Export CSV ─────────────────────────────────────────────────────
    rows = []
    for s, f in zip(NOISE_LEVELS, noise_f1):
        rows.append({'corruption': 'gaussian_noise', 'level': s, 'f1_macro': f})
    for d, f in zip(DRIFT_MAGNITUDES, drift_f1):
        rows.append({'corruption': 'sensor_drift', 'level': d, 'f1_macro': f})
    for m, f in zip(MISSING_RATES, missing_f1):
        rows.append({'corruption': 'missing_data', 'level': m, 'f1_macro': f})

    csv_path = os.path.join(OUTPUT_DIR, 'robustness_results.csv')
    pd.DataFrame(rows).to_csv(csv_path, index=False)
    logger.info(f"Results saved → {csv_path}")

    # ── Plot ───────────────────────────────────────────────────────────
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    # Noise
    axes[0].plot(NOISE_LEVELS, noise_f1, 'o-', color='#2196F3', linewidth=2, markersize=7)
    axes[0].axhline(baseline_f1, color='gray', linestyle='--', alpha=0.5, label='Baseline')
    axes[0].set_xlabel('Gaussian Noise Std (σ)', fontsize=11)
    axes[0].set_ylabel('F1-macro', fontsize=11)
    axes[0].set_title('Robustness to Sensor Noise', fontsize=12)
    axes[0].set_ylim(0, 1.05)
    axes[0].legend(fontsize=9)
    axes[0].grid(True, alpha=0.3)

    # Drift
    axes[1].plot(DRIFT_MAGNITUDES, drift_f1, 's-', color='#FF9800', linewidth=2, markersize=7)
    axes[1].axhline(baseline_f1, color='gray', linestyle='--', alpha=0.5, label='Baseline')
    axes[1].set_xlabel('Drift Magnitude', fontsize=11)
    axes[1].set_ylabel('F1-macro', fontsize=11)
    axes[1].set_title('Robustness to Sensor Drift', fontsize=12)
    axes[1].set_ylim(0, 1.05)
    axes[1].legend(fontsize=9)
    axes[1].grid(True, alpha=0.3)

    # Missing
    pct_labels = [int(m * 100) for m in MISSING_RATES]
    axes[2].plot(pct_labels, missing_f1, '^-', color='#F44336', linewidth=2, markersize=7)
    axes[2].axhline(baseline_f1, color='gray', linestyle='--', alpha=0.5, label='Baseline')
    axes[2].set_xlabel('Missing Sensor Data (%)', fontsize=11)
    axes[2].set_ylabel('F1-macro', fontsize=11)
    axes[2].set_title('Robustness to Missing Sensors', fontsize=12)
    axes[2].set_ylim(0, 1.05)
    axes[2].legend(fontsize=9)
    axes[2].grid(True, alpha=0.3)

    fig.suptitle('PredBlock Anomaly Detector — Robustness Analysis', fontsize=13,
                 fontweight='bold')
    plt.tight_layout()

    for ext in ('pdf', 'png'):
        path = os.path.join(OUTPUT_DIR, 'figures', f'robustness_analysis.{ext}')
        fig.savefig(path, dpi=300, bbox_inches='tight')
    plt.close(fig)
    logger.info(f"Plot saved → {os.path.join(OUTPUT_DIR, 'figures', 'robustness_analysis.pdf')}")

    print("\n" + "=" * 60)
    print(f"  Done.  Outputs in: {OUTPUT_DIR}")
    print("=" * 60)


if __name__ == '__main__':
    main()
