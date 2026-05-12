# Programmer: Amna Ali + Abdullah Mohammedi
import argparse
import json
import os
import queue
import re
import threading
import time
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import urlopen

import numpy as np
import pandas as pd
import requests


API_BASE_URL  = "https://api.aladhan.com/v1/gToHCalendar"
OPEN_METEO_URL = "https://archive-api.open-meteo.com/v1/archive"
NOMINATIM_URL  = "https://nominatim.openstreetmap.org/search"

REQUIRED_COLUMNS = [
    "Dealer Initials",
    "Dealer Name",
    "Dealer City",
    "Job Card Date",
    "Job Card Number",
    "Part Code",
    "Part Description",
    "Category",
    "Quantity",
    "Total Price",
    "Vehicle Name",
    "Model Year",
]


#Column Normalization
def _normalize_col(col_name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(col_name).lower())


def _build_column_map(df: pd.DataFrame) -> Dict[str, str]:
    lookup = {_normalize_col(c): c for c in df.columns}
    mapping = {}
    for req in REQUIRED_COLUMNS:
        normalized = _normalize_col(req)
        if normalized in lookup:
            mapping[lookup[normalized]] = req

    synonyms = {
        "jobcarddate":     "Job Card Date",
        "jobcardnumber":   "Job Card Number",
        "jobcardno":       "Job Card Number",
        "jobcard":         "Job Card Number",
        "partcode":        "Part Code",
        "partdescription": "Part Description",
        "vehicle":         "Vehicle Name",
        "vehiclemodel":    "Vehicle Name",
        "totalprice":      "Total Price",
        "dealercity":      "Dealer City",
        "dealername":      "Dealer Name",
        "dealerinitials":  "Dealer Initials",
        "modelyear":       "Model Year",
    }
    for normalized, target in synonyms.items():
        if normalized in lookup and target not in mapping.values():
            mapping[lookup[normalized]] = target

    return mapping


#Read File and merge
def read_uploaded_files(file_paths: List[str]) -> pd.DataFrame:
    all_frames = []

    for file_path in file_paths:
        ext = os.path.splitext(file_path)[1].lower()

        if ext == ".csv":
            frame = pd.read_csv(file_path)
            frame = frame.rename(columns=_build_column_map(frame))
            all_frames.append(frame)
            continue

        if ext in {".xlsx", ".xls"}:
            workbook = pd.ExcelFile(file_path)
            for sheet_name in workbook.sheet_names:
                frame = workbook.parse(sheet_name=sheet_name)
                frame = frame.rename(columns=_build_column_map(frame))
                frame["_source_sheet"] = sheet_name
                all_frames.append(frame)
            continue

        raise ValueError(f"Unsupported file type: {file_path}")

    if not all_frames:
        raise ValueError("No valid data found in uploaded files")

    merged = pd.concat(all_frames, ignore_index=True)
    return merged


#Categorization of Parts
def categorize_part(part_desc: str) -> str:
    d = str(part_desc).lower()
    if any(x in d for x in ["oil filter", "air filter", "fuel filter", "filter"]):
        return "Filters"
    if any(x in d for x in ["brake pad", "brake shoe", "disc", "rotor"]):
        return "Brakes"
    if any(x in d for x in ["belt", "timing belt", "fan belt"]):
        return "Belts"
    if any(x in d for x in ["engine oil", "lubricant"]):
        return "Lubricants"
    if any(x in d for x in ["plug", "coil"]):
        return "Ignition"
    if any(x in d for x in ["sensor"]):
        return "Sensors"
    if any(x in d for x in ["pump"]):
        return "Pumps"
    return "Other"


#Eid Fetching from Aladhan API
def _get_month_hijri_calendar(month: int, year: int) -> List[dict]:
    url = f"{API_BASE_URL}/{month}/{year}?{urlencode({'adjustment': 0})}"
    with urlopen(url, timeout=5) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if payload.get("code") != 200:
        return []
    return payload.get("data", [])


