"""
Overpressure Control Model
Reinforcement Learning (PPO) for valve operation optimization
"""

import numpy as np
import pandas as pd
import gym
from gym import spaces
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv
from stable_baselines3.common.callbacks import EvalCallback
from typing import Dict, Tuple
import yaml


class PipelinePressureEnv(gym.Env):
    """Custom Gym environment for pipeline pressure control"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """Initialize environment"""
        super(PipelinePressureEnv, self).__init__()
        
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.pipeline_config = self.config['pipeline']
        
        # State space: [pressure, flow_rate, temperature]
        self.observation_space = spaces.Box(
            low=np.array([0, 0, 0]),
            high=np.array([150, 150, 100]),  # Max values
            dtype=np.float32
        )
        
        # Action space: valve position (0 = closed, 1 = fully open)
        self.action_space = spaces.Box(
            low=np.array([0.0]),
            high=np.array([1.0]),
            dtype=np.float32
        )
        
        # Initialize state
        self.state = None
        self.steps = 0
        self.max_steps = 1000
        
        self.reset()
    
    def reset(self):
        """Reset environment to initial state"""
        # Start with normal conditions
        self.state = np.array([
            self.pipeline_config['normal_pressure'],
            np.random.uniform(self.pipeline_config['flow_rate_min'], 
                            self.pipeline_config['flow_rate_max']),
            self.pipeline_config['normal_temperature']
        ], dtype=np.float32)
        
        self.steps = 0
        return self.state
    
    def step(self, action):
        """Execute one step in the environment"""
        valve_position = action[0]
        
        # Current state
        pressure, flow_rate, temperature = self.state
        
        # Simulate pressure dynamics based on valve position
        # Simplified model: valve opening reduces pressure
        pressure_change = np.random.normal(0, 2)  # Random fluctuation
        
        if valve_position > 0.7:  # Valve more open
            pressure_change -= 3 * valve_position
        elif valve_position < 0.3:  # Valve more closed
            pressure_change += 2 * (1 - valve_position)
        
        new_pressure = pressure + pressure_change
        new_pressure = np.clip(new_pressure, 0, 150)
        
        # Flow rate affected by valve
        new_flow_rate = flow_rate * valve_position + np.random.normal(0, 1)
        new_flow_rate = np.clip(new_flow_rate, 
                                self.pipeline_config['flow_rate_min'],
                                self.pipeline_config['flow_rate_max'])
        
        # Temperature slightly affected by pressure
        new_temperature = temperature + np.random.normal(0, 0.5)
        new_temperature = np.clip(new_temperature, 0, 100)
        
        # Update state
        self.state = np.array([new_pressure, new_flow_rate, new_temperature], dtype=np.float32)
        
        # Calculate reward
        reward = self._calculate_reward(new_pressure, valve_position)
        
        # Check if done
        self.steps += 1
        done = self.steps >= self.max_steps
        
        # Info
        info = {
            'pressure': new_pressure,
            'flow_rate': new_flow_rate,
            'temperature': new_temperature,
            'valve_position': valve_position
        }
        
        return self.state, reward, done, info
    
    def _calculate_reward(self, pressure, valve_position):
        """Calculate reward based on pressure control"""
        target_pressure = self.pipeline_config['normal_pressure']
        alert_pressure = self.pipeline_config['alert_pressure']
        critical_pressure = self.pipeline_config['critical_pressure']
        
        # Reward for maintaining normal pressure
        if abs(pressure - target_pressure) < 5:
            reward = 10.0
        elif abs(pressure - target_pressure) < 10:
            reward = 5.0
        else:
            reward = -abs(pressure - target_pressure) * 0.5
        
        # Penalty for overpressure
        if pressure > alert_pressure:
            reward -= 20.0
        if pressure > critical_pressure:
            reward -= 50.0
        
        # Small penalty for excessive valve movement
        reward -= abs(valve_position - 0.5) * 0.1
        
        return reward
    
    def render(self, mode='human'):
        """Render environment state"""
        print(f"Step: {self.steps}, Pressure: {self.state[0]:.2f} bar, "
              f"Flow: {self.state[1]:.2f} kg/s, Temp: {self.state[2]:.2f}°C")


class OverpressureController:
    """PPO-based controller for overpressure management"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """Initialize controller"""
        self.config_path = config_path
        self.env = None
        self.model = None
    
    def create_env(self):
        """Create and wrap environment"""
        env = PipelinePressureEnv(self.config_path)
        self.env = DummyVecEnv([lambda: env])
        return self.env
    
    def train(self, total_timesteps: int = 100000, save_path: str = "models/saved/overpressure_controller"):
        """Train the PPO controller"""
        
        if self.env is None:
            self.create_env()
        
        print("Training Overpressure Controller...")
        
        # Create PPO model
        self.model = PPO(
            "MlpPolicy",
            self.env,
            verbose=1,
            learning_rate=3e-4,
            n_steps=2048,
            batch_size=64,
            n_epochs=10,
            gamma=0.99,
            gae_lambda=0.95,
            clip_range=0.2,
            tensorboard_log="./logs/ppo_pipeline/"
        )
        
        # Train
        self.model.learn(total_timesteps=total_timesteps)
        
        print(f"\nTraining completed!")
        
        # Save model
        self.save_model(save_path)
        
        return self.model
    
    def predict(self, state: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Predict valve action for given state"""
        action, _states = self.model.predict(state, deterministic=True)
        return action
    
    def evaluate(self, n_episodes: int = 10) -> Dict:
        """Evaluate trained controller"""
        
        if self.env is None:
            self.create_env()
        
        episode_rewards = []
        episode_lengths = []
        
        for episode in range(n_episodes):
            obs = self.env.reset()
            done = False
            episode_reward = 0
            episode_length = 0
            
            while not done:
                action, _states = self.model.predict(obs, deterministic=True)
                obs, reward, done, info = self.env.step(action)
                episode_reward += reward[0]
                episode_length += 1
            
            episode_rewards.append(episode_reward)
            episode_lengths.append(episode_length)
        
        metrics = {
            'mean_reward': np.mean(episode_rewards),
            'std_reward': np.std(episode_rewards),
            'mean_length': np.mean(episode_lengths),
            'std_length': np.std(episode_lengths)
        }
        
        print(f"\nEvaluation Results ({n_episodes} episodes):")
        print(f"Mean Reward: {metrics['mean_reward']:.2f} ± {metrics['std_reward']:.2f}")
        print(f"Mean Length: {metrics['mean_length']:.2f} ± {metrics['std_length']:.2f}")
        
        return metrics
    
    def save_model(self, path: str = "models/saved/overpressure_controller"):
        """Save trained model"""
        self.model.save(path)
        print(f"Model saved to {path}")
    
    def load_model(self, path: str = "models/saved/overpressure_controller"):
        """Load trained model"""
        if self.env is None:
            self.create_env()
        
        self.model = PPO.load(path, env=self.env)
        print(f"Model loaded from {path}")


if __name__ == "__main__":
    # Example usage
    controller = OverpressureController()
    
    # Train
    controller.train(total_timesteps=50000)
    
    # Evaluate
    metrics = controller.evaluate(n_episodes=10)
