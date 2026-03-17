"""
Ablation Study: Contribution of Physics-Informed Features
==========================================================
Compares 4 model variants across 5 random seeds:
  A) Full model — all features
  B) Without corrosion_depth (corrosion-risk proxy)
  C) Without physics/thermodynamic features (density + corrosion_depth)
  D) Baseline — raw sensor readings only

Metrics: F1-macro, PR-AUC (macro), AUC-ROC (macro)
Uses the same time-based 70/15/15 split as the main evaluation.
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
from sklearn.metrics import f1_score, roc_auc_score, average_precision_score
from sklearn.preprocessing import label_binarize
from sklearn.utils import resample as sklearn_resample
from loguru import logger

# Reuse data helpers from the main evaluation script
from multiclass_rf_evaluation import (
    load_and_combine_data, time_based_split,
    derive_multiclass_label, CLASSES, N_CLASSES
)

# ── Configuration ──────────────────────────────────────────────────────────
SEEDS = [42, 7, 21, 99, 123]
METRICS = ['f1_macro', 'pr_auc', 'auc_roc']
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'paper_evaluation_multiclass')

# ── Feature groups (mapped to actual dataset columns) ──────────────────────
RAW_SENSOR_FEATURES = [
    'pressure', 'temperature', 'flow_rate',
    'H2O', 'H2S', 'SO2', 'O2',
    'NOx', 'N2', 'CH4',
    'acoustic_emission', 'vibration',
]

PHYSICS_THERMO_FEATURES = [
    'density',           # CO2Properties.density() — Span-Wagner surrogate
]

CORROSION_DERIVED_FEATURES = [
    'corrosion_depth',   # cumulative corrosion from CorrosionKinetics
]

ALL_FEATURES = RAW_SENSOR_FEATURES + PHYSICS_THERMO_FEATURES + CORROSION_DERIVED_FEATURES

VARIANTS = {
    'A_Full_Model': ALL_FEATURES,
    'B_No_Corrosion_Depth': [f for f in ALL_FEATURES
                             if f not in CORROSION_DERIVED_FEATURES],
    'C_No_Physics_Features': [f for f in ALL_FEATURES
                              if f not in PHYSICS_THERMO_FEATURES + CORROSION_DERIVED_FEATURES],
    'D_Raw_Sensors_Only': RAW_SENSOR_FEATURES,
}


# ── Evaluation ─────────────────────────────────────────────────────────────
def _subsample(train_df, max_n=15000, seed=42):
    """Stratified subsample to keep memory usage manageable."""
    if len(train_df) <= max_n:
        return train_df
    labels = derive_multiclass_label(train_df)
    rng = np.random.RandomState(seed)
    idx_all = []
    for c in range(N_CLASSES):
        c_idx = np.where(labels == c)[0]
        frac = len(c_idx) / len(labels)
        n_keep = max(int(max_n * frac), min(len(c_idx), 10))
        chosen = rng.choice(c_idx, size=min(n_keep, len(c_idx)), replace=False)
        idx_all.append(chosen)
    idx_all = np.concatenate(idx_all)
    rng.shuffle(idx_all)
    return train_df.iloc[idx_all].reset_index(drop=True)


def run_ablation(train_df, test_df):
    """Run all ablation variants across 5 seeds."""

    # Subsample training data to avoid memory errors on constrained machines
    train_df = _subsample(train_df, max_n=15000)
    logger.info(f"Ablation training on {len(train_df)} samples (subsampled)")

    y_train = derive_multiclass_label(train_df)
    y_test  = derive_multiclass_label(test_df)

    ablation_results = {v: {m: [] for m in METRICS} for v in VARIANTS}

    for variant_name, feat_cols in VARIANTS.items():
        # Verify all columns exist
        missing = [c for c in feat_cols if c not in train_df.columns]
        if missing:
            logger.warning(f"{variant_name}: missing columns {missing}, skipping")
            continue

        X_train = train_df[feat_cols].values
        X_test  = test_df[feat_cols].values

        for seed in SEEDS:
            clf = RandomForestClassifier(
                n_estimators=50,
                max_depth=20,
                random_state=seed,
                class_weight='balanced',
                n_jobs=1,
            )
            clf.fit(X_train, y_train)
            y_pred = clf.predict(X_test)
            y_prob = clf.predict_proba(X_test)

            # Align probabilities to all N_CLASSES columns
            prob_aligned = np.zeros((len(y_test), N_CLASSES))
            for idx, cls_label in enumerate(clf.classes_):
                prob_aligned[:, cls_label] = y_prob[:, idx]

            y_bin = label_binarize(y_test, classes=list(range(N_CLASSES)))

            ablation_results[variant_name]['f1_macro'].append(
                f1_score(y_test, y_pred, average='macro', zero_division=0))
            ablation_results[variant_name]['auc_roc'].append(
                roc_auc_score(y_bin, prob_aligned, multi_class='ovr', average='macro'))
            ablation_results[variant_name]['pr_auc'].append(
                average_precision_score(y_bin, prob_aligned, average='macro'))

    return ablation_results


def print_summary(ablation_results):
    """Print and save a summary table."""
    rows = []
    for v in VARIANTS:
        row = {'Variant': v}
        for m in METRICS:
            vals = ablation_results[v][m]
            if vals:
                row[f'{m}_mean'] = np.mean(vals)
                row[f'{m}_std']  = np.std(vals)
            else:
                row[f'{m}_mean'] = np.nan
                row[f'{m}_std']  = np.nan
        rows.append(row)

    df_ablation = pd.DataFrame(rows)

    print("\n" + "=" * 80)
    print("  Ablation Study Results  (mean ± std over 5 seeds)")
    print("=" * 80)
    for _, r in df_ablation.iterrows():
        print(f"\n  {r['Variant']}:")
        for m in METRICS:
            print(f"    {m:12s}: {r[f'{m}_mean']:.4f} ± {r[f'{m}_std']:.4f}")

    csv_path = os.path.join(OUTPUT_DIR, 'ablation_results.csv')
    df_ablation.to_csv(csv_path, index=False)
    logger.info(f"Table saved → {csv_path}")
    return df_ablation


def plot_ablation(ablation_results):
    """Bar chart comparing all variants."""
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    colors = ['#2196F3', '#FF9800', '#F44336', '#9C27B0']
    variant_keys = list(VARIANTS.keys())
    labels = [v.replace('_', '\n', 1).replace('_', ' ') for v in variant_keys]

    for ax, metric in zip(axes, METRICS):
        means = [np.mean(ablation_results[v][metric]) for v in variant_keys]
        stds  = [np.std(ablation_results[v][metric])  for v in variant_keys]
        x = np.arange(len(variant_keys))
        bars = ax.bar(x, means, yerr=stds, capsize=5, color=colors, alpha=0.85,
                      width=0.6, edgecolor='white', linewidth=0.5)

        # Value labels on bars
        for bar, m, s in zip(bars, means, stds):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + s + 0.005,
                    f'{m:.4f}', ha='center', va='bottom', fontsize=8, fontweight='bold')

        ax.set_title(metric.replace('_', ' ').upper(), fontsize=11, fontweight='bold')
        ax.set_ylabel("Score")
        ymin = max(0, min(means) - 0.05)
        ax.set_ylim(ymin, 1.02)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=8, ha='center')
        ax.grid(axis='y', alpha=0.3)

    fig.suptitle("Ablation Study: Contribution of Physics-Informed Features",
                 fontsize=13, fontweight='bold')
    plt.tight_layout()

    os.makedirs(os.path.join(OUTPUT_DIR, 'figures'), exist_ok=True)
    for ext in ('pdf', 'png'):
        path = os.path.join(OUTPUT_DIR, 'figures', f'ablation_study.{ext}')
        fig.savefig(path, dpi=300, bbox_inches='tight')
    plt.close(fig)
    logger.info(f"Chart saved → {os.path.join(OUTPUT_DIR, 'figures', 'ablation_study.pdf')}")


# ── Main ───────────────────────────────────────────────────────────────────
def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Load data & time-based split (reuse from main evaluation)
    df = load_and_combine_data()
    train_df, val_df, test_df = time_based_split(df)

    # Print feature groups
    print("\n--- Feature Groups ---")
    print(f"  Raw sensors       ({len(RAW_SENSOR_FEATURES):2d}): {RAW_SENSOR_FEATURES}")
    print(f"  Physics/thermo    ({len(PHYSICS_THERMO_FEATURES):2d}): {PHYSICS_THERMO_FEATURES}")
    print(f"  Corrosion-derived ({len(CORROSION_DERIVED_FEATURES):2d}): {CORROSION_DERIVED_FEATURES}")
    print(f"  Total features    ({len(ALL_FEATURES):2d})")

    print("\n--- Ablation Variants ---")
    for v, cols in VARIANTS.items():
        print(f"  {v:30s}: {len(cols)} features")

    # Run ablation
    ablation_results = run_ablation(train_df, test_df)

    # Report
    print_summary(ablation_results)

    # Plot
    plot_ablation(ablation_results)

    print("\n" + "=" * 60)
    print("  Ablation study complete.  Outputs in:", OUTPUT_DIR)
    print("=" * 60)


if __name__ == "__main__":
    main()
