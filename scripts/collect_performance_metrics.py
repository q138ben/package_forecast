"""
Collect performance metrics from deployed service.
"""

import argparse
import json
import sys
import time
from datetime import datetime
from zipfile import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.config import get_project_config

try:
    from google.cloud import monitoring_v3

    GOOGLE_CLOUD_AVAILABLE = True
except ImportError:
    GOOGLE_CLOUD_AVAILABLE = False
    print("Warning: google-cloud-monitoring not installed")


def collect_metrics(project_id: str, service_name: str, output_path: str):
    """Collect performance metrics from Cloud Monitoring."""

    if not GOOGLE_CLOUD_AVAILABLE:
        print("Skipping metric collection - google-cloud-monitoring not available")
        with open(output_path, "w") as f:
            json.dump({"error": "google-cloud-monitoring not installed"}, f)
        return

    client = monitoring_v3.MetricServiceClient()
    project_name = f"projects/{project_id}"

    # Define time range (last 24 hours)
    now = time.time()
    seconds = int(now)
    nanos = int((now - seconds) * 10**9)
    interval = monitoring_v3.TimeInterval(
        {
            "end_time": {"seconds": seconds, "nanos": nanos},
            "start_time": {"seconds": (seconds - 86400), "nanos": nanos},
        }
    )

    metrics_to_collect = {
        "request_count": "run.googleapis.com/request_count",
        "request_latencies": "run.googleapis.com/request_latencies",
        "container_cpu_utilization": "run.googleapis.com/container/cpu/utilization",
        "container_memory_utilization": "run.googleapis.com/container/memory/utilization",
    }

    collected_metrics = {
        "timestamp": datetime.utcnow().isoformat(),
        "project_id": project_id,
        "service_name": service_name,
        "metrics": {},
    }

    for metric_name, metric_type in metrics_to_collect.items():
        try:
            results = client.list_time_series(
                request={
                    "name": project_name,
                    "filter": f'metric.type = "{metric_type}" AND resource.labels.service_name = "{service_name}"',
                    "interval": interval,
                    "view": monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
                }
            )

            values = []
            for result in results:
                for point in result.points:
                    values.append(point.value.double_value or point.value.int64_value)

            if values:
                collected_metrics["metrics"][metric_name] = {
                    "count": len(values),
                    "mean": sum(values) / len(values) if values else 0,
                    "min": min(values),
                    "max": max(values),
                }
            else:
                collected_metrics["metrics"][metric_name] = {
                    "count": 0,
                    "message": "No data available",
                }

        except Exception as e:
            collected_metrics["metrics"][metric_name] = {"error": str(e)}

    # Save metrics
    with open(output_path, "w") as f:
        json.dump(collected_metrics, f, indent=2)

    print(f"Collected metrics for {len(collected_metrics['metrics'])} metric types")
    print(f"Metrics saved to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Collect performance metrics")

    # Get defaults from environment
    config = get_project_config()

    parser.add_argument(
        "--project-id", default=config.get("project_id"), help="GCP project ID"
    )
    parser.add_argument(
        "--service-name",
        default=config.get("service_name"),
        help="Cloud Run service name",
    )
    parser.add_argument(
        "--output", default="performance-metrics.json", help="Output file"
    )
    args = parser.parse_args()

    if not args.project_id:
        print("Error: GCP_PROJECT_ID not set in environment or .env file")
        sys.exit(1)

    collect_metrics(args.project_id, args.service_name, args.output)


if __name__ == "__main__":
    main()
