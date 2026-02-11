"""
Main entry point for training and running the forecast service.

Usage:
    python main.py train   # Train models for all locations
    python main.py serve   # Start the API server
"""
import sys
from src.models.train import train_all_locations


def train():
    """Train forecasting models for all locations."""
    print("Starting training pipeline...")
    results = train_all_locations()
    
    print("\n" + "="*60)
    print("Training Summary:")
    print("="*60)
    for location, result in results.items():
        if 'error' in result:
            print(f"Location {location}: ❌ Failed - {result['error']}")
        else:
            cv = result['cv_metrics']
            test = result['test_metrics']
            print(f"Location {location}: ✓ Success")
            print(f"  CV ({cv['n_folds']}-fold): RMSE={cv['avg_rmse']:.2f}±{cv['std_rmse']:.2f}, MAPE={cv['avg_mape']:.2f}%±{cv['std_mape']:.2f}%")
            print(f"  Final Test:  RMSE={test['rmse']:.2f}, MAPE={test['mape']:.2f}%")


def serve():
    """Start the FastAPI server."""
    import uvicorn
    from src.api.app import app
    
    print("Starting API server...")
    print("API documentation available at: http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python main.py [train|serve]")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == 'train':
        train()
    elif command == 'serve':
        serve()
    else:
        print(f"Unknown command: {command}")
        print("Usage: python main.py [train|serve]")
        sys.exit(1)
