import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("System_timing_log.csv", parse_dates=["timestamp"])
print(df.groupby(["function","phase"])["duration_sec"].describe())

# Plot per-phase averages
avg = df.groupby("phase")["duration_sec"].mean().sort_values()
avg.plot(kind="barh", figsize=(10,5))
plt.title("Average Duration per Phase (seconds)")
plt.xlabel("Seconds")
plt.tight_layout()
plt.show()

df = pd.read_csv("Model_timing_log.csv", parse_dates=["timestamp"])
print(df.groupby(["function","phase"])["duration_sec"].describe())

# Plot per-phase averages
avg = df.groupby("phase")["duration_sec"].mean().sort_values()
avg.plot(kind="barh", figsize=(10,5))
plt.title("Average Duration per Phase (seconds)")
plt.xlabel("Seconds")
plt.tight_layout()
plt.show()
