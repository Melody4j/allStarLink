#!/usr/bin/env node
import { spawn } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

function startVite() {
  console.log('[Vite Server] Starting Vite dev server...');
  const vite = spawn('node', [
    path.join(__dirname, 'node_modules/vite/bin/vite.js'),
    '--host', '0.0.0.0'
  ], {
    cwd: __dirname,
    stdio: 'inherit'
  });

  vite.on('close', (code) => {
    console.log(`[Vite Server] Process exited with code ${code}, restarting in 2 seconds...`);
    setTimeout(startVite, 2000);
  });

  vite.on('error', (err) => {
    console.error('[Vite Server] Error:', err);
    setTimeout(startVite, 2000);
  });
}

startVite();
