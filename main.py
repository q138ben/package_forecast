"""
Main entry point for training, forecasting, and running the forecast service.

Usage:
    python main.py train     # Train models for all locations
    python main.py forecast  # Generate forecasts using trained models
    python main.py serve     # Start the API server
"""

import argparse
from src.models.train import train_all_locations
from src.models.forecast import forecast_all_locations


def train(data_path, artifacts_dir):
    """Train forecasting models for all locations."""
    print("Starting training pipeline...")
    try:
        train_all_locations(data_path=data_path, artifacts_dir=artifacts_dir)
    except Exception as e:
        raise RuntimeError(f"Training failed: {e}")


def forecast(artifacts_dir):
    """Generate forecasts using trained models for all locations."""
    print("Starting forecasting pipeline...")
    try:
        forecast_all_locations(artifacts_dir=artifacts_dir)
    except Exception as e:
        raise RuntimeError(f"Forecasting failed: {e}")


def serve():
    """Start the FastAPI server."""
    import uvicorn
    from src.api.app import app

    print("Starting API server...")
    print("API documentation available at: http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Package Forecast CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Train command
    train_parser = subparsers.add_parser("train", help="Train models for all locations")
    train_parser.add_argument("--data-path", type=str, default="data-4-.csv", help="Path to input data CSV")
    train_parser.add_argument("--artifacts-dir", type=str, default="artifacts", help="Directory to save models and artifacts")

    # Forecast command
    forecast_parser = subparsers.add_parser("forecast", help="Generate forecasts using trained models")
    forecast_parser.add_argument("--artifacts-dir", type=str, default="artifacts", help="Directory containing models and artifacts")

    # Serve command
    subparsers.add_parser("serve", help="Start the API server")

    args = parser.parse_args()

    if args.command == "train":
        train(data_path=args.data_path, artifacts_dir=args.artifacts_dir)
    elif args.command == "forecast":
        forecast(artifacts_dir=args.artifacts_dir)
    elif args.command == "serve":
        serve()
