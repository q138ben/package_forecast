"""
Generate a comprehensive data profile report.
"""

import argparse

import pandas as pd


def generate_profile(input_path: str, output_path: str):
    """Generate data profile report."""
    print(f"Loading data from {input_path}...")
    df = pd.read_csv(input_path)

    print("Generating profile report (this may take a moment)...")

    # Simple profile generation without heavy dependencies
    profile_html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Data Profile Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; }}
        .section {{ margin: 30px 0; }}
        h1, h2 {{ color: #333; }}
    </style>
</head>
<body>
    <h1>Data Profile Report</h1>
    <p>Generated: {pd.Timestamp.now()}</p>
    
    <div class="section">
        <h2>Overview</h2>
        <table>
            <tr><th>Property</th><th>Value</th></tr>
            <tr><td>Rows</td><td>{len(df)}</td></tr>
            <tr><td>Columns</td><td>{len(df.columns)}</td></tr>
        </table>
    </div>
    
    <div class="section">
        <h2>Column Statistics</h2>
        {df.describe().to_html()}
    </div>
    
    <div class="section">
        <h2>Missing Values</h2>
        <table>
            <tr><th>Column</th><th>Missing</th><th>Percentage</th></tr>
"""

    for col in df.columns:
        missing = df[col].isnull().sum()
        pct = (missing / len(df)) * 100
        profile_html += f"            <tr><td>{col}</td><td>{missing}</td><td>{pct:.2f}%</td></tr>\n"

    profile_html += """
        </table>
    </div>
</body>
</html>
"""

    with open(output_path, "w") as f:
        f.write(profile_html)

    print(f"Profile report saved to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Generate data profile report")
    parser.add_argument("--input", required=True, help="Input CSV file")
    parser.add_argument(
        "--output", default="data-profile.html", help="Output HTML report"
    )
    args = parser.parse_args()

    generate_profile(args.input, args.output)


if __name__ == "__main__":
    main()
