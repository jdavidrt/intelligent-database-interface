/* Captura de pantallazos del IDI en vivo para los informes HTML.
 *
 * Consolidado de lo que funcionó el 2026-07-15 generando IDI_Segundo_Informe.html
 * (ver docs/reports/GUIA_GENERACION_INFORMES_HTML.md §5 para el playbook y los gotchas).
 *
 * Uso:
 *   1. Levantar el stack a mano (llama-server :7860, uvicorn :5000 SIN --reload, vite :5173).
 *   2. En un directorio temporal: npm i playwright-core  (usa el Edge del sistema, no descarga nada)
 *   3. node capture_shots.js
 *
 * Los PNG se escriben en docs/reports/figures/.
 */
const { chromium } = require('playwright-core');
const path = require('path');

const OUT = path.resolve(__dirname, '..', 'figures');
const APP = 'http://localhost:5173';
const LLM_TIMEOUT = 240_000; // modelo local 3B: paciencia

const out = n => path.join(OUT, n);

// ── helpers ──────────────────────────────────────────────────────────────────

async function botCount(page) {
    return page.evaluate(
        () => document.querySelectorAll('.message.bot-message:not(.agent-progress)').length,
    );
}

/** Envía una pregunta y espera el turno completo; devuelve el texto del último bot-message. */
async function ask(page, q) {
    const n = await botCount(page);
    await page.fill('.chat-input', q);
    await page.press('.chat-input', 'Enter');
    await page.waitForFunction(
        m => document.querySelectorAll('.message.bot-message:not(.agent-progress)').length > m,
        n, { timeout: LLM_TIMEOUT },
    );
    await page.waitForSelector('.send-btn:not([disabled])', { timeout: LLM_TIMEOUT });
    await page.waitForTimeout(1200); // que asienten gráficos/typewriter
    return page.evaluate(() => {
        const els = document.querySelectorAll('.message.bot-message:not(.agent-progress)');
        return els[els.length - 1]?.innerText ?? '';
    });
}

/** Respuesta usable para el informe: tiene RESULTS, pasó verificación y sin JOIN espurio. */
const cleanAnswer = t =>
    t.includes('RESULTS') && !t.includes('Verification failed') && !/\bJOIN\b/i.test(t);

/** Entra al chat (pasando por el selector de BD si aparece). */
async function enterChat(page) {
    await page.goto(APP);
    try {
        await page.waitForSelector('text=Select the database', { timeout: 8000 });
        await page.waitForTimeout(2500); // gotcha #1: animación de entrada
        await page.click('button:has-text("soundwave")');
    } catch { /* ya estaba en el chat */ }
    await page.waitForSelector('.chat-input', { timeout: 60_000 });
}

/** Screenshot del último par pregunta+respuesta sin que la barra de input lo tape (gotcha #6). */
async function shootPair(page, file) {
    const user = page.locator('.message.user-message').last();
    const bot = page.locator('.message.bot-message:not(.agent-progress)').last();
    const bb = await bot.boundingBox();
    const need = Math.ceil(bb.height) + 500;
    if (need > 850) {
        await page.setViewportSize({ width: 1360, height: need });
        await page.waitForTimeout(500);
    }
    await bot.evaluate(el => el.scrollIntoView({ block: 'center' }));
    await page.waitForTimeout(400);
    const b1 = await user.boundingBox();
    const b2 = await bot.boundingBox();
    const input = await page.locator('.input-area').boundingBox();
    const top = Math.max(0, Math.min(b1.y, b2.y) - 10);
    let bottom = Math.max(b1.y + b1.height, b2.y + b2.height) + 10;
    if (input) bottom = Math.min(bottom, input.y - 6);
    const left = Math.max(0, Math.min(b1.x, b2.x) - 10);
    const right = Math.max(b1.x + b1.width, b2.x + b2.width) + 10;
    await page.screenshot({
        path: out(file),
        clip: { x: left, y: top, width: right - left, height: bottom - top },
    });
    await page.setViewportSize({ width: 1360, height: 850 });
    await page.waitForTimeout(300);
    console.log('OK', file);
}

/** Pregunta con reintentos hasta obtener una respuesta limpia, luego shootPair. */
async function askCleanAndShoot(page, q, file, attempts = 4, validate = cleanAnswer) {
    for (let i = 0; i < attempts; i++) {
        const txt = await ask(page, q);
        if (validate(txt)) { await shootPair(page, file); return true; }
        console.log(`retry ${file} (intento ${i + 1} no fue limpio)`);
    }
    console.log(`WARN ${file}: sin respuesta limpia en ${attempts} intentos`);
    return false;
}

/* Gotcha #3: el backend bufferiza el stream NDJSON de /query, así que la barra de
 * progreso jamás se pinta. Este init-script envuelve fetch y re-emite las líneas
 * REALES con pausas, reteniendo el resultado final para poder capturar el progreso. */
function replayStreamInitScript() {
    return () => {
        const orig = window.fetch.bind(window);
        window.fetch = async (input, init) => {
            const url = typeof input === 'string' ? input : input.url;
            if (!url.includes('/query')) return orig(input, init);
            const resp = await orig(input, init);
            const text = await resp.text();
            const lines = text.split('\n').filter(l => l.trim());
            const enc = new TextEncoder();
            const stream = new ReadableStream({
                async start(controller) {
                    for (let i = 0; i < lines.length; i++) {
                        controller.enqueue(enc.encode(lines[i] + '\n'));
                        const beforeResult = i === lines.length - 2;
                        await new Promise(r => setTimeout(r, beforeResult ? 12000 : 700));
                    }
                    controller.close();
                },
            });
            return new Response(stream, {
                status: resp.status,
                headers: { 'Content-Type': 'application/x-ndjson' },
            });
        };
    };
}

// ── main: las 9 tomas del Segundo Informe (adaptar para informes futuros) ─────

(async () => {
    const browser = await chromium.launch({ channel: 'msedge', headless: true });
    const ctx = await browser.newContext({
        viewport: { width: 1360, height: 850 },
        deviceScaleFactor: 2, // nítido en impresión
    });

    // Captura 2.1A — selector de BD (esperar la animación de entrada)
    const p1 = await ctx.newPage();
    await p1.goto(APP);
    await p1.waitForSelector('text=Select the database', { timeout: 30_000 });
    await p1.waitForTimeout(3500);
    await p1.screenshot({ path: out('shot_2_1a_selector.png') });

    // Captura 2.1B — chat con el drawer "Database Map" abierto
    await p1.click('button:has-text("soundwave")');
    await p1.waitForSelector('.chat-input', { timeout: 60_000 });
    await p1.click('button:has-text("DB Profile")');
    await p1.waitForSelector('h3:has-text("soundwave")', { timeout: 120_000 });
    await p1.waitForTimeout(500);
    await p1.screenshot({ path: out('shot_2_1b_chat_drawer.png') });

    // Captura 2.3 — esquema (dos <details> expandidos) + glosario
    const details = p1.locator('details');
    for (let i = 0; i < Math.min(2, await details.count()); i++) await details.nth(i).click();
    await p1.waitForTimeout(400);
    await p1.screenshot({ path: out('shot_2_3a_schema.png') });
    const glossary = p1.locator('h4:has-text("Glossary")').first();
    await glossary.scrollIntoViewIfNeeded();
    await p1.waitForTimeout(300);
    await p1.screenshot({ path: out('shot_2_3b_glossary.png') });
    // gotcha #2: cerrar el drawer con su ✕, no con la pestaña del header
    await p1.click('[aria-label="Close panel"]');

    // Captura 2.2 — respuesta de 4 paneles (reintentos hasta SQL limpio)
    await askCleanAndShoot(p1, 'Show me all artists from Colombia.', 'shot_2_2_four_panels.png');

    // Captura 2.4 — las tres rutas, en un chat fresco
    const p2 = await ctx.newPage();
    await enterChat(p2);
    await askCleanAndShoot(p2, 'How many artists are from Colombia?', 'shot_2_4a_route_data.png');
    await ask(p2, 'What tables does this database have?');
    await shootPair(p2, 'shot_2_4b_route_meta.png');
    await ask(p2, 'What is the weather today?'); // gotcha #5: esta sí redirige; "capital of France" no
    await shootPair(p2, 'shot_2_4c_route_offtopic.png');

    // Captura 2.5 — barra de progreso (re-emisión del stream real, gotcha #3)
    const ctx2 = await browser.newContext({
        viewport: { width: 1360, height: 850 },
        deviceScaleFactor: 2,
    });
    const p3 = await ctx2.newPage();
    await p3.addInitScript(replayStreamInitScript());
    await enterChat(p3);
    await p3.fill('.chat-input', 'What is the average track duration in minutes?');
    await p3.press('.chat-input', 'Enter');
    await p3.waitForSelector('.agent-step-adapter', { timeout: LLM_TIMEOUT });
    await p3.waitForFunction(
        () => document.querySelectorAll('.agent-step-adapter').length >= 3,
        null, { timeout: 60_000 },
    );
    await p3.waitForTimeout(600);
    await p3.locator('.agent-progress').screenshot({ path: out('shot_2_5_progress.png') });

    await browser.close();
    console.log('DONE — revisar visualmente cada PNG antes de incrustar (embed_shots.py)');
})().catch(e => { console.error('FATAL', e); process.exit(1); });
