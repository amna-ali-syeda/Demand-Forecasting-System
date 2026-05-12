const express = require("express");
const cors = require("cors");
const path = require("path");
const fs = require("fs");
const { execFile } = require("child_process");
const csv = require("csvtojson");
const multer = require("multer");
const XLSX = require("xlsx");

const app = express();
app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ limit: "50mb", extended: true }));

const UPLOADED_RAW_PATH = path.join(__dirname, "datasets", "uploaded_raw");
if (!fs.existsSync(UPLOADED_RAW_PATH)) {
  fs.mkdirSync(UPLOADED_RAW_PATH, { recursive: true });
}

// Setup file upload
const storage = multer.diskStorage({
  destination: (req, file, cb) => cb(null, UPLOADED_RAW_PATH),
  filename: (req, file, cb) => {
    const ext = path.extname(file.originalname).toLowerCase();
    const baseName = path
      .basename(file.originalname, ext)
      .replace(/[^a-zA-Z0-9_-]/g, "_");
    cb(null, `${baseName}_${Date.now()}${ext}`);
  },
});
const upload = multer({
  storage: storage,
  limits: { fileSize: 250 * 1024 * 1024 },
  fileFilter: (req, file, cb) => {
    const allowedMimes = [
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      "application/vnd.ms-excel",
      "text/csv",
      "application/csv",
    ];
    const allowedExtensions = [".xlsx", ".xls", ".csv"];
    const ext = path.extname(file.originalname).toLowerCase();

    if (
      allowedMimes.includes(file.mimetype) ||
      allowedExtensions.includes(ext)
    ) {
      cb(null, true);
    } else {
      cb(
        new Error(
          "Invalid file format. Only .xlsx, .xls, and .csv are allowed.",
        ),
      );
    }
  },
});

// Update these paths if needed
const METRICS_PATH = path.join(__dirname, "metrics");
const PREDICTIONS_PATH = path.join(__dirname, "modelPredictions");
const DATASETS_PATH = path.join(__dirname, "datasets");
const PREPROCESSED_NO_WEATHER_PATH = path.join(
  DATASETS_PATH,
  "preprocessed_without_weather",
);
const PIPELINE_STATE_PATH = path.join(DATASETS_PATH, "pipeline_state.json");

// Ensure datasets folder exists
if (!fs.existsSync(DATASETS_PATH)) {
  fs.mkdirSync(DATASETS_PATH, { recursive: true });
}
if (!fs.existsSync(PREPROCESSED_NO_WEATHER_PATH)) {
  fs.mkdirSync(PREPROCESSED_NO_WEATHER_PATH, { recursive: true });
}

// Serve static frontend files 
app.use("/static", express.static(path.join(__dirname, "static")));
app.use("/", express.static(path.join(__dirname, "templates")));
app.use("/datasets", express.static(DATASETS_PATH));
app.use("/modelPredictions", express.static(PREDICTIONS_PATH));
// Serve metrics directory so frontend can fetch CSV fallbacks directly
app.use("/metrics", express.static(path.join(__dirname, "metrics")));

// Serve login page as default root
app.get("/", (req, res) => {
  res.sendFile(path.join(__dirname, "templates", "login.html"));
});

async function readCsv(filePath) {
  try {
    return await csv().fromFile(filePath);
  } catch (err) {
    return null;
  }
}

function readPipelineState() {
  if (!fs.existsSync(PIPELINE_STATE_PATH)) {
    return {
      latestUploadAt: null,
      latestProcessedFile: null,
      lastTrainedUploadAt: null,
      modelReady: false,
      latestUploadHasRows: null,
      latestRowsCount: 0,
      latestUploadStatus: null,
    };
  }

  try {
    const raw = fs.readFileSync(PIPELINE_STATE_PATH, "utf8");
    return JSON.parse(raw);
  } catch {
    return {
      latestUploadAt: null,
      latestProcessedFile: null,
      lastTrainedUploadAt: null,
      modelReady: false,
      latestUploadHasRows: null,
      latestRowsCount: 0,
      latestUploadStatus: null,
    };
  }
}

function writePipelineState(state) {
  fs.writeFileSync(PIPELINE_STATE_PATH, JSON.stringify(state, null, 2), "utf8");
}

// Clear pipeline state on every server start so each session begins fresh
writePipelineState({
  latestUploadAt: null,
  latestProcessedFile: null,
  lastTrainedUploadAt: null,
  modelReady: false,
  latestUploadHasRows: null,
  latestRowsCount: 0,
  latestUploadStatus: null,
});

