import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# -------------------------------------------------------
# Load and prepare data
# -------------------------------------------------------
path = Path("timing_log.csv")
if not path.exists():
    raise FileNotFoundError("timing_log.csv not found — run translation tests first!")

df = pd.read_csv(path, parse_dates=["timestamp"])

# Filter only relevant benchmarked functions
benchmark_funcs = [
    "translate_text_OpenAI_Paid",
    "translate_text_Google_Paid",
    "translate_text_Google_Free"
]
df = df[df["function"].isin(benchmark_funcs)]

# -------------------------------------------------------
# Compute summary statistics
# -------------------------------------------------------
summary = (
    df.groupby("function")["duration_sec"]
    .agg(["count", "mean", "std", "min", "max"])
    .sort_values("mean")
)
print("\n=== MODEL LATENCY SUMMARY (seconds) ===")
print(summary)
print("\n")

# -------------------------------------------------------
# Plot: Average duration by model
# -------------------------------------------------------
plt.figure(figsize=(8, 4))
summary["mean"].plot(
    kind="barh",
    color=["#ffb347", "#77dd77", "#aec6cf"],
    edgecolor="black"
)
plt.title("Average Translation Duration by Model")
plt.xlabel("Seconds (mean per call)")
plt.ylabel("Model")
plt.tight_layout()
plt.show()

# -------------------------------------------------------
# Optional: Boxplot for latency distribution
# -------------------------------------------------------
plt.figure(figsize=(8, 5))
df.boxplot(column="duration_sec", by="function", grid=False)
plt.title("Latency Distribution per Model")
plt.suptitle("")  # remove automatic subtitle
plt.ylabel("Seconds")
plt.tight_layout()
plt.show()

# -------------------------------------------------------
# Optional: Time-series visualization (for repeated tests)
# -------------------------------------------------------
plt.figure(figsize=(10, 5))
for func, group in df.groupby("function"):
    plt.plot(group["timestamp"], group["duration_sec"], label=func)
plt.title("Timing Results Over Time")
plt.xlabel("Timestamp")
plt.ylabel("Duration (s)")
plt.legend()
plt.tight_layout()
plt.show()