def fetch_eid_dates(years: List[int]) -> List[pd.Timestamp]:
    eid_dates: List[pd.Timestamp] = []

    for year in sorted(set(years)):
        for month in range(1, 13):
            try:
                month_data = _get_month_hijri_calendar(month, year)
            except (URLError, TimeoutError, ValueError):
                continue

            for day_entry in month_data:
                hijri    = day_entry.get("hijri", {})
                holidays = [h.lower() for h in hijri.get("holidays", [])]
                if not holidays:
                    continue

                is_eid = any("eid" in h for h in holidays)
                if not is_eid:
                    continue

                gregorian_date = day_entry.get("gregorian", {}).get("date")
                if not gregorian_date:
                    continue

                # API date format is DD-MM-YYYY
                parsed = pd.to_datetime(gregorian_date, format="%d-%m-%Y", errors="coerce")
                if pd.notna(parsed):
                    eid_dates.append(parsed.normalize())

    return sorted(set(eid_dates))


def fetch_eid_dates_bounded(years: List[int], total_timeout: float = 90.0) -> List[pd.Timestamp]:
    """
    Wraps fetch_eid_dates with a hard wall-clock time limit.
    If the Aladhan API is unreachable, the calls time out (5 s each × 120 calls = up to 10 min).
    This wrapper caps that at `total_timeout` seconds and returns whatever was found so far.
    """
    result_box: list = []
    q: queue.Queue = queue.Queue()

    def _worker() -> None:
        q.put(fetch_eid_dates(years))

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    try:
        result_box = q.get(timeout=total_timeout)
    except queue.Empty:
        print(f"  WARNING: Eid date API timed out after {total_timeout:.0f}s — continuing without Eid data")
        result_box = []
    return result_box


#Geocoding city names to lat/lon via OpenStreetMap Nominatim API
def geocode_city(city_name: str) -> Optional[Tuple[float, float]]:
    """
    Convert a single city name to (latitude, longitude) using the free
    OpenStreetMap Nominatim API.

    - Appends ', Pakistan' to every query so results are country-specific.
    - Returns None if the city cannot be geocoded (row will get NaN).
    - No files are read or written — purely in-memory per run.
    """
    headers = {"User-Agent": "kia-parts-weather-pipeline/1.0"}
    query   = f"{city_name.strip()}, Pakistan"
    params  = {"q": query, "format": "json", "limit": 1}

    try:
        resp    = requests.get(NOMINATIM_URL, params=params, headers=headers, timeout=10)
        results = resp.json()
        if results:
            lat = float(results[0]["lat"])
            lon = float(results[0]["lon"])
            return (lat, lon)
        else:
            print(f"  WARNING: Could not geocode '{city_name}' -- Precipitation will be NaN")
            return None
    except Exception as e:
        print(f"  WARNING: Geocoding error for '{city_name}': {e}")
        return None


def geocode_all_cities(
    cities: List[str],
) -> Dict[str, Optional[Tuple[float, float]]]:
    """
    Geocode every unique dealer city found in the dataset.

    - Iterates through unique city names only (not every row).
    - Stores results in a plain dict for the duration of this run:
        { "Karachi": (24.8607, 67.0011), "Lahore": (31.5497, 74.3436), ... }
    - Respects Nominatim's 1-request-per-second rate limit.
    - Cities that fail geocoding are stored as None and will have NaN precipitation.
    """
    coords: Dict[str, Optional[Tuple[float, float]]] = {}

    print(f"\nGeocoding {len(cities)} unique dealer cities from dataset...")
    for city in cities:
        city_clean = str(city).strip()
        if not city_clean or city_clean in coords:
            continue

        result = geocode_city(city_clean)
        coords[city_clean] = result

        if result:
            print(f"  {city_clean} -> lat={result[0]:.4f}, lon={result[1]:.4f}")

        # Nominatim rate limit: max 1 request per second
        time.sleep(1.1)

    successful = sum(1 for v in coords.values() if v is not None)
    print(f"  Geocoded {successful}/{len(coords)} cities successfully")
    return coords


