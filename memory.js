// copilotSessionDiscovery.js
// Node.js / VS Code extension friendly
// CommonJS version

const fs = require('fs');
const os = require('os');
const path = require('path');

async function pathExists(p) {
  try {
    await fs.promises.access(p, fs.constants.F_OK);
    return true;
  } catch {
    return false;
  }
}

async function statSafe(p) {
  try {
    return await fs.promises.stat(p);
  } catch {
    return null;
  }
}

function getHomeDir() {
  return os.homedir();
}

function getWorkspaceStorageRoots() {
  const home = getHomeDir();
  const roots = [];

  switch (process.platform) {
    case 'win32': {
      const appData = process.env.APPDATA || path.join(home, 'AppData', 'Roaming');
      roots.push(path.join(appData, 'Code', 'User', 'workspaceStorage'));
      roots.push(path.join(appData, 'Code - Insiders', 'User', 'workspaceStorage'));
      roots.push(path.join(appData, 'VSCodium', 'User', 'workspaceStorage'));
      break;
    }

    case 'darwin': {
      const base = path.join(home, 'Library', 'Application Support');
      roots.push(path.join(base, 'Code', 'User', 'workspaceStorage'));
      roots.push(path.join(base, 'Code - Insiders', 'User', 'workspaceStorage'));
      roots.push(path.join(base, 'VSCodium', 'User', 'workspaceStorage'));
      break;
    }

    default: {
      const config = process.env.XDG_CONFIG_HOME || path.join(home, '.config');
      roots.push(path.join(config, 'Code', 'User', 'workspaceStorage'));
      roots.push(path.join(config, 'Code - Insiders', 'User', 'workspaceStorage'));
      roots.push(path.join(config, 'VSCodium', 'User', 'workspaceStorage'));
      break;
    }
  }

  return roots;
}

function getCliSessionStateRoot() {
  return path.join(getHomeDir(), '.copilot', 'session-state');
}

async function readDirSafe(dir) {
  try {
    return await fs.promises.readdir(dir, { withFileTypes: true });
  } catch {
    return [];
  }
}

async function readTextSafe(filePath) {
  try {
    return await fs.promises.readFile(filePath, 'utf8');
  } catch {
    return '';
  }
}

function normalizeWhitespace(text) {
  return String(text || '').replace(/\s+/g, ' ').trim();
}

