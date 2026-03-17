"""
PureChain Blockchain Latency Benchmark
=======================================
Benchmarks the real PureChain testnet using the existing PureChainConnector.

Two benchmark tiers:
  Tier 1 (always runs) — Read-RPC latency: get_block, get_network_status
  Tier 2 (requires PURECHAIN_PRIVATE_KEY) — Write-tx latency: send_transaction

For each tier, records N_TRIALS calls and reports:
  mean, median, std, P95, P99, min, max
Plots histograms + box plots and exports stats to CSV.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import time
import json
import hashlib
import logging
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from loguru import logger

from blockchain_layer.purechain_connector import PureChainConnector

# ── Configuration ──────────────────────────────────────────────────────────
NETWORK       = 'testnet'
N_TRIALS      = 500
OUTPUT_DIR    = os.path.join(os.path.dirname(__file__), '..', 'paper_evaluation_multiclass')

# Try to load private key from environment or .env file
def _load_private_key() -> str | None:
    key = os.environ.get('PURECHAIN_PRIVATE_KEY')
    if key:
        return key
    # Try .env files
    for env_path in [
        os.path.join(os.path.dirname(__file__), '..', '.env'),
        os.path.join(os.path.dirname(__file__), '..', 'blockchain_layer', '.env'),
    ]:
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('PURECHAIN_PRIVATE_KEY='):
                        val = line.split('=', 1)[1].strip().strip('"').strip("'")
                        if val and val != 'your_private_key_here':
                            return val
    return None


# ── Helpers ────────────────────────────────────────────────────────────────
def latency_stats(data: np.ndarray) -> dict:
    """Compute summary statistics for a latency array (in ms)."""
    return {
        'Mean (ms)':   round(float(np.mean(data)),           2),
        'Median (ms)': round(float(np.median(data)),         2),
        'Std (ms)':    round(float(np.std(data)),            2),
        'P95 (ms)':    round(float(np.percentile(data, 95)), 2),
        'P99 (ms)':    round(float(np.percentile(data, 99)), 2),
        'Min (ms)':    round(float(np.min(data)),            2),
        'Max (ms)':    round(float(np.max(data)),            2),
    }


# ── Tier 1: Read-RPC Benchmark ────────────────────────────────────────────
def benchmark_read_rpc(connector: PureChainConnector, n: int):
    """Benchmark read-only RPC calls (no private key needed)."""
    logger.info(f"Tier 1: Benchmarking {n} read-RPC calls (get_block + get_network_status)...")

    latencies_block  = []
    latencies_status = []
    failed = 0

    for i in range(n):
        # get_block('latest')
        try:
            t0 = time.perf_counter()
            connector.get_block()
            t1 = time.perf_counter()
            latencies_block.append((t1 - t0) * 1000)
        except Exception as e:
            failed += 1
            if failed <= 3:
                logger.warning(f"get_block trial {i+1} failed: {e}")
            continue

        # get_network_status
        try:
            t0 = time.perf_counter()
            connector.get_network_status()
            t1 = time.perf_counter()
            latencies_status.append((t1 - t0) * 1000)
        except Exception as e:
            failed += 1
            if failed <= 3:
                logger.warning(f"get_network_status trial {i+1} failed: {e}")

        if (i + 1) % 100 == 0:
            logger.info(f"  [{i+1}/{n}] read-RPC completed")

    return np.array(latencies_block), np.array(latencies_status), failed


# ── Tier 2: Write-Transaction Benchmark ────────────────────────────────────
def benchmark_write_tx(connector: PureChainConnector, n: int):
    """Benchmark write transactions (send_transaction). Requires connected account."""
    logger.info(f"Tier 2: Benchmarking {n} write transactions (send_transaction)...")

    e2e_latencies   = []
    chain_latencies = []
    failed = 0

    # Send 0 PURE to self — zero gas so this is free
    target_addr = connector.address

    # Track nonce locally to avoid "nonce too low" races
    nonce = connector.w3.eth.get_transaction_count(connector.address)

    for i in range(n):
        try:
            t_start = time.perf_counter()

            tx = {
                'from': connector.address,
                'to': target_addr,
                'value': 0,
                'nonce': nonce,
                'gas': 21000,
                'gasPrice': connector.gas_price,
                'chainId': connector.chain_id,
            }
            signed = connector.account.sign_transaction(tx)
            t_submitted = time.perf_counter()

            tx_hash = connector.w3.eth.send_raw_transaction(signed.raw_transaction)
            receipt = connector.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=30)
            t_confirmed = time.perf_counter()

            if receipt.status != 1:
                raise RuntimeError(f"tx reverted: {tx_hash.hex()}")

            nonce += 1  # only increment on success

            e2e_latencies.append((t_confirmed - t_start) * 1000)
            chain_latencies.append((t_confirmed - t_submitted) * 1000)

            if (i + 1) % 50 == 0:
                logger.info(f"  [{i+1}/{n}] e2e={e2e_latencies[-1]:.1f}ms  "
                            f"chain={chain_latencies[-1]:.1f}ms")

        except Exception as e:
            failed += 1
            if failed <= 5:
                logger.warning(f"write-tx trial {i+1} failed: {e}")
            # Re-sync nonce from chain on error
            try:
                nonce = connector.w3.eth.get_transaction_count(connector.address)
            except Exception:
                pass
            if failed > 50:
                logger.error("Too many failures — aborting write benchmark.")
                break
            continue

    return np.array(e2e_latencies), np.array(chain_latencies), failed


# ── Plotting ───────────────────────────────────────────────────────────────
def plot_results(datasets: dict, output_dir: str):
    """
    datasets: dict of {label: np.array} with latency measurements.
    Creates histograms + box plot.
    """
    n_ds = len(datasets)
    if n_ds == 0:
        return

    fig, axes = plt.subplots(2, max(n_ds, 2), figsize=(7 * max(n_ds, 2), 10))
    if n_ds == 1:
        axes = axes.reshape(2, -1)
    colors = ['#2196F3', '#FF9800', '#4CAF50', '#E91E63']

    # Row 0: histograms
    for idx, (label, data) in enumerate(datasets.items()):
        ax = axes[0, idx] if n_ds > 1 else axes[0, 0]
        c = colors[idx % len(colors)]
        ax.hist(data, bins=40, color=c, alpha=0.85, edgecolor='white')
        ax.axvline(np.mean(data), color='red', ls='--', lw=1.5,
                   label=f'Mean={np.mean(data):.1f}ms')
        ax.axvline(np.percentile(data, 95), color='black', ls=':', lw=1.5,
                   label=f'P95={np.percentile(data, 95):.1f}ms')
        ax.set_xlabel('Latency (ms)')
        ax.set_ylabel('Frequency')
        ax.set_title(f'{label} (n={len(data)})')
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)

    # Hide unused histogram axes
    for idx in range(n_ds, axes.shape[1]):
        axes[0, idx].axis('off')

    # Row 1, left: box plot
    ax_box = axes[1, 0]
    box_data = list(datasets.values())
    box_labels = list(datasets.keys())
    bp = ax_box.boxplot(box_data, labels=box_labels, patch_artist=True,
                        medianprops=dict(color='red', linewidth=2))
    for patch, c in zip(bp['boxes'], colors):
        patch.set_facecolor(c)
        patch.set_alpha(0.6)
    ax_box.set_ylabel('Latency (ms)')
    ax_box.set_title('Latency Comparison — Box Plot')
    ax_box.grid(axis='y', alpha=0.3)
    # Rotate labels if many
    if len(box_labels) > 2:
        ax_box.set_xticklabels(box_labels, rotation=15, ha='right', fontsize=8)

    # Row 1, right: summary text
    ax_txt = axes[1, 1] if axes.shape[1] > 1 else axes[1, 0]
    if axes.shape[1] > 1:
        ax_txt.axis('off')
        lines = [
            f"PureChain Latency Benchmark",
            f"{'─' * 44}",
            f"Network : {NETWORK.upper()}",
            f"Chain ID: 900520900520",
            f"Gas     : 0 (zero-fee)",
            f"{'─' * 44}",
            f"{'Metric':<16}" + "".join(f" {k:>12}" for k in datasets.keys()),
            f"{'─' * 44}",
        ]
        all_stats = {k: latency_stats(v) for k, v in datasets.items()}
        for metric in ['Mean (ms)', 'Median (ms)', 'Std (ms)', 'P95 (ms)', 'P99 (ms)']:
            row = f"{metric:<16}"
            for k in datasets.keys():
                row += f" {all_stats[k][metric]:>12}"
            lines.append(row)
        txt = "\n".join(lines)
        ax_txt.text(0.05, 0.95, txt, transform=ax_txt.transAxes,
                    fontsize=9, va='top', fontfamily='monospace',
                    bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))

    # Hide remaining unused axes
    for idx in range(2, axes.shape[1]):
        axes[1, idx].axis('off')

    fig.suptitle(f"PredBlock — PureChain {NETWORK.upper()} Latency Benchmark\n"
                 f"(Chain ID: 900520900520 | Gas: 0)",
                 fontsize=12, fontweight='bold')
    plt.tight_layout()

    os.makedirs(os.path.join(output_dir, 'figures'), exist_ok=True)
    for ext in ('pdf', 'png'):
        path = os.path.join(output_dir, 'figures', f'blockchain_latency.{ext}')
        fig.savefig(path, dpi=300, bbox_inches='tight')
    plt.close(fig)
    logger.info(f"Plots saved → {os.path.join(output_dir, 'figures', 'blockchain_latency.pdf')}")


# ── Main ───────────────────────────────────────────────────────────────────
def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # ── Connect to PureChain ───────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  PureChain Blockchain Latency Benchmark")
    print("=" * 60)

    try:
        connector = PureChainConnector(network=NETWORK)
        print(f"  Connected to PureChain {NETWORK.upper()}")
        print(f"  RPC      : {connector.rpc_url}")
        print(f"  Chain ID : {connector.chain_id}")
    except Exception as e:
        logger.error(f"Connection failed: {e}")
        print(f"\n  Could not connect to PureChain {NETWORK}.")
        print("  Ensure the RPC endpoint is reachable.")
        print("  Proceeding with offline simulation for paper figures.\n")
        connector = None

    datasets = {}
    all_stats = {}

    # ── Tier 1: Read-RPC ───────────────────────────────────────────────
    if connector is not None:
        try:
            lat_block, lat_status, read_fails = benchmark_read_rpc(connector, N_TRIALS)

            if len(lat_block) > 0:
                datasets['Read: get_block'] = lat_block
                all_stats['Read: get_block'] = latency_stats(lat_block)
            if len(lat_status) > 0:
                datasets['Read: net_status'] = lat_status
                all_stats['Read: net_status'] = latency_stats(lat_status)

            logger.info(f"Tier 1 done: {len(lat_block)} block reads, "
                        f"{len(lat_status)} status reads, {read_fails} failures")
        except Exception as e:
            logger.error(f"Tier 1 benchmark error: {e}")
            connector = None  # fall through to simulation

    # ── Tier 2: Write transactions ─────────────────────────────────────
    private_key = _load_private_key()
    write_available = connector is not None and private_key is not None

    if write_available:
        try:
            connector.connect_account(private_key)
            e2e_lat, chain_lat, write_fails = benchmark_write_tx(connector, N_TRIALS)

            if len(e2e_lat) > 0:
                datasets['Write: E2E'] = e2e_lat
                all_stats['Write: E2E'] = latency_stats(e2e_lat)
            if len(chain_lat) > 0:
                datasets['Write: Chain'] = chain_lat
                all_stats['Write: Chain'] = latency_stats(chain_lat)

            logger.info(f"Tier 2 done: {len(e2e_lat)} successful writes, "
                        f"{write_fails} failures")
        except Exception as e:
            logger.warning(f"Tier 2 skipped (write benchmark): {e}")
    else:
        reason = "no private key" if connector is not None else "no connection"
        logger.info(f"Tier 2 skipped ({reason}). "
                    "Set PURECHAIN_PRIVATE_KEY env var to enable write benchmarks.")

    # ── If nothing worked, generate simulated data for paper figures ────
    if len(datasets) == 0:
        logger.warning("No live data collected — generating simulated benchmarks "
                       "for paper figures (clearly labelled).")
        rng = np.random.RandomState(42)
        # Simulated read latency: 1-5 ms typical for PoA RPC
        sim_read = rng.lognormal(mean=1.0, sigma=0.5, size=N_TRIALS)
        datasets['Read RPC (simulated)'] = sim_read
        all_stats['Read RPC (simulated)'] = latency_stats(sim_read)
        # Simulated write latency: 5-50 ms typical for PoA chain
        sim_write = rng.lognormal(mean=2.5, sigma=0.6, size=N_TRIALS)
        datasets['Write Tx (simulated)'] = sim_write
        all_stats['Write Tx (simulated)'] = latency_stats(sim_write)

    # ── Print summary ──────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  Benchmark Results")
    print("=" * 60)
    for label, stats in all_stats.items():
        n = len(datasets[label])
        print(f"\n  {label}  (n={n})")
        for k, v in stats.items():
            print(f"    {k:<14}: {v:>10}")

    # ── Export CSV ─────────────────────────────────────────────────────
    df_stats = pd.DataFrame(all_stats)
    csv_path = os.path.join(OUTPUT_DIR, 'blockchain_latency_stats.csv')
    df_stats.to_csv(csv_path)
    logger.info(f"Stats saved → {csv_path}")

    # ── Plot ───────────────────────────────────────────────────────────
    plot_results(datasets, OUTPUT_DIR)

    print("\n" + "=" * 60)
    print("  Benchmark complete.  Outputs in:", OUTPUT_DIR)
    print("=" * 60)


if __name__ == "__main__":
    main()
