// ── Theme Switcher ───────────────────────────────────────
const themes = [
    { name: 'Mystic Dusk', key: 'mystic-dusk' },
    { name: 'Desert Bloom', key: 'desert-bloom' },
    { name: 'Abyss', key: 'abyss' },
    { name: 'Neon Burst', key: 'neon-burst' },
    { name: 'Lavender Dream', key: 'lavender-dream' },
];

let currentThemeIndex = 0;
const themeBtn = document.getElementById('theme-btn');
const themeName = document.getElementById('theme-name');

function applyTheme(index) {
    const theme = themes[index];
    if (theme.key === 'mystic-dusk') {
        document.documentElement.removeAttribute('data-theme');
    } else {
        document.documentElement.setAttribute('data-theme', theme.key);
    }
    themeName.textContent = theme.name;
    localStorage.setItem('idi-theme', index);
}

const saved = localStorage.getItem('idi-theme');
if (saved !== null) {
    currentThemeIndex = parseInt(saved, 10);
    applyTheme(currentThemeIndex);
}

themeBtn.addEventListener('click', () => {
    currentThemeIndex = (currentThemeIndex + 1) % themes.length;
    applyTheme(currentThemeIndex);
});

// ── Chat helpers ─────────────────────────────────────────
const chatBox = document.getElementById('chat-box');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');
const stopBtn = document.getElementById('stop-btn');

let currentAbortController = null;

function appendUserMessage(text) {
    const div = document.createElement('div');
    div.className = 'message user-message';
    div.innerText = text;
    chatBox.appendChild(div);
    chatBox.scrollTop = chatBox.scrollHeight;
}

function showGenerating() {
    const indicator = document.createElement('div');
    indicator.className = 'generating-indicator';
    indicator.id = 'generating-indicator';
    indicator.innerHTML = `
        <span class="label">Generating</span>
        <div class="bouncing-balls">
            <span></span><span></span><span></span>
        </div>
    `;
    chatBox.appendChild(indicator);
    chatBox.scrollTop = chatBox.scrollHeight;
}

function removeGenerating() {
    const el = document.getElementById('generating-indicator');
    if (el) el.remove();
}

// ── SQL Syntax Highlighter ────────────────────────────────
/**
 * Highlight SQL keywords/strings/numbers/etc. in `code`.
 *
 * Strategy: split the string into alternating "safe" (already-wrapped span)
 * and "raw" segments. Only raw segments get further token substitutions.
 * This prevents keywords from matching inside span class="..." attributes or
 * inside already-colored spans (which would produce malformed nested HTML).
 */
function highlightSQL(code) {
    // 1. HTML-escape the raw SQL
    let escaped = code
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');

    // 2. Apply passes in priority order, protecting prior spans each time.
    //    Each pass: split on existing <span…>…</span>, apply only to gaps.
    const applyToRaw = (html, re, replacement) => {
        // Tokenise into alternating raw / already-wrapped-span chunks.
        // Spans are left verbatim; only raw chunks get the substitution.
        const result = [];
        const spanRe = /(<span[^>]*>(?:[^<]|<(?!\/span>))*<\/span>)/g;
        let cursor = 0, sm;
        while ((sm = spanRe.exec(html)) !== null) {
            if (sm.index > cursor) {
                result.push(html.slice(cursor, sm.index).replace(re, replacement));
            }
            result.push(sm[1]); // protected span — untouched
            cursor = sm.index + sm[0].length;
        }
        if (cursor < html.length) {
            result.push(html.slice(cursor).replace(re, replacement));
        }
        return result.join('');
    };

    // Comments first (highest priority)
    escaped = applyToRaw(escaped,
        /(--[^\n]*|\/\*[\s\S]*?\*\/)/g,
        '<span class="sql-comment">$1</span>');

    // Strings
    escaped = applyToRaw(escaped,
        /('([^'\\]|\\.)*'|"([^"\\]|\\.)*")/g,
        '<span class="sql-string">$1</span>');

    // Named params (:name)
    escaped = applyToRaw(escaped,
        /(:[a-zA-Z_]\w*)/g,
        '<span class="sql-param">$1</span>');

    // Numbers
    escaped = applyToRaw(escaped,
        /\b(\d+(?:\.\d+)?)\b/g,
        '<span class="sql-number">$1</span>');

    // Keywords (case-insensitive, whole-word)
    escaped = applyToRaw(escaped,
        /\b(SELECT|FROM|WHERE|JOIN|LEFT|RIGHT|INNER|OUTER|FULL|CROSS|ON|GROUP\s+BY|ORDER\s+BY|PARTITION\s+BY|HAVING|LIMIT|OFFSET|AS|DISTINCT|COUNT|SUM|AVG|MIN|MAX|COALESCE|NULLIF|CASE|WHEN|THEN|ELSE|END|AND|OR|NOT|IN|IS|NULL|LIKE|BETWEEN|EXISTS|UNION|ALL|WITH|OVER|RANK|ROW_NUMBER|DENSE_RANK|TOP|FETCH|NEXT|ROWS|ONLY|ASC|DESC|BY|INTO|SET|VALUES|INSERT|UPDATE|DELETE|CREATE|DROP|ALTER|TABLE|VIEW|INDEX|DATABASE|SCHEMA)\b/gi,
        (m) => `<span class="sql-kw">${m}</span>`);

    // Operators
    escaped = applyToRaw(escaped,
        /([=<>!]{1,2}|[+\-*/%]|\|\|)/g,
        '<span class="sql-op">$1</span>');

    return escaped;
}