function safeJsonParse(text) {
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

function extractStringsDeep(node, out, pathHint = '') {
  if (node == null) return;

  if (typeof node === 'string') {
    const t = normalizeWhitespace(node);
    if (t.length >= 4) out.push({ text: t, path: pathHint });
    return;
  }

  if (Array.isArray(node)) {
    for (let i = 0; i < node.length; i += 1) {
      extractStringsDeep(node[i], out, `${pathHint}[${i}]`);
    }
    return;
  }

  if (typeof node === 'object') {
    const preferredKeys = new Set([
      'text',
      'value',
      'content',
      'message',
      'prompt',
      'response',
      'markdown',
      'body',
      'query',
      'title',
      'label'
    ]);

    for (const [key, value] of Object.entries(node)) {
      if (preferredKeys.has(key)) {
        extractStringsDeep(value, out, pathHint ? `${pathHint}.${key}` : key);
      }
    }

    for (const [key, value] of Object.entries(node)) {
      if (!preferredKeys.has(key)) {
        extractStringsDeep(value, out, pathHint ? `${pathHint}.${key}` : key);
      }
    }
  }
}

function guessRole(obj) {
  const candidates = [
    obj?.role,
    obj?.sender,
    obj?.author,
    obj?.source,
    obj?.message?.role,
    obj?.turn?.role,
    obj?.participant
  ]
    .filter(Boolean)
    .map(v => String(v).toLowerCase());

  for (const value of candidates) {
    if (value.includes('user') || value.includes('human')) return 'user';
    if (value.includes('assistant') || value.includes('model') || value.includes('copilot')) return 'assistant';
  }

  const type = String(obj?.type || obj?.kind || obj?.event || '').toLowerCase();
  if (type.includes('user')) return 'user';
  if (type.includes('prompt')) return 'user';
  if (type.includes('assistant')) return 'assistant';
  if (type.includes('response')) return 'assistant';

  return 'unknown';
}

function bestTextFromObject(obj) {
  const found = [];
  extractStringsDeep(obj, found);

  const cleaned = [];
  const seen = new Set();

  for (const item of found) {
    const text = item.text;
    if (text.length > 50000) continue;
    if (text.startsWith('http://') || text.startsWith('https://')) continue;

    if (!seen.has(text)) {
      seen.add(text);
      cleaned.push(item);
    }
  }

  cleaned.sort((a, b) => b.text.length - a.text.length);
  return cleaned.slice(0, 3).map(x => x.text);
}

function buildNormalizedMessage(obj, fallbackIndex) {
  const role = guessRole(obj);
  const parts = bestTextFromObject(obj);
  const text = parts.join('\n\n').trim();

  if (!text) return null;

  const timestamp =
    obj?.timestamp ||
    obj?.time ||
    obj?.createdAt ||
    obj?.created_at ||
    obj?.date ||
    null;

  return {
    id: obj?.id || `msg-${fallbackIndex}`,
    role,
    text,
    timestamp,
    raw: obj
  };
}

async function parseJsonlFile(filePath) {
  const text = await readTextSafe(filePath);
  const lines = text.split(/\r?\n/).filter(Boolean);

  const messages = [];
  let i = 0;

  for (const line of lines) {
    const obj = safeJsonParse(line);
    if (!obj) continue;

    const msg = buildNormalizedMessage(obj, i++);
    if (msg) messages.push(msg);
  }

  return messages;
}

function findCandidateArrays(rootObj) {
  if (!rootObj || typeof rootObj !== 'object') return [];

  const arrays = [];

  function walk(node, keyPath = '') {
    if (!node || typeof node !== 'object') return;

    if (Array.isArray(node)) {
      if (node.length > 0 && node.some(x => typeof x === 'object')) {
        arrays.push({ path: keyPath, value: node });
      }
      for (let i = 0; i < node.length; i += 1) {
        walk(node[i], `${keyPath}[${i}]`);
      }
      return;
    }

    for (const [key, value] of Object.entries(node)) {
      walk(value, keyPath ? `${keyPath}.${key}` : key);
    }
  }

  walk(rootObj);
  return arrays;
}

async function parseJsonFile(filePath) {
  const text = await readTextSafe(filePath);
  const obj = safeJsonParse(text);
  if (!obj) return [];

  let messageLikeArray = null;

  const directCandidates = [
    obj.messages,
    obj.turns,
    obj.events,
    obj.items,
    obj.chat,
    obj.conversation
  ].filter(Array.isArray);

  if (directCandidates.length > 0) {
    messageLikeArray = directCandidates[0];
  } else {
    const arrays = findCandidateArrays(obj);
    arrays.sort((a, b) => b.value.length - a.value.length);
    messageLikeArray = arrays.length ? arrays[0].value : null;
  }

  if (!messageLikeArray) {
    const single = buildNormalizedMessage(obj, 0);
    return single ? [single] : [];
  }

  const messages = [];
  for (let i = 0; i < messageLikeArray.length; i += 1) {
    const msg = buildNormalizedMessage(messageLikeArray[i], i);
    if (msg) messages.push(msg);
  }
  return messages;
}

function deriveLabelFromMessages(messages, fallback) {
  const firstUser = messages.find(m => m.role === 'user');
  if (firstUser?.text) {
    return firstUser.text.slice(0, 80);
  }
  return fallback;
}

async function discoverWorkspaceStorageSessions() {
  const results = [];
  const roots = getWorkspaceStorageRoots();

  for (const root of roots) {
    if (!(await pathExists(root))) continue;

    const workspaceDirs = await readDirSafe(root);

    for (const entry of workspaceDirs) {
      if (!entry.isDirectory()) continue;

      const workspaceFolder = path.join(root, entry.name);
      const chatSessionsDir = path.join(workspaceFolder, 'chatSessions');
      if (!(await pathExists(chatSessionsDir))) continue;

      const files = await readDirSafe(chatSessionsDir);
      for (const file of files) {
        if (!file.isFile()) continue;
        if (!file.name.endsWith('.json') && !file.name.endsWith('.jsonl')) continue;

        const fullPath = path.join(chatSessionsDir, file.name);
        const stat = await statSafe(fullPath);

        let messages = [];
        if (file.name.endsWith('.jsonl')) {
          messages = await parseJsonlFile(fullPath);
        } else {
          messages = await parseJsonFile(fullPath);
        }

        if (!messages.length) continue;

        results.push({
          source: 'workspaceStorage',
          os: process.platform,
          root,
          workspaceStorageId: entry.name,
          filePath: fullPath,
          fileName: file.name,
          sessionId: `${entry.name}:${file.name}`,
          label: deriveLabelFromMessages(messages, file.name),
          modifiedAt: stat ? stat.mtime.toISOString() : null,
          messages
        });
      }
    }
  }

  return results;
}

async function discoverCliSessionStateSessions() {
  const root = getCliSessionStateRoot();
  const results = [];

  if (!(await pathExists(root))) return results;

  const sessionDirs = await readDirSafe(root);
  for (const entry of sessionDirs) {
    if (!entry.isDirectory()) continue;

    const sessionDir = path.join(root, entry.name);
    const eventsPath = path.join(sessionDir, 'events.jsonl');
    if (!(await pathExists(eventsPath))) continue;

    const stat = await statSafe(eventsPath);
    const messages = await parseJsonlFile(eventsPath);
    if (!messages.length) continue;

    results.push({
      source: 'session-state',
      os: process.platform,
      root,
      sessionDir,
      filePath: eventsPath,
      fileName: 'events.jsonl',
      sessionId: entry.name,
      label: deriveLabelFromMessages(messages, entry.name),
      modifiedAt: stat ? stat.mtime.toISOString() : null,
      messages
    });
  }

  return results;
}

async function discoverAllSessions() {
  const [workspaceSessions, cliSessions] = await Promise.all([
    discoverWorkspaceStorageSessions(),
    discoverCliSessionStateSessions()
  ]);

  const all = [...workspaceSessions, ...cliSessions];

  all.sort((a, b) => {
    const ta = a.modifiedAt ? new Date(a.modifiedAt).getTime() : 0;
    const tb = b.modifiedAt ? new Date(b.modifiedAt).getTime() : 0;
    return tb - ta;
  });

  return all;
}

function buildQuickPickItems(sessions) {
  return sessions.map(session => ({
    label: session.label || session.fileName || session.sessionId,
    description:
      session.source === 'workspaceStorage'
        ? `VS Code • ${session.fileName}`
        : `Copilot CLI • ${session.sessionId}`,
    detail: session.filePath,
    session
  }));
}

function toTranscript(session, options = {}) {
  const maxMessages = Number.isInteger(options.maxMessages) ? options.maxMessages : 50;
  const slice = session.messages.slice(0, maxMessages);

  return slice
    .map((m, idx) => {
      const role = (m.role || 'unknown').toUpperCase();
      return `[${idx + 1}] ${role}\n${m.text}`;
    })
    .join('\n\n---\n\n');
}

module.exports = {
  getWorkspaceStorageRoots,
  getCliSessionStateRoot,
  discoverWorkspaceStorageSessions,
  discoverCliSessionStateSessions,
  discoverAllSessions,
  buildQuickPickItems,
  toTranscript
};
