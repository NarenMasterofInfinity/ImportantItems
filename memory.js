const vscode = require('vscode');
const fs = require('fs');
const os = require('os');
const path = require('path');
const cp = require('child_process');

const STATE_KEY = 'copilotSessionMemory.activeSession';
const SESSION_ROOT = path.join(os.homedir(), '.copilot', 'session-state');

function activate(context) {
  const participant = vscode.chat.createChatParticipant(
    'copilot-session-memory.memory',
    createHandler(context)
  );

  participant.iconPath = new vscode.ThemeIcon('history');

  context.subscriptions.push(participant);
}

function deactivate() {}

function createHandler(extensionContext) {
  /**
   * @type {vscode.ChatRequestHandler}
   */
  return async (request, chatContext, stream, token) => {
    try {
      if (request.command === 'clear') {
        await extensionContext.workspaceState.update(STATE_KEY, undefined);
        stream.markdown('Cleared the loaded session memory.');
        return;
      }

      if (request.command === 'show') {
        const active = extensionContext.workspaceState.get(STATE_KEY);
        if (!active) {
          stream.markdown('No session memory is loaded. Use `/reuse` first.');
          return;
        }

        stream.markdown(
          [
            `Loaded session: \`${active.id}\``,
            '',
            active.summary ? active.summary : '_No summary cached yet._'
          ].join('\n')
        );
        return;
      }

      let active = extensionContext.workspaceState.get(STATE_KEY);

      const shouldPick =
        request.command === 'reuse' ||
        !active ||
        (request.prompt || '').trim().startsWith('pick ') ||
        (request.prompt || '').trim() === '';

      if (shouldPick) {
        const picked = await pickSession();
        if (!picked) {
          stream.markdown('No session selected.');
          return;
        }

        stream.progress(`Loading session ${picked.id}...`);

        const transcript = await loadSessionTranscript(picked);
        const summary = await summarizeTranscript(request.model, transcript, token);

        active = {
          id: picked.id,
          label: picked.label,
          workspace: picked.workspace || '',
          when: picked.when || '',
          transcript,
          summary
        };

        await extensionContext.workspaceState.update(STATE_KEY, active);

        if (!request.prompt || !request.prompt.trim()) {
          stream.markdown(
            [
              `Loaded session memory from \`${picked.id}\`.`,
              '',
              'Summary:',
              '',
              summary
            ].join('\n')
          );
          return;
        }
      }

      if (!active) {
        stream.markdown('No session memory is loaded. Use `@memory /reuse`.');
        return;
      }

      stream.progress(`Using memory from session ${active.id}...`);

      const messages = buildMessagesForContinuation(active, request.prompt || '', chatContext);
      const chatResponse = await request.model.sendRequest(messages, {}, token);

      for await (const fragment of chatResponse.text) {
        stream.markdown(fragment);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      stream.markdown(`Failed: ${escapeMd(message)}`);
    }
  };
}

async function pickSession() {
  const sessions = await discoverSessions();

  if (!sessions.length) {
    void vscode.window.showWarningMessage(
      `No Copilot sessions found under ${SESSION_ROOT}`
    );
    return undefined;
  }

  const items = sessions.map(session => ({
    label: session.label,
    description: session.workspace || session.id,
    detail: `${session.when || 'unknown time'} • ${session.id}`,
    session
  }));

  const picked = await vscode.window.showQuickPick(items, {
    title: 'Select a Copilot session to reuse',
    matchOnDescription: true,
    matchOnDetail: true,
    placeHolder: 'Choose the old session whose memory should be injected into this chat'
  });

  return picked ? picked.session : undefined;
}

async function discoverSessions() {
  if (!fs.existsSync(SESSION_ROOT)) {
    return [];
  }

  const dirents = await fs.promises.readdir(SESSION_ROOT, { withFileTypes: true });
  const sessions = [];

  for (const entry of dirents) {
    if (!entry.isDirectory()) continue;

    const sessionId = entry.name;
    const sessionDir = path.join(SESSION_ROOT, sessionId);
    const workspaceYaml = path.join(sessionDir, 'workspace.yaml');
    const planMd = path.join(sessionDir, 'plan.md');
    const eventsJsonl = path.join(sessionDir, 'events.jsonl');

    if (!fs.existsSync(eventsJsonl)) continue;

    let workspace = '';
    let label = sessionId;

    if (fs.existsSync(workspaceYaml)) {
      const yaml = await safeReadFile(workspaceYaml);
      workspace =
        firstYamlValue(yaml, ['cwd', 'workspace', 'workspace_root', 'repository', 'repo']) || '';
    }

    if (fs.existsSync(planMd)) {
      const plan = await safeReadFile(planMd);
      const title = firstMarkdownHeading(plan);
      if (title) {
        label = title;
      }
    } else {
      label = workspace ? `${path.basename(workspace)}` : sessionId;
    }

    const stat = await fs.promises.stat(eventsJsonl);
    sessions.push({
      id: sessionId,
      dir: sessionDir,
      label,
      workspace,
      when: stat.mtime.toLocaleString()
    });
  }

  sessions.sort((a, b) => {
    const ta = new Date(a.when).getTime();
    const tb = new Date(b.when).getTime();
    return (Number.isFinite(tb) ? tb : 0) - (Number.isFinite(ta) ? ta : 0);
  });

  return sessions;
}

async function loadSessionTranscript(session) {
  const exported = await tryExportWithCopilotSessionTools(session.id);
  if (exported) {
    return exported;
  }

  const raw = await extractTranscriptFromEvents(session.dir);
  const planPath = path.join(session.dir, 'plan.md');
  const workspacePath = path.join(session.dir, 'workspace.yaml');

  let extras = [];

  if (fs.existsSync(workspacePath)) {
    const yaml = await safeReadFile(workspacePath);
    extras.push('Workspace metadata:\n' + yaml);
  }

  if (fs.existsSync(planPath)) {
    const plan = await safeReadFile(planPath);
    extras.push('Plan:\n' + plan);
  }

  return [
    `Session ID: ${session.id}`,
    session.workspace ? `Workspace: ${session.workspace}` : '',
    '',
    raw,
    '',
    extras.join('\n\n')
  ]
    .filter(Boolean)
    .join('\n');
}

async function tryExportWithCopilotSessionTools(sessionId) {
  const tmpRoot = await fs.promises.mkdtemp(path.join(os.tmpdir(), 'cst-export-'));

  try {
    const args = [
      'export-markdown',
      '--session-id',
      sessionId,
      '--output-dir',
      tmpRoot,
      '--include-diffs'
    ];

    const result = cp.spawnSync('copilot-session-tools', args, {
      encoding: 'utf8',
      timeout: 30000
    });

    if (result.error || result.status !== 0) {
      return null;
    }

    const files = await fs.promises.readdir(tmpRoot);
    const mdFile = files.find(f => f.toLowerCase().endsWith('.md'));
    if (!mdFile) return null;

    return await safeReadFile(path.join(tmpRoot, mdFile));
  } catch {
    return null;
  } finally {
    fs.rm(tmpRoot, { recursive: true, force: true }, () => {});
  }
}

async function extractTranscriptFromEvents(sessionDir) {
  const eventsPath = path.join(sessionDir, 'events.jsonl');
  const text = await safeReadFile(eventsPath);
  const lines = text.split(/\r?\n/).filter(Boolean);

  const out = [];
  let userCount = 0;
  let assistantCount = 0;

  for (const line of lines) {
    let obj;
    try {
      obj = JSON.parse(line);
    } catch {
      continue;
    }

    const role = inferRole(obj);
    const content = extractBestText(obj);

    if (!content) continue;

    if (role === 'user') {
      userCount += 1;
      out.push(`User ${userCount}:\n${content}`);
    } else if (role === 'assistant') {
      assistantCount += 1;
      out.push(`Assistant ${assistantCount}:\n${content}`);
    }
  }

  if (!out.length) {
    return 'Could not parse structured messages from events.jsonl. Raw events exist but did not match the fallback parser.';
  }

  return out.join('\n\n---\n\n');
}

function inferRole(obj) {
  const candidates = [
    obj.role,
    obj.message?.role,
    obj.turn?.role,
    obj.author,
    obj.sender,
    obj.source
  ].filter(Boolean).map(v => String(v).toLowerCase());

  for (const value of candidates) {
    if (value.includes('user')) return 'user';
    if (value.includes('assistant')) return 'assistant';
    if (value.includes('model')) return 'assistant';
  }

  const eventType = String(obj.type || obj.event || obj.kind || '').toLowerCase();
  if (eventType.includes('user')) return 'user';
  if (eventType.includes('assistant')) return 'assistant';
  if (eventType.includes('prompt')) return 'user';
  if (eventType.includes('response')) return 'assistant';

  const text = JSON.stringify(obj).toLowerCase();
  if (text.includes('"role":"user"')) return 'user';
  if (text.includes('"role":"assistant"')) return 'assistant';

  return undefined;
}

function extractBestText(obj) {
  const candidates = [];

  collectStringsFromKnownPaths(obj, candidates);

  const cleaned = candidates
    .map(s => String(s).trim())
    .filter(Boolean)
    .filter(s => s.length > 8)
    .filter(s => !looksLikeNoise(s));

  if (!cleaned.length) return '';

  cleaned.sort((a, b) => b.length - a.length);
  return dedupeNearby(cleaned).slice(0, 3).join('\n\n');
}

function collectStringsFromKnownPaths(obj, out) {
  const visited = new Set();

  function walk(node, keyPath = '') {
    if (!node || typeof node !== 'object') return;
    if (visited.has(node)) return;
    visited.add(node);

    for (const [key, value] of Object.entries(node)) {
      const currentPath = keyPath ? `${keyPath}.${key}` : key;

      if (typeof value === 'string') {
        const lower = currentPath.toLowerCase();
        if (
          lower.includes('content') ||
          lower.includes('text') ||
          lower.includes('prompt') ||
          lower.includes('message') ||
          lower.includes('response') ||
          lower.includes('transformedcontent') ||
          lower.includes('markdown')
        ) {
          out.push(value);
        }
      } else if (Array.isArray(value)) {
        for (const item of value) {
          if (typeof item === 'string') {
            out.push(item);
          } else {
            walk(item, currentPath);
          }
        }
      } else if (value && typeof value === 'object') {
        walk(value, currentPath);
      }
    }
  }

  walk(obj);
}

function looksLikeNoise(s) {
  const lower = s.toLowerCase();
  return (
    lower.startsWith('http://') ||
    lower.startsWith('https://') ||
    lower.includes('x-amz-signature') ||
    lower.length > 50000
  );
}

function dedupeNearby(items) {
  const result = [];
  for (const item of items) {
    const normalized = item.replace(/\s+/g, ' ').trim();
    const exists = result.some(
      x =>
        x.replace(/\s+/g, ' ').trim() === normalized ||
        x.includes(item) ||
        item.includes(x)
    );
    if (!exists) result.push(item);
  }
  return result;
}

async function summarizeTranscript(model, transcript, token) {
  const capped = transcript.length > 120000
    ? transcript.slice(0, 120000) + '\n\n[truncated]'
    : transcript;

  const messages = [
    vscode.LanguageModelChatMessage.User(
      [
        'Summarize this earlier Copilot session so it can be reused as memory in a fresh chat.',
        '',
        'Return markdown with exactly these sections:',
        '1. Goal',
        '2. Decisions',
        '3. Current state',
        '4. Important files or components',
        '5. Next steps',
        '',
        'Be concrete. Preserve technical choices, constraints, and unresolved items.',
        '',
        'SESSION TRANSCRIPT:',
        capped
      ].join('\n')
    )
  ];

  const response = await model.sendRequest(messages, {}, token);
  let text = '';
  for await (const chunk of response.text) {
    text += chunk;
  }
  return text.trim();
}

function buildMessagesForContinuation(active, prompt, chatContext) {
  const historyParts = [];

  for (const turn of chatContext.history || []) {
    if (turn instanceof vscode.ChatRequestTurn) {
      historyParts.push(`User: ${turn.prompt}`);
    } else if (turn instanceof vscode.ChatResponseTurn) {
      let combined = '';
      for (const part of turn.response) {
        if (part && part.value && typeof part.value.value === 'string') {
          combined += part.value.value + '\n';
        }
      }
      if (combined.trim()) {
        historyParts.push(`Assistant: ${combined.trim()}`);
      }
    }
  }

  const systemLikeMemory = [
    'You are continuing work from an earlier Copilot session.',
    '',
    `Original session id: ${active.id}`,
    active.workspace ? `Workspace: ${active.workspace}` : '',
    '',
    'Memory summary:',
    active.summary || '(no summary)',
    '',
    'Use this memory as context, but do not pretend you still have access to hidden state from that old session.',
    'If something is uncertain, say so explicitly.'
  ]
    .filter(Boolean)
    .join('\n');

  const messages = [
    vscode.LanguageModelChatMessage.User(systemLikeMemory)
  ];

  if (historyParts.length) {
    messages.push(
      vscode.LanguageModelChatMessage.User(
        'Relevant messages already exchanged in this new chat:\n\n' + historyParts.join('\n\n')
      )
    );
  }

  messages.push(
    vscode.LanguageModelChatMessage.User(
      `Current user request:\n${prompt || 'Continue from the loaded session memory.'}`
    )
  );

  return messages;
}

function firstYamlValue(yaml, keys) {
  for (const key of keys) {
    const re = new RegExp(`^\\s*${escapeRegex(key)}\\s*:\\s*(.+?)\\s*$`, 'mi');
    const match = yaml.match(re);
    if (match) {
      return String(match[1]).replace(/^['"]|['"]$/g, '').trim();
    }
  }
  return '';
}

function firstMarkdownHeading(md) {
  const match = md.match(/^#\s+(.+)$/m);
  return match ? match[1].trim() : '';
}

async function safeReadFile(filePath) {
  try {
    return await fs.promises.readFile(filePath, 'utf8');
  } catch {
    return '';
  }
}

function escapeRegex(s) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function escapeMd(s) {
  return String(s).replace(/[`*_{}[\]()#+\-.!]/g, '\\$&');
}

module.exports = {
  activate,
  deactivate
};
