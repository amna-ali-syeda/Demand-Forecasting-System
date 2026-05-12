# Developer: Muhammad Hammad Haider

import os
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder


BASE_DIR = Path(__file__).resolve().parent
DATASETS_DIR = BASE_DIR / "datasets"
MODELS_DIR = BASE_DIR / "models"


def _find_latest_preprocessed_input() -> Path:
    """
    Find the latest preprocessed input file.
    Now checks preprocessed_without_weather directory first (which despite its name,
    DOES contain precipitation data added by basic_data_preprocessing.py).
    """
    preferred_dir = DATASETS_DIR / "preprocessed_without_weather"
    if preferred_dir.exists():
        # Match both naming patterns produced by basic_data_preprocessing.py
        candidates = []
        for pattern in [
            "preprocessed_data_without_weather_*.csv",
            "preprocessed_data_with_precipitation_*.csv",
        ]:
            candidates.extend(preferred_dir.glob(pattern))

        candidates = sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)
        if candidates:
            return candidates[0]

    fallback_files = [
        DATASETS_DIR / "filtered_data_with_cultural_dynamic.csv",
        DATASETS_DIR / "daily_merged_parts.csv",
    ]
    for path in fallback_files:
        if path.exists():
            return path

    raise FileNotFoundError("No preprocessed input file found for feature engineering")


