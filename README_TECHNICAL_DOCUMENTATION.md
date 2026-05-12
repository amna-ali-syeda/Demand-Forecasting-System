# Demand Forecasting System - Technical Documentation

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture Overview](#architecture-overview)
3. [Frontend Architecture](#frontend-architecture)
4. [Backend Architecture](#backend-architecture)
5. [API Endpoints & Data Flow](#api-endpoints--data-flow)
6. [File Upload System](#file-upload-system)
7. [Styling & Responsiveness](#styling--responsiveness)
8. [Data Processing Pipeline](#data-processing-pipeline)
9. [Key Features Explained](#key-features-explained)
10. [Technologies Used](#technologies-used)

---

## Project Overview

This is a **Demand Forecasting System** that uses multiple machine learning models (LightGBM, LSTM, Neural Networks, Random Forest, XGBoost, Voting Ensemble) and statistical models (ARIMA) to predict future demand for products. The application compares model performance against a benchmark (ARIMA) and provides a web-based interface for users to view predictions, metrics, and upload new dealer data.

### Key Objectives:

- Compare multiple forecasting models against a benchmark
- Provide real-time demand predictions
- Enable users to upload custom dealer data for processing
- Display comprehensive performance metrics and visualizations
- Offer a professional, responsive user interface

---

## Architecture Overview

The system follows a **Client-Server Architecture** with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (Client)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │   HTML5      │  │  Vanilla JS  │  │   CSS3       │           │
│  │  Templates   │  │  Logic       │  │  Styling     │           │
│  └──────────────┘  └──────────────┘  └──────────────┘           │
│                            ↓                                      │
│                    Fetch API (HTTP)                               │
└─────────────────────────────────────────────────────────────────┘
                              ↕ (Request/Response)
┌─────────────────────────────────────────────────────────────────┐
│                    Backend (Server)                              │
│  ┌──────────────────────────────────────────┐                  │
│  │      Express.js Server (Port 5008)       │                  │
│  │  ┌──────────────┐  ┌──────────────┐     │                  │
│  │  │   API        │  │   File       │     │                  │
│  │  │   Endpoints  │  │   Upload     │     │                  │
│  │  └──────────────┘  └──────────────┘     │                  │
│  └──────────────────────────────────────────┘                  │
│                            ↓                                      │
│  ┌──────────────────────────────────────────┐                  │
│  │    CSV Data Processing & File Storage    │                  │
│  │  • csvtojson (CSV parsing)               │                  │
│  │  • xlsx (Excel file conversion)          │                  │
│  │  • multer (file upload handling)         │                  │
│  └──────────────────────────────────────────┘                  │
│                            ↓                                      │
│  ┌──────────────────────────────────────────┐                  │
│  │    Static Files & Data Directories       │                  │
│  │  • datasets/ (uploaded files)            │                  │
│  │  • metrics/ (model performance)          │                  │
│  │  • modelPredictions/ (forecast results)  │                  │
│  │  • models/ (trained ML models)           │                  │
│  └──────────────────────────────────────────┘                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Frontend Architecture

### 1. **HTML Templates Structure**

The frontend consists of 6 main HTML templates served from the `templates/` folder:

#### **a) index.html - Project Overview**

- **Purpose**: Homepage showing project objectives and system overview
- **Key Components**:

  - Page header with project title
  - Overview section with objectives, methodology, and expected outcomes
  - Test Samples section showing total demand and data points
  - Navigation menu linking to all pages
  - Clean gradient footer

- **Data Display Logic**:
  ```javascript
  fetch("/api/december-data")
    .then((response) => response.json())
    .then((data) => {
      // Aggregates prediction data
      // Calculates total demand from all rows
      // Displays in stat cards
    });
  ```

#### **b) comparison.html - Model Comparison**

- **Purpose**: Compare performance metrics of all 8 models
- **Models Displayed**:

  1. ARIMA (Benchmark)
  2. LightGBM
  3. LSTM
  4. Neural Network
  5. Random Forest
  6. XGBoost
  7. Voting Ensemble

- **Key Components**:

  - Bar charts showing MAPE, RMSE, MAE metrics
  - Model comparison table with detailed metrics
  - Canvas-based charts (converted from Plotly for reliability)
  - Hover effects showing exact values

- **Data Source**: `/api/comparison-data` endpoint
- **Visualization**: Chart.js for metrics display

#### **c) best_model.html - Best Performing Model**

- **Purpose**: Highlight the best-performing model with detailed analysis
- **Key Components**:

  - Best model identification
  - Detailed performance metrics
  - Comparison with benchmark (ARIMA)
  - Statistical summary and confidence intervals

- **Data Parsing Logic**:
  ```javascript
  // Handles space-separated keys from API
  // E.g., "Best Model" instead of "best_model"
  fetch("/api/best-model")
    .then((response) => response.json())
    .then((data) => {
      // Parse model metadata
      // Extract performance scores
      // Display in formatted cards
    });
  ```

#### **d) predictions.html - December 2025 Predictions**

- **Purpose**: Display forecasted demand for December 2025
- **Key Components**:

  - Statistics cards (total predicted demand, daily average, etc.)
  - Detailed prediction table
  - Daily/cumulative prediction visualization
  - Data aggregation for multiple prediction rows

- **Data Aggregation Logic**:
  ```javascript
  // Handles both aggregated and detailed prediction data
  if (data.dates && data.quantities) {
    // Already aggregated format
  } else {
    // Aggregate from detailed rows
    // Sum quantities by date
    // Calculate rolling averages
  }
  ```

#### **e) benchmark.html - Benchmark Analysis**

- **Purpose**: Compare best model against ARIMA benchmark
- **Key Components**:
  - ARIMA benchmark metrics (MAPE, RMSE, MAE)
  - Best model metrics
  - Percentage improvement calculation
  - Visual comparison charts

#### **f) upload.html - File Upload Interface**

- **Purpose**: Allow users to upload dealer data with validation
- **Key Components**:

  - Drag-and-drop file upload area
  - Required columns list (12 mandatory columns)
  - Real-time column validation
  - Data preview (first 10 rows)
  - Upload progress indicator
  - Status messages

- **Required Columns** (Must all be present):

  1. Dealer Initials
  2. Dealer Name
  3. Dealer City
  4. Job Card Date
  5. Job Card Number
  6. Part Code
  7. Part Description
  8. Category
  9. Quantity
  10. Total Price
  11. Vehicle Name
  12. Model Year

- **Validation Logic**:

  ```javascript
  const REQUIRED_COLUMNS = [
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
  ];

  // Check if file columns match requirements
  const missingColumns = REQUIRED_COLUMNS.filter(
    (col) => !fileColumns.includes(col)
  );

  // Disable upload button if any columns missing
  uploadBtn.disabled = missingColumns.length > 0;
  ```

### 2. **Frontend Styling (CSS)**

**File**: `static/css/style.css` (555 lines)

#### **Color Scheme**:

```css
--primary-color: #1f77b4 (Blue)
--primary-dark: #0d47a1 (Dark Blue)
--secondary-color: #ff7f0e (Orange)
--success-color: #2ca02c (Green)
--danger-color: #d62728 (Red)
--light-bg: #f5f7fa (Light Gray)
```

#### **Design Elements**:

**a) Navigation Bar**:

- Gradient background: `linear-gradient(135deg, #0d47a1 → #1f77b4 → #1565c0)`
- Sticky positioning (stays at top during scroll)
- Responsive flexbox layout
- Hover effects with opacity transitions

**b) Page Headers**:

- Gradient text using `-webkit-background-clip: text`
- Left border accent (5px solid primary color)
- Subtle background gradient
- Responsive font sizing (2.5rem → 1.8rem → 1.5rem)

**c) Cards & Sections**:

- Box shadows with two levels: `--shadow` and `--shadow-lg`
- Hover effects: `translateY(-4px)` for depth
- Gradient backgrounds (white to light gray)
- Border-radius: 8-12px for rounded corners
- Smooth transitions (0.3s ease)

**d) Footer**:

- **Before optimization**: `padding: 3rem 2rem` (tall)
- **After optimization**: `padding: 1rem 2rem` (compact)
- Gradient background matching navbar
- Minimal top border (4px)

#### **Responsive Breakpoints**:

**Desktop (>1024px)**:

- Full padding: 2rem
- Multi-column grids (auto-fit, minmax)
- Large chart heights: 400-500px

**Tablet (768px-1024px)**:

- Reduced padding: 1.5rem
- Grid items: minmax(400px, 1fr)
- Chart heights: 300px
- Navigation gap: 1rem

**Mobile (480px-768px)**:

- Minimal padding: 1rem
- Single column layouts
- Grid template: 1fr (full width)
- Chart heights: 300px
- Font sizes reduced by 20%

**Small Phones (<480px)**:

- Ultra-minimal padding: 0.5rem
- All elements single column
- Chart heights: 250px
- Font sizes: 0.8rem-1.5rem range
- Optimized gaps: 0.5rem-0.8rem

### 3. **JavaScript Frontend Logic**

#### **Key Functions**:

**a) Data Fetching Pattern**:

```javascript
// Consistent pattern across all pages
fetch("/api/endpoint")
  .then((response) => response.json())
  .then((data) => {
    // Process data
    // Handle edge cases
    // Render to DOM
  })
  .catch((error) => console.error("Error:", error));
```

**b) Chart Rendering** (Chart.js):

```javascript
const ctx = document.getElementById("myChart").getContext("2d");
const chart = new Chart(ctx, {
  type: "bar", // or 'line', 'doughnut', etc.
  data: {
    labels: modelNames,
    datasets: [
      {
        label: "MAPE Score",
        data: metricsData,
        backgroundColor: "rgba(31, 119, 180, 0.6)",
        borderColor: "#1f77b4",
        borderWidth: 2,
      },
    ],
  },
  options: { responsive: true, maintainAspectRatio: false },
});
```

**c) File Upload & Validation**:

```javascript
// Parse CSV/Excel file
function handleFile(file) {
  if (
    file.type.includes("sheet-ml") ||
    file.type === "application/vnd.ms-excel"
  ) {
    // Handle Excel files - send to backend
    uploadToServer(file);
  } else {
    // Parse CSV directly in browser
    const reader = new FileReader();
    reader.onload = (e) => {
      const csv = e.target.result;
      const rows = csv.split("\n");
      const headers = rows[0].split(",");
      displayFileInfo(headers);
    };
    reader.readAsText(file);
  }
}

// Validate columns
function displayFileInfo(headers) {
  const missingCols = REQUIRED_COLUMNS.filter((col) => !headers.includes(col));
  if (missingCols.length === 0) {
    uploadBtn.disabled = false; // Enable upload
  }
}
```

**d) Data Aggregation** (for detailed predictions):

```javascript
function aggregatePredictions(detailedRows) {
  const aggregated = {};

  detailedRows.forEach((row) => {
    const date = row["Date"];
    aggregated[date] = (aggregated[date] || 0) + parseFloat(row["Quantity"]);
  });

  return aggregated;
}
```

---

## Backend Architecture

### 1. **Server Setup (Express.js)**

**File**: `server.js` (Main backend file)

#### **Initialization**:

```javascript
const express = require("express");
const path = require("path");
const fs = require("fs");
const csvtojson = require("csvtojson");
const XLSX = require("xlsx");
const multer = require("multer");
const cors = require("cors");

const app = express();
const PORT = 5008;

// Middleware
app.use(cors()); // Enable Cross-Origin requests from frontend
app.use(express.json());
app.use(express.static("static")); // Serve static files (CSS, JS, Plotly.js)
app.use(express.static("templates")); // Serve HTML templates
```

#### **Directory Structure**:

```
/datasets      - Uploaded user files
/metrics       - CSV files with model performance metrics
/modelPredictions - Model output predictions
/models        - Trained ML model files
/static        - CSS, JS, Plotly library
/templates     - HTML templates
```

#### **Folder Auto-Creation**:

```javascript
// Ensure datasets folder exists for file uploads
if (!fs.existsSync("datasets")) {
  fs.mkdirSync("datasets", { recursive: true });
}
```

### 2. **API Endpoints**

#### **a) /api/december-data**

**Purpose**: Fetch December 2025 predictions from best model

**Request**: `GET http://localhost:5008/api/december-data`

**Response Structure**:

```json
{
  "dates": ["2025-12-01", "2025-12-02", ...],
  "quantities": [150, 245, ...],
  "totalDemand": 7500,
  "averageDaily": 242.5
}
```

**Backend Logic**:

```javascript
app.get("/api/december-data", async (req, res) => {
  try {
    // Read predictions CSV
    const csvPath = "modelPredictions/december_2025_daily_predictions.csv";

    // Parse CSV to JSON
    const data = await csvtojson().fromFile(csvPath);

    // Extract dates and quantities
    // Handle column name variations (Date, date, etc.)
    // Aggregate by date if multiple entries exist

    res.json(aggregatedData);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});
```

**Frontend Connection**:

```javascript
// In index.html, predictions.html, benchmark.html
fetch("/api/december-data")
  .then((res) => res.json())
  .then((data) => {
    // Display total demand in stat cards
    // Populate prediction tables
    // Render charts
  });
```

---

#### **b) /api/comparison-data**

**Purpose**: Fetch all model metrics for comparison page

**Request**: `GET http://localhost:5008/api/comparison-data`

**Response Structure**:

```json
{
  "models": [
    {
      "name": "LightGBM",
      "MAPE": 8.5,
      "RMSE": 125.4,
      "MAE": 95.2,
      "R²": 0.92
    },
    {
      "name": "ARIMA",
      "MAPE": 15.2,
      "RMSE": 245.8,
      "MAE": 180.5,
      "R²": 0.78
    }
    // ... 5 more models
  ]
}
```

**Backend Logic**:

```javascript
app.get("/api/comparison-data", async (req, res) => {
  try {
    // Read all metric CSV files from metrics/ folder
    const files = fs.readdirSync("metrics");
    const allMetrics = [];

    for (const file of files) {
      const data = await csvtojson().fromFile(`metrics/${file}`);

      // Extract model name from filename
      const modelName = file.replace("_metrics.csv", "");

      // Get average metrics across all rows
      const avgMetrics = calculateAverages(data);

      allMetrics.push({
        name: modelName,
        ...avgMetrics,
      });
    }

    res.json({ models: allMetrics });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});
```

**Frontend Connection**:

```javascript
// In comparison.html
fetch("/api/comparison-data")
  .then((res) => res.json())
  .then((data) => {
    // Create model name array
    // Create MAPE dataset
    // Create RMSE dataset
    // Create MAE dataset
    // Render multi-series bar charts
  });
```

---

#### **c) /api/best-model**

**Purpose**: Fetch best performing model details

**Request**: `GET http://localhost:5008/api/best-model`

**Response Structure**:

```json
{
  "name": "LightGBM",
  "MAPE": 8.5,
  "RMSE": 125.4,
  "MAE": 95.2,
  "R²": 0.92,
  "improvementOverARIMA": {
    "MAPEPercent": 44.1,
    "RMSEPercent": 48.9
  }
}
```

**Backend Logic**:

```javascript
app.get("/api/best-model", async (req, res) => {
  try {
    // Read all metric files
    // Calculate MAPE for each model
    // Find model with lowest MAPE (best)
    // Compare with ARIMA metrics

    const bestModel = {
      name: modelWithLowestMAPE,
      metrics: bestMetrics,
      improvementOverARIMA: calculateImprovement(),
    };

    res.json(bestModel);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});
```

**Frontend Connection**:

```javascript
// In best_model.html
fetch("/api/best-model")
  .then((res) => res.json())
  .then((data) => {
    // Display model name prominently
    // Show metric cards
    // Display improvement percentages
    // Create comparison visualizations
  });
```

---

#### **d) /api/upload** (File Upload)

**Purpose**: Accept and process user-uploaded dealer data files

**Request**:

```
POST /api/upload
Content-Type: multipart/form-data
Body: FormData with file
```

**Response Structure**:

```json
{
  "success": true,
  "filename": "sample_dealer_data.csv",
  "rowsCount": 40,
  "columnsCount": 12,
  "columns": [
    "Dealer Initials",
    "Dealer Name",
    ...
  ]
}
```

**Backend Logic**:

```javascript
// Configure multer for file uploads
const upload = multer({
  storage: multer.memoryStorage(), // Store in RAM, not disk
  fileFilter: (req, file, cb) => {
    // Only allow CSV and Excel files
    const allowedMimes = [
      "text/csv",
      "application/vnd.ms-excel",
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ];

    if (allowedMimes.includes(file.mimetype)) {
      cb(null, true);
    } else {
      cb(new Error("Only CSV and Excel files allowed"));
    }
  },
});

app.post("/api/upload", upload.single("file"), async (req, res) => {
  try {
    // Get file from request
    const file = req.file;

    // Determine file type
    if (file.mimetype.includes("sheet")) {
      // Convert Excel to CSV
      const workbook = XLSX.read(file.buffer, { type: "buffer" });
      const sheet = workbook.Sheets[workbook.SheetNames[0]];
      const jsonData = XLSX.utils.sheet_to_json(sheet);

      // Convert JSON to CSV format
      const csvContent = convertToCSV(jsonData);

      // Save to datasets folder
      const filename = `${Date.now()}_uploaded_data.csv`;
      fs.writeFileSync(`datasets/${filename}`, csvContent);
    } else if (file.mimetype === "text/csv") {
      // CSV file - save directly
      const filename = `${Date.now()}_uploaded_data.csv`;
      fs.writeFileSync(`datasets/${filename}`, file.buffer);
    }

    // Parse and return column information
    const data = await csvtojson().fromString(file.buffer.toString());
    const columns = Object.keys(data[0]);

    res.json({
      success: true,
      filename: filename,
      rowsCount: data.length,
      columnsCount: columns.length,
      columns: columns,
    });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});
```

**Frontend Connection**:

```javascript
// In upload.html
const formData = new FormData();
formData.append("file", selectedFile);

fetch("/api/upload", {
  method: "POST",
  body: formData,
})
  .then((res) => res.json())
  .then((data) => {
    if (data.success) {
      showStatus("File uploaded successfully!", "success");
      // Store filename for future processing
    }
  });
```

---

### 3. **File Processing Pipeline**

#### **CSV/Excel File Handling**:

```
User selects file (CSV or Excel)
           ↓
Frontend validation (column check)
           ↓
Upload to /api/upload endpoint
           ↓
Backend determines file type
           ├─ If Excel: Convert to CSV using XLSX library
           └─ If CSV: Use directly
           ↓
File read into memory
           ↓
Parse to JSON (csvtojson)
           ↓
Extract column information
           ↓
Save to datasets/ folder with timestamp
           ↓
Return success response with metadata
           ↓
Frontend displays confirmation & file info
```

#### **Duplicate Prevention**:

```javascript
// If filename already exists
function ensureUniqueFilename(filename) {
  let finalName = filename;
  let counter = 1;

  while (fs.existsSync(`datasets/${finalName}`)) {
    const name = filename.split(".")[0];
    finalName = `${name}_${counter}.csv`;
    counter++;
  }

  return finalName;
}
```

---

## API Endpoints & Data Flow

### **Complete Request-Response Cycle Example**

#### **Scenario: User Views December Predictions**

**1. Page Load** (predictions.html):

```html
<body onload="loadPredictions()"></body>
```

**2. JavaScript Fetch**:

```javascript
function loadPredictions() {
  fetch("/api/december-data")
    .then((response) => {
      if (!response.ok) throw new Error("Failed to fetch");
      return response.json();
    })
    .then((data) => {
      // Update stat cards
      document.getElementById("totalDemand").textContent =
        data.totalDemand.toLocaleString();

      // Update table
      populatePredictionTable(data);

      // Render chart
      renderPredictionChart(data.dates, data.quantities);
    })
    .catch((error) => {
      console.error("Error:", error);
      document.getElementById("statsContainer").innerHTML =
        "<p>Error loading predictions</p>";
    });
}
```

**3. Server Processing** (server.js):

```javascript
// Read CSV from disk
const csvData = fs.readFileSync(
  "modelPredictions/december_2025_daily_predictions.csv",
  "utf8"
);

// Parse CSV to JSON
const rows = csvtojson().fromString(csvData);

// Aggregate data
let totalDemand = 0;
const aggregated = {};

rows.forEach((row) => {
  const quantity = parseFloat(row.Quantity || row.quantity);
  totalDemand += quantity;
  aggregated[row.Date] = quantity;
});

// Send back
res.json({
  dates: Object.keys(aggregated),
  quantities: Object.values(aggregated),
  totalDemand: totalDemand,
  averageDaily: totalDemand / Object.keys(aggregated).length,
});
```

**4. Response** (JSON):

```json
{
  "dates": ["2025-12-01", "2025-12-02", ...],
  "quantities": [150, 245, 300, ...],
  "totalDemand": 7500,
  "averageDaily": 242.5
}
```

**5. Frontend Rendering**:

```javascript
// Update DOM
document.getElementById("totalDemand").innerHTML = "7,500 units";
document.getElementById("avgDaily").innerHTML = "242.5 units";

// Create chart
const ctx = document.getElementById("predictionChart").getContext("2d");
new Chart(ctx, {
  type: "line",
  data: {
    labels: data.dates,
    datasets: [
      {
        label: "Daily Predictions",
        data: data.quantities,
        borderColor: "#1f77b4",
        backgroundColor: "rgba(31, 119, 180, 0.1)",
        tension: 0.4,
        fill: true,
      },
    ],
  },
});
```

---

## File Upload System

### **Complete File Upload Flow**

```
1. USER INTERFACE (upload.html)
   ├─ Drag-and-drop area
   ├─ File input
   └─ Upload button

2. CLIENT-SIDE VALIDATION
   ├─ Check file type (CSV/Excel)
   ├─ Parse file content
   ├─ Extract columns
   └─ Compare with REQUIRED_COLUMNS

3. VALIDATION FEEDBACK
   ├─ Green checkmarks for found columns
   ├─ Red X for missing columns
   ├─ Enable/disable upload button
   └─ Show preview table (first 10 rows)

4. UPLOAD REQUEST (if all columns present)
   ├─ Create FormData with file
   ├─ POST to /api/upload
   └─ Show progress indicator

5. SERVER PROCESSING
   ├─ Receive file via multer
   ├─ Validate file type
   ├─ Check if Excel or CSV
   ├─ Parse to JSON/CSV
   ├─ Generate unique filename
   └─ Save to datasets/ folder

6. SUCCESS RESPONSE
   ├─ Return filename
   ├─ Return row count
   ├─ Return column list
   └─ Return success status

7. FRONTEND CONFIRMATION
   ├─ Display success message
   ├─ Show file details
   ├─ Clear form for next upload
   └─ Store file reference
```

### **Required Column Validation**

The system enforces 12 mandatory columns:

```javascript
const REQUIRED_COLUMNS = [
  "Dealer Initials", // User/dealer identifier
  "Dealer Name", // Full dealer name
  "Dealer City", // Geographic location
  "Job Card Date", // Transaction date
  "Job Card Number", // Transaction ID
  "Part Code", // Product identifier
  "Part Description", // Product details
  "Category", // Product category
  "Quantity", // Units sold
  "Total Price", // Revenue
  "Vehicle Name", // Vehicle model
  "Model Year", // Year of vehicle
];
```

**Validation Logic**:

```javascript
function displayFileInfo(fileColumns) {
  const container = document.getElementById("columnValidation");
  container.innerHTML = ""; // Clear previous warnings

  REQUIRED_COLUMNS.forEach((col) => {
    const found = fileColumns.includes(col);
    const status = found ? "✓" : "✗";
    const color = found ? "#2ca02c" : "#d62728";

    container.innerHTML += `
      <div style="color: ${color}">
        ${status} ${col}
      </div>
    `;
  });

  const missingCount = REQUIRED_COLUMNS.filter(
    (col) => !fileColumns.includes(col)
  ).length;

  document.getElementById("uploadBtn").disabled = missingCount > 0;
}
```

---

## Styling & Responsiveness

### **CSS Strategy**

The application uses a **Mobile-First Responsive Design** approach:

#### **1. Base Styles** (Applied to all devices):

```css
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box; /* Prevents padding overflow */
}

body {
  font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
  color: #2c3e50;
  background-color: #f5f7fa;
  line-height: 1.6;
}

.container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 2rem; /* Default padding */
  min-height: calc(100vh - 200px);
}
```

#### **2. Gradient Design System**

**Navbar Gradient** (Diagonal, top-left to bottom-right):

```css
background: linear-gradient(
  135deg,
  #0d47a1 0%,
  /* Dark blue */ #1f77b4 50%,
  /* Medium blue */ #1565c0 100% /* Bright blue */
);
```

**Card Hover Effect**:

```css
.stat-card {
  transition: transform 0.3s ease, box-shadow 0.3s ease;
}

.stat-card:hover {
  transform: translateY(-8px); /* Lift effect */
  box-shadow: 0 8px 24px rgba(...); /* Enhanced shadow */
}
```

#### **3. Responsive Breakpoints**

**Desktop (>1024px)**:

```css
.container {
  padding: 1.5rem;
  max-width: 95%;
}
.overview-grid {
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 1.5rem;
}
.chart-container {
  height: 400px;
}
```

**Tablet (768px-1024px)**:

```css
.container {
  padding: 1rem;
}
.nav-menu {
  gap: 1rem;
  font-size: 0.9rem;
}
.stats-grid {
  grid-template-columns: repeat(2, 1fr);
  gap: 1rem;
}
.chart-container {
  height: 300px;
}
```

**Mobile (480px-768px)**:

```css
.container {
  padding: 1rem;
}
.nav-item a {
  padding: 0.5rem;
}
.overview-grid {
  grid-template-columns: 1fr;
}
.stats-grid {
  grid-template-columns: repeat(2, 1fr);
  gap: 1rem;
}
.chart-container {
  height: 300px;
}
```

**Small Phones (<480px)**:

```css
.container {
  padding: 0.5rem;
}
.page-header h1 {
  font-size: 1.5rem;
}
.stats-grid {
  grid-template-columns: 1fr;
}
.chart-container {
  height: 250px;
}
.footer {
  padding: 0.6rem 0.5rem;
  font-size: 0.75rem;
}
```

---

## Data Processing Pipeline

### **Model Metrics Flow**

```
Training Phase (Python)
    ↓
┌─────────────────────────────────────┐
│ train_lightGBM.py                   │
│ train_xgboost.py                    │
│ train_lstm.py                       │
│ train_nn.py                         │
│ train_randomForest.py               │
│ train_voting_ensemble.py            │
│ train_ARIMA.py                      │
└─────────────────────────────────────┘
    ↓ (Output)
├─ metrics/lightgbm_metrics.csv
├─ metrics/xgboost_metrics.csv
├─ metrics/lstm_metrics.csv
├─ metrics/nn_metrics.csv
├─ metrics/random_forest_metrics.csv
├─ metrics/voting_ensemble_metrics.csv
└─ metrics/arima_metrics.csv
    ↓
select_best_model_and_predict.py
    ↓
┌─────────────────────────────────────┐
│ Determines best model (lowest MAPE) │
│ Selects model with metrics < 10%    │
│ Generates December predictions      │
└─────────────────────────────────────┘
    ↓
├─ modelPredictions/december_2025_daily_predictions.csv
├─ modelPredictions/december_2025_detailed_predictions.csv
    ↓
Frontend Reads (via API)
    ↓
Display to Users
```

### **Data Format Examples**

**Metrics CSV** (metrics/lightgbm_metrics.csv):

```csv
Date,MAPE,RMSE,MAE,R²
2025-12-01,8.5,125.4,95.2,0.92
2025-12-02,9.1,132.1,98.5,0.91
2025-12-03,8.2,120.3,92.1,0.93
```

````

**Predictions CSV** (modelPredictions/december_2025_daily_predictions.csv):
```csv
Date,Predicted_Quantity
2025-12-01,1500
2025-12-02,1625
2025-12-03,1450
...
2025-12-31,1550
````

---

## Key Features Explained

### **1. Multi-Model Comparison**

**Why Multiple Models?**

- Different models capture different patterns
- Some excel with linear trends (ARIMA)
- Others handle non-linearity (Neural Networks, Tree-based)
- Ensemble combines strengths of multiple models

**How Frontend Shows It**:

```javascript
// comparison.html fetches all models
fetch('/api/comparison-data')
  .then(data => {
    // Creates arrays for each metric
    const models = data.models.map(m => m.name);
    const mapeScores = data.models.map(m => m.MAPE);
    const rmseScores = data.models.map(m => m.RMSE);

    // Creates multiple datasets
    new Chart(ctx, {
      data: {
        datasets: [
          { label: 'MAPE', data: mapeScores, ... },
          { label: 'RMSE', data: rmseScores, ... }
        ]
      }
    });
  });
```

### **2. Benchmark Comparison**

**ARIMA as Baseline**:

- ARIMA is traditional statistical forecasting
- Serves as baseline for ML model comparison
- If ML model MAPE < ARIMA MAPE, it's an improvement
- Percentage improvement: `((ARIMA - ML) / ARIMA) * 100`

**Frontend Logic**:

```javascript
const improvement = ((arimaMAP - bestModelMAP) / arimaMAP) * 100;
document.getElementById("improvement").textContent = `${improvement.toFixed(
  1
)}% better`;
```

### **3. December 2025 Predictions**

**Data Aggregation**:

- Multiple prediction rows (detailed) → Single daily total
- Handles different data granularities
- Sums quantities by date
- Calculates running totals

### **4. File Upload with Validation**

**Client-Side Validation Benefits**:

- Instant feedback (no server round-trip)
- Better UX (button disabled until valid)
- Prevents invalid uploads

**Server-Side Validation Benefits**:

- Security (file type verification)
- Data integrity (column checking)
- Error handling

---

## Technologies Used

### **Frontend Stack**

| Technology         | Version      | Purpose                                         |
| ------------------ | ------------ | ----------------------------------------------- |
| HTML5              | -            | Page structure and semantic markup              |
| CSS3               | -            | Styling, gradients, responsive design           |
| Vanilla JavaScript | ES6+         | DOM manipulation, API calls, validation         |
| Chart.js           | Latest       | Data visualization (bar, line, doughnut charts) |
| Plotly.js          | 3.6 MB Local | Advanced interactive charts (fallback)          |
| Fetch API          | Built-in     | HTTP requests to backend                        |

### **Backend Stack**

| Technology | Version | Purpose |
| Technology | Version | Purpose |
|-----------|---------|---------|
| Node.js | v24.11.1 | Runtime environment |
| Express.js | Latest | Web server framework |
| Express CORS | Latest | Enable cross-origin requests |
| csvtojson | Latest | Parse CSV to JSON |
| xlsx | Latest | Handle Excel file conversion |
| multer | Latest | File upload handling |
| fs (Node built-in) | - | File system operations |
| path (Node built-in) | - | Path utilities |

### **Data Pipeline (Python)**

| Technology       | Purpose                        |
| ---------------- | ------------------------------ |
| pandas           | Data manipulation              |
| scikit-learn     | Train/evaluate models          |
| LightGBM         | Lightweight gradient boosting  |
| TensorFlow/Keras | LSTM and Neural Network models |
| XGBoost          | Extreme gradient boosting      |
| Statsmodels      | ARIMA statistical model        |
| numpy            | Numerical computations         |

---

## Connection Architecture Summary

### **Request Flow Diagram**

```
┌──────────────────────────────────────────────────────────────┐
│                    BROWSER (Frontend)                        │
│  User Views Page → JavaScript fetch() → Sends HTTP Request   │
└──────────────────────────────────────────────────────────────┘
                              ↕ HTTP (JSON)
┌──────────────────────────────────────────────────────────────┐
│                    PORT 5008 (Backend)                       │
│  Express Server Receives Request                             │
│  ├─ Match route (e.g., /api/comparison-data)                │
│  ├─ Read CSV files from disk                                │
│  ├─ Parse and process data                                  │
│  ├─ Format as JSON                                          │
│  └─ Send response                                           │
└──────────────────────────────────────────────────────────────┘
                              ↕ HTTP (JSON)
┌──────────────────────────────────────────────────────────────┐
│                    BROWSER (Frontend)                        │
│  JavaScript .then(data => {                                 │
│    ├─ Parse JSON                                            │
│    ├─ Update DOM elements                                   │
│    └─ Render charts                                         │
│  })                                                         │
└──────────────────────────────────────────────────────────────┘
```

---

## Key Design Patterns Used

### **1. MVC-like Separation**

- **Model**: CSV data files (datasets, metrics, predictions)
- **View**: HTML templates (index.html, comparison.html, etc.)
- **Controller**: Express routes (/api/\*)

### **2. RESTful API Design**

- GET endpoints for data retrieval
- POST endpoint for file uploads
- JSON responses
- Standard HTTP status codes

### **3. Client-Side Caching**

```javascript
// Prevent unnecessary server calls
let cachedData = null;

function fetchComparisonData() {
  if (cachedData) {
    return Promise.resolve(cachedData);
  }
  return fetch("/api/comparison-data")
    .then((res) => res.json())
    .then((data) => {
      cachedData = data;
      return data;
    });
}
```

### **4. Error Handling**

```javascript
fetch("/api/data")
  .then((res) => {
    if (!res.ok) throw new Error("Failed to fetch");
    return res.json();
  })
  .catch((error) => {
    console.error("Error:", error);
    // Display fallback UI
  });
```

---

## Summary

This Demand Forecasting System demonstrates a complete web application with:

1. **Professional Frontend** - Responsive design with gradient styling, multiple pages, and interactive charts
2. **Robust Backend** - Express server serving static files and JSON APIs
3. **File Management** - User upload system with column validation
4. **Data Integration** - CSV parsing, aggregation, and real-time serving
5. **Model Comparison** - Visual and numerical comparison of 9 different forecasting models
6. **Responsive Design** - Works seamlessly on desktop, tablet, and mobile devices

The architecture ensures scalability, maintainability, and user-friendly interaction throughout the application.
