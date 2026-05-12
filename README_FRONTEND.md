# Node.js Frontend for Demand Forecasting System

A modern web-based frontend for the FYP Demand Forecasting System using Node.js/Express, HTML, CSS, and JavaScript.

## Setup

### 1. Install Dependencies

```powershell
npm install
```

### 2. Run the Application

```powershell
npm start
```

The application will start on `http://localhost:5000`

### 3. Project Structure

```
├── server.js                  # Express backend
├── package.json               # Node dependencies
├── templates/                 # Static HTML templates
│   ├── index.html            # Overview page
│   ├── comparison.html       # Model comparison
│   ├── best_model.html       # Best model analysis
│   ├── predictions.html      # Demand predictions
│   ├── benchmark.html        # Benchmark comparison
│   ├── base.html             # Legacy template (unused)
│   └── overview.html         # Legacy template (unused)
├── static/
│   └── css/
│       └── style.css         # Stylesheet
├── metrics/                   # CSV data files
│   ├── *_metrics.csv
│   ├── best_model_comparison.csv
│   └── arima_metrics.csv
└── modelPredictions/          # Prediction CSV files
    └── december_2025_detailed_predictions.csv
```

## Pages

### 1. Overview (http://localhost:5000/index.html)

- Project objectives and methodology
- Quick statistics dashboard (models trained, best MAPE, best R², test samples)
- Key features summary

### 2. Model Comparison (http://localhost:5000/comparison.html)

- Performance metrics table (sortable by MAPE)
- MAPE comparison bar chart
- R² score comparison bar chart
- RMSE vs MAE scatter plot with model labels

### 3. Best Model (http://localhost:5000/best_model.html)

- Winner announcement card
- Performance metrics (MAPE, R², MAE, RMSE)
- Model performance radar chart

### 4. Predictions (http://localhost:5000/predictions.html)

- Summary statistics (total demand, avg daily, peak day, std deviation)
- Daily demand forecast line chart
- Detailed predictions table with dates and quantities

### 5. Benchmark Comparison (http://localhost:5000/benchmark.html)

- ARIMA vs Best Model comparison cards
- MAPE improvement percentage
- R² score improvement
- Side-by-side bar charts for visual comparison

## Features

- ✅ Responsive design (works on desktop & mobile)
- ✅ Interactive charts with Chart.js and Plotly.js
- ✅ Real-time data loading from CSV files via API
- ✅ Professional styling with hover effects
- ✅ Mobile-friendly navigation (no emojis)
- ✅ Performance metrics visualization
- ✅ Lightweight static HTML (no server-side rendering overhead)

## API Endpoints

The Express server provides the following REST API endpoints:

- **GET /api/metrics** - Returns all model metrics from CSV files
- **GET /api/comparison** - Returns best model comparison data
- **GET /api/comparison-data** - Returns formatted data for comparison charts (excludes ARIMA)
- **GET /api/december-data** - Returns December 2025 prediction data
- **GET /api/benchmark-data** - Returns ARIMA vs best model benchmark data
- **GET /health** - Health check endpoint

## Customization

### Update Data Paths

Edit `server.js` lines 12-13 to match your data directory:

```javascript
const METRICS_PATH = path.join(__dirname, "metrics");
const PREDICTIONS_PATH = path.join(__dirname, "modelPredictions");
```

### Modify Styling

Edit `static/css/style.css` to customize colors, fonts, and layout.

### Add New Pages

1. Create new HTML template in `templates/`
2. Add new API endpoint in `server.js` (if needed)
3. Add navigation link in template header

## Requirements

- Node.js 14+
- npm 6+

## Troubleshooting

**Port already in use:**

```powershell
# Change port in server.js (line 155)
app.listen(PORT, () => {...});
# Or set environment variable
$env:PORT = 5001
npm start
```

**Data not loading:**

- Verify CSV files exist in `metrics/` and `modelPredictions/` directories
- Check file names match server.js expectations (lines 12-13)
- Verify CSV column names match API expectations

**Charts not showing:**

- Clear browser cache (Ctrl+F5)
- Check browser console for JavaScript errors (F12 → Console tab)
- Verify API endpoints are responding: visit http://localhost:5000/api/test

**API returns empty data:**

- Check console output in cmd.exe where npm start is running
- Verify CSV files have correct headers and data
- Check ARIMA exclusion logic in `/api/comparison-data` endpoint

## Development Notes

- All templates are static HTML with client-side JavaScript (no server-side rendering)
- CSV data is read on-demand by API endpoints using `csvtojson` library
- Charts are rendered client-side using Chart.js and Plotly.js
- ARIMA model is excluded from the main comparison table but included in benchmark comparison

## License

FYP 2025
