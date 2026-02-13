"""
Main entry point for training, forecasting, and running the forecast service.

Usage:
    python main.py train     # Train models for all locations
    python main.py forecast  # Generate forecasts using trained models
    python main.py serve     # Start the API server
"""
import sys
from src.models.train import train_all_locations
from src.models.forecast import forecast_all_locations


def train():
    """Train forecasting models for all locations."""
    print("Starting training pipeline...")
    try:
        train_all_locations()
    except Exception as e:
        raise RuntimeError(f"Training failed: {e}") 


def forecast():
    """Generate forecasts using trained models for all locations."""
    print("Starting forecasting pipeline...")
    try:
        forecast_all_locations()
    except Exception as e:
        raise RuntimeError(f"Forecasting failed: {e}")
    

def serve():
    """Start the FastAPI server."""
    import uvicorn
    from src.api.app import app
    
    print("Starting API server...")
    print("API documentation available at: http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python main.py [train|forecast|serve]")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == 'train':
        train()
    elif command == 'forecast':
        forecast()
    elif command == 'serve':
        serve()
    else:
        print(f"Unknown command: {command}")
        print("Usage: python main.py [train|forecast|serve]")
        sys.exit(1)
