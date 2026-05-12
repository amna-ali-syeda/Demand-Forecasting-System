# Programmer: Muhammad Hammad Haider

import argparse
import json
import os
import pickle
import subprocess
import sys
from datetime import timedelta

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler


def calculate_mape(y_true, y_pred):
    y_true = np.array(y_true)
    y_pred = np.array(y_pred)
    mask = y_true != 0
    if not np.any(mask):
        return 0.0
    # Weight each error by actual quantity 
    weights = y_true[mask]
    errors = np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])
    return float(np.average(errors, weights=weights) * 100)

def ensure_dirs(base_dir):
    for folder in ["models", "metrics", "modelPredictions", "datasets"]:
        os.makedirs(os.path.join(base_dir, folder), exist_ok=True)


def run_feature_engineering_new(base_dir):
    script_path = os.path.join(base_dir, "feature_engineering_new.py")
    if not os.path.exists(script_path):
        raise FileNotFoundError("feature_engineering_new.py not found")

    result = subprocess.run(
        [sys.executable, script_path],
        cwd=base_dir,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def load_training_data(base_dir):
    dataset_path = os.path.join(base_dir, "datasets", "feature_engineered_dataset.csv")
    if not os.path.exists(dataset_path):
        raise FileNotFoundError(
            "feature_engineered_dataset.csv not found. Run feature engineering before retraining."
        )

    df = pd.read_csv(dataset_path)
    if "Job_Date" not in df.columns:
        raise ValueError("Dataset must contain Job_Date column")

    df["Job_Date"] = pd.to_datetime(df["Job_Date"], errors="coerce")
    df = df.dropna(subset=["Job_Date", "Quantity"])

    feature_list_path = os.path.join(base_dir, "models", "feature_list.pkl")
    if os.path.exists(feature_list_path):
        with open(feature_list_path, "rb") as f:
            features = pickle.load(f)
    else:
        features = [
            c
            for c in df.columns
            if c not in {"Quantity", "Job_Date"} and pd.api.types.is_numeric_dtype(df[c])
        ]
        with open(feature_list_path, "wb") as f:
            pickle.dump(features, f)

    missing = [c for c in features if c not in df.columns]
    if missing:
        raise ValueError(f"Feature columns missing in dataset: {', '.join(missing)}")

    return df, features


def train_or_load_model(base_dir, df, features, retrain):
    model_path = os.path.join(base_dir, "models", "random_forest_model.pkl")
    scaler_path = os.path.join(base_dir, "models", "random_forest_scaler.pkl")

    # Automated 80/20 split while preserving chronology to avoid leakage.
    df_sorted = df.sort_values("Job_Date").reset_index(drop=True)
    split_index = max(1, int(len(df_sorted) * 0.8))
    if split_index >= len(df_sorted):
        split_index = len(df_sorted) - 1

    x_train = df_sorted.iloc[:split_index][features]
    y_train = df_sorted.iloc[:split_index]["Quantity"]
    x_test = df_sorted.iloc[split_index:][features]
    y_test = df_sorted.iloc[split_index:]["Quantity"]

    scaler = StandardScaler()
    x_train_scaled = scaler.fit_transform(x_train)
    x_test_scaled = scaler.transform(x_test)

    def fit_and_save():
        fitted_scaler = StandardScaler()
        fitted_x_train = fitted_scaler.fit_transform(x_train)
        fitted_x_test = fitted_scaler.transform(x_test)
        fitted_model = RandomForestRegressor(
            n_estimators=500,
            max_depth=7,
            min_samples_split=50,
            min_samples_leaf=20,
            max_features=0.5,
            max_samples=0.7,
            random_state=42,
            n_jobs=-1,
        )
        fitted_model.fit(fitted_x_train, y_train)
        joblib.dump(fitted_model, model_path)
        joblib.dump(fitted_scaler, scaler_path)
        return fitted_model, fitted_scaler, fitted_x_test

    should_retrain = retrain or not os.path.exists(model_path)
    if should_retrain:
        model, scaler, x_test_scaled = fit_and_save()
    else:
        try:
            model = joblib.load(model_path)
            if os.path.exists(scaler_path):
                scaler = joblib.load(scaler_path)
            x_test_scaled = scaler.transform(x_test)
        except ValueError:
            # Feature set changed; retrain automatically.
            should_retrain = True
            model, scaler, x_test_scaled = fit_and_save()

    preds = np.maximum(model.predict(x_test_scaled), 0)
    ZERO_CLIP_THRESHOLD = 20.0

    recent_14 = df_sorted.iloc[max(0, split_index - 14):split_index]
    zero_parts = set(
        recent_14.groupby("Part_Code_Encoded")["Quantity"]
        .sum()
        .pipe(lambda s: s[s == 0].index)
    )

    test_parts = df_sorted.iloc[split_index:]["Part_Code_Encoded"].values
    preds = np.where(
        np.isin(test_parts, list(zero_parts)) & (preds < ZERO_CLIP_THRESHOLD),
        0.0,
        preds
    )
    metrics = {
        "Model": "Random Forest",
        "MAE": float(mean_absolute_error(y_test, preds)),
        "RMSE": float(np.sqrt(mean_squared_error(y_test, preds))),
        "R2": float(r2_score(y_test, preds)) if len(y_test) > 1 else 0.0,
        "MAPE": float(calculate_mape(y_test, preds)),
        "Train_Samples": int(len(x_train)),
        "Test_Samples": int(len(x_test)),
    }

    metrics_path = os.path.join(base_dir, "metrics", "random_forest_metrics.csv")
    pd.DataFrame([metrics]).to_csv(metrics_path, index=False)

    test_pred_path = os.path.join(base_dir, "modelPredictions", "random_forest_predictions.csv")
    pd.DataFrame({"Actual": y_test.values, "Predicted": preds}).to_csv(test_pred_path, index=False)

    return model, scaler, should_retrain


def generate_future_predictions(base_dir, df, features, model, scaler, months_ahead):
    if months_ahead not in {1, 3, 6}:
        raise ValueError("months_ahead must be one of: 1, 3, 6")

    dataset_start = df["Job_Date"].min()
    last_date = df["Job_Date"].max()
    end_date = last_date + pd.DateOffset(months=months_ahead)
    future_dates = pd.date_range(start=last_date + timedelta(days=1), end=end_date, freq="D")

    if "Part_Code_Encoded" not in df.columns:
        raise ValueError("Part_Code_Encoded is required for Random Forest future prediction")

    if "Month" not in df.columns:
        df = df.copy()
        df["Month"] = pd.to_datetime(df["Job_Date"], errors="coerce").dt.month

    unique_parts = df["Part_Code_Encoded"].dropna().astype(int).unique()
    latest_per_part = df.sort_values("Job_Date").groupby("Part_Code_Encoded").last().reset_index()

    global_medians = {f: float(pd.to_numeric(df[f], errors="coerce").median()) for f in features}

    rows = []
    for part_encoded in unique_parts:
        temp = latest_per_part[latest_per_part["Part_Code_Encoded"] == part_encoded]

        for date in future_dates:
            row = {
                "Day": date.day,
                "WeekDay": date.dayofweek,
                "Month": date.month,
                "Year": date.year,
                "IsWeekend": int(date.dayofweek >= 5),
                "WeekOfYear": int(date.isocalendar().week),
                "IsMonthStart": int(date.day <= 7),
                "IsMonthEnd": int(date.day >= 24),
                "Weekend_x_Month": int(date.dayofweek >= 5) * date.month,
                "Days_Since_Start": int((date - dataset_start).days),
                "Part_Code_Encoded": int(part_encoded),
            }

            hist = df[
                (df["Part_Code_Encoded"] == part_encoded) & (df["Month"] == date.month)
            ]
            for f in ["WeeklyPartAvgQuantity", "MonthlyPartAvgQuantity", "MonthAvg_Qty"]:
                if f in features and f not in row and not hist.empty:
                    row[f] = float(pd.to_numeric(hist[f], errors="coerce").mean())

            for f in features:
                if f in row:
                    continue
                if not temp.empty and f in temp.columns and pd.notna(temp.iloc[0][f]):
                    row[f] = float(temp.iloc[0][f])
                else:
                    row[f] = global_medians.get(f, 0.0)

            row["_date"] = date
            rows.append(row)

    future_df = pd.DataFrame(rows)
    x_future = future_df[features]
    x_future_scaled = scaler.transform(x_future)
    future_df["Predicted_Quantity"] = np.maximum(model.predict(x_future_scaled), 0)

    encoders_path = os.path.join(base_dir, "models", "label_encoders.pkl")
    if os.path.exists(encoders_path):
        with open(encoders_path, "rb") as f:
            encoders = pickle.load(f)
        part_encoder = encoders.get("part")
        if part_encoder is not None:
            future_df["Part_Code"] = part_encoder.inverse_transform(
                future_df["Part_Code_Encoded"].astype(int)
            )
        else:
            future_df["Part_Code"] = future_df["Part_Code_Encoded"].astype(str)
    else:
        future_df["Part_Code"] = future_df["Part_Code_Encoded"].astype(str)

    detailed = future_df.groupby(["_date", "Part_Code"], as_index=False)[
        "Predicted_Quantity"
    ].sum()
    detailed = detailed.rename(columns={"_date": "Date"})
    detailed["Date"] = pd.to_datetime(detailed["Date"], errors="coerce")
    detailed = detailed.dropna(subset=["Date"]).sort_values(["Date", "Part_Code"])

    daily = future_df.groupby("_date", as_index=False)["Predicted_Quantity"].sum()
    daily.columns = ["Date", "Total_Predicted_Quantity"]

    output_file = os.path.join(base_dir, "modelPredictions", "random_forest_future_predictions.csv")
    detailed.assign(Date=detailed["Date"].dt.strftime("%Y-%m-%d")).to_csv(
        output_file, index=False
    )

    daily_rows_json = [
        {
            "Date": d.strftime("%Y-%m-%d"),
            "Total_Predicted_Quantity": float(q),
        }
        for d, q in zip(daily["Date"], daily["Total_Predicted_Quantity"])
    ]

    detailed_rows_json = [
        {
            "Date": d.strftime("%Y-%m-%d"),
            "Part_Code": str(p),
            "Predicted_Quantity": float(q),
        }
        for d, p, q in zip(
            detailed["Date"], detailed["Part_Code"], detailed["Predicted_Quantity"]
        )
    ]

    return {
        "dates": [r["Date"] for r in daily_rows_json],
        "quantities": [r["Total_Predicted_Quantity"] for r in daily_rows_json],
        "rows": detailed_rows_json,
        "daily_rows": daily_rows_json,
        "output_file": output_file,
    }


def main():
    parser = argparse.ArgumentParser(description="Random Forest retrain and prediction pipeline")
    parser.add_argument("--retrain", action="store_true", help="Force retraining of Random Forest")
    parser.add_argument("--months-ahead", type=int, default=1, choices=[1, 3, 6])
    args = parser.parse_args()

    base_dir = os.path.dirname(os.path.abspath(__file__))
    ensure_dirs(base_dir)

    # Always regenerate features using the active pipeline before training/prediction.
    run_feature_engineering_new(base_dir)

    df, features = load_training_data(base_dir)
    model, scaler, retrained = train_or_load_model(base_dir, df, features, args.retrain)
    forecast = generate_future_predictions(base_dir, df, features, model, scaler, args.months_ahead)

    print(
        json.dumps(
            {
                "success": True,
                "retrained": bool(retrained),
                "monthsAhead": int(args.months_ahead),
                "dates": forecast["dates"],
                "quantities": forecast["quantities"],
                "rows": forecast["rows"],
                "output_file": forecast["output_file"],
            }
        )
    )


if __name__ == "__main__":
    main()