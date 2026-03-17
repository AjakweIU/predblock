"""
Multiclass Random Forest Anomaly Detection — Full Evaluation
=============================================================
1. Train & evaluate across 5 random seeds
2. Report mean ± std for F1, AUC-ROC, Precision, Recall (macro & per-class)
3. Bootstrapped 95% confidence intervals on the test set
4. Precision-Recall curves + PR-AUC per class
5. Confusion matrix on the held-out test set

Classes: ['normal', 'leakage', 'corrosion', 'overpressure']
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # non-interactive backend for saving figures
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    f1_score, roc_auc_score, precision_score, recall_score,
    confusion_matrix, ConfusionMatrixDisplay,
    precision_recall_curve, average_precision_score
)
from sklearn.utils import resample
from sklearn.preprocessing import label_binarize
from collections import Counter
from loguru import logger

# ── Configuration ──────────────────────────────────────────────────────────
SEEDS = [42, 7, 21, 99, 123]
CLASSES = ['normal', 'leakage', 'corrosion', 'overpressure']
N_CLASSES = len(CLASSES)
N_BOOTSTRAP = 1000
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'paper_evaluation_multiclass')

FEATURE_COLS = ['pressure', 'temperature', 'flow_rate', 'H2O', 'H2S', 'SO2', 'O2']


# ── Data helpers ───────────────────────────────────────────────────────────
def load_and_combine_data() -> pd.DataFrame:
    """Load train + test CSVs and combine into a single time-sorted DataFrame."""
    base = os.path.join(os.path.dirname(__file__), '..')
    train_data = pd.read_csv(os.path.join(base, 'data', 'train_physics.csv'))
    test_data  = pd.read_csv(os.path.join(base, 'data', 'test_physics.csv'))

    # Also include validation set if it exists
    val_path = os.path.join(base, 'data', 'val_physics.csv')
    if os.path.exists(val_path):
        val_data = pd.read_csv(val_path)
        df = pd.concat([train_data, val_data, test_data], ignore_index=True)
        logger.info(f"Combined train({len(train_data)}) + val({len(val_data)}) + test({len(test_data)}) = {len(df)}")
    else:
        df = pd.concat([train_data, test_data], ignore_index=True)
        logger.info(f"Combined train({len(train_data)}) + test({len(test_data)}) = {len(df)}")

    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp').reset_index(drop=True)
    return df


def time_based_split(df: pd.DataFrame, train_frac=0.70, val_frac=0.15):
    """
    Strict chronological train/validation/test split (70/15/15).
    No future data leaks into earlier splits.
    """
    n = len(df)
    train_end = int(n * train_frac)
    val_end   = int(n * (train_frac + val_frac))

    train_df = df.iloc[:train_end].copy()
    val_df   = df.iloc[train_end:val_end].copy()
    test_df  = df.iloc[val_end:].copy()

    # ── Assert no temporal overlap ─────────────────────────────────────
    assert train_df['timestamp'].max() < val_df['timestamp'].min(), \
        "LEAKAGE: train/val temporal overlap!"
    assert val_df['timestamp'].max() < test_df['timestamp'].min(), \
        "LEAKAGE: val/test temporal overlap!"

    # ── Derive multiclass labels for reporting ─────────────────────────
    for split_df in (train_df, val_df, test_df):
        split_df['anomaly_type'] = derive_multiclass_label(split_df)

    # ── Report ─────────────────────────────────────────────────────────
    print("\n" + "=" * 65)
    print("  Time-Based Split Summary  (70 / 15 / 15)")
    print("=" * 65)
    for name, split in [("Train", train_df), ("Validation", val_df), ("Test", test_df)]:
        dist = {CLASSES[k]: v for k, v in sorted(Counter(split['anomaly_type']).items())}
        print(f"\n  {name}: {len(split)} samples")
        print(f"    Period : {split['timestamp'].min()}  -->  {split['timestamp'].max()}")
        print(f"    Classes: {dist}")

    print("\n  ** No temporal leakage detected. Splits are clean. **")
    return train_df, val_df, test_df


def derive_multiclass_label(df: pd.DataFrame) -> np.ndarray:
    """
    Derive a single multiclass label from binary risk columns.
    Priority when multiple flags are set: leakage > corrosion > overpressure.
    0 = normal, 1 = leakage, 2 = corrosion, 3 = overpressure
    """
    labels = np.zeros(len(df), dtype=int)  # default: normal (0)
    labels[df['overpressure_risk'].values == 1] = 3
    labels[df['corrosion_risk'].values == 1]    = 2
    labels[df['leakage_risk'].values == 1]      = 1
    return labels


def prepare_features(df: pd.DataFrame) -> np.ndarray:
    """Extract feature matrix, adding acoustic/vibration if present."""
    cols = list(FEATURE_COLS)
    for extra in ('acoustic', 'vibration', 'acoustic_emission'):
        if extra in df.columns:
            cols.append(extra)
    return df[cols].values


# ── 1. Multi-seed training and evaluation ──────────────────────────────────
def multiseed_evaluation(X_train, y_train, X_test, y_test):
    """Train RF across several seeds; collect macro & per-class metrics."""

    # Storage: metric_name -> list[float] (macro) or list[array] (per-class)
    macro_results = {m: [] for m in ['f1_macro', 'auc_roc_macro',
                                      'precision_macro', 'recall_macro']}
    perclass_results = {m: [] for m in ['f1_per', 'precision_per', 'recall_per']}

    for seed in SEEDS:
        clf = RandomForestClassifier(
            n_estimators=100,
            max_depth=None,
            random_state=seed,
            class_weight='balanced',
            n_jobs=-1
        )
        clf.fit(X_train, y_train)
        y_pred = clf.predict(X_test)
        y_prob = clf.predict_proba(X_test)

        # Macro metrics
        macro_results['f1_macro'].append(
            f1_score(y_test, y_pred, average='macro', zero_division=0))
        macro_results['precision_macro'].append(
            precision_score(y_test, y_pred, average='macro', zero_division=0))
        macro_results['recall_macro'].append(
            recall_score(y_test, y_pred, average='macro', zero_division=0))

        # AUC-ROC (OvR, macro)
        y_bin = label_binarize(y_test, classes=list(range(N_CLASSES)))
        # Ensure y_prob columns align with the 4 classes even if a class is
        # missing in the training fold (unlikely but defensive)
        prob_aligned = np.zeros((len(y_test), N_CLASSES))
        for idx, cls_label in enumerate(clf.classes_):
            prob_aligned[:, cls_label] = y_prob[:, idx]
        macro_results['auc_roc_macro'].append(
            roc_auc_score(y_bin, prob_aligned, multi_class='ovr', average='macro'))

        # Per-class metrics (arrays of length N_CLASSES)
        perclass_results['f1_per'].append(
            f1_score(y_test, y_pred, average=None,
                     labels=list(range(N_CLASSES)), zero_division=0))
        perclass_results['precision_per'].append(
            precision_score(y_test, y_pred, average=None,
                            labels=list(range(N_CLASSES)), zero_division=0))
        perclass_results['recall_per'].append(
            recall_score(y_test, y_pred, average=None,
                         labels=list(range(N_CLASSES)), zero_division=0))

    # ── Print macro results ────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  Multi-Seed Results (mean ± std)  —  Macro Averages")
    print("=" * 60)
    for metric, vals in macro_results.items():
        print(f"  {metric:20s}: {np.mean(vals):.4f} ± {np.std(vals):.4f}")

    # ── Print per-class results ────────────────────────────────────────────
    print("\n" + "-" * 60)
    print("  Per-Class Results (mean ± std)")
    print("-" * 60)
    for metric, arrs in perclass_results.items():
        stacked = np.vstack(arrs)  # shape (n_seeds, n_classes)
        means = stacked.mean(axis=0)
        stds  = stacked.std(axis=0)
        print(f"\n  {metric}:")
        for i, cls in enumerate(CLASSES):
            print(f"    {cls:15s}: {means[i]:.4f} ± {stds[i]:.4f}")

    return macro_results, perclass_results


# ── 2. Bootstrapped 95% Confidence Intervals ──────────────────────────────
def bootstrap_ci(X_train, y_train, X_test, y_test, n_bootstrap=N_BOOTSTRAP):
    """Bootstrapped 95% CI for macro F1, Precision, Recall, AUC-ROC."""

    clf = RandomForestClassifier(
        n_estimators=100, random_state=42,
        class_weight='balanced', n_jobs=-1
    )
    clf.fit(X_train, y_train)
    y_pred = clf.predict(X_test)
    y_prob = clf.predict_proba(X_test)

    # Align probabilities
    prob_aligned = np.zeros((len(y_test), N_CLASSES))
    for idx, cls_label in enumerate(clf.classes_):
        prob_aligned[:, cls_label] = y_prob[:, idx]

    boot_metrics = {m: [] for m in ['f1', 'precision', 'recall', 'auc_roc']}
    rng = np.random.RandomState(42)

    for _ in range(n_bootstrap):
        idx = rng.choice(len(y_test), size=len(y_test), replace=True)
        yt = np.array(y_test)[idx]
        yp = np.array(y_pred)[idx]
        yprob = prob_aligned[idx]

        boot_metrics['f1'].append(
            f1_score(yt, yp, average='macro', zero_division=0))
        boot_metrics['precision'].append(
            precision_score(yt, yp, average='macro', zero_division=0))
        boot_metrics['recall'].append(
            recall_score(yt, yp, average='macro', zero_division=0))

        yb = label_binarize(yt, classes=list(range(N_CLASSES)))
        try:
            boot_metrics['auc_roc'].append(
                roc_auc_score(yb, yprob, multi_class='ovr', average='macro'))
        except ValueError:
            # May happen if a bootstrap sample lacks a class
            boot_metrics['auc_roc'].append(np.nan)

    print("\n" + "=" * 60)
    print("  Bootstrapped 95% Confidence Intervals  (n={})".format(n_bootstrap))
    print("=" * 60)
    for metric, vals in boot_metrics.items():
        arr = np.array(vals)
        arr = arr[~np.isnan(arr)]
        lo, hi = np.percentile(arr, [2.5, 97.5])
        print(f"  {metric:12s} (macro): [{lo:.4f},  {hi:.4f}]")

    return clf, y_pred, prob_aligned, boot_metrics


# ── 3. Confusion Matrix ───────────────────────────────────────────────────
def plot_confusion_matrix(y_test, y_pred, output_dir):
    """Plot and save confusion matrix."""
    cm = confusion_matrix(y_test, y_pred, labels=list(range(N_CLASSES)))
    disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=CLASSES)

    fig, ax = plt.subplots(figsize=(7, 6))
    disp.plot(ax=ax, colorbar=True, cmap='Blues')
    ax.set_title("Confusion Matrix — PredBlock Multiclass Anomaly Detector")
    plt.tight_layout()

    os.makedirs(os.path.join(output_dir, 'figures'), exist_ok=True)
    path_pdf = os.path.join(output_dir, 'figures', 'confusion_matrix.pdf')
    path_png = os.path.join(output_dir, 'figures', 'confusion_matrix.png')
    fig.savefig(path_pdf, dpi=300)
    fig.savefig(path_png, dpi=300)
    plt.close(fig)
    logger.info(f"Confusion matrix saved → {path_pdf}")
    logger.info(f"Confusion matrix saved → {path_png}")


# ── 4. Precision-Recall Curves + PR-AUC ───────────────────────────────────
def plot_pr_curves(y_test, prob_aligned, output_dir):
    """Plot per-class Precision-Recall curves and report PR-AUC."""
    y_bin = label_binarize(y_test, classes=list(range(N_CLASSES)))

    fig, ax = plt.subplots(figsize=(8, 6))

    print("\n" + "=" * 60)
    print("  PR-AUC per Class")
    print("=" * 60)

    for i, cls in enumerate(CLASSES):
        prec, rec, _ = precision_recall_curve(y_bin[:, i], prob_aligned[:, i])
        pr_auc = average_precision_score(y_bin[:, i], prob_aligned[:, i])
        ax.plot(rec, prec, label=f"{cls} (PR-AUC={pr_auc:.3f})")
        print(f"  {cls:15s}: PR-AUC = {pr_auc:.4f}")

    ax.set_xlabel("Recall")
    ax.set_ylabel("Precision")
    ax.set_title("Precision-Recall Curves — PredBlock Multiclass")
    ax.legend(loc='lower left')
    ax.grid(True, alpha=0.3)
    plt.tight_layout()

    os.makedirs(os.path.join(output_dir, 'figures'), exist_ok=True)
    path_pdf = os.path.join(output_dir, 'figures', 'pr_curves.pdf')
    path_png = os.path.join(output_dir, 'figures', 'pr_curves.png')
    fig.savefig(path_pdf, dpi=300)
    fig.savefig(path_png, dpi=300)
    plt.close(fig)
    logger.info(f"PR curves saved → {path_pdf}")
    logger.info(f"PR curves saved → {path_png}")


# ── Main ───────────────────────────────────────────────────────────────────
def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Load & combine all data, then perform strict time-based split
    df = load_and_combine_data()
    train_df, val_df, test_df = time_based_split(df)

    # Derive multiclass labels
    y_train = derive_multiclass_label(train_df)
    y_val   = derive_multiclass_label(val_df)
    y_test  = derive_multiclass_label(test_df)

    # Features
    X_train = prepare_features(train_df)
    X_val   = prepare_features(val_df)
    X_test  = prepare_features(test_df)

    # Print class distribution across all splits
    print("\n--- Class Distribution (label counts) ---")
    print(f"  {'class':15s}  {'train':>7s}  {'val':>7s}  {'test':>7s}")
    for i, cls in enumerate(CLASSES):
        n_tr = (y_train == i).sum()
        n_va = (y_val == i).sum()
        n_te = (y_test == i).sum()
        print(f"  {cls:15s}  {n_tr:7d}  {n_va:7d}  {n_te:7d}")

    # 1. Multi-seed evaluation (train on train, evaluate on test)
    macro_results, perclass_results = multiseed_evaluation(
        X_train, y_train, X_test, y_test)

    # 2. Bootstrapped 95% CI (also returns the best-seed model & predictions)
    clf_best, y_pred_best, prob_aligned, boot_metrics = bootstrap_ci(
        X_train, y_train, X_test, y_test)

    # 3. Confusion matrix
    plot_confusion_matrix(y_test, y_pred_best, OUTPUT_DIR)

    # 4. PR curves + PR-AUC
    plot_pr_curves(y_test, prob_aligned, OUTPUT_DIR)

    print("\n" + "=" * 60)
    print("  Evaluation complete.  Outputs in:", OUTPUT_DIR)
    print("=" * 60)


if __name__ == "__main__":
    main()
