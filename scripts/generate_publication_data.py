"""
Generate Publication-Quality Datasets
Creates train/validation/test splits with physics-based simulation
"""

import os
import sys
import argparse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ai_layer.physics_based_simulator import PhysicsBasedSimulator


def plot_dataset_overview(data: pd.DataFrame, save_path: str):
    """Create overview plots of generated dataset"""
    
    fig, axes = plt.subplots(3, 3, figsize=(15, 12))
    fig.suptitle('Physics-Based CCS Pipeline Data Overview', fontsize=16, fontweight='bold')
    
    # Pressure
    axes[0, 0].plot(data['pressure'], linewidth=0.5, alpha=0.7)
    axes[0, 0].axhline(y=75, color='g', linestyle='--', label='Normal')
    axes[0, 0].axhline(y=90, color='orange', linestyle='--', label='Warning')
    axes[0, 0].axhline(y=100, color='r', linestyle='--', label='Critical')
    axes[0, 0].set_ylabel('Pressure (bar)')
    axes[0, 0].set_title('Pressure Profile')
    axes[0, 0].legend(fontsize=8)
    axes[0, 0].grid(alpha=0.3)
    
    # Temperature
    axes[0, 1].plot(data['temperature'], linewidth=0.5, alpha=0.7, color='orange')
    axes[0, 1].set_ylabel('Temperature (°C)')
    axes[0, 1].set_title('Temperature Profile')
    axes[0, 1].grid(alpha=0.3)
    
    # Flow Rate
    axes[0, 2].plot(data['flow_rate'], linewidth=0.5, alpha=0.7, color='blue')
    axes[0, 2].set_ylabel('Flow Rate (kg/s)')
    axes[0, 2].set_title('Flow Rate Profile')
    axes[0, 2].grid(alpha=0.3)
    
    # H2O
    axes[1, 0].plot(data['H2O'], linewidth=0.5, alpha=0.7, color='cyan')
    axes[1, 0].axhline(y=50, color='g', linestyle='--', label='Normal')
    axes[1, 0].axhline(y=100, color='orange', linestyle='--', label='Alert')
    axes[1, 0].set_ylabel('H₂O (ppmv)')
    axes[1, 0].set_title('Water Content')
    axes[1, 0].legend(fontsize=8)
    axes[1, 0].grid(alpha=0.3)
    
    # H2S
    axes[1, 1].plot(data['H2S'], linewidth=0.5, alpha=0.7, color='purple')
    axes[1, 1].axhline(y=10, color='g', linestyle='--', label='Normal')
    axes[1, 1].axhline(y=20, color='orange', linestyle='--', label='Alert')
    axes[1, 1].set_ylabel('H₂S (ppmv)')
    axes[1, 1].set_title('Hydrogen Sulfide')
    axes[1, 1].legend(fontsize=8)
    axes[1, 1].grid(alpha=0.3)
    
    # SO2
    axes[1, 2].plot(data['SO2'], linewidth=0.5, alpha=0.7, color='red')
    axes[1, 2].axhline(y=50, color='g', linestyle='--', label='Normal')
    axes[1, 2].axhline(y=100, color='orange', linestyle='--', label='Alert')
    axes[1, 2].set_ylabel('SO₂ (ppmv)')
    axes[1, 2].set_title('Sulfur Dioxide')
    axes[1, 2].legend(fontsize=8)
    axes[1, 2].grid(alpha=0.3)
    
    # O2
    axes[2, 0].plot(data['O2'], linewidth=0.5, alpha=0.7, color='green')
    axes[2, 0].axhline(y=10, color='g', linestyle='--', label='Normal')
    axes[2, 0].axhline(y=15, color='orange', linestyle='--', label='Alert')
    axes[2, 0].set_ylabel('O₂ (ppmv)')
    axes[2, 0].set_title('Oxygen (Leakage Indicator)')
    axes[2, 0].legend(fontsize=8)
    axes[2, 0].grid(alpha=0.3)
    axes[2, 0].set_xlabel('Sample Index')
    
    # Acoustic Emission
    axes[2, 1].plot(data['acoustic_emission'], linewidth=0.5, alpha=0.7, color='brown')
    axes[2, 1].set_ylabel('Acoustic Emission (AU)')
    axes[2, 1].set_title('Acoustic Emission')
    axes[2, 1].grid(alpha=0.3)
    axes[2, 1].set_xlabel('Sample Index')
    
    # Anomaly Distribution
    anomaly_counts = [
        data['leakage_risk'].sum(),
        data['corrosion_risk'].sum(),
        data['overpressure_risk'].sum()
    ]
    axes[2, 2].bar(['Leakage', 'Corrosion', 'Overpressure'], anomaly_counts, 
                   color=['red', 'orange', 'purple'])
    axes[2, 2].set_ylabel('Count')
    axes[2, 2].set_title('Anomaly Distribution')
    axes[2, 2].grid(axis='y', alpha=0.3)
    axes[2, 2].set_xlabel('Anomaly Type')
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"✓ Overview plot saved to {save_path}")
    plt.close()


def plot_correlation_matrix(data: pd.DataFrame, save_path: str):
    """Plot correlation matrix of key variables"""
    
    # Select key variables
    vars_to_plot = ['pressure', 'temperature', 'flow_rate', 'H2O', 'H2S', 'SO2', 
                    'O2', 'acoustic_emission', 'vibration', 'density']
    
    corr_data = data[vars_to_plot].corr()
    
    plt.figure(figsize=(10, 8))
    sns.heatmap(corr_data, annot=True, fmt='.2f', cmap='coolwarm', center=0,
                square=True, linewidths=1, cbar_kws={"shrink": 0.8})
    plt.title('Correlation Matrix of Pipeline Variables', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"✓ Correlation matrix saved to {save_path}")
    plt.close()


