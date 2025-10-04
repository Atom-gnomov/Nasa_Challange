import pandas as pd

# Read the CSV file
df = pd.read_csv("fishing_year_values.csv")  # Replace with your actual CSV filename

# Drop the 'summer_factor' column
df = df.drop(columns=["summer_factor"])

# Map moon_phase to integers
moon_phase_map = {
    "New Moon": 0,
    "First Quarter": 1,
    "Full Moon": 2,
    "Last Quarter": 3,
    "Waning": 4,
    "Waxing": 5
}
df["moon_phase"] = df["moon_phase"].map(moon_phase_map)

# Save the processed data to a new CSV
df.to_csv("processed_data.csv", index=False)

print("Processed CSV saved as 'processed_data.csv'.")