function getLatestProcessedFileInfo() {
  const files = fs.existsSync(PREPROCESSED_NO_WEATHER_PATH)
    ? fs.readdirSync(PREPROCESSED_NO_WEATHER_PATH)
    : [];
  const processed = files
    .filter(
      (f) =>
        (f.startsWith("preprocessed_data_without_weather") ||
          f.startsWith("filtered_data_with_cultural_dynamic")) &&
        f.toLowerCase().endsWith(".csv"),
    )
    .map((filename) => {
      const abs = path.join(PREPROCESSED_NO_WEATHER_PATH, filename);
      const stats = fs.statSync(abs);
      return {
        filename,
        abs,
        mtimeMs: stats.mtimeMs,
      };
    })
    .sort((a, b) => b.mtimeMs - a.mtimeMs);

  if (!processed.length) return null;
  const latest = processed[0];
  return {
    filename: latest.filename,
    downloadUrl: `/datasets/preprocessed_without_weather/${encodeURIComponent(latest.filename)}`,
    updatedAt: new Date(latest.mtimeMs).toISOString(),
  };
}

function runPreprocessingPipeline(inputPaths, outputDir, finalFileName) {
  const scriptPath = path.join(__dirname, "basic_data_preprocessing.py");
  const venvPython = path.join(__dirname, ".venv", "Scripts", "python.exe");
  const pythonExecutable = fs.existsSync(venvPython)
    ? venvPython
    : process.env.PYTHON_EXECUTABLE || "python";

  const args = [
    "-u",           // unbuffered stdout/stderr so errors are always captured
    scriptPath,
    "--inputs",
    ...inputPaths,
    "--output-dir",
    outputDir,
    "--final-filename",
    finalFileName,
  ];

  return new Promise((resolve, reject) => {
    execFile(
      pythonExecutable,
      args,
      { cwd: __dirname, timeout: 900000, maxBuffer: 10 * 1024 * 1024 },
      (err, stdout, stderr) => {
        if (err) {
          return reject(
            new Error(
              stderr ||
                stdout ||
                err.message ||
                "Preprocessing pipeline failed",
            ),
          );
        }

        const lines = String(stdout || "")
          .split(/\r?\n/)
          .map((line) => line.trim())
          .filter(Boolean);
        const lastLine = lines.length ? lines[lines.length - 1] : "{}";

        try {
          const parsed = JSON.parse(lastLine);
          resolve(parsed);
        } catch (parseError) {
          reject(
            new Error(
              `Preprocessing output parse failed. stdout: ${stdout || "<empty>"}, stderr: ${stderr || "<empty>"}`,
            ),
          );
        }
      },
    );
  });
}

function runRandomForestPipeline({ retrainModel, monthsAhead }) {
  const scriptPath = path.join(__dirname, "random_forest_model.py");
  const venvPython = path.join(__dirname, ".venv", "Scripts", "python.exe");
  const pythonExecutable = fs.existsSync(venvPython)
    ? venvPython
    : process.env.PYTHON_EXECUTABLE || "python";

  const args = [scriptPath, "--months-ahead", String(monthsAhead)];
  if (retrainModel) args.push("--retrain");

  return new Promise((resolve, reject) => {
    execFile(
      pythonExecutable,
      args,
      { cwd: __dirname, timeout: 600000, maxBuffer: 50 * 1024 * 1024 },
      (err, stdout, stderr) => {
        if (err) {
          return reject(new Error(stderr || err.message));
        }

        const lines = String(stdout || "")
          .split(/\r?\n/)
          .map((line) => line.trim())
          .filter(Boolean);
        const lastLine = lines.length ? lines[lines.length - 1] : "{}";

        try {
          const parsed = JSON.parse(lastLine);
          resolve(parsed);
        } catch (parseError) {
          reject(
            new Error(
              `Random Forest output parse failed. stdout: ${stdout || "<empty>"}, stderr: ${stderr || "<empty>"}`,
            ),
          );
        }
      },
    );
  });
}

app.get("/api/metrics", async (req, res) => {
  try {
    const files = fs.existsSync(METRICS_PATH)
      ? fs.readdirSync(METRICS_PATH)
      : [];
    const metricsFiles = files.filter((f) => f.endsWith("_metrics.csv"));
    const all = [];
    for (const f of metricsFiles) {
      const data = await readCsv(path.join(METRICS_PATH, f));
      if (data) all.push(...data);
    }
    res.json(all);
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: "Failed to load metrics" });
  }
});

