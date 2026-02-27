"""
Data validation script for package forecast data.

Validates data quality, schema, and consistency checks.
"""

import argparse
import json
import sys

import pandas as pd


def validate_schema(df: pd.DataFrame) -> dict:
    """Validate data schema and structure."""
    checks = []

    # Check required columns
    required_columns = ["date", "location_A", "location_B", "location_C"]
    for col in required_columns:
        checks.append(
            {
                "check": f"Column {col} exists",
                "passed": bool(col in df.columns),
                "severity": "critical",
            }
        )

    # Check date column is parseable
    try:
        pd.to_datetime(df["date"])
        checks.append(
            {
                "check": "Date column is valid datetime",
                "passed": True,
                "severity": "critical",
            }
        )
    except Exception as e:
        checks.append(
            {
                "check": "Date column is valid datetime",
                "passed": False,
                "severity": "critical",
                "message": str(e),
            }
        )

    return checks


def validate_data_quality(df: pd.DataFrame) -> dict:
    """Validate data quality checks."""
    checks = []

    # Check for null values
    for col in ["location_A", "location_B", "location_C"]:
        if col in df.columns:
            null_count = int(df[col].isnull().sum())
            null_pct = float((null_count / len(df)) * 100)
            checks.append(
                {
                    "check": f"{col} missing values",
                    "passed": bool(null_count == 0),
                    "severity": "high" if null_count > 0 else "info",
                    "details": f"{null_count} missing ({null_pct:.2f}%)",
                }
            )

    # Check for negative values
    for col in ["location_A", "location_B", "location_C"]:
        if col in df.columns:
            negative_count = int((df[col] < 0).sum())
            checks.append(
                {
                    "check": f"{col} no negative values",
                    "passed": bool(negative_count == 0),
                    "severity": "high",
                    "details": f"{negative_count} negative values",
                }
            )

    # Check for outliers (values > 3 std from mean)
    for col in ["location_A", "location_B", "location_C"]:
        if col in df.columns:
            mean = float(df[col].mean())
            std = float(df[col].std())
            outliers = int(((df[col] - mean).abs() > 3 * std).sum())
            checks.append(
                {
                    "check": f"{col} outliers check",
                    "passed": bool(outliers < len(df) * 0.05),  # Less than 5% outliers
                    "severity": "medium",
                    "details": f"{outliers} potential outliers (>3σ)",
                }
            )

    return checks


def validate_temporal_consistency(df: pd.DataFrame) -> dict:
    """Validate temporal consistency."""
    checks = []

    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")

    # Check date gaps
    date_diffs = df["date"].diff()
    max_gap = int(date_diffs.max().days) if len(date_diffs) > 1 else 0
    checks.append(
        {
            "check": "No large date gaps",
            "passed": bool(max_gap <= 7),  # No gaps larger than 7 days
            "severity": "medium",
            "details": f"Max gap: {max_gap} days",
        }
    )

    # Check for duplicate dates
    duplicate_dates = int(df["date"].duplicated().sum())
    checks.append(
        {
            "check": "No duplicate dates",
            "passed": bool(duplicate_dates == 0),
            "severity": "high",
            "details": f"{duplicate_dates} duplicate dates",
        }
    )

    # Check date range reasonableness
    date_range_days = int((df["date"].max() - df["date"].min()).days)
    checks.append(
        {
            "check": "Sufficient historical data",
            "passed": bool(date_range_days >= 180),  # At least 6 months
            "severity": "medium",
            "details": f"{date_range_days} days of data",
        }
    )

    return checks


def validate_statistical_properties(df: pd.DataFrame) -> dict:
    """Validate statistical properties."""
    checks = []

    for col in ["location_A", "location_B", "location_C"]:
        if col in df.columns:
            # Check variance (data shouldn't be constant)
            variance = float(df[col].var())
            checks.append(
                {
                    "check": f"{col} has variance",
                    "passed": bool(variance > 0),
                    "severity": "high",
                    "details": f"Variance: {variance:.2f}",
                }
            )

            # Check mean is reasonable (not zero or extremely high)
            mean = float(df[col].mean())
            checks.append(
                {
                    "check": f"{col} mean is reasonable",
                    "passed": bool(10 < mean < 10000),
                    "severity": "medium",
                    "details": f"Mean: {mean:.2f}",
                }
            )

    return checks


def run_validation(input_path: str, output_path: str = None) -> dict:
    """Run all validation checks."""
    print(f"Loading data from {input_path}...")
    df = pd.read_csv(input_path)

    print(f"Data shape: {df.shape}")
    print("\nRunning validation checks...")

    all_checks = []
    all_checks.extend(validate_schema(df))
    all_checks.extend(validate_data_quality(df))
    all_checks.extend(validate_temporal_consistency(df))
    all_checks.extend(validate_statistical_properties(df))

    # Summarize results
    passed = sum(1 for c in all_checks if c["passed"])
    failed = len(all_checks) - passed
    critical_failures = sum(
        1 for c in all_checks if not c["passed"] and c.get("severity") == "critical"
    )

    report = {
        "status": "passed" if critical_failures == 0 else "failed",
        "timestamp": pd.Timestamp.now().isoformat(),
        "input_file": input_path,
        "data_shape": list(df.shape),
        "total_checks": len(all_checks),
        "passed_checks": passed,
        "failed_checks": failed,
        "critical_failures": critical_failures,
        "checks": all_checks,
    }

    # Print summary
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    print(f"Status: {report['status'].upper()}")
    print(f"Total Checks: {len(all_checks)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Critical Failures: {critical_failures}")
    print("=" * 60)

    # Print failed checks
    if failed > 0:
        print("\nFailed Checks:")
        for check in all_checks:
            if not check["passed"]:
                severity = check.get("severity", "unknown")
                details = check.get("details", "")
                print(f"  [{severity.upper()}] {check['check']}: {details}")

    # Save report
    if output_path:
        with open(output_path, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\nValidation report saved to {output_path}")

    return report


def main():
    parser = argparse.ArgumentParser(description="Validate package forecast data")
    parser.add_argument("--input", required=True, help="Input CSV file")
    parser.add_argument(
        "--output", default="validation-report.json", help="Output JSON report"
    )
    args = parser.parse_args()

    report = run_validation(args.input, args.output)

    # Exit with error code if validation failed
    if report["status"] == "failed":
        sys.exit(1)


if __name__ == "__main__":
    main()