def run_feature_engineering() -> dict:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    DATASETS_DIR.mkdir(parents=True, exist_ok=True)

    input_path = _find_latest_preprocessed_input()
    clean_df = pd.read_csv(input_path)

    #Date detection and cleaning
    if "Jobcard Date" in clean_df.columns:
        clean_df["Job_Date"] = pd.to_datetime(clean_df["Jobcard Date"], errors="coerce")
    elif "Job Card Date" in clean_df.columns:
        clean_df["Job_Date"] = pd.to_datetime(clean_df["Job Card Date"], errors="coerce")
    else:
        raise ValueError("No date column found. Expected 'Jobcard Date' or 'Job Card Date'")

    clean_df = clean_df.dropna(subset=["Job_Date", "Part Code", "Quantity"]).copy()
    clean_df["Quantity"] = pd.to_numeric(clean_df["Quantity"], errors="coerce").fillna(0)
    
    #Time features
    clean_df["Day"] = clean_df["Job_Date"].dt.day
    clean_df["WeekDay"] = clean_df["Job_Date"].dt.dayofweek
    clean_df["Month"] = clean_df["Job_Date"].dt.month
    clean_df["Year"] = clean_df["Job_Date"].dt.year
    clean_df["IsWeekend"] = (clean_df["WeekDay"] >= 5).astype(int)
    clean_df["WeekOfYear"] = clean_df["Job_Date"].dt.isocalendar().week.astype(int)
    clean_df["IsMonthStart"] = (clean_df["Day"] <= 7).astype(int)
    clean_df["IsMonthEnd"] = (clean_df["Day"] >= 24).astype(int)
    clean_df["Weekend_x_Month"] = clean_df["IsWeekend"] * clean_df["Month"]
    clean_df = clean_df.sort_values(["Part Code", "Job_Date"])
    
    #Rolling demand features
    clean_df["WeeklyPartAvgQuantity"] = clean_df.groupby("Part Code")["Quantity"].transform(
        lambda x: x.rolling(window=7, min_periods=1).mean()
    )
    clean_df["MonthlyPartAvgQuantity"] = clean_df.groupby("Part Code")["Quantity"].transform(
        lambda x: x.rolling(window=30, min_periods=1).mean()
    )

    clean_df["Rolling_3Days_Quantity"] = clean_df.groupby("Part Code")["Quantity"].transform(
        lambda x: x.rolling(window=3, min_periods=1).mean()
    )
    clean_df["Rolling_14Days_Quantity"] = clean_df.groupby("Part Code")["Quantity"].transform(
        lambda x: x.rolling(window=14, min_periods=1).mean()
    )
    clean_df["Rolling_Quantity_Standard_Deviation"] = clean_df.groupby("Part Code")["Quantity"].transform(
        lambda x: x.rolling(window=7, min_periods=1).std().fillna(0)
    )

    clean_df["DaysSinceLastUse"] = clean_df.groupby("Part Code")["Job_Date"].diff().dt.days.fillna(0)
    clean_df["ZeroDemand_14Day_Rate"] = clean_df.groupby("Part Code")["Quantity"].transform(
        lambda x: x.rolling(window=14, min_periods=1).apply(lambda w: (w == 0).mean())
    )
    clean_df["LastQty_WasZero"] = (
        clean_df.groupby("Part Code")["Quantity"].shift(1).fillna(0) == 0
    ).astype(int)
    clean_df["Demand_Trend"] = clean_df["WeeklyPartAvgQuantity"] - clean_df["MonthlyPartAvgQuantity"]
    clean_df["Demand_Momentum"] = clean_df.groupby("Part Code")["Quantity"].transform(
        lambda x: x.diff().fillna(0)
    )

    clean_df["Total_Part_Usage"] = clean_df.groupby("Part Code")["Quantity"].transform("sum")
    clean_df["Frequency_Of_Part_Orders"] = clean_df.groupby("Part Code").cumcount() + 1
    clean_df["Month_Average_Quantity"] = clean_df.groupby(["Part Code", "Month"])["Quantity"].transform("mean")
    clean_df["Days_Since_Start"] = (clean_df["Job_Date"] - clean_df["Job_Date"].min()).dt.days

    #City features
    clean_df["Dealer City"] = clean_df.get("Dealer City", "Unknown").fillna("Unknown")
    city_demand = clean_df.groupby("Dealer City")["Quantity"].agg(["mean", "std", "count"]).reset_index()
    city_demand.columns = ["Dealer City", "CityAvgDemand", "CityDemandStandardDeviation", "City_Order_Count"]
    city_demand["CityDemandStandardDeviation"] = city_demand["CityDemandStandardDeviation"].fillna(0)
    clean_df = clean_df.merge(city_demand, on="Dealer City", how="left")

    #Encoding features
    le_part = LabelEncoder()
    clean_df["Part_Code_Encoded"] = le_part.fit_transform(clean_df["Part Code"].astype(str))
    le_city = LabelEncoder()
    clean_df["Dealer_City_Encoded"] = le_city.fit_transform(clean_df["Dealer City"].astype(str))

    encoders = {
        "part": le_part,
        "city": le_city,
    }
    with open(MODELS_DIR / "label_encoders.pkl", "wb") as f:
        pickle.dump(encoders, f)

    #Weather features
    has_precipitation = "Precipitation" in clean_df.columns

    if has_precipitation:
        print("  Weather features ENABLED — Precipitation column found in input data")

        # Fill missing precipitation values with 0 
        clean_df["Precipitation"] = pd.to_numeric(
            clean_df["Precipitation"], errors="coerce"
        ).fillna(0)

        # rainy day indicator
        clean_df["isRainy"] = (clean_df["Precipitation"] > 0.0).astype(int)

        # Sort by city and date for correct rolling calculations per city
        clean_df = clean_df.sort_values(["Dealer City", "Job_Date"])

        # Rolling 3-day cumulative rainfall per city
        clean_df["Rolling_3Day_Rain"] = clean_df.groupby("Dealer City")["Precipitation"].transform(
            lambda x: x.rolling(window=3, min_periods=1).sum()
        )

        # Rolling 7-day cumulative rainfall per city
        clean_df["Rolling_7Day_Rain"] = clean_df.groupby("Dealer City")["Precipitation"].transform(
            lambda x: x.rolling(window=7, min_periods=1).sum()
        )

        # Average precipitation over last 14 days per city
        clean_df["Rolling_14Day_Avg_Rain"] = clean_df.groupby("Dealer City")["Precipitation"].transform(
            lambda x: x.rolling(window=14, min_periods=1).mean()
        )

        # Heavy rain indicator: precipitation above 10mm in a single day
        clean_df["isHeavyRain"] = (clean_df["Precipitation"] > 10.0).astype(int)

        # Interaction: rainy day during weekend (may affect workshop visits)
        clean_df["Rain_x_Weekend"] = clean_df["isRainy"] * clean_df["IsWeekend"]

        # Interaction: rain during cultural event period
        if "Cultural_Factor" in clean_df.columns:
            clean_df["Rain_x_Cultural"] = clean_df["isRainy"] * clean_df["Cultural_Factor"]

        # Re-sort by Part Code and date for consistency with rest of pipeline
        clean_df = clean_df.sort_values(["Part Code", "Job_Date"])
    else:
        print("  Weather features DISABLED — no Precipitation column found in input data")

    #Feature list
    all_features = [
        # Time-based features
        "Day",
        "WeekDay",
        "Month",
        "Year",
        "IsWeekend",
        "WeekOfYear",
        "IsMonthStart",
        "IsMonthEnd",
        "Days_Since_Start",
        "Weekend_x_Month",
        # Rolling demand features
        "WeeklyPartAvgQuantity",
        "MonthlyPartAvgQuantity",
        "Rolling_3Days_Quantity",
        "Rolling_14Days_Quantity",
        "Rolling_Quantity_Standard_Deviation",
        "DaysSinceLastUse",
        "Demand_Trend",
        "Demand_Momentum",
        "ZeroDemand_14Day_Rate",
        "LastQty_WasZero",
        # Aggregate features
        "Total_Part_Usage",
        "Frequency_Of_Part_Orders",
        "Month_Average_Quantity",
        # City features
        "CityAvgDemand",
        "CityDemandStandardDeviation",
        "City_Order_Count",
        # Encoded features
        "Part_Code_Encoded",
        "Dealer_City_Encoded",
        # Cultural factor
        "Cultural_Factor",
        # Weather features
        "Precipitation",
        "isRainy",
        "Rolling_3Day_Rain",
        "Rolling_7Day_Rain",
        "Rolling_14Day_Avg_Rain",
        "isHeavyRain",
        "Rain_x_Weekend",
        "Rain_x_Cultural",
    ]

    # Only keep features that actually exist in the dataframe
    existing_features = [f for f in all_features if f in clean_df.columns]
    temp_df = clean_df[existing_features + ["Quantity"]].dropna()

    if temp_df.empty:
        raise ValueError("Feature engineering produced no usable rows")

    #Feature selection based on correlation with target variable (Quantity)
    correlation_matrix = temp_df.corr(numeric_only=True)
    target_corr = correlation_matrix["Quantity"].drop("Quantity").abs().sort_values(ascending=False)
    selected_features = target_corr.head(20).index.tolist()
    #Force included features
    always_include = [
        "ZeroDemand_14Day_Rate", "LastQty_WasZero",
        "Cultural_Factor",
        "Precipitation", "isRainy", "Rolling_3Day_Rain",
        "Rolling_7Day_Rain", "isHeavyRain", "Rain_x_Weekend", "Rain_x_Cultural",
    ]
    for f in always_include:
        if f in clean_df.columns and f not in selected_features:
            selected_features.append(f)
    if len(selected_features) < 6:
        selected_features = target_corr.head(6).index.tolist()

    # Log which weather features made it into the top 20
    weather_feature_names = [
        "Precipitation", "isRainy", "Rolling_3Day_Rain", "Rolling_7Day_Rain",
        "Rolling_14Day_Avg_Rain", "isHeavyRain", "Rain_x_Weekend", "Rain_x_Cultural",
    ]
    selected_weather = [f for f in selected_features if f in weather_feature_names]
    if selected_weather:
        print(f"  Weather features selected by correlation: {selected_weather}")
    else:
        print("  No weather features made it into top 20 by correlation")

    feature_engineered_df = clean_df[selected_features + ["Quantity", "Job_Date"]].dropna()

    #Save feature engineered dataset and encoders
    output_path = DATASETS_DIR / "feature_engineered_dataset.csv"
    feature_engineered_df.to_csv(output_path, index=False)

    with open(MODELS_DIR / "feature_list.pkl", "wb") as f:
        pickle.dump(selected_features, f)

    return {
        "input": str(input_path),
        "output": str(output_path),
        "rows": int(len(feature_engineered_df)),
        "features": int(len(selected_features)),
        "selected_features": selected_features,
        "weather_features_included": selected_weather if has_precipitation else [],
    }


if __name__ == "__main__":
    result = run_feature_engineering()
    print(result)