# Deployment Guide: Frontend on Vercel + Backend Locally

This document explains how to deploy your Demand Forecasting System with the frontend on Vercel and the backend running locally or on a separate server.

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  Vercel (Frontend)                                           │
│  - Static HTML/CSS/JS templates                             │
│  - Makes API calls to backend URL                           │
│  - Accessible globally                                       │
└──────────────────────────────────────────────────────────────┘
                           ↓ (API calls)
┌──────────────────────────────────────────────────────────────┐
│  Your Server (Backend)                                       │
│  - Node.js server (server.js)                               │
│  - Python preprocessing & ML (basic_data_preprocessing.py)  │
│  - Model training (random_forest_model.py)                  │
│  - Persistent storage                                        │
└──────────────────────────────────────────────────────────────┘
```

---

## Step 1: Prepare Your GitHub Repository

Your GitHub repo already has the full codebase. To organize it:

### 1.1 Create two branches (optional but recommended):

```bash
git checkout -b main                    # Frontend for Vercel
git checkout -b backend-deployment      # Backend for your server
```

### 1.2 On `main` branch (Vercel deployment):

Files to keep:
- `templates/` (all HTML)
- `static/` (CSS and JS)
- `package.json` (frontend-only version - already updated)
- `vercel.json` (deployment config - already updated)
- `.vercelignore` (ignore backend files - already updated)
- `build.js` (API config injection)
- `README.md`

Files that will be ignored (excluded from Vercel):
- `server.js` (local dev only)
- `basic_data_preprocessing.py`
- `feature_engineering_new.py`
- `random_forest_model.py`
- `requirements.txt`
- `datasets/`, `metrics/`, `models/`, `modelPredictions/`

### 1.3 Push to GitHub:

```bash
git add .
git commit -m "Frontend-only deployment for Vercel"
git push origin main
```

---

## Step 2: Deploy Frontend to Vercel

### 2.1 Sign up for Vercel

Go to [vercel.com](https://vercel.com) and sign up with your GitHub account.

### 2.2 Connect your GitHub repo

1. Click "New Project"
2. Import your GitHub repository
3. Select the `main` branch
4. Click "Deploy"

### 2.3 Set Environment Variable for Backend URL

After initial deployment, go to Vercel dashboard:

1. **Project Settings** → **Environment Variables**
2. Add a new variable:
   - **Name**: `API_BASE_URL`
   - **Value**: `https://your-backend-domain.com` (or `http://localhost:5000` for testing)
3. Redeploy the project (Settings → Redeploy)

---

## Step 3: Run Backend Locally or on a Separate Server

### Option A: Local Development

```bash
# Navigate to your project directory
cd "e:\Personal_Documents\FYP_Ideas\Amna_FYP\FYP final"

# Install dependencies (already done)
npm install
pip install -r requirements.txt

# Start the backend
npm start
```

The backend will run on `http://localhost:5000`.

### Option B: Deploy Backend to a Hosting Service

Popular options:

#### **Render.com** (easiest, free tier available)
1. Push your backend to GitHub
2. Go to [render.com](https://render.com)
3. Create "New Web Service"
4. Connect your GitHub repo
5. Set buildcommand: `npm install && pip install -r requirements.txt`
6. Set start command: `npm start`
7. Copy the deployed URL (e.g., `https://fyp-backend.onrender.com`)
8. Go back to Vercel and update `API_BASE_URL` to this URL

#### **Heroku** (also good)
```bash
git push heroku main
```

#### **DigitalOcean App Platform**
Similar process to Render.

---

## Step 4: Test the Deployed Frontend

1. Go to your Vercel deployment URL (e.g., `https://fyp-frontend.vercel.app`)
2. You should see the login page
3. Log in and try uploading data
4. The frontend should make API calls to your backend

---

## Step 5: Update Frontend API URL (if needed)

If you change your backend URL later:

### On Vercel:
1. Settings → Environment Variables
2. Update `API_BASE_URL`
3. Redeploy (Settings → Redeploy)

### Locally (for testing):
1. The build script uses `process.env.API_BASE_URL` or defaults to `http://localhost:5000`
2. Run `npm run build` to regenerate `static/api-config.js`

---

## GitHub Workflow Going Forward

### For frontend changes (templates/static):
```bash
git checkout main
# make changes
git add .
git commit -m "Update frontend"
git push origin main
# Vercel auto-deploys
```

### For backend changes:
```bash
git checkout backend-deployment   # if using separate branch
# make changes to server.js, Python scripts
git add .
git commit -m "Update backend"
git push origin backend-deployment
# Deploy to your backend hosting service (Render/Heroku/etc)
```

---

## Troubleshooting

### Frontend shows "API Error" or blank page

**Check:**
1. Is the backend server running? (`http://your-backend-url/health` should return `{"status":"ok"}`)
2. Is `API_BASE_URL` set correctly in Vercel Environment Variables?
3. Are there CORS issues? (Check browser console for errors)

**Fix CORS:** If the backend returns CORS errors, ensure `server.js` has:
```javascript
const cors = require("cors");
app.use(cors());
```

### Upload fails

**Check:**
- Backend server is running
- Python dependencies are installed (`pip install -r requirements.txt`)
- Backend has write permissions to `datasets/` folder

### Build fails on Vercel

**Check:**
- `.vercelignore` is correctly excluding backend files
- `build.js` is executable and has no syntax errors
- Run locally: `node build.js`

---

## Quick Reference

| Component | Location | Language | Deployed On |
|-----------|----------|----------|-------------|
| Frontend | `templates/`, `static/` | HTML/JS/CSS | Vercel |
| Backend API | `server.js` | Node.js | Your Server |
| Data Processing | `basic_data_preprocessing.py` | Python | Your Server |
| Model Training | `random_forest_model.py` | Python | Your Server |

---

## Environment Variables Summary

### Vercel (Frontend)
- `API_BASE_URL`: Backend server URL

### Your Server (Backend)
- `PORT`: (optional) defaults to 5000
- `PYTHON_EXECUTABLE`: (optional) path to Python binary

---

## Summary

✅ You've already configured:
- `.gitignore` for local development
- `.vercelignore` for Vercel deployment
- `.gitignore` for clean commits
- `vercel.json` for Vercel config
- `package.json` for frontend-only
- `build.js` to inject API URL

✅ Next steps:
1. Push to GitHub (main branch)
2. Deploy to Vercel
3. Set `API_BASE_URL` environment variable
4. Run backend locally or deploy to a separate service
5. Access your app!

---

## Support

For issues:
- Vercel docs: https://vercel.com/docs
- Render docs: https://render.com/docs
- Check `browser console` (F12) for frontend errors
- Check terminal output for backend errors
