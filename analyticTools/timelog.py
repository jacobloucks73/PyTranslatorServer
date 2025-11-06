import csv
import time
from datetime import datetime
from contextlib import contextmanager
from pathlib import Path

# =======================================================
# Dual-output timing block
# =======================================================

@contextmanager
def time_block(session_id: str, function: str, phase: str):
    """
    Measures wall-clock duration for a code block.
    Writes timing info to both the general system CSV (timing_log.csv)
    and a focused model benchmarking CSV (model_timing_log.csv).
    """
    start_time = time.time()
    timestamp = datetime.now()

    try:
        yield
    finally:
        end_time = time.time()
        duration = end_time - start_time

        # Prepare record
        record = {
            "timestamp": timestamp,
            "session_id": session_id,
            "function": function,
            "phase": phase,
            "duration_sec": round(duration, 6)
        }

        # === Primary CSV (system-wide) ===
        sys_log = Path("System_timing_log.csv")
        write_csv_record(sys_log, record)

        # === Secondary CSV (model-specific) ===
        model_log = Path("Model_timing_log.csv")
        # Filter to only model benchmarking calls
        if any(tag in function.lower() for tag in [
            "openai", "google_paid", "google_free"
        ]):
            write_csv_record(model_log, record)

        # Optional: print live output
        #print(f"⏱ [{function}] {phase} = {duration:.3f}s")


def write_csv_record(path: Path, record: dict):
    """Appends a single record to the given CSV, creating headers if missing."""
    file_exists = path.exists()
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=record.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(record)
