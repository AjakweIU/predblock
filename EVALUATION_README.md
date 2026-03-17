# PredBlock - Automated Evaluation for Publication

## 🚀 One-Command Evaluation

Run the complete evaluation pipeline to generate all metrics, tables, plots, and figures for your research paper.

### Windows (Git Bash or WSL):
```bash
bash run_full_evaluation.sh
```

### Windows (Command Prompt):
```batch
run_full_evaluation.bat
```

## 📊 What Gets Generated

The script automatically:

1. ✅ **Checks environment** (Python, Node.js, venv)
2. ✅ **Generates data** (if not exists)
3. ✅ **Validates data quality** against literature
4. ✅ **Trains all AI models** (Leakage, Impurity, Corrosion)
5. ✅ **Evaluates performance** with metrics
6. ✅ **Tests blockchain** integration
7. ✅ **Generates publication materials**

## 📁 Output Structure

```
paper_evaluation/
├── results.json                    # All metrics in JSON
├── evaluation_report.txt           # Human-readable report
├── data_validation_report.txt      # Data quality validation
├── blockchain_metrics.json         # Blockchain performance
├── PUBLICATION_SUMMARY.md          # Summary for paper
├── RESULTS_SUMMARY.txt             # Quick results
├── figures/                        # Publication-quality figures (300 DPI)
│   ├── anomaly_distribution.png
│   ├── sensor_timeseries.png
│   └── ...
├── tables/                         # LaTeX tables
│   ├── performance_table.tex
│   └── ...
├── models/                         # Trained models (copied here)
└── logs/                           # Training and evaluation logs
    ├── leakage_training.log
    ├── impurity_training.log
    ├── corrosion_training.log
    ├── evaluation.log
    └── blockchain_test.log
```

## 📋 Metrics Generated

### Data Quality Metrics
- Dataset size and temporal coverage
- Anomaly distribution (leakage, corrosion, overpressure)
- Temporal autocorrelation
- Literature validation (IEAGHG, DNV GL, NIST)

### AI Model Performance
For each model (Leakage, Impurity, Corrosion):
- Accuracy
- Precision
- Recall
- F1-Score
- AUC-ROC
- Confusion Matrix
- Inference Time

### Baseline Comparisons
- Threshold-based detection
- Isolation Forest
- One-Class SVM
- Statistical Process Control

### Blockchain Performance
- Transaction latency
- Throughput
- Gas cost (0 PURE!)
- Network status

## 🎯 For Your Paper

After running the evaluation:

### 1. Import Figures
```latex
\begin{figure}[h]
  \centering
  \includegraphics[width=0.8\textwidth]{paper_evaluation/figures/anomaly_distribution.png}
  \caption{Anomaly distribution in test dataset}
  \label{fig:anomaly_dist}
\end{figure}
```

### 2. Import Tables
```latex
\input{paper_evaluation/tables/performance_table.tex}
```

### 3. Cite Metrics
From `evaluation_report.txt`:
- "Our model achieved 95.2% accuracy with 0.94 F1-score..."
- "The dataset contains 10,000 samples with 3.55% anomaly rate..."
- "Zero gas fees on PureChain enable cost-effective deployment..."

### 4. Reference Methodology
From `docs/DATA_GENERATION_METHODOLOGY.md`:
- Physics-based simulation approach
- Thermodynamic models (Span-Wagner EOS)
- Validation against literature

## ⚙️ Prerequisites

### Before Running:

1. **Virtual Environment Activated**
   ```bash
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   ```

2. **Dependencies Installed**
   ```bash
   pip install -r requirements.txt
   ```

3. **Optional: PureChain Bridge**
   For blockchain tests (optional):
   ```bash
   # Terminal 1
   cd blockchain_layer
   npm install
   npm start
   ```

## 🔧 Troubleshooting

### Script Fails at Step X

**Check logs:**
```bash
cat paper_evaluation/logs/evaluation.log
```

### Models Not Training

**Check training logs:**
```bash
cat paper_evaluation/logs/leakage_training.log
cat paper_evaluation/logs/impurity_training.log
cat paper_evaluation/logs/corrosion_training.log
```

### Blockchain Tests Skipped

**Start bridge manually:**
```bash
cd blockchain_layer
npm start
```

Then re-run evaluation.

### Missing Dependencies

**Reinstall:**
```bash
pip install -r requirements.txt
cd blockchain_layer && npm install
```

## 📊 Manual Evaluation Steps

If you prefer to run steps individually:

```bash
# 1. Generate data
python scripts/generate_publication_data.py

# 2. Validate data
python scripts/validate_data_quality.py --data data/test_physics.csv

# 3. Train models
python main.py train --data data/train_physics.csv

# 4. Evaluate
python scripts/evaluate_for_paper.py --test-data data/test_physics.csv

# 5. Test blockchain (optional)
cd blockchain_layer && npm start
# In another terminal:
python -c "from blockchain_layer.purechain_interface import PureChainInterface; pc = PureChainInterface(); print(pc.health_check())"
```

## 📝 Customization

### Change Output Directory

Edit the script:
```bash
OUTPUT_DIR="my_custom_output"
```

### Skip Blockchain Tests

Comment out Step 6 in the script.

### Add More Baselines

Edit `scripts/evaluate_for_paper.py` and add your baseline in `compare_baselines()` method.

## 🎓 Citation

If you use this evaluation framework, please cite:

```bibtex
@article{predblock2025,
  title={PredBlock: AI-Blockchain Framework for Predictive Maintenance of CCS Pipelines},
  author={Your Name},
  journal={Journal Name},
  year={2025},
  note={Physics-based simulation validated against IEAGHG, DNV GL, and NIST standards}
}
```

## 📧 Support

For issues or questions:
1. Check `paper_evaluation/logs/` for error messages
2. Review `PUBLICATION_SUMMARY.md` for guidance
3. Consult `docs/` for detailed documentation

---

**Ready to generate publication materials?** Run the script and get all metrics in one go! 🚀