app.get("/api/comparison", async (req, res) => {
  try {
    const file = path.join(METRICS_PATH, "best_model_comparison.csv");
    if (!fs.existsSync(file)) return res.json(null);
    const data = await readCsv(file);
    res.json(data && data.length ? data[0] : null);
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: "Failed to load comparison report" });
  }
});

app.get("/api/comparison-data", async (req, res) => {
  try {
    const files = fs.existsSync(METRICS_PATH)
      ? fs.readdirSync(METRICS_PATH)
      : [];
    console.log("Files in metrics folder:", files);
    const metricsFiles = files.filter(
      (f) => f.endsWith("_metrics.csv") && f !== "arima_metrics.csv",
    );
    console.log("Filtered metrics files:", metricsFiles);
    const all = [];
    for (const f of metricsFiles) {
      try {
        const filePath = path.join(METRICS_PATH, f);
        const data = await readCsv(filePath);
        console.log(`Read ${f}:`, data);
        if (data && data.length > 0) all.push(...data);
      } catch (fileErr) {
        console.error(`Error reading ${f}:`, fileErr);
      }
    }
    console.log("All data combined:", all);
    if (!all.length) {
      console.log("No data found, returning empty object");
      return res.json({});
    }
    // Convert strings to numbers where appropriate
    const parsed = all.map((row) => ({
      Model: row.Model.trim().replace(/^["']|["']$/g, ""),
      MAE: Number(row.MAE),
      RMSE: Number(row.RMSE),
      R2: Number(row.R2),
      MAPE: Number(row.MAPE),
    }));
    parsed.sort((a, b) => a.MAPE - b.MAPE);
    res.json({
      models: parsed.map((r) => r.Model),
      mae: parsed.map((r) => r.MAE),
      rmse: parsed.map((r) => r.RMSE),
      r2: parsed.map((r) => r.R2),
      mape: parsed.map((r) => r.MAPE),
    });
  } catch (err) {
    console.error("Error in /api/comparison-data:", err);
    res.status(500).json({ error: "Failed to prepare comparison data" });
  }
});

async function handlePredictionsData(req, res) {
  try {
    const monthsAheadRaw = Number(req.query.monthsAhead || 1);
    const monthsAhead = [1, 3, 6].includes(monthsAheadRaw) ? monthsAheadRaw : 1;
    const retrainModelRequested =
      String(req.query.retrainModel || "false").toLowerCase() === "true";

    if (retrainModelRequested) {
      return res.status(400).json({
        error:
          "Retraining is only allowed during upload. Upload new data and use the Retrain Model option on the Upload page.",
        requiresAction: "upload_and_train",
      });
    }

    const state = readPipelineState();
    const latestProcessed = getLatestProcessedFileInfo();
    if (!latestProcessed || !state.latestUploadAt) {
      return res.status(400).json({
        error:
          "No uploaded dataset found. Please upload data and train the model first.",
        requiresAction: "upload_and_train",
      });
    }

    if (
      !state.lastTrainedUploadAt ||
      state.lastTrainedUploadAt !== state.latestUploadAt ||
      !state.modelReady
    ) {
      return res.status(400).json({
        error:
          "Model is not trained on the latest uploaded data. Please upload data and enable Retrain Model.",
        requiresAction: "upload_and_train",
      });
    }

    const rfModelPath = path.join(
      __dirname,
      "models",
      "random_forest_model.pkl",
    );
    if (!fs.existsSync(rfModelPath)) {
      return res.status(400).json({
        error:
          "Random Forest model not found. Please upload data and train the model first.",
        requiresAction: "upload_and_train",
      });
    }

    const rfResult = await runRandomForestPipeline({
      retrainModel: false,
      monthsAhead,
    });

    const outputFilename = rfResult?.output_file
      ? path.basename(rfResult.output_file)
      : null;

    return res.json({
      dates: rfResult.dates || [],
      quantities: rfResult.quantities || [],
      rows: rfResult.rows || [],
      dailyRows: rfResult.daily_rows || [],
      downloadUrl: outputFilename
        ? `/modelPredictions/${encodeURIComponent(outputFilename)}`
        : null,
      control: {
        retrainModelRequested: false,
        monthsAhead,
        model: "Random Forest",
        retrained: false,
      },
    });
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: "Failed to load predictions data" });
  }
}

