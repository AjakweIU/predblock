"""
Baseline Comparison: PredBlock RF vs Threshold / Isolation Forest / One-Class SVM
==================================================================================
Compares F1-macro for PredBlock (multiclass RF, 4-class, seed 42) against
three unsupervised/heuristic baselines on the same time-based test split.

Baselines are binary (normal vs anomaly) detectors.  To compute a comparable
F1-macro we treat their predictions as 2-class (normal=0, anomaly=1) and
evaluate against a binarised ground truth (0 = normal, 1 = any anomaly).
PredBlock is evaluated on the full 4-class task (macro F1 over normal,
leakage, corrosion, overpressure).

Produces updated bar chart: baseline_comparison.png / .pdf
"""

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.svm import OneClassSVM
from sklearn.metrics import f1_score
from loguru import logger

from multiclass_rf_evaluation import (
    load_and_combine_data, time_based_split,
    derive_multiclass_label, prepare_features, CLASSES
)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'paper_evaluation_multiclass')
FIG_DIR    = os.path.join(OUTPUT_DIR, 'figures')


def main():
    os.makedirs(FIG_DIR, exist_ok=True)

    # ── Load data & split (same pipeline as main evaluation) ─────────────
    df = load_and_combine_data()
    train_df, _, test_df = time_based_split(df)

    y_train_mc = derive_multiclass_label(train_df)
    y_test_mc  = derive_multiclass_label(test_df)

    X_train = prepare_features(train_df)
    X_test  = prepare_features(test_df)

    # Binary labels for baselines: 0 = normal, 1 = any anomaly
    y_test_bin = (y_test_mc > 0).astype(int)

    # ── PredBlock (multiclass RF, seed 42) — full 4-class F1-macro ──────
    logger.info("Training PredBlock RF (seed 42)...")
    clf = RandomForestClassifier(
        n_estimators=100, max_depth=None, random_state=42,
        class_weight='balanced', n_jobs=-1
    )
    clf.fit(X_train, y_train_mc)
    y_pred_mc = clf.predict(X_test)
    f1_predblock = f1_score(y_test_mc, y_pred_mc, average='macro', zero_division=0)
    logger.info(f"PredBlock F1-macro (4-class) = {f1_predblock:.4f}")

    # ── Baseline 1: Threshold (O2 > 95th percentile) ────────────────────
    logger.info("Running Threshold baseline...")
    o2_col_idx = 6  # O2 is the 7th feature column
    o2_values = X_test[:, o2_col_idx]
    threshold = np.percentile(o2_values, 95)
    y_pred_thresh = (o2_values > threshold).astype(int)
    f1_thresh = f1_score(y_test_bin, y_pred_thresh, average='macro', zero_division=0)
    logger.info(f"Threshold F1-macro (binary) = {f1_thresh:.4f}")

    # ── Baseline 2: Isolation Forest ─────────────────────────────────────
    logger.info("Running Isolation Forest baseline...")
    iso = IsolationForest(contamination=0.05, random_state=42, n_jobs=-1)
    iso.fit(X_train)
    y_pred_iso = (iso.predict(X_test) == -1).astype(int)
    f1_iso = f1_score(y_test_bin, y_pred_iso, average='macro', zero_division=0)
    logger.info(f"Isolation Forest F1-macro (binary) = {f1_iso:.4f}")

    # ── Baseline 3: One-Class SVM ────────────────────────────────────────
    logger.info("Running One-Class SVM baseline...")
    rng = np.random.RandomState(42)
    n_sub = min(10000, len(X_train))
    idx_sub = rng.choice(len(X_train), size=n_sub, replace=False)
    svm = OneClassSVM(nu=0.05)
    svm.fit(X_train[idx_sub])
    y_pred_svm = (svm.predict(X_test) == -1).astype(int)
    f1_svm = f1_score(y_test_bin, y_pred_svm, average='macro', zero_division=0)
    logger.info(f"One-Class SVM F1-macro (binary) = {f1_svm:.4f}")

    # ── Summary ──────────────────────────────────────────────────────────
    methods   = ['PredBlock\n(4-class RF)', 'Threshold', 'Isolation\nForest', 'One-Class\nSVM']
    f1_scores = [f1_predblock, f1_thresh, f1_iso, f1_svm]

    print("\n" + "=" * 60)
    print("  Anomaly Detection: F1-macro Comparison")
    print("=" * 60)
    for m, s in zip(methods, f1_scores):
        print(f"  {m.replace(chr(10), ' '):25s}: {s:.4f}")

    # ── Plot ─────────────────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(10, 6))
    colors = ['#2ecc71'] + ['#95a5a6'] * 3
    bars = ax.bar(range(len(methods)), f1_scores, color=colors, alpha=0.8,
                  edgecolor='white', linewidth=0.5, width=0.6)

    ax.set_ylabel('F1-macro', fontsize=12)
    ax.set_title('Anomaly Detection: PredBlock vs Baselines', fontsize=13,
                 fontweight='bold')
    ax.set_ylim(0, 1.1)
    ax.set_xticks(range(len(methods)))
    ax.set_xticklabels(methods, fontsize=10, ha='center')
    ax.grid(True, alpha=0.3, axis='y')

    for bar, score in zip(bars, f1_scores):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2., height + 0.01,
                f'{score:.3f}', ha='center', va='bottom',
                fontweight='bold', fontsize=11)

    plt.tight_layout()

    for ext in ('pdf', 'png'):
        path = os.path.join(FIG_DIR, f'baseline_comparison.{ext}')
        fig.savefig(path, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"\n  Saved -> {os.path.join(FIG_DIR, 'baseline_comparison.png')}")
    print("=" * 60)


if __name__ == '__main__':
    main()
