"""
PredBlock: AI-Blockchain Framework for CCS Pipeline Monitoring
Main entry point for the system
"""

import argparse
import yaml
from ai_layer.data_simulator import PipelineDataSimulator
from ai_layer.models.impurity_tracker import ImpurityTracker
from ai_layer.models.corrosion_predictor import CorrosionPredictor
from ai_layer.models.leakage_detector import LeakageDetector
from ai_layer.models.overpressure_controller import OverpressureController


def generate_data(args):
    """Generate simulated pipeline data"""
    print("Generating simulated pipeline data...")
    
    simulator = PipelineDataSimulator()
    dataset = simulator.generate_dataset(
        n_samples=args.samples,
        anomaly_prob=args.anomaly_prob,
        save_path=args.output
    )
    
    print(f"Generated {len(dataset)} samples")
    print(f"Saved to {args.output}")


def train_models(args):
    """Train all AI models"""
    print("Training AI models...")
    
    import pandas as pd
    
    # Load data
    data = pd.read_csv(args.data)
    print(f"Loaded {len(data)} samples from {args.data}")
    
    # Train Impurity Tracker
    if not args.model or args.model == 'impurity':
        print("\n=== Training Impurity Tracker ===")
        tracker = ImpurityTracker()
        tracker.train(data)
        tracker.save_model()
    
    # Train Corrosion Predictor
    if not args.model or args.model == 'corrosion':
        print("\n=== Training Corrosion Predictor ===")
        predictor = CorrosionPredictor()
        predictor.train(data, epochs=args.epochs)
        predictor.save_model()
    
    # Train Leakage Detector
    if not args.model or args.model == 'leakage':
        print("\n=== Training Leakage Detector ===")
        detector = LeakageDetector()
        detector.train(data)
        detector.save_model()
    
    # Train Overpressure Controller
    if not args.model or args.model == 'overpressure':
        print("\n=== Training Overpressure Controller ===")
        controller = OverpressureController()
        controller.train(total_timesteps=args.timesteps)
    
    print("\nAll models trained successfully!")


def run_monitoring(args):
    """Run real-time monitoring system"""
    print("Starting PredBlock monitoring system...")
    
    # Import monitoring system
    from scripts.monitoring_system import MonitoringSystem
    
    system = MonitoringSystem()
    system.start()


def deploy_contracts(args):
    """Deploy smart contracts to blockchain"""
    print("Deploying smart contracts...")
    
    from scripts.deploy_contracts import deploy_all_contracts
    
    deploy_all_contracts(network=args.network)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='PredBlock CCS Pipeline Monitoring System')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Generate data command
    gen_parser = subparsers.add_parser('generate', help='Generate simulated data')
    gen_parser.add_argument('--samples', type=int, default=10000, help='Number of samples')
    gen_parser.add_argument('--anomaly-prob', type=float, default=0.05, help='Anomaly probability')
    gen_parser.add_argument('--output', type=str, default='data/simulated_pipeline_data.csv', help='Output file')
    
    # Train models command
    train_parser = subparsers.add_parser('train', help='Train AI models')
    train_parser.add_argument('--data', type=str, default='data/simulated_pipeline_data.csv', help='Training data')
    train_parser.add_argument('--model', type=str, choices=['impurity', 'corrosion', 'leakage', 'overpressure'], 
                             help='Specific model to train (default: all)')
    train_parser.add_argument('--epochs', type=int, default=50, help='Training epochs for LSTM')
    train_parser.add_argument('--timesteps', type=int, default=100000, help='Timesteps for RL training')
    
    # Run monitoring command
    monitor_parser = subparsers.add_parser('monitor', help='Run monitoring system')
    monitor_parser.add_argument('--config', type=str, default='config/config.yaml', help='Config file')
    
    # Deploy contracts command
    deploy_parser = subparsers.add_parser('deploy', help='Deploy smart contracts')
    deploy_parser.add_argument('--network', type=str, default='sepolia', help='Blockchain network')
    
    args = parser.parse_args()
    
    if args.command == 'generate':
        generate_data(args)
    elif args.command == 'train':
        train_models(args)
    elif args.command == 'monitor':
        run_monitoring(args)
    elif args.command == 'deploy':
        deploy_contracts(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