app.get("/api/predictions-data", handlePredictionsData);
// Backward-compatible alias.
app.get("/api/december-data", handlePredictionsData);

app.get("/api/benchmark-data", async (req, res) => {
  try {
    const file = path.join(METRICS_PATH, "best_model_comparison.csv");
    if (!fs.existsSync(file)) return res.json({});
    const data = await readCsv(file);
    if (!data || !data.length) return res.json({});
    const row = data[0];
    res.json({
      best_model: row["Best_Model"] || row["Best Model"] || null,
      best_mape: Number(row["Best_MAPE"] || row["Best MAPE"] || 0),
      benchmark_mape: Number(
        row["Benchmark_MAPE"] || row["Benchmark MAPE"] || 0,
      ),
      best_r2: Number(row["Best_R2"] || row["Best R2"] || 0),
      benchmark_r2: Number(row["Benchmark_R2"] || row["Benchmark R2"] || 0),
    });
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: "Failed to load benchmark data" });
  }
});

app.get("/api/latest-processed-file", (req, res) => {
  try {
    const latest = getLatestProcessedFileInfo();
    if (!latest) {
      return res.json({ available: false });
    }
    res.json({
      available: true,
      ...latest,
    });
  } catch (err) {
    console.error(err);
    res.status(500).json({
      available: false,
      error: "Failed to find latest processed file",
    });
  }
});

app.get("/api/pipeline-state", (req, res) => {
  try {
    const state = readPipelineState();
    const canTrain = Boolean(
      state.latestUploadAt &&
      state.latestUploadAt !== state.lastTrainedUploadAt &&
      state.latestUploadHasRows === true,
    );
    res.json({
      success: true,
      latestUploadAt: state.latestUploadAt,
      lastTrainedUploadAt: state.lastTrainedUploadAt,
      modelReady: Boolean(state.modelReady),
      latestUploadHasRows:
        typeof state.latestUploadHasRows === "boolean"
          ? state.latestUploadHasRows
          : null,
      latestRowsCount: Number(state.latestRowsCount || 0),
      latestUploadStatus: state.latestUploadStatus || null,
      canTrain,
    });
  } catch (err) {
    console.error(err);
    res
      .status(500)
      .json({ success: false, error: "Failed to read pipeline state" });
  }
});

app.post("/api/train-model", async (req, res) => {
  try {
    const state = readPipelineState();
    if (!state.latestUploadAt) {
      return res.status(400).json({
        success: false,
        error: "No uploaded data found. Upload data first.",
      });
    }

    if (
      state.lastTrainedUploadAt === state.latestUploadAt &&
      state.modelReady
    ) {
      return res.status(400).json({
        success: false,
        error:
          "Model is already trained for the latest upload. Upload new data to retrain.",
      });
    }

    if (state.latestUploadHasRows !== true) {
      if (state.latestUploadStatus === "raw_uploaded_preprocessing_failed") {
        return res.status(400).json({
          success: false,
          error:
            "Cannot train model: uploaded to raw storage but preprocessing failed. Re-upload corrected data first.",
        });
      }

      return res.status(400).json({
        success: false,
        error:
          "Cannot train model: preprocessing resulted in 0 rows. Upload data that survives preprocessing filters.",
      });
    }

    const trainingResult = await runRandomForestPipeline({
      retrainModel: true,
      monthsAhead: 1,
    });

    state.lastTrainedUploadAt = state.latestUploadAt;
    state.modelReady = true;
    writePipelineState(state);

    res.json({
      success: true,
      retrained: Boolean(trainingResult?.retrained),
      forecastRows: Array.isArray(trainingResult?.rows)
        ? trainingResult.rows.length
        : 0,
    });
  } catch (err) {
    console.error(err);
    res
      .status(500)
      .json({ success: false, error: "Model training failed: " + err.message });
  }
});

