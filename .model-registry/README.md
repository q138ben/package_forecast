# Model Registry

This directory contains the model registry entries for all trained and deployed models.

## Structure

Each model version has a JSON file with the following information:
- Version identifier
- Training timestamp
- Git commit SHA
- Performance metrics
- Artifact locations
- Deployment status
- Metadata

## Example Entry

```json
{
  "version": "v20260227-143052-a1b2c3d",
  "timestamp": "2026-02-27T14:30:52.123456",
  "git_commit": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0",
  "metrics": {
    "location_A": {
      "rmse": 45.2,
      "mae": 32.1,
      "wape": 12.5
    },
    "location_B": {
      "rmse": 52.8,
      "mae": 38.4,
      "wape": 14.2
    },
    "location_C": {
      "rmse": 48.5,
      "mae": 35.7,
      "wape": 13.8
    },
    "summary": {
      "average_rmse": 48.8,
      "average_mae": 35.4,
      "average_wape": 13.5
    }
  },
  "artifacts_location": "gs://package-forecast-artifacts/v20260227-143052-a1b2c3d",
  "status": "production_candidate",
  "trained_locations": ["A", "B", "C"],
  "model_type": "prophet",
  "metadata": {
    "training_framework": "prophet",
    "horizon_days": 30,
    "cv_folds": 5,
    "test_days": 30
  }
}
```

## Status Values

- `registered` - Model has been trained and registered
- `production_candidate` - Model meets quality thresholds for production
- `production` - Model is currently deployed in production
- `deprecated` - Model has been superseded by a newer version
- `archived` - Model artifacts are archived (not actively used)

## Files

- `{version}.json` - Model registry entry
- `production.txt` - Current production version pointer

## Usage

### List All Registered Models
```bash
ls -1 .model-registry/*.json | xargs -n 1 basename | sed 's/.json//'
```

### Get Current Production Version
```bash
cat .model-registry/production.txt
```

### View Model Details
```bash
cat .model-registry/v20260227-143052-a1b2c3d.json | jq
```

### Compare Models
```python
from src.models.artifact_manager import ArtifactManager

manager = ArtifactManager()
comparison = manager.compare_versions('v1', 'v2')
print(comparison)
```

## Maintenance

- Registry entries are created automatically by CI/CD pipeline
- Production pointer is updated when models are promoted
- Old entries can be archived after deprecation
- Keep production model entries indefinitely for audit trail

## Notes

- This directory is tracked in git for version control
- Each entry is immutable once created
- Registry provides full audit trail of model lineage
- Use `scripts/register_model.py` to create new entries