def generate_publication_datasets(output_dir: str = "data"):
    """Generate complete set of datasets for publication"""
    
    print("="*70)
    print("GENERATING PUBLICATION-QUALITY DATASETS")
    print("Physics-Based CCS Pipeline Simulation")
    print("="*70)
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(f"{output_dir}/plots", exist_ok=True)
    
    simulator = PhysicsBasedSimulator()
    
    # 1. Training Dataset (Large, diverse)
    print("\n" + "="*70)
    print("1. TRAINING DATASET")
    print("="*70)
    train_data = simulator.generate_realistic_dataset(
        n_samples=50000,
        n_leakage_events=12,  # Increased from 8
        n_corrosion_events=8,  # Increased from 5
        n_overpressure_events=8,  # Increased from 5
        save_path=f"{output_dir}/train_physics.csv"
    )
    
    plot_dataset_overview(train_data.iloc[:5000], f"{output_dir}/plots/train_overview.png")
    
    # 2. Validation Dataset
    print("\n" + "="*70)
    print("2. VALIDATION DATASET")
    print("="*70)
    val_data = simulator.generate_realistic_dataset(
        n_samples=15000,
        n_leakage_events=5,  # Increased from 3
        n_corrosion_events=3,  # Increased from 2
        n_overpressure_events=3,  # Increased from 2
        save_path=f"{output_dir}/val_physics.csv"
    )
    
    # 3. Test Dataset
    print("\n" + "="*70)
    print("3. TEST DATASET")
    print("="*70)
    test_data = simulator.generate_realistic_dataset(
        n_samples=10000,
        n_leakage_events=4,  # Increased from 2
        n_corrosion_events=2,  # Increased from 1
        n_overpressure_events=3,  # Increased from 2
        save_path=f"{output_dir}/test_physics.csv"
    )
    
    plot_dataset_overview(test_data, f"{output_dir}/plots/test_overview.png")
    plot_correlation_matrix(test_data, f"{output_dir}/plots/correlation_matrix.png")
    
    # 4. Generate summary statistics
    print("\n" + "="*70)
    print("DATASET SUMMARY")
    print("="*70)
    
    summary = {
        'Dataset': ['Training', 'Validation', 'Test'],
        'Samples': [len(train_data), len(val_data), len(test_data)],
        'Duration (days)': [
            len(train_data) / (60*24),
            len(val_data) / (60*24),
            len(test_data) / (60*24)
        ],
        'Leakage Events': [
            train_data['leakage_risk'].sum(),
            val_data['leakage_risk'].sum(),
            test_data['leakage_risk'].sum()
        ],
        'Corrosion Events': [
            train_data['corrosion_risk'].sum(),
            val_data['corrosion_risk'].sum(),
            test_data['corrosion_risk'].sum()
        ],
        'Overpressure Events': [
            train_data['overpressure_risk'].sum(),
            val_data['overpressure_risk'].sum(),
            test_data['overpressure_risk'].sum()
        ],
        'Anomaly Rate (%)': [
            100 * (train_data['leakage_risk'].sum() + train_data['corrosion_risk'].sum() + 
                   train_data['overpressure_risk'].sum()) / len(train_data),
            100 * (val_data['leakage_risk'].sum() + val_data['corrosion_risk'].sum() + 
                   val_data['overpressure_risk'].sum()) / len(val_data),
            100 * (test_data['leakage_risk'].sum() + test_data['corrosion_risk'].sum() + 
                   test_data['overpressure_risk'].sum()) / len(test_data)
        ]
    }
    
    summary_df = pd.DataFrame(summary)
    summary_df.to_csv(f"{output_dir}/dataset_summary.csv", index=False)
    
    print("\n" + summary_df.to_string(index=False))
    
    # 5. Statistical validation
    print("\n" + "="*70)
    print("STATISTICAL VALIDATION")
    print("="*70)
    
    print("\nTest Dataset Statistics:")
    print("-" * 70)
    
    stats = test_data[['pressure', 'temperature', 'flow_rate', 'H2O', 'H2S', 'SO2', 'O2']].describe()
    print(stats)
    
    # Check autocorrelation
    from scipy.stats import pearsonr
    
    print("\nTemporal Autocorrelation (lag-1):")
    print("-" * 70)
    for col in ['pressure', 'temperature', 'flow_rate', 'H2O']:
        if len(test_data) > 1:
            corr, _ = pearsonr(test_data[col][:-1], test_data[col][1:])
            print(f"  {col:20s}: {corr:.4f}")
    
    print("\n" + "="*70)
    print("✓ ALL DATASETS GENERATED SUCCESSFULLY")
    print("="*70)
    print(f"\nFiles created in '{output_dir}/':")
    print("  • train_physics.csv (50,000 samples)")
    print("  • val_physics.csv (15,000 samples)")
    print("  • test_physics.csv (10,000 samples)")
    print("  • dataset_summary.csv")
    print(f"\nPlots created in '{output_dir}/plots/':")
    print("  • train_overview.png")
    print("  • test_overview.png")
    print("  • correlation_matrix.png")
    
    print("\n" + "="*70)
    print("NEXT STEPS")
    print("="*70)
    print("1. Review the generated plots to verify data quality")
    print("2. Train AI models: python main.py train --data data/train_physics.csv")
    print("3. Evaluate on test set: python scripts/evaluate_system.py --test-data data/test_physics.csv")
    print("4. Refer to docs/DATA_GENERATION_METHODOLOGY.md for publication details")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Generate publication-quality datasets for CCS pipeline monitoring'
    )
    parser.add_argument('--output-dir', type=str, default='data',
                       help='Output directory for datasets')
    
    args = parser.parse_args()
    
    generate_publication_datasets(args.output_dir)