// Overview data endpoint — computes correlation matrix + cultural/weather stats from feature-engineered dataset
app.get("/api/overview-data", async (req, res) => {
  try {
    const state = readPipelineState();
    const featureDataPath = path.join(__dirname, "datasets", "feature_engineered_dataset.csv");
    const featureDataExists = fs.existsSync(featureDataPath);

    if (!state.latestUploadAt) {
      return res.json({ available: false, reason: "no_upload" });
    }
    if (!featureDataExists) {
      return res.json({ available: false, reason: "no_model" });
    }

    const allData = await readCsv(featureDataPath);
    if (!allData || allData.length === 0) {
      return res.json({ available: false, reason: "empty_data" });
    }

    // Sample up to 5000 rows for performance
    const sampleSize = 5000;
    const step = allData.length > sampleSize ? Math.floor(allData.length / sampleSize) : 1;
    const data = allData.filter((_, i) => i % step === 0);

    const firstRow = data[0] || {};
    const allCols = Object.keys(firstRow).filter(c => c !== "Job_Date");

    // Keep only columns with numeric-looking values
    const numericCols = allCols.filter(col => {
      const vals = data.slice(0, 30).map(r => Number(r[col]));
      return vals.filter(v => !isNaN(v) && isFinite(v)).length >= 20;
    });

    // Quantity last for visual clarity in heatmap
    const featureCols = numericCols.filter(c => c !== "Quantity");
    const allNumCols = [...featureCols, "Quantity"];

    // Build numeric arrays once
    const arrays = {};
    for (const col of allNumCols) {
      arrays[col] = data.map(r => {
        const v = Number(r[col]);
        return isNaN(v) || !isFinite(v) ? null : v;
      });
    }

    // Pearson correlation
    function computeCorr(a, b) {
      const paired = [];
      for (let i = 0; i < a.length; i++) {
        if (a[i] !== null && b[i] !== null) paired.push([a[i], b[i]]);
      }
      if (paired.length < 2) return 0;
      const n = paired.length;
      let ma = 0, mb = 0;
      for (const [x, y] of paired) { ma += x; mb += y; }
      ma /= n; mb /= n;
      let num = 0, da = 0, db = 0;
      for (const [x, y] of paired) {
        const dx = x - ma, dy = y - mb;
        num += dx * dy; da += dx * dx; db += dy * dy;
      }
      const denom = Math.sqrt(da * db);
      return denom === 0 ? 0 : parseFloat((num / denom).toFixed(3));
    }

    const corrMatrix = {};
    for (const c1 of allNumCols) {
      corrMatrix[c1] = {};
      for (const c2 of allNumCols) {
        corrMatrix[c1][c2] = c1 === c2 ? 1.0 : computeCorr(arrays[c1], arrays[c2]);
      }
    }

    // Cultural and weather visuals come from the preprocessed file.
    let culturalStats = null;
    let weatherStats = null;

    const latestProc = getLatestProcessedFileInfo();
    if (latestProc) {
      const prepPath = path.join(PREPROCESSED_NO_WEATHER_PATH, latestProc.filename);
      if (fs.existsSync(prepPath)) {
        try {
          const prepData = await readCsv(prepPath);
          if (prepData && prepData.length) {
            const prepFirst = prepData[0] || {};
            const avg = arr => arr.length > 0
              ? parseFloat((arr.reduce((s, r) => s + Number(r.Quantity || 0), 0) / arr.length).toFixed(2))
              : 0;

            // Cultural stats — use full dataset so counts match actual record totals.
            if ("Cultural_Factor" in prepFirst) {
              const withEv = prepData.filter(r => Number(r.Cultural_Factor) > 0);
              const withoutEv = prepData.filter(r => Number(r.Cultural_Factor) === 0);
              if (withEv.length > 0 && withoutEv.length > 0) {
                const eventBreakdown = {};
                withEv.forEach(r => {
                  const ev = String(r.Cultural_Event || "Cultural Event").trim() || "Cultural Event";
                  if (!eventBreakdown[ev]) eventBreakdown[ev] = { total: 0, count: 0 };
                  eventBreakdown[ev].total += Number(r.Quantity || 0);
                  eventBreakdown[ev].count += 1;
                });
                culturalStats = {
                  avgWithCultural: avg(withEv),
                  avgWithoutCultural: avg(withoutEv),
                  countWithCultural: withEv.length,
                  countWithoutCultural: withoutEv.length,
                  eventBreakdown: Object.entries(eventBreakdown)
                    .sort(([, a], [, b]) => b.total / b.count - a.total / a.count)
                    .map(([name, s]) => ({
                      name,
                      avgQty: parseFloat((s.total / s.count).toFixed(2)),
                      count: s.count,
                    })),
                };
              }
            }

            // Weather stats
            if ("Precipitation" in prepFirst) {
              const noRain    = prepData.filter(r => Number(r.Precipitation) === 0);
              const lightRain = prepData.filter(r => Number(r.Precipitation) > 0 && Number(r.Precipitation) <= 10);
              const heavyRain = prepData.filter(r => Number(r.Precipitation) > 10);
              if (noRain.length > 0 || lightRain.length > 0 || heavyRain.length > 0) {
                weatherStats = {
                  avgNoRain:      avg(noRain),
                  avgLightRain:   avg(lightRain),
                  avgHeavyRain:   avg(heavyRain),
                  noRainCount:    noRain.length,
                  lightRainCount: lightRain.length,
                  heavyRainCount: heavyRain.length,
                };
              }
            }
          }
        } catch (_) {}
      }
    }

    // Monthly demand pattern 
    const monthBuckets = {};
    for (const row of data) {
      const m = Number(row.Month);
      if (!isNaN(m) && m >= 1 && m <= 12) {
        if (!monthBuckets[m]) monthBuckets[m] = { total: 0, count: 0 };
        monthBuckets[m].total += Number(row.Quantity || 0);
        monthBuckets[m].count += 1;
      }
    }
    const monthlyAvg = Array.from({ length: 12 }, (_, i) => {
      const m = i + 1;
      return monthBuckets[m] ? parseFloat((monthBuckets[m].total / monthBuckets[m].count).toFixed(2)) : 0;
    });

    // Date range from Job_Date column
    let dateRange = null;
    const jobDates = allData.map(r => r.Job_Date).filter(Boolean).sort();
    if (jobDates.length) {
      dateRange = { start: jobDates[0], end: jobDates[jobDates.length - 1] };
    }

    res.json({
      available: true,
      features: allNumCols,
      correlationMatrix: corrMatrix,
      culturalStats,
      weatherStats,
      monthlyAvg,
      dateRange,
      rowCount: allData.length,
      featureCount: featureCols.length,
    });
  } catch (err) {
    console.error("/api/overview-data error:", err);
    res.status(500).json({ available: false, error: "Failed to compute overview data: " + err.message });
  }
});

