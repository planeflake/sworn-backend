import os
import pickle
import random
import numpy as np
from collections import deque

# Try to import scikit-learn
SKLEARN_AVAILABLE = False
try:
    from sklearn.neural_network import MLPRegressor
    from sklearn.preprocessing import StandardScaler
    SKLEARN_AVAILABLE = True
except ImportError:
    print("Warning: scikit-learn not available. Neural network features will be disabled.")
    SKLEARN_AVAILABLE = False

def create_trader_nn_model(input_shape):
    """Create a neural network model for trader state evaluation."""
    if not SKLEARN_AVAILABLE:
        print("Warning: scikit-learn is not available, neural network features will be disabled")
        return None
    
    # Create MLPRegressor with similar architecture to the TensorFlow model
    model = {
        'model': MLPRegressor(
            hidden_layer_sizes=(128, 64, 32),  # Similar to the TF model
            activation='relu',
            solver='adam',
            alpha=0.0001,  # L2 regularization
            batch_size='auto',
            learning_rate='constant',
            learning_rate_init=0.001,
            max_iter=200,
            random_state=42,
            early_stopping=True
        ),
        'scaler': StandardScaler(),  # For feature normalization
        'is_fitted': False
    }
    
    return model


def save_model(model, path="models/trader_nn_model.pkl"):
    """Save the neural network model."""
    if not SKLEARN_AVAILABLE or model is None:
        print("Warning: Cannot save model - scikit-learn not available or model is None")
        return
        
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    full_path = os.path.join(base_dir, path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    
    with open(full_path, 'wb') as f:
        pickle.dump(model, f)


def load_model(path="models/trader_nn_model.pkl"):
    """Load the neural network model."""
    if not SKLEARN_AVAILABLE:
        print("Warning: scikit-learn is not available, cannot load neural network model")
        return None
        
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    full_path = os.path.join(base_dir, path)
    if os.path.exists(full_path):
        try:
            with open(full_path, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            print(f"Error loading model: {e}")
    return None


class ExperienceBuffer:
    """Buffer to store trader experiences for training."""
    
    def __init__(self, capacity=10000):
        self.capacity = capacity
        self.buffer = deque(maxlen=capacity)
    
    def add(self, state, reward):
        """Add an experience to the buffer."""
        features = state.get_state_features()
        self.buffer.append((features, reward))
    
    def sample(self, batch_size):
        """Sample a batch of experiences."""
        if len(self.buffer) < batch_size:
            return list(self.buffer)
        return random.sample(self.buffer, batch_size)
    
    def __len__(self):
        return len(self.buffer)


def train_model_from_buffer(model, buffer, batch_size=64, epochs=None):
    """Train the neural network model using experiences from the buffer."""
    if not SKLEARN_AVAILABLE:
        print("Warning: scikit-learn is not available, cannot train model")
        return None
        
    if model is None:
        print("Warning: No model to train")
        return None
        
    if len(buffer) < batch_size:
        print(f"Not enough experiences for training (have {len(buffer)}, need {batch_size})")
        return model
    
    # Sample from buffer
    experiences = buffer.sample(batch_size)
    
    # Prepare training data
    X = np.array([exp[0] for exp in experiences])
    y = np.array([exp[1] for exp in experiences])
    
    # Fit scaler if not already fitted
    if not model['is_fitted']:
        print("Fitting scaler for the first time")
        model['scaler'].fit(X)
        model['is_fitted'] = True
    
    # Transform features
    X_scaled = model['scaler'].transform(X)
    
    # For regression, we don't need partial_fit as it's not compatible with MLPRegressor
    # in regression mode. Just use fit() instead.
    print(f"Training model on {len(X)} examples")
    model['model'].fit(X_scaled, y)
    
    return model


def load_experience_buffer(path="data/experience_buffer.pkl"):
    """Load experience buffer from disk."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    full_path = os.path.join(base_dir, path)
    
    if os.path.exists(full_path):
        try:
            with open(full_path, 'rb') as f:
                return pickle.load(f)
        except:
            pass
    
    return ExperienceBuffer()


def save_experience_buffer(buffer, path="data/experience_buffer.pkl"):
    """Save experience buffer to disk."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    full_path = os.path.join(base_dir, path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    
    with open(full_path, 'wb') as f:
        pickle.dump(buffer, f)