"""Entry point. From a clean checkout: pip install -r requirements.txt && python run.py"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from clean import get_clean_tickets, attendance_only
from lot_anomaly import sku_anomaly_scan
import report


def main():
    print("Loading and cleaning data...")
    tickets, agents, orders, customers, products = get_clean_tickets()
    att = attendance_only(tickets)

    print("Running anomaly scan...")
    scan = sku_anomaly_scan(att, products)
    flagged = scan[scan["flagged"]]["product_name"].tolist()
    print(f"  Flagged SKU(s): {flagged or 'none'}")

    print("Building report...")
    report.build()

    if (os.environ.get("GROQ_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")) and flagged:
        print("\nAI key found — running optional defect-summarization step...")
        import defect_summarizer as ds
        for name in flagged:
            result = ds.summarize_flagged_tickets(att, products, name)
            if result is not None:
                print(f"\nDominant failure modes for {name}:")
                print(ds.dominant_failure_mode(result).head(10).to_string(index=False))
    else:
        print("\n(Optional AI-assist step skipped — set GROQ_API_KEY or ANTHROPIC_API_KEY to enable it. "
              "Core report above does not depend on it.)")

    print("\nDone. Open outputs/report.html in a browser.")


if __name__ == "__main__":
    main()