// Cultural factors endpoint
app.get("/api/cultural-factors", async (req, res) => {
  try {
    const file = path.join(
      DATASETS_PATH,
      "filtered_data_with_cultural_dynamic.csv",
    );
    if (!fs.existsSync(file)) {
      return res.json({
        error: "Cultural factors data not found",
        available: false,
      });
    }
    const data = await readCsv(file);
    if (!data)
      return res.json({ error: "Failed to read data", available: false });

    // Calculate cultural event statistics
    const eventCounts = {};
    data.forEach((row) => {
      const event = row.Cultural_Event || "None";
      eventCounts[event] = (eventCounts[event] || 0) + 1;
    });

    res.json({
      available: true,
      totalRecords: data.length,
      eventCounts: eventCounts,
      culturalPercentage: (
        (data.filter((r) => r.Cultural_Factor === "1").length / data.length) *
        100
      ).toFixed(2),
    });
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: "Failed to load cultural factors data" });
  }
});

// Visuals endpoint
app.get("/api/visuals", (req, res) => {
  try {
    const VISUALS_PATH = path.join(__dirname, "visuals");
    if (!fs.existsSync(VISUALS_PATH)) {
      return res.json({ error: "Visuals folder not found", visuals: [] });
    }

    const files = fs.readdirSync(VISUALS_PATH);
    const pngFiles = files.filter((f) => f.endsWith(".png"));

    const visuals = pngFiles.map((file) => ({
      name: file.replace(".png", "").replace(/_/g, " "),
      path: `/visuals/${file}`,
      filename: file,
    }));

    res.json({
      available: true,
      visuals: visuals,
      count: visuals.length,
    });
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: "Failed to load visuals list" });
  }
});

// Serve visuals directory
app.use("/visuals", express.static(path.join(__dirname, "visuals")));

// Simple health check
app.get("/health", (req, res) => res.json({ status: "ok" }));

// Test endpoint to check metrics path
app.get("/api/test", (req, res) => {
  const files = fs.readdirSync(METRICS_PATH);
  res.json({
    metricsPath: METRICS_PATH,
    files: files,
    metricsFiles: files.filter((f) => f.endsWith("_metrics.csv")),
  });
});