#Fetching Precipitation from Open-Meteo API
def fetch_weather_for_city(
    city:       str,
    lat:        float,
    lon:        float,
    start_date: date,
    end_date:   date,
) -> Dict[str, float]:
    """
    Fetch daily precipitation sum (mm) from the Open-Meteo archive API
    for one city over its full date range.
    Only precipitation_sum is requested — no temperature.
    Returns a dict keyed by date string:
        { "2024-01-15": 0.0, "2024-01-16": 3.2, ... }
    Returns an empty dict if the API call fails.
    """
    params = {
        "latitude":   lat,
        "longitude":  lon,
        "start_date": start_date.isoformat(),
        "end_date":   end_date.isoformat(),
        "daily":      "precipitation_sum",   # only precipitation, no temperature
        "timezone":   "Asia/Karachi",
    }

    precipitation_by_date: Dict[str, float] = {}

    try:
        resp = requests.get(OPEN_METEO_URL, params=params, timeout=20)
        resp.raise_for_status()
        data  = resp.json()
        daily = data.get("daily", {})
        dates = daily.get("time", [])
        rains = daily.get("precipitation_sum", [])

        for d, r in zip(dates, rains):
            precipitation_by_date[d] = r if r is not None else 0.0

        print(f"  Open-Meteo: {city} -> {len(precipitation_by_date)} days fetched "
              f"({start_date} to {end_date})")

    except Exception as e:
        print(f"  WARNING: Open-Meteo fetch failed for '{city}': {e}")

    return precipitation_by_date


#Complete Weather Lookup Construction for All Cities
def build_weather_lookup(
    df: pd.DataFrame,
) -> Dict[str, Dict[str, float]]:
    """
    Build a full precipitation lookup for every unique dealer city in the
    cleaned dataset. City names come directly from the Dealer City column.

    Process:
    1. Extract unique city names and their date ranges from the dataset.
    2. Geocode each city name to lat/lon via Nominatim (no file upload needed).
    3. Fetch precipitation from Open-Meteo for each city's date range.
    4. Return a nested lookup:
         { city_name: { "YYYY-MM-DD": precipitation_mm } }
    """

    #Find unique cities and their date ranges from the dataset itself
    city_date_ranges: Dict[str, Tuple[date, date]] = {}
    for city, group in df.groupby("Dealer City"):
        city_clean = str(city).strip()
        dates = pd.to_datetime(group["Jobcard Date"]).dt.date
        city_date_ranges[city_clean] = (dates.min(), dates.max())

    unique_cities = list(city_date_ranges.keys())

    #Geocode all cities — lat/lon fetched from city name automatically
    coords = geocode_all_cities(unique_cities)

    #Fetch precipitation for each successfully geocoded city
    weather_lookup: Dict[str, Dict[str, float]] = {}

    print(f"\nFetching precipitation data from Open-Meteo for {len(coords)} cities...")
    for city, date_range in city_date_ranges.items():
        if coords.get(city) is None:
            print(f"  SKIPPING '{city}' -- geocoding failed, Precipitation will be NaN")
            continue

        lat, lon         = coords[city]
        start_dt, end_dt = date_range

        weather_lookup[city] = fetch_weather_for_city(
            city, lat, lon, start_dt, end_dt
        )

        # Small pause between API calls
        time.sleep(0.3)

    return weather_lookup


#Attaching Precipitation to Main DataFrame via Merge
def attach_weather_to_df(
    df:             pd.DataFrame,
    weather_lookup: Dict[str, Dict[str, float]],
) -> pd.DataFrame:
    """
    Add a Precipitation column (mm/day) via a vectorized merge instead of
    iterrows, which was O(n) with Python-level overhead and timed out on large
    datasets. 
    """
    df = df.copy()
    df["_city_key"]  = df["Dealer City"].astype(str).str.strip()
    df["_date_key"]  = pd.to_datetime(df["Jobcard Date"]).dt.strftime("%Y-%m-%d")

    # Flatten the nested lookup dict into a small DataFrame for joining
    weather_rows = [
        {"_city_key": city, "_date_key": date_str, "Precipitation": precip}
        for city, day_dict in weather_lookup.items()
        for date_str, precip in day_dict.items()
    ]

    if weather_rows:
        weather_df = pd.DataFrame(weather_rows)
        df = df.merge(weather_df, on=["_city_key", "_date_key"], how="left")
    else:
        df["Precipitation"] = np.nan

    df = df.drop(columns=["_city_key", "_date_key"])

    matched = df["Precipitation"].notna().sum()
    total   = len(df)
    print(f"\n  Precipitation attached: {matched:,} / {total:,} rows "
          f"({100 * matched / total:.1f}% coverage)")

    return df


