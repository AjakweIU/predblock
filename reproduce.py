#!/usr/bin/env python
"""
reproduce.py -- One-command reproduction of all key tables and figures.

Usage:
    conda env create -f environment.yml
    conda activate predblock
    python reproduce.py            # run all evaluations (offline, no blockchain key needed)
    python reproduce.py --online   # also run blockchain latency benchmark (needs PURECHAIN_PRIVATE_KEY)

Steps executed:
    1. Generate physics-based train/val/test datasets (deterministic seed)
    2. Multiclass RF evaluation (5 seeds, bootstrap CIs, confusion matrix, PR curves)
    3. Baseline comparison (binary PredBlock + Isolation Forest + One-Class SVM + Threshold)
    4. Ablation study (4 feature variants x 5 seeds)
    5. Robustness analysis (noise, drift, missing data)
    6. RL compression controller (Q-learning vs PID, 5 seeds)
    7. Lambda sensitivity sweep (5 lambda pairs x 5 seeds)
    8. [--online only] Blockchain latency benchmark (PureChain testnet)
    9. EOS validation (surrogate vs CoolProp -- skipped if CoolProp not installed)

All outputs are written to paper_evaluation_multiclass/.
"""

import subprocess
import sys
import os
import time

SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scripts')
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

# Ordered list of (description, script_path, online_only)
STEPS = [
    ("Generate physics-based datasets",
     "generate_publication_data.py", False),
    ("Multiclass RF evaluation (5 seeds + bootstrap CIs + PR curves)",
     "multiclass_rf_evaluation.py", False),
    ("Baseline comparison (binary PredBlock + unsupervised baselines + binary PR curves)",
     "baseline_comparison.py", False),
    ("Ablation study (physics-informed features)",
     "ablation_study.py", False),
    ("Robustness analysis (noise, drift, missing data)",
     "robustness_analysis.py", False),
    ("RL compression controller (Q-learning vs PID)",
     "rl_compression_eval.py", False),
    ("Lambda sensitivity sweep",
     "lambda_sensitivity_sweep.py", False),
    ("Blockchain latency benchmark (PureChain testnet)",
     "blockchain_latency_benchmark.py", True),
    ("EOS validation (surrogate vs CoolProp)",
     "eos_validation.py", False),
]


def run_step(description, script, online_mode):
    script_path = os.path.join(SCRIPTS_DIR, script)
    if not os.path.exists(script_path):
        print(f"  [SKIP] {script} not found")
        return True

    print(f"\n{'='*70}")
    print(f"  {description}")
    print(f"  Script: scripts/{script}")
    print(f"{'='*70}")

    env = os.environ.copy()
    env['PYTHONIOENCODING'] = 'utf-8'

    t0 = time.time()
    result = subprocess.run(
        [sys.executable, script_path],
        cwd=ROOT_DIR,
        env=env,
        capture_output=False,
    )
    elapsed = time.time() - t0

    if result.returncode == 0:
        print(f"  [OK] Completed in {elapsed:.1f}s")
        return True
    else:
        print(f"  [FAIL] Exit code {result.returncode} after {elapsed:.1f}s")
        return False


def main():
    online = '--online' in sys.argv

    print("="*70)
    print("  PredBlock -- Reproduce All Key Tables and Figures")
    print("="*70)
    print(f"  Mode: {'online (includes blockchain benchmark)' if online else 'offline'}")
    print(f"  Output directory: paper_evaluation_multiclass/")
    print()

    passed = 0
    failed = 0
    skipped = 0

    for desc, script, online_only in STEPS:
        if online_only and not online:
            print(f"\n  [SKIP] {desc} (pass --online to enable)")
            skipped += 1
            continue
        ok = run_step(desc, script, online)
        if ok:
            passed += 1
        else:
            failed += 1

    print(f"\n{'='*70}")
    print(f"  SUMMARY: {passed} passed, {failed} failed, {skipped} skipped")
    print(f"  Outputs in: paper_evaluation_multiclass/")
    print(f"{'='*70}")

    sys.exit(1 if failed > 0 else 0)


if __name__ == '__main__':
    main()
