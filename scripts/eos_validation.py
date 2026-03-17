"""
EOS Validation: Surrogate Density Equation vs. CoolProp (Span-Wagner)
======================================================================
Compares the CO2Properties.density() surrogate used in the physics-based
simulator against the full Span-Wagner EOS implemented in CoolProp.

Operating window: 7–20 MPa (70–200 bar), 305–330 K (31.85–56.85 °C)

Outputs:
  - Percentage error at each (P, T) grid point
  - Max / mean absolute error
  - Heatmap of the error + CoolProp reference density
  - Saved to paper_evaluation_multiclass/figures/eos_validation.{pdf,png}
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import CoolProp.CoolProp as CP

from ai_layer.physics_based_simulator import CO2Properties

# ── Configuration ──────────────────────────────────────────────────────────
P_MIN_MPA, P_MAX_MPA = 7, 20        # MPa
T_MIN_K,   T_MAX_K   = 305, 330     # K
N_P, N_T = 30, 25                   # grid resolution

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'paper_evaluation_multiclass', 'figures')


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # ── Build (P, T) grid ──────────────────────────────────────────────
    P_pa  = np.linspace(P_MIN_MPA * 1e6, P_MAX_MPA * 1e6, N_P)   # Pa
    T_k   = np.linspace(T_MIN_K, T_MAX_K, N_T)                    # K
    PP, TT = np.meshgrid(P_pa, T_k)

    # ── CoolProp reference (full Span-Wagner EOS) ──────────────────────
    rho_coolprop = np.zeros_like(PP)
    for i in range(TT.shape[0]):
        for j in range(PP.shape[1]):
            try:
                rho_coolprop[i, j] = CP.PropsSI('D', 'P', PP[i, j], 'T', TT[i, j], 'CO2')
            except Exception:
                rho_coolprop[i, j] = np.nan

    # ── Surrogate density (CO2Properties.density) ──────────────────────
    # The surrogate accepts (pressure_bar, temperature_celsius)
    co2 = CO2Properties()
    rho_surrogate = np.zeros_like(PP)
    for i in range(TT.shape[0]):
        for j in range(PP.shape[1]):
            p_bar = PP[i, j] / 1e5           # Pa → bar
            t_c   = TT[i, j] - 273.15        # K  → °C
            rho_surrogate[i, j] = co2.density(p_bar, t_c)

    # ── Percentage error ───────────────────────────────────────────────
    pct_error = np.abs(rho_surrogate - rho_coolprop) / rho_coolprop * 100

    # ── Report ─────────────────────────────────────────────────────────
    print("\n" + "=" * 65)
    print("  Surrogate vs. CoolProp (Span-Wagner) — CO2 Density Comparison")
    print("=" * 65)
    print(f"  Operating window : {P_MIN_MPA}–{P_MAX_MPA} MPa,  {T_MIN_K}–{T_MAX_K} K")
    print(f"  Grid resolution  : {N_P} x {N_T} = {N_P * N_T} points")
    print(f"  Mean abs % error : {np.nanmean(pct_error):.2f}%")
    print(f"  Max  abs % error : {np.nanmax(pct_error):.2f}%")
    print(f"  Median % error   : {np.nanmedian(pct_error):.2f}%")

    # Identify worst-case point
    idx = np.unravel_index(np.nanargmax(pct_error), pct_error.shape)
    worst_P = PP[idx] / 1e6
    worst_T = TT[idx]
    print(f"  Worst-case point : P = {worst_P:.1f} MPa,  T = {worst_T:.1f} K")
    print(f"    Surrogate ρ    : {rho_surrogate[idx]:.2f} kg/m³")
    print(f"    CoolProp  ρ    : {rho_coolprop[idx]:.2f} kg/m³")

    # ── Heatmap plots ──────────────────────────────────────────────────
    PP_mpa = PP / 1e6

    fig, axes = plt.subplots(1, 3, figsize=(19, 5))

    # Panel 1: CoolProp reference
    c1 = axes[0].contourf(PP_mpa, TT, rho_coolprop, levels=20, cmap='viridis')
    fig.colorbar(c1, ax=axes[0], label='Density (kg/m³)')
    axes[0].set_title("CoolProp (Span-Wagner)\nReference Density")
    axes[0].set_xlabel("Pressure (MPa)")
    axes[0].set_ylabel("Temperature (K)")

    # Panel 2: Surrogate density
    c2 = axes[1].contourf(PP_mpa, TT, rho_surrogate, levels=20, cmap='viridis')
    fig.colorbar(c2, ax=axes[1], label='Density (kg/m³)')
    axes[1].set_title("Surrogate Approximation\n(CO2Properties.density)")
    axes[1].set_xlabel("Pressure (MPa)")
    axes[1].set_ylabel("Temperature (K)")

    # Panel 3: Percentage error
    c3 = axes[2].contourf(PP_mpa, TT, pct_error, levels=20, cmap='Reds')
    fig.colorbar(c3, ax=axes[2], label='Absolute Error (%)')
    axes[2].set_title(f"% Error  (mean={np.nanmean(pct_error):.1f}%,"
                      f" max={np.nanmax(pct_error):.1f}%)")
    axes[2].set_xlabel("Pressure (MPa)")
    axes[2].set_ylabel("Temperature (K)")

    fig.suptitle("EOS Validation: Surrogate Approximation vs. Full Span-Wagner EOS",
                 fontsize=13, y=1.02)
    plt.tight_layout()

    path_pdf = os.path.join(OUTPUT_DIR, 'eos_validation.pdf')
    path_png = os.path.join(OUTPUT_DIR, 'eos_validation.png')
    fig.savefig(path_pdf, dpi=300, bbox_inches='tight')
    fig.savefig(path_png, dpi=300, bbox_inches='tight')
    plt.close(fig)

    print(f"\n  Figures saved → {path_pdf}")
    print(f"                → {path_png}")
    print("=" * 65)


if __name__ == "__main__":
    main()
