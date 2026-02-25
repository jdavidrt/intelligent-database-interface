/**
 * SQL syntax highlighter — ported from sandbox/frontend/app.js.
 * Returns an HTML string with <span> tokens for SQL syntax.
 */
export function highlightSQL(code: string): string {
    // 1. HTML-escape the raw SQL
    let escaped = code
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');

    // 2. Apply passes in priority order, protecting prior spans each time.
    //    Each pass: split on existing <span…>…</span>, apply only to gaps.
    const applyToRaw = (html: string, re: RegExp, replacement: string | ((m: string) => string)): string => {
        const result: string[] = [];
        const spanRe = /(<span[^>]*>(?:[^<]|<(?!\/span>))*<\/span>)/g;
        let cursor = 0;
        let sm: RegExpExecArray | null;
        while ((sm = spanRe.exec(html)) !== null) {
            if (sm.index > cursor) {
                const raw = html.slice(cursor, sm.index);
                result.push(typeof replacement === 'function'
                    ? raw.replace(re, replacement)
                    : raw.replace(re, replacement));
            }
            result.push(sm[1]);
            cursor = sm.index + sm[0].length;
        }
        if (cursor < html.length) {
            const raw = html.slice(cursor);
            result.push(typeof replacement === 'function'
                ? raw.replace(re, replacement)
                : raw.replace(re, replacement));
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
        (m: string) => `<span class="sql-kw">${m}</span>`);

    // Operators
    escaped = applyToRaw(escaped,
        /([=<>!]{1,2}|[+\-*/%]|\|\|)/g,
        '<span class="sql-op">$1</span>');

    return escaped;
}
