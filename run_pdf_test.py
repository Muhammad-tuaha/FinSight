import os
import sys
import json
import logging

# Load .env file
env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            if "=" in line and not line.startswith("#"):
                k, v = line.strip().split("=", 1)
                os.environ[k] = v

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "finsight"))

from pipeline import run_analysis

logging.basicConfig(level=logging.INFO)

def test_pdfs():
    reports_dir = "reports"
    for pdf_name in os.listdir(reports_dir):
        if pdf_name.endswith(".pdf"):
            pdf_path = os.path.join(reports_dir, pdf_name)
            print(f"\n========================================================")
            print(f"Running pipeline on: {pdf_path}")
            print(f"========================================================")
            try:
                # We pass Unknown to test if Gemini extracts the real company name and sector from document
                result = run_analysis(
                    pdf_path=pdf_path,
                    company_name="Auto-Detect Company",
                    sector=None,
                    output_dir="results/"
                )
                print("\n--- Extracted Metadata ---")
                print(json.dumps(result["metadata"], indent=2))
                print("\n--- Extracted Ratios ---")
                print(json.dumps(result["ratios"]["current"], indent=2))
                print("\n--- Red Flags ---")
                print(json.dumps(result["red_flags"], indent=2))
                if "ratio_formulas" in result:
                    print("\n--- Ratio Formulas Available ---")
                    print("Yes, ratio formulas included.")
            except Exception as e:
                print(f"Error analyzing {pdf_name}: {e}")

if __name__ == "__main__":
    test_pdfs()