#Main Preprocessing Function
def preprocess_and_add_cultural_factors(
    merged_df:      pd.DataFrame,
    output_dir:     str,
    final_filename: str,
    run_timestamp:  str,
    include_weather: bool = True,
) -> Tuple[pd.DataFrame, Dict[str, str]]:

    required_minimum = ["Vehicle Name", "Dealer City", "Part Code", "Quantity", "Part Description"]
    missing_minimum  = [c for c in required_minimum if c not in merged_df.columns]
    if missing_minimum:
        raise ValueError(f"Missing required columns after merge: {', '.join(missing_minimum)}")

    date_col = "Job Card Date" if "Job Card Date" in merged_df.columns else "Jobcard Date"
    if date_col not in merged_df.columns:
        raise ValueError("Missing required date column: Job Card Date")

    df = merged_df.copy()
    df = df[df["Vehicle Name"].notna() & df["Dealer City"].notna() & df[date_col].notna()]

    words   = ["carnival", "sorento", "picanto", "stonic", "sportage"]
    pattern = "|".join(words)
    df      = df[df["Vehicle Name"].astype(str).str.lower().str.contains(pattern, na=False)]

    df["Jobcard Date"] = pd.to_datetime(df[date_col], errors="coerce")
    if df["Jobcard Date"].isna().all():
        raise ValueError("No valid datetimes parsed from Job Card Date")

    df["Job_Date"] = df["Jobcard Date"].dt.date
    df = df.sort_values(by=["Job_Date", "Part Code", "Jobcard Date"]).reset_index(drop=True)

    os.makedirs(output_dir, exist_ok=True)

    df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce").fillna(0)
    if "Total Price" in df.columns:
        df["Total Price"] = pd.to_numeric(df["Total Price"], errors="coerce").fillna(0)
    else:
        df["Total Price"] = 0

    df["Daily_Part_Quantity"]  = df.groupby(["Job_Date", "Part Code"])["Quantity"].transform("sum")
    df["Daily_Part_Row_Count"] = df.groupby(["Job_Date", "Part Code"])["Part Code"].transform("count")
    df["Job_Month"]            = df["Jobcard Date"].dt.to_period("M")

    monthly_summary = df.groupby(["Part Code", "Job_Month"]).agg(
        Monthly_Quantity     =("Quantity",   "sum"),
        Monthly_Jobcard_Count=("Part Code",  "count"),
    ).reset_index()

    to_remove = monthly_summary[
        (monthly_summary["Monthly_Quantity"]      < 50) &
        (monthly_summary["Monthly_Jobcard_Count"] < 50)
    ]

    df_filtered = df.merge(
        to_remove[["Part Code", "Job_Month"]],
        on=["Part Code", "Job_Month"],
        how="left",
        indicator=True,
    )
    df_filtered = df_filtered[df_filtered["_merge"] == "left_only"].drop(columns=["_merge"])
    df_filtered["Part Category"] = df_filtered["Part Description"].apply(categorize_part)

    group_columns = {
        "Quantity":             "sum",
        "Job Card Number":      lambda x: ",".join(x.dropna().astype(str).unique()),
        "Part Description":     "first",
        "Vehicle Name":         "first",
        "Dealer City":          "first",
        "Part Category":        "first",
        "Total Price":          "sum",
        "Daily_Part_Quantity":  "first",
        "Daily_Part_Row_Count": "first",
        "Jobcard Date":         "first",
        "Job_Month":            "first",
    }
    if "Dealer Name" in df_filtered.columns:
        group_columns["Dealer Name"] = "first"

    df_daily = df_filtered.groupby(["Job_Date", "Part Code"], as_index=False).agg(group_columns)

    # Standard deviation based filtering
    part_std_stats = df_daily.groupby("Part Code")["Quantity"].agg(
        Std_Dev="std", Mean="mean", Min="min", Max="max", Count="count"
    ).reset_index()
    part_std_stats = part_std_stats.sort_values("Std_Dev", ascending=False)
    std_before_path = os.path.join(
        output_dir, f"part_std_deviation_before_cultural_{run_timestamp}.csv"
    )
    part_std_stats.to_csv(std_before_path, index=False)

    parts_to_keep = part_std_stats[part_std_stats["Std_Dev"].fillna(0) >= 2]["Part Code"]
    df_cultural   = df_daily[df_daily["Part Code"].isin(parts_to_keep)].copy()

    #Cultural Factor Engineering
    df_cultural["Cultural_Factor"] = 0
    df_cultural["Cultural_Event"]  = "None"

    current_year   = datetime.now().year
    min_year       = int(df_cultural["Jobcard Date"].dt.year.min()) if not df_cultural.empty else current_year
    max_year       = int(df_cultural["Jobcard Date"].dt.year.max()) if not df_cultural.empty else current_year
    # Only fetch years present in the data (+1 to catch Eid that falls just after last record).
    years_to_fetch = list(range(min_year, max_year + 2))
    print(f"Fetching Eid dates for {len(years_to_fetch)} years ({years_to_fetch[0]}–{years_to_fetch[-1]})...")
    eid_dates = fetch_eid_dates_bounded(years_to_fetch, total_timeout=90.0)

    for eid_date in eid_dates:
        start_date = eid_date - pd.Timedelta(days=7)
        end_date   = eid_date
        mask = (
            (df_cultural["Jobcard Date"] >= start_date) &
            (df_cultural["Jobcard Date"] <= end_date)
        )
        df_cultural.loc[mask, "Cultural_Factor"] = 1
        df_cultural.loc[mask, "Cultural_Event"]  = "Eid"

    wedding_months = [1, 6, 7, 11, 12]
    wedding_mask   = df_cultural["Jobcard Date"].dt.month.isin(wedding_months)
    df_cultural.loc[wedding_mask, "Cultural_Factor"] = 1
    df_cultural.loc[
        wedding_mask & (df_cultural["Cultural_Event"] == "None"), "Cultural_Event"
    ] = "Wedding Season"
    df_cultural.loc[
        wedding_mask & (df_cultural["Cultural_Event"] == "Eid"), "Cultural_Event"
    ] = "Eid, Wedding Season"

    #Weather API Integration (Precipitation Only)
    if include_weather:
        print("\n--- Weather Data Integration (Precipitation Only) ---")
        weather_lookup = build_weather_lookup(df_cultural)
        df_cultural    = attach_weather_to_df(df_cultural, weather_lookup)

    #Save final preprocessed dataset and std deviation stats after cultural factor engineering
    final_output_path = os.path.join(output_dir, final_filename)
    df_cultural.to_csv(final_output_path, index=False)

    std_after = df_cultural.groupby("Part Code")["Quantity"].agg(
        Std_Dev="std", Mean="mean", Min="min", Max="max", Count="count"
    ).reset_index()
    std_after.to_csv(
        os.path.join(output_dir, f"part_std_deviation_cultural_{run_timestamp}.csv"),
        index=False,
    )

    outputs: Dict[str, str] = {
        "final_output":    final_output_path,
        "eid_dates_found": str(len(eid_dates)),
    }
    if include_weather and len(df_cultural) > 0:
        outputs["precipitation_coverage_pct"] = (
            f"{100 * df_cultural['Precipitation'].notna().sum() / len(df_cultural):.1f}%"
        )
    return df_cultural, outputs


