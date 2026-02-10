#!/usr/bin/env python
"""
Integration test to verify the complete forecasting pipeline.
"""
import sys
import time
import requests
from pathlib import Path


def test_models_exist():
    """Check that all model files were generated."""
    print("Testing: Model files exist...")
    models_dir = Path("models")
    
    required_files = [
        "location_A_model.pkl",
        "location_A_forecast.csv",
        "location_A_results.json",
        "location_B_model.pkl",
        "location_B_forecast.csv",
        "location_B_results.json",
        "location_C_model.pkl",
        "location_C_forecast.csv",
        "location_C_results.json",
    ]
    
    for filename in required_files:
        filepath = models_dir / filename
        if not filepath.exists():
            print(f"  ❌ Missing: {filename}")
            return False
        print(f"  ✓ Found: {filename}")
    
    return True


def test_api_endpoints():
    """Test API endpoints are responding correctly."""
    print("\nTesting: API endpoints...")
    base_url = "http://localhost:8000"
    
    # Wait a bit for server to be ready
    time.sleep(2)
    
    tests = [
        ("GET /", f"{base_url}/"),
        ("GET /health", f"{base_url}/health"),
        ("GET /forecast/A", f"{base_url}/forecast/A"),
        ("GET /forecast/B", f"{base_url}/forecast/B"),
        ("GET /forecast/C", f"{base_url}/forecast/C"),
        ("GET /forecasts/all", f"{base_url}/forecasts/all"),
    ]
    
    for name, url in tests:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print(f"  ✓ {name}: {response.status_code}")
            else:
                print(f"  ❌ {name}: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"  ❌ {name}: Connection failed - {e}")
            print("     Make sure the API is running: python main.py serve")
            return False
    
    return True


def test_forecast_format():
    """Verify forecast response has correct format."""
    print("\nTesting: Forecast response format...")
    
    try:
        response = requests.get("http://localhost:8000/forecast/A", timeout=5)
        data = response.json()
        
        # Check required fields
        required = ["location", "forecast_generated", "horizon_days", "forecasts"]
        for field in required:
            if field not in data:
                print(f"  ❌ Missing field: {field}")
                return False
        
        # Check forecasts structure
        if len(data["forecasts"]) != 30:
            print(f"  ❌ Expected 30 forecasts, got {len(data['forecasts'])}")
            return False
        
        # Check first forecast entry
        forecast = data["forecasts"][0]
        forecast_fields = ["date", "forecast", "lower_bound", "upper_bound"]
        for field in forecast_fields:
            if field not in forecast:
                print(f"  ❌ Missing forecast field: {field}")
                return False
        
        print(f"  ✓ Response format correct")
        print(f"  ✓ Location: {data['location']}")
        print(f"  ✓ Forecast days: {data['horizon_days']}")
        print(f"  ✓ First forecast date: {forecast['date']}")
        print(f"  ✓ First forecast value: {forecast['forecast']:.2f}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def main():
    """Run all tests."""
    print("="*60)
    print("Package Forecast - Integration Tests")
    print("="*60)
    
    results = []
    
    # Test 1: Model files
    results.append(("Model files", test_models_exist()))
    
    # Test 2: API endpoints (only if API is running)
    print("\n" + "="*60)
    print("API Tests (requires: python main.py serve)")
    print("="*60)
    results.append(("API endpoints", test_api_endpoints()))
    results.append(("Forecast format", test_forecast_format()))
    
    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")
    
    # Exit code
    all_passed = all(result for _, result in results)
    if all_passed:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print("\n⚠️  Some tests failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
