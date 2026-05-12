#!/usr/bin/env node

const fs = require("fs");
const path = require("path");

const ROOT_DIR = __dirname;
const TEMPLATES_DIR = path.join(ROOT_DIR, "templates");
const STATIC_DIR = path.join(ROOT_DIR, "static");
const DIST_DIR = path.join(ROOT_DIR, "dist");
const DIST_STATIC_DIR = path.join(DIST_DIR, "static");

const API_BASE_URL = process.env.API_BASE_URL || "http://localhost:5008";

function ensureDir(dirPath) {
  fs.mkdirSync(dirPath, { recursive: true });
}

function writeApiConfig(targetDir) {
  ensureDir(targetDir);

  const configContent = `window.API_CONFIG = {
  BASE_URL: ${JSON.stringify(API_BASE_URL)}
};

window.resolveApiUrl = function resolveApiUrl(endpoint) {
  const base = String(window.API_CONFIG.BASE_URL || "").replace(/\\/$/, "");
  const path = String(endpoint || "");

  if (!base) return path;
  if (/^https?:\\/\\//i.test(path)) return path;

  return base + (path.startsWith("/") ? path : "/" + path);
};

window.apiFetch = function apiFetch(endpoint, options) {
  return fetch(window.resolveApiUrl(endpoint), options);
};
`;

  fs.writeFileSync(
    path.join(targetDir, "api-config.js"),
    configContent,
    "utf8",
  );
}

function transformHtml(html) {
  let output = html.replace(
    /<script src="\.\.\/static\/api-config\.js"><\/script>\s*/g,
    "",
  );

  if (!output.includes("/static/api-config.js")) {
    output = output.replace(
      "<head>",
      '  <head>\n    <script src="/static/api-config.js"></script>',
    );
  }

  return output.replace(/\.\.\/static\//g, "/static/");
}

function copyTemplates() {
  const templateFiles = fs
    .readdirSync(TEMPLATES_DIR)
    .filter((file) => file.endsWith(".html"));

  templateFiles.forEach((file) => {
    const sourcePath = path.join(TEMPLATES_DIR, file);
    const destinationPath = path.join(DIST_DIR, file);
    const content = fs.readFileSync(sourcePath, "utf8");
    fs.writeFileSync(destinationPath, transformHtml(content), "utf8");
  });
}

function build() {
  console.log(`Building static frontend with API_BASE_URL=${API_BASE_URL}`);

  fs.rmSync(DIST_DIR, { recursive: true, force: true });
  ensureDir(DIST_DIR);
  fs.cpSync(STATIC_DIR, DIST_STATIC_DIR, { recursive: true });

  writeApiConfig(STATIC_DIR);
  writeApiConfig(DIST_STATIC_DIR);
  copyTemplates();

  console.log("Static build complete: dist/");
}

build();
