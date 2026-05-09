const { app, BrowserWindow } = require("electron");
const { spawn } = require("child_process");
const fs = require("fs");
const http = require("http");
const path = require("path");

const isDev = !app.isPackaged;
const backendPort = isDev ? 8000 : 18765;
let backendProcess = null;

function parseEnvLines(content) {
  const values = new Map();
  for (const line of content.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#") || !trimmed.includes("=")) {
      continue;
    }
    const [key, ...parts] = trimmed.split("=");
    values.set(key.trim(), parts.join("=").trim());
  }
  return values;
}

function isMeaningfulEnvValue(value) {
  if (!value) {
    return false;
  }
  const normalized = value.trim().replace(/^["']|["']$/g, "");
  return Boolean(normalized) && !["your_api_key_here", "your_key_here", "changeme"].includes(normalized.toLowerCase());
}

function syncPackagedEnv(source, target) {
  if (!fs.existsSync(source)) {
    return;
  }

  if (!fs.existsSync(target)) {
    fs.mkdirSync(path.dirname(target), { recursive: true });
    fs.writeFileSync(target, "", "utf8");
    return;
  }

  const sourceText = fs.readFileSync(source, "utf8");
  const targetText = fs.readFileSync(target, "utf8");
  const sourceValues = parseEnvLines(sourceText);
  const targetValues = parseEnvLines(targetText);
  const syncKeys = [
    "AI_PROVIDER",
    "AI_API_KEY",
    "AI_BASE_URL",
    "AI_MODEL",
    "AI_TIMEOUT_SECONDS",
    "AI_MAX_TOKENS"
  ];
  const targetLines = targetText.split(/\r?\n/);
  let changed = false;

  for (const key of syncKeys) {
    const sourceValue = sourceValues.get(key);
    if (!isMeaningfulEnvValue(sourceValue)) {
      continue;
    }
    const targetValue = targetValues.get(key);
    if (isMeaningfulEnvValue(targetValue)) {
      continue;
    }

    const lineIndex = targetLines.findIndex((line) => line.trim().startsWith(`${key}=`));
    if (lineIndex >= 0) {
      targetLines[lineIndex] = `${key}=${sourceValue}`;
    } else {
      targetLines.push(`${key}=${sourceValue}`);
    }
    changed = true;
  }

  if (changed) {
    fs.mkdirSync(path.dirname(target), { recursive: true });
    fs.writeFileSync(target, targetLines.join("\n"), "utf8");
  }
}

function waitForBackend(timeoutMs = 20000) {
  const startedAt = Date.now();
  return new Promise((resolve) => {
    const check = () => {
      const request = http.get(`http://127.0.0.1:${backendPort}/api/health`, (response) => {
        response.resume();
        if (response.statusCode === 200) {
          resolve(true);
          return;
        }
        retry();
      });
      request.on("error", retry);
      request.setTimeout(1000, () => {
        request.destroy();
        retry();
      });
    };

    const retry = () => {
      if (Date.now() - startedAt >= timeoutMs) {
        resolve(false);
        return;
      }
      setTimeout(check, 500);
    };

    check();
  });
}

function startBackendIfPackaged() {
  if (isDev) {
    return;
  }

  const backendPath = path.join(process.resourcesPath, "backend", "ielts-backend.exe");
  const packagedEnvPath = path.join(process.resourcesPath, ".env");
  const userDataDir = app.getPath("userData");
  const userDbPath = path.join(userDataDir, "data", "ielts_tutor.sqlite");
  const userEnvPath = path.join(userDataDir, ".env");

  fs.mkdirSync(path.dirname(userDbPath), { recursive: true });
  syncPackagedEnv(packagedEnvPath, userEnvPath);
  if (!fs.existsSync(userEnvPath)) {
    fs.writeFileSync(userEnvPath, "", "utf8");
  }

  backendProcess = spawn(backendPath, [], {
    windowsHide: true,
    stdio: "ignore",
    env: {
      ...process.env,
      IELTS_TUTOR_DB_PATH: userDbPath,
      IELTS_TUTOR_ENV_PATH: userEnvPath,
      IELTS_TUTOR_PORT: String(backendPort),
      IELTS_TUTOR_RESOURCES_PATH: process.resourcesPath
    }
  });

  backendProcess.on("error", () => {
    backendProcess = null;
  });
}

async function createWindow() {
  const window = new BrowserWindow({
    width: 1220,
    height: 820,
    minWidth: 980,
    minHeight: 680,
    backgroundColor: "#f8fafc",
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false
    }
  });

  if (isDev) {
    window.loadURL("http://127.0.0.1:5173");
  } else {
    const loadingHtml = `
      <!doctype html>
      <html>
        <head>
          <meta charset="utf-8" />
          <style>
            body {
              margin: 0;
              min-height: 100vh;
              display: grid;
              place-items: center;
              font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
              background: #f8fafc;
              color: #0f172a;
            }
            main {
              text-align: center;
            }
            p {
              color: #64748b;
            }
          </style>
        </head>
        <body>
          <main>
            <h1>雅思 AI 私教</h1>
            <p>正在启动本地学习服务...</p>
          </main>
        </body>
      </html>
    `;
    window.loadURL(`data:text/html;charset=utf-8,${encodeURIComponent(loadingHtml)}`);
    await waitForBackend();
    window.loadFile(path.join(__dirname, "../dist/index.html"));
  }
}

app.whenReady().then(async () => {
  startBackendIfPackaged();
  await createWindow();
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});

app.on("before-quit", () => {
  if (backendProcess) {
    backendProcess.kill();
    backendProcess = null;
  }
});

app.on("activate", () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});
