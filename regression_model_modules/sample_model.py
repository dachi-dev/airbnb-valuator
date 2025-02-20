from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
import pandas as pd

# Load Sampled Airbnb + Real Estate Data
df = pd.read_csv("sample_airbnb_data.csv")

# Define Features and Target
features = ["Nightly Price", "Bedrooms", "Bathrooms", "Occupancy Rate"]
X = df[features]
y = df["Property Value"]  # Known property value from real estate data

# Train/Test Split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Train Regression Model
model = RandomForestRegressor(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# Evaluate Model Performance
predicted_values = model.predict(X_test)
mae = abs(predicted_values - y_test).mean()
print(f"Mean Absolute Error: ${mae:,.2f}")

# Predict average property value from the sample
average_predicted_value = model.predict(X).mean()

# Estimated total Airbnb listings (using capture-recapture or search pagination)
estimated_total_listings = 500_000  # Replace with your estimation

# Calculate total estimated property value
total_airbnb_property_value = average_predicted_value * estimated_total_listings
print(f"Estimated Total Airbnb Property Value: ${total_airbnb_property_value:,.2f}")