#Main function to parse arguments and run the full preprocessing pipeline

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Preprocessing pipeline: sales data + cultural factors + precipitation"
    )
    parser.add_argument(
        "--inputs", nargs="+", required=True,
        help="Uploaded sales file paths (.csv or .xlsx). City names are read from these files."
    )
    parser.add_argument(
        "--output-dir", required=True,
        help="Directory to save processed datasets"
    )
    parser.add_argument(
        "--final-filename", default="",
        help="Name of final output CSV file (auto-generated if not provided)"
    )
    parser.add_argument(
        "--no-weather", action="store_true",
        help="Skip weather API integration (geocoding + precipitation fetch)"
    )

    args          = parser.parse_args()
    include_weather = not args.no_weather
    run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    final_filename = (
        args.final_filename.strip()
        if args.final_filename and args.final_filename.strip()
        else f"preprocessed_data_{'no_weather' if not include_weather else 'with_precipitation'}_{run_timestamp}.csv"
    )

    merged_df = read_uploaded_files(args.inputs)

    processed_df, outputs = preprocess_and_add_cultural_factors(
        merged_df       = merged_df,
        output_dir      = args.output_dir,
        final_filename  = final_filename,
        run_timestamp   = run_timestamp,
        include_weather = include_weather,
    )

    result = {
        "success": True,
        "rows":    int(len(processed_df)),
        "columns": int(len(processed_df.columns)),
        "outputs": outputs,
    }
    print(json.dumps(result))


if __name__ == "__main__":
    main()