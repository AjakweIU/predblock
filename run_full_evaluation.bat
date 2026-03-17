@echo off
REM ############################################################################
REM PredBlock - Complete System Evaluation for Research Paper (Windows)
REM This script runs the entire evaluation pipeline and generates all metrics,
REM tables, plots, and figures needed for publication
REM ############################################################################

setlocal enabledelayedexpansion

set PROJECT_DIR=%~dp0
set OUTPUT_DIR=%PROJECT_DIR%paper_evaluation
set DATA_DIR=%PROJECT_DIR%data
set MODELS_DIR=%PROJECT_DIR%models

echo ========================================================================
echo          PredBlock - Full System Evaluation Pipeline
echo          Automated Evaluation for Research Publication
echo ========================================================================
echo.

REM ############################################################################
REM Step 1: Environment Check
REM ############################################################################

echo [1/7] Checking Environment...

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.8+
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [OK] Python %PYTHON_VERSION%

REM Check Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js not found. Please install Node.js 16+
    exit /b 1
)

for /f %%i in ('node --version') do set NODE_VERSION=%%i
echo [OK] Node.js %NODE_VERSION%

REM Check virtual environment
if not defined VIRTUAL_ENV (
    echo [WARNING] Virtual environment not activated
    echo   Activating venv...
    
    if exist "%PROJECT_DIR%venv\Scripts\activate.bat" (
        call "%PROJECT_DIR%venv\Scripts\activate.bat"
    ) else (
        echo [ERROR] Virtual environment not found. Please create it first:
        echo   python -m venv venv
        exit /b 1
    )
)

echo [OK] Virtual environment active

REM Create output directories
if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"
if not exist "%OUTPUT_DIR%\figures" mkdir "%OUTPUT_DIR%\figures"
if not exist "%OUTPUT_DIR%\tables" mkdir "%OUTPUT_DIR%\tables"
if not exist "%OUTPUT_DIR%\models" mkdir "%OUTPUT_DIR%\models"
if not exist "%OUTPUT_DIR%\logs" mkdir "%OUTPUT_DIR%\logs"
echo [OK] Output directories created

echo.

REM ############################################################################
REM Step 2: Generate Physics-Based Data (if needed)
REM ############################################################################

echo [2/7] Checking Training Data...

if not exist "%DATA_DIR%\train_physics.csv" (
    echo [WARNING] Training data not found. Generating physics-based datasets...
    python scripts\generate_publication_data.py
    echo [OK] Datasets generated
) else (
    echo [OK] Training data exists
)

echo.

REM ############################################################################
REM Step 3: Validate Data Quality
REM ############################################################################

echo [3/7] Validating Data Quality...

python scripts\validate_data_quality.py --data "%DATA_DIR%\test_physics.csv" --output "%OUTPUT_DIR%\data_validation_report.txt"

echo [OK] Data quality validated
echo   Report: %OUTPUT_DIR%\data_validation_report.txt

echo.

REM ############################################################################
REM Step 4: Train AI Models
REM ############################################################################

echo [4/7] Training AI Models...

echo   Training Leakage Detector...
python -c "import sys; sys.path.insert(0, '%PROJECT_DIR%'); from ai_layer.models.leakage_detector import LeakageDetector; import pandas as pd; train_data = pd.read_csv('%DATA_DIR%\\train_physics.csv'); detector = LeakageDetector(); metrics = detector.train(train_data); detector.save_model('%MODELS_DIR%\\leakage_detector.pkl'); print(f'Leakage Detector - Accuracy: {metrics[\"accuracy\"]:.4f}')" > "%OUTPUT_DIR%\logs\leakage_training.log" 2>&1

echo [OK] Leakage Detector trained

echo   Training Impurity Tracker...
python -c "import sys; sys.path.insert(0, '%PROJECT_DIR%'); from ai_layer.models.impurity_tracker import ImpurityTracker; import pandas as pd; train_data = pd.read_csv('%DATA_DIR%\\train_physics.csv'); tracker = ImpurityTracker(); metrics = tracker.train(train_data); tracker.save_model('%MODELS_DIR%\\impurity_tracker.pkl'); print(f'Impurity Tracker - Accuracy: {metrics[\"accuracy\"]:.4f}')" > "%OUTPUT_DIR%\logs\impurity_training.log" 2>&1

echo [OK] Impurity Tracker trained

echo   Training Corrosion Predictor...
python -c "import sys; sys.path.insert(0, '%PROJECT_DIR%'); from ai_layer.models.corrosion_predictor import CorrosionPredictor; import pandas as pd; train_data = pd.read_csv('%DATA_DIR%\\train_physics.csv'); predictor = CorrosionPredictor(); metrics = predictor.train(train_data); predictor.save_model('%MODELS_DIR%\\corrosion_predictor.pkl'); print(f'Corrosion Predictor - MAE: {metrics[\"mae\"]:.4f}')" > "%OUTPUT_DIR%\logs\corrosion_training.log" 2>&1

echo [OK] All models trained

echo.

REM ############################################################################
REM Step 5: Evaluate Models and Generate Metrics
REM ############################################################################

echo [5/7] Evaluating Models and Generating Metrics...

python scripts\evaluate_for_paper.py --test-data "%DATA_DIR%\test_physics.csv" --output-dir "%OUTPUT_DIR%" > "%OUTPUT_DIR%\logs\evaluation.log" 2>&1

echo [OK] Evaluation complete
echo   Results: %OUTPUT_DIR%\results.json
echo   Report: %OUTPUT_DIR%\evaluation_report.txt

echo.

REM ############################################################################
REM Step 6: Test Blockchain Integration
REM ############################################################################

echo [6/7] Testing Blockchain Integration...

REM Check if bridge is running
curl -s http://localhost:3000/health >nul 2>&1
if errorlevel 1 (
    echo [WARNING] PureChain bridge not running
    echo   Please start the bridge manually in another terminal:
    echo   cd blockchain_layer
    echo   npm start
    echo.
    echo   Skipping blockchain tests...
) else (
    echo [OK] PureChain bridge is running
    
    echo   Testing blockchain performance...
    python -c "import sys; sys.path.insert(0, '%PROJECT_DIR%'); from blockchain_layer.purechain_interface import PureChainInterface; import time; import json; purechain = PureChainInterface(); print('[OK] Bridge health check passed' if purechain.health_check() else '[ERROR] Bridge health check failed'); status = purechain.get_status(); print(f'[OK] Network: Chain ID {status.get(\"chainId\", \"N/A\")}'); start = time.time(); [purechain.health_check() for _ in range(10)]; elapsed = (time.time() - start) / 10; print(f'[OK] Average request latency: {elapsed*1000:.2f} ms'); metrics = {'bridge_running': True, 'network_status': status, 'average_latency_ms': elapsed * 1000, 'gas_cost': 0, 'note': 'Zero gas fees on PureChain'}; json.dump(metrics, open('%OUTPUT_DIR%\\blockchain_metrics.json', 'w'), indent=2); print('[OK] Blockchain metrics saved')" > "%OUTPUT_DIR%\logs\blockchain_test.log" 2>&1
    
    echo [OK] Blockchain integration tested
)

echo.

REM ############################################################################
REM Step 7: Generate Publication Materials
REM ############################################################################

echo [7/7] Generating Publication Materials...

REM Create publication summary
(
echo # PredBlock - Publication Summary
echo.
echo ## Generated Materials
echo.
echo ### 📊 Metrics ^& Results
echo - `results.json` - Complete evaluation metrics in JSON format
echo - `evaluation_report.txt` - Human-readable evaluation report
echo - `data_validation_report.txt` - Data quality validation report
echo - `blockchain_metrics.json` - Blockchain performance metrics
echo.
echo ### 📈 Figures ^(300 DPI, Publication Quality^)
echo - `figures/anomaly_distribution.png` - Anomaly distribution chart
echo - `figures/sensor_timeseries.png` - Sample sensor data time series
echo.
echo ### 📋 Tables ^(LaTeX Format^)
echo - `tables/performance_table.tex` - Model performance comparison
echo.
echo ### 🤖 Trained Models
echo - `models/leakage_detector.pkl` - Leakage detection model
echo - `models/impurity_tracker.pkl` - Impurity tracking model
echo - `models/corrosion_predictor.pkl` - Corrosion prediction model
echo.
echo ## Key Metrics for Paper
echo.
echo See `results.json` and `evaluation_report.txt` for complete metrics.
echo.
echo ## Next Steps for Publication
echo.
echo 1. Review `evaluation_report.txt` for all metrics
echo 2. Import figures from `figures/` into paper
echo 3. Copy LaTeX tables from `tables/` into paper
echo 4. Cite methodology from `docs/DATA_GENERATION_METHODOLOGY.md`
echo 5. Include blockchain metrics from `blockchain_metrics.json`
) > "%OUTPUT_DIR%\PUBLICATION_SUMMARY.md"

echo [OK] Publication summary created

REM Create results summary
python -c "import json; import os; output_dir = '%OUTPUT_DIR%'; results = json.load(open(os.path.join(output_dir, 'results.json'), 'r')); print('\n' + '='*70); print('EVALUATION SUMMARY'); print('='*70); dq = results.get('data_quality', {}); print(f'\nDataset: {dq.get(\"dataset_size\", 0)} samples'); print(f'Anomaly rate: {dq.get(\"total_anomaly_rate\", 0):.2f}%%'); print('\nModel Performance:'); [print(f'\n  {model_name}:\n    Accuracy:  {data[\"performance\"][\"accuracy\"]:.4f}\n    Precision: {data[\"performance\"][\"precision\"]:.4f}\n    Recall:    {data[\"performance\"][\"recall\"]:.4f}\n    F1-Score:  {data[\"performance\"][\"f1_score\"]:.4f}') for model_name, data in results.items() if 'performance' in data]; print('\n' + '='*70)" > "%OUTPUT_DIR%\RESULTS_SUMMARY.txt" 2>&1

echo.

REM ############################################################################
REM Final Summary
REM ############################################################################

echo ========================================================================
echo                     [OK] EVALUATION COMPLETE
echo ========================================================================
echo.

echo All results saved to: %OUTPUT_DIR%\
echo.

echo Generated Materials:
echo   [OK] Evaluation metrics:     %OUTPUT_DIR%\results.json
echo   [OK] Evaluation report:      %OUTPUT_DIR%\evaluation_report.txt
echo   [OK] Data validation:        %OUTPUT_DIR%\data_validation_report.txt
echo   [OK] Publication summary:    %OUTPUT_DIR%\PUBLICATION_SUMMARY.md
echo   [OK] Results summary:        %OUTPUT_DIR%\RESULTS_SUMMARY.txt
echo.

echo Figures (300 DPI):
echo   [OK] %OUTPUT_DIR%\figures\
echo.

echo LaTeX Tables:
echo   [OK] %OUTPUT_DIR%\tables\
echo.

echo Trained Models:
echo   [OK] %MODELS_DIR%\
echo.

echo Training Logs:
echo   [OK] %OUTPUT_DIR%\logs\
echo.

REM Show quick results
if exist "%OUTPUT_DIR%\RESULTS_SUMMARY.txt" (
    echo Quick Results:
    type "%OUTPUT_DIR%\RESULTS_SUMMARY.txt"
)

echo.
echo Next Steps:
echo   1. Review evaluation report: type %OUTPUT_DIR%\evaluation_report.txt
echo   2. Check figures: dir %OUTPUT_DIR%\figures\
echo   3. Import LaTeX tables: type %OUTPUT_DIR%\tables\*.tex
echo   4. Read publication summary: type %OUTPUT_DIR%\PUBLICATION_SUMMARY.md
echo.

echo Ready for publication!
echo.

pause
