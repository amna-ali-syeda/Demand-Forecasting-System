#!/usr/bin/env node

/**
 * Build script to inject API_BASE_URL into HTML templates
 * This runs on Vercel before serving static files
 */

const fs = require('fs');
const path = require('path');

const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:5000';

console.log(`Injecting API_BASE_URL: ${API_BASE_URL}`);

// Create or update api-config.js
const configContent = `
// Auto-generated at build time
window.API_CONFIG = {
  BASE_URL: '${API_BASE_URL}'
};

// Helper function for API calls
window.apiCall = async (endpoint, options = {}) => {
  const url = window.API_CONFIG.BASE_URL + endpoint;
  return fetch(url, options);
};
`;

fs.writeFileSync(path.join(__dirname, 'static', 'api-config.js'), configContent);
console.log('✓ Created static/api-config.js');

// Inject script tag into HTML templates
const templatesDir = path.join(__dirname, 'templates');
const templateFiles = fs.readdirSync(templatesDir).filter(f => f.endsWith('.html'));

templateFiles.forEach(file => {
  const filePath = path.join(templatesDir, file);
  let content = fs.readFileSync(filePath, 'utf8');
  
  // Check if api-config.js is already included
  if (!content.includes('api-config.js')) {
    // Insert the script tag after the opening <head> tag
    content = content.replace(
      '  <head>',
      '  <head>\n    <script src="../static/api-config.js"></script>'
    );
    fs.writeFileSync(filePath, content);
    console.log(`✓ Updated ${file}`);
  } else {
    console.log(`✓ ${file} already has api-config.js`);
  }
});

console.log('Build complete!');