// Upload endpoint
app.post("/api/upload", upload.array("files", 20), async (req, res) => {
  try {
    const uploadedFiles = req.files || [];
    if (!uploadedFiles.length) {
      return res
        .status(400)
        .json({ success: false, error: "No files provided" });
    }
    const timestamp = Date.now();
    const persistedInputPaths = [];
    let totalUploadBytes = 0;

    for (const file of uploadedFiles) {
      const absPath = file.path;
      persistedInputPaths.push(absPath);
      totalUploadBytes += Number(file.size || 0);
    }

    const finalFileName = `preprocessed_data_without_weather_${timestamp}.csv`;
    let preprocessingResult;
    try {
      preprocessingResult = await runPreprocessingPipeline(
        persistedInputPaths,
        PREPROCESSED_NO_WEATHER_PATH,
        finalFileName,
      );
    } catch (preprocessingError) {
      const failedState = readPipelineState();
      failedState.latestUploadAt = String(timestamp);
      failedState.latestProcessedFile = null;
      failedState.modelReady = false;
      failedState.latestUploadHasRows = false;
      failedState.latestRowsCount = 0;
      failedState.latestUploadStatus = "raw_uploaded_preprocessing_failed";
      writePipelineState(failedState);

      return res.status(422).json({
        success: false,
        rawUploadSaved: true,
        preprocessingSucceeded: false,
        warningCode: "RAW_UPLOAD_PREPROCESSING_FAILED",
        error: "Uploaded to raw storage, preprocessing failed.",
        details: preprocessingError.message,
        uploadedFiles: uploadedFiles.map((f) => f.originalname),
        uploadedFilesCount: uploadedFiles.length,
        totalUploadSizeMB: Number(
          (totalUploadBytes / (1024 * 1024)).toFixed(2),
        ),
        canTrain: false,
      });
    }

    const rowsCount = Number(preprocessingResult?.rows || 0);

    const state = readPipelineState();
    state.latestUploadAt = String(timestamp);
    state.latestProcessedFile = finalFileName;
    state.modelReady = false;
    state.latestUploadHasRows = rowsCount > 0;
    state.latestRowsCount = rowsCount;
    state.latestUploadStatus =
      rowsCount > 0 ? "preprocessed_ok" : "preprocessed_zero_rows";
    writePipelineState(state);

    const finalFilePath = path.join(
      PREPROCESSED_NO_WEATHER_PATH,
      finalFileName,
    );
    const previewRows = fs.existsSync(finalFilePath)
      ? await csv()
          .fromFile(finalFilePath)
          .then((rows) => rows.slice(0, 10))
      : [];

    res.json({
      success: true,
      rawUploadSaved: true,
      preprocessingSucceeded: true,
      uploadedFiles: uploadedFiles.map((f) => f.originalname),
      uploadedFilesCount: uploadedFiles.length,
      totalInputRows: null,
      totalUploadSizeMB: Number((totalUploadBytes / (1024 * 1024)).toFixed(2)),
      rowsCount,
      columnsCount: preprocessingResult?.columns || 0,
      finalFileName,
      downloadUrl: `/datasets/preprocessed_without_weather/${encodeURIComponent(finalFileName)}`,
      modelTrained: false,
      canTrain: rowsCount > 0,
      warningCode: rowsCount === 0 ? "PREPROCESSING_ZERO_ROWS" : null,
      warningMessage:
        rowsCount === 0
          ? "Preprocessing completed but produced 0 rows. Training and predictions are unavailable for this upload."
          : null,
      outputs: preprocessingResult?.outputs || {},
      preview: previewRows,
    });
  } catch (err) {
    console.error("Upload error:", err);
    res
      .status(500)
      .json({ success: false, error: "Upload failed: " + err.message });
  }
});

app.use((err, req, res, next) => {
  if (err instanceof multer.MulterError) {
    if (err.code === "LIMIT_FILE_SIZE") {
      return res.status(400).json({
        success: false,
        error:
          "Upload failed: file too large. Current limit is 250 MB per file.",
      });
    }
    return res
      .status(400)
      .json({ success: false, error: `Upload failed: ${err.message}` });
  }

  if (err) {
    return res.status(500).json({ success: false, error: err.message });
  }

  next();
});

const PORT = process.env.PORT || 5000;
app.listen(PORT, () => {
  console.log(`\n=== SERVER STARTED ===`);
  console.log(`Node.js backend listening on http://localhost:${PORT}`);
  console.log(`==================\n`);
});
