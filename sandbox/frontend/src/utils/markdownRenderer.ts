import { highlightSQL } from './sqlHighlighter';

// Only these sections are shown to the user, in this order
const ALLOWED_SECTIONS: string[] = [
    'Business Interpretation',
    'SQL Query',
    'How to Interpret the Results',
];

// Strip <think>...</think> blocks that reasoning models may emit
const THINK_RE = /<think>[\s\S]*?<\/think>/gi;

interface Section {
    heading: string | null;
    content: string[];
}

/**
 * Split a markdown string into named sections at ### headings.
 */
function splitIntoSections(text: string): Section[] {
    const lines = text.split('\n');
    const sections: Section[] = [];
    let current: Section = { heading: null, content: [] };

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

function renderMdText(text: string): string {
    const lines = text.split('\n');
    let html = '';
    let inList = false;

    const closeList = () => {
        if (inList) { html += '</ul>'; inList = false; }
    };
    const inlinify = (s: string): string => s
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

        if (h3)      { closeList(); html += `<h3>${inlinify(h3[1])}</h3>`; }
        else if (h2) { closeList(); html += `<h2>${inlinify(h2[1])}</h2>`; }
        else if (h1) { closeList(); html += `<h1>${inlinify(h1[1])}</h1>`; }
        else if (hr) { closeList(); html += '<hr>'; }
        else if (bullet || numbered) {
            if (!inList) { html += '<ul>'; inList = true; }
            html += `<li>${inlinify((bullet ?? numbered)![1])}</li>`;
        } else if (trimmed === '') {
            closeList();
        } else {
            closeList();
            html += `<p>${inlinify(line)}</p>`;
        }
    }
    closeList();
    return html;
}

/**
 * Render a markdown string to an HTML string.
 * Fenced code blocks with lang=sql get syntax highlighted.
 */
function renderMarkdown(md: string): string {
    const parts: Array<{ type: 'md' | 'code'; lang: string; content: string }> = [];
    const codeRe = /```([a-z]*)\n?([\s\S]*?)```/g;
    let last = 0;
    let m: RegExpExecArray | null;

    while ((m = codeRe.exec(md)) !== null) {
        if (m.index > last) parts.push({ type: 'md', lang: '', content: md.slice(last, m.index) });
        parts.push({ type: 'code', lang: m[1].toLowerCase(), content: m[2] });
        last = m.index + m[0].length;
    }
    if (last < md.length) parts.push({ type: 'md', lang: '', content: md.slice(last) });

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

/**
 * Build the final HTML string for a bot response.
 * - Strips <think>...</think> blocks
 * - Shows only: Business Interpretation, SQL Query, How to Interpret the Results
 * - Renders markdown including SQL highlighting
 */
export function buildBotMessageHTML(rawText: string): string {
    // Strip any <think> reasoning blocks the model may have emitted
    const cleaned = rawText.replace(THINK_RE, '').trim();
    const sections = splitIntoSections(cleaned);

    let html = '';

    for (const sec of sections) {
        const heading = sec.heading;
        const body = sec.content.join('\n').trim();

        // No heading = preamble text before the first section; skip it
        if (!heading) continue;

        // Only render allowed sections
        const isAllowed = ALLOWED_SECTIONS.some(a => heading.includes(a));
        if (!isAllowed) continue;

        html += `<h3 class="section-heading">${heading}</h3>`;

        if (body) {
            let renderedBody = body;
            const isSQLSection = heading.toLowerCase().includes('sql query');
            if (isSQLSection && !body.includes('```')) {
                renderedBody = '```sql\n' + body.trim() + '\n```';
            }
            html += `<div class="section-body">${renderMarkdown(renderedBody)}</div>`;
        }
    }

    return html;
}

/**
 * Returns true if text contains an odd number of ``` fences —
 * meaning we are currently inside an unclosed code block.
 */
export function insideCodeFence(text: string): boolean {
    const matches = text.match(/```/g);
    return matches ? matches.length % 2 !== 0 : false;
}