// ── Markdown Renderer ─────────────────────────────────────
// Sections to completely remove (thought process)
const HIDDEN_SECTIONS = [
    'Validated Logical Grain',
    'Potential Pitfalls & Mitigations',
    'Confidence Score',
];

// Sections to collapse into a <details> toggle
const COLLAPSIBLE_SECTIONS = [
    'Assumptions',
];

/**
 * Split a markdown string into named sections at ### headings.
 * Returns an array of { heading: string|null, content: string }.
 */
function splitIntoSections(text) {
    const lines = text.split('\n');
    const sections = [];
    let current = { heading: null, content: [] };

    for (const line of lines) {
        const h3 = line.match(/^###\s+(.+)/);
        if (h3) {
            sections.push(current);
            current = { heading: h3[1].trim(), content: [] };
        } else {
            current.content.push(line);
        }
    }
    sections.push(current);
    return sections;
}

/**
 * Render a markdown string to an HTML string.
 * Handles: ### headings, ## headings, # headings,
 *          **bold**, *italic*, bullet lists, fenced code blocks,
 *          horizontal rules, plain paragraphs.
 * Fenced code blocks with lang=sql get syntax highlighted.
 */
function renderMarkdown(md) {
    // Split off fenced code blocks so we don't mangle their content
    const parts = [];
    const codeRe = /```([a-z]*)\n?([\s\S]*?)```/g;
    let last = 0, m;
    while ((m = codeRe.exec(md)) !== null) {
        if (m.index > last) parts.push({ type: 'md', content: md.slice(last, m.index) });
        parts.push({ type: 'code', lang: m[1].toLowerCase(), content: m[2] });
        last = m.index + m[0].length;
    }
    if (last < md.length) parts.push({ type: 'md', content: md.slice(last) });

    let html = '';
    for (const part of parts) {
        if (part.type === 'code') {
            const inner = part.lang === 'sql'
                ? highlightSQL(part.content)
                : part.content.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
            html += `<pre><code class="lang-${part.lang || 'plain'}">${inner}</code></pre>`;
        } else {
            html += renderMdText(part.content);
        }
    }
    return html;
}

function renderMdText(text) {
    const lines = text.split('\n');
    let html = '';
    let inList = false;

    const closeList = () => { if (inList) { html += '</ul>'; inList = false; } };
    const inlinify = (s) => s
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.+?)\*/g, '<em>$1</em>')
        .replace(/`([^`]+)`/g, '<code>$1</code>');

    for (const line of lines) {
        const h3 = line.match(/^###\s+(.*)/);
        const h2 = line.match(/^##\s+(.*)/);
        const h1 = line.match(/^#\s+(.*)/);
        const bullet = line.match(/^[\*\-]\s+(.*)/);
        const numbered = line.match(/^\d+\.\s+(.*)/);
        const hr = line.match(/^---+$/);
        const trimmed = line.trim();

        if (h3) { closeList(); html += `<h3>${inlinify(h3[1])}</h3>`; }
        else if (h2) { closeList(); html += `<h2>${inlinify(h2[1])}</h2>`; }
        else if (h1) { closeList(); html += `<h1>${inlinify(h1[1])}</h1>`; }
        else if (hr) { closeList(); html += '<hr>'; }
        else if (bullet || numbered) {
            if (!inList) { html += '<ul>'; inList = true; }
            html += `<li>${inlinify((bullet || numbered)[1])}</li>`;
        } else if (trimmed === '') {
            closeList();
            // blank line → paragraph break (don't emit a tag, just close list)
        } else {
            closeList();
            html += `<p>${inlinify(line)}</p>`;
        }
    }
    closeList();
    return html;
}

/**
 * Build the final DOM for a bot response.
 * - Filters hidden sections
 * - Collapses Assumptions into <details>
 * - Renders markdown including SQL highlighting
 */
function buildBotMessage(rawText) {
    const wrapper = document.createElement('div');
    wrapper.className = 'message bot-message';

    const sections = splitIntoSections(rawText);

    for (const sec of sections) {
        const heading = sec.heading;
        const body = sec.content.join('\n').trim();

        // Skip entirely hidden sections
        if (heading && HIDDEN_SECTIONS.some(h => heading.includes(h))) continue;

        // Collapsible sections
        if (heading && COLLAPSIBLE_SECTIONS.some(h => heading.includes(h))) {
            if (!body) continue;
            const details = document.createElement('details');
            details.className = 'assumptions-details';
            const summary = document.createElement('summary');
            summary.className = 'assumptions-summary';
            summary.innerHTML = '<span class="thinking-dots"><span></span><span></span><span></span></span>Thinking';
            details.appendChild(summary);
            const inner = document.createElement('div');
            inner.className = 'assumptions-body';
            inner.innerHTML = renderMarkdown(body);
            details.appendChild(inner);
            wrapper.appendChild(details);
            continue;
        }

        // Normal sections
        if (heading) {
            const hEl = document.createElement('h3');
            hEl.className = 'section-heading';
            hEl.textContent = heading;
            wrapper.appendChild(hEl);
        }
        if (body) {
            // Safety net: if this is the SQL Query section and the body has no
            // fenced code block, wrap the whole body as a sql block so it always
            // gets syntax-highlighted and never rendered as markdown prose.
            let renderedBody = body;
            const isSQLSection = heading && heading.toLowerCase().includes('sql query');
            if (isSQLSection && !body.includes('```')) {
                renderedBody = '```sql\n' + body.trim() + '\n```';
            }
            const bodyEl = document.createElement('div');
            bodyEl.className = 'section-body';
            bodyEl.innerHTML = renderMarkdown(renderedBody);
            wrapper.appendChild(bodyEl);
        }
    }

    return wrapper;
}

// ── Typewriter with live rendering and click-to-skip ─────
/**
 * Returns true if `text` contains an odd number of ``` fences,
 * meaning we are currently inside an unclosed code block.
 */
function insideCodeFence(text) {
    const matches = text.match(/```/g);
    return matches ? matches.length % 2 !== 0 : false;
}

/**
 * Typewriter-render a bot message character-by-character.
 *
 * Strategy: accumulate chars into a buffer and re-render via buildBotMessage()
 * every RENDER_EVERY chars. While inside an unclosed ``` fence we defer the
 * re-render (raw SQL mid-fence would show as unstyled text). Once the fence
 * closes the whole block renders at once, already highlighted.
 *
 * Clicking the bubble at any point flushes the full text instantly.
 */
function typewriterAppend(rawText, speedMs = 22) {
    if (rawText.startsWith('⚠️')) {
        const div = document.createElement('div');
        div.className = 'message bot-message';
        div.textContent = rawText;
        chatBox.appendChild(div);
        chatBox.scrollTop = chatBox.scrollHeight;
        return;
    }

    const chars = [...rawText]; // unicode-safe split
    const total = chars.length;
    const RENDER_EVERY = 6; // re-render DOM every N chars

    const liveDiv = document.createElement('div');
    liveDiv.className = 'message bot-message typing-live';
    chatBox.appendChild(liveDiv);
    chatBox.scrollTop = chatBox.scrollHeight;

    let i = 0;
    let buffer = '';
    let done = false;
    let timerId = null;

    function render(text) {
        const node = buildBotMessage(text);
        const cursor = document.createElement('span');
        cursor.className = 'typewriter-cursor';
        node.appendChild(cursor);
        liveDiv.innerHTML = '';
        while (node.firstChild) liveDiv.appendChild(node.firstChild);
    }

    function flush() {
        if (done) return;
        done = true;
        if (timerId) clearTimeout(timerId);
        const node = buildBotMessage(rawText);
        liveDiv.innerHTML = '';
        while (node.firstChild) liveDiv.appendChild(node.firstChild);
        liveDiv.classList.remove('typing-live');
        chatBox.scrollTop = chatBox.scrollHeight;
    }

    liveDiv.addEventListener('click', flush);

    function tick() {
        if (done) return;
        const batchEnd = Math.min(i + RENDER_EVERY, total);
        buffer += chars.slice(i, batchEnd).join('');
        i = batchEnd;

        // Only re-render when NOT inside an unclosed code fence.
        // This prevents the flash of raw SQL text before the fence closes.
        if (!insideCodeFence(buffer)) {
            render(buffer);
            chatBox.scrollTop = chatBox.scrollHeight;
        }

        if (i >= total) {
            flush();
            return;
        }
        timerId = setTimeout(tick, speedMs);
    }
    tick();
}

// ── Send logic ────────────────────────────────────────────
const setWaiting = (waiting) => {
    sendBtn.disabled = waiting;
    userInput.disabled = waiting;
    stopBtn.disabled = !waiting;
};

const sendMessage = async () => {
    const message = userInput.value.trim();
    if (!message) return;

    appendUserMessage(message);
    userInput.value = '';
    setWaiting(true);
    showGenerating();

    currentAbortController = new AbortController();

    try {
        const response = await fetch('http://localhost:5000/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message }),
            signal: currentAbortController.signal,
        });
        const data = await response.json();
        removeGenerating();

        if (data.response) {
            typewriterAppend(data.response);
        } else {
            typewriterAppend(`⚠️ Error: ${data.error || 'Unknown error'}`);
        }
    } catch (err) {
        removeGenerating();
        if (err.name === 'AbortError') {
            typewriterAppend('⚠️ Request cancelled.');
        } else {
            typewriterAppend('⚠️ Could not connect to the backend. Is it running on port 5000?');
        }
    } finally {
        currentAbortController = null;
        setWaiting(false);
        userInput.focus();
    }
};

stopBtn.addEventListener('click', () => {
    if (currentAbortController) {
        currentAbortController.abort();
    }
});

sendBtn.addEventListener('click', sendMessage);
userInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendMessage();
});
