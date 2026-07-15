"""Incrusta capturas de pantalla en un informe HTML del proyecto IDI.

Reemplaza cada placeholder <div class="shot">...</div> (en orden de aparición)
por un <figure class="fig"> con las imágenes en base64 y su leyenda "Captura N.M".
Usado por primera vez el 2026-07-15 para IDI_Segundo_Informe.html; la configuración
de ese informe queda abajo como ejemplo. Ver GUIA_GENERACION_INFORMES_HTML.md §5.4.

Reglas que este script hace cumplir:
- Aborta sin escribir si no encuentra EXACTAMENTE len(CAPTURAS) placeholders.
- Conserva CRLF y UTF-8 del archivo (newline="").
- Assert final: no queda ningún class="shot".
"""
import base64
import re
from pathlib import Path

REPORTS = Path(__file__).resolve().parent.parent
REPORT = REPORTS / "IDI_Segundo_Informe.html"
FIGS = REPORTS / "figures"

# Una entrada por placeholder, en orden de aparición en el documento.
# "imgs" admite varias imágenes apiladas dentro de la misma figure.
CAPTURAS = [
    {
        "num": "2.1",
        "imgs": [
            ("shot_2_1a_selector.png", "Pantalla de selección de base de datos (DatabaseSelector)"),
            ("shot_2_1b_chat_drawer.png", "Vista general del chat con el drawer 'Database Map' (DB Info) abierto"),
        ],
        "caption": ("Captura 2.1 — Pantalla de selección de base de datos (DatabaseSelector, arriba) y "
                    "vista general del chat con el drawer &quot;DB Info&quot; (Database Map) abierto (abajo). "
                    "Fuente: sistema IDI en ejecución local."),
    },
    {
        "num": "2.2",
        "imgs": [("shot_2_2_four_panels.png", "Respuesta didáctica de cuatro paneles en el chat")],
        "caption": ("Captura 2.2 — Respuesta completa de cuatro paneles en el chat: "
                    "&quot;What I understood / The SQL / Why this query / Results&quot; "
                    "(qué entendí, el SQL generado, por qué esta consulta con la verificación tripartita, "
                    "y el resultado). Fuente: sistema IDI en ejecución local."),
    },
    {
        "num": "2.3",
        "imgs": [
            ("shot_2_3a_schema.png", "Drawer Database Map con tablas del esquema SoundWave expandidas"),
            ("shot_2_3b_glossary.png", "Drawer Database Map mostrando el glosario de términos del dominio"),
        ],
        "caption": ("Captura 2.3 — Drawer &quot;DB Info&quot; (Database Map) con el esquema de SoundWave: "
                    "tablas expandidas con columnas, tipos y claves (arriba) y glosario de términos crípticos "
                    "del dominio con su significado (abajo). Fuente: sistema IDI en ejecución local."),
    },
    {
        "num": "2.4",
        "imgs": [
            ("shot_2_4a_route_data.png", "Ruta 1: consulta de datos respondida con SQL"),
            ("shot_2_4b_route_meta.png", "Ruta 2: pregunta sobre la base seleccionada respondida desde el perfil"),
            ("shot_2_4c_route_offtopic.png", "Ruta 3: pregunta fuera del propósito de IDI redirigida cortésmente"),
        ],
        "caption": ("Captura 2.4 — Ejemplo real de las tres rutas de enrutamiento en el chat: una consulta de "
                    "datos respondida con SQL verificado (arriba), una pregunta sobre la base seleccionada "
                    "respondida directamente desde el perfil (centro) y una pregunta fuera del propósito de IDI "
                    "redirigida cortésmente (abajo). Fuente: sistema IDI en ejecución local."),
    },
    {
        "num": "2.5",
        "imgs": [("shot_2_5_progress.png", "Barra de progreso del pipeline con etiquetas de perfil activo por agente")],
        "caption": ("Captura 2.5 — Barra de progreso del pipeline durante una consulta en curso: cada agente "
                    "muestra su estado y la etiqueta del perfil de instrucción activo (&quot;profile: …&quot;) "
                    "aplicado por el registro de adaptadores. Fuente: sistema IDI en ejecución local."),
    },
]

SHOT_RE = re.compile(r'<div class="shot">.*?</div>')


def data_uri(png: Path) -> str:
    return "data:image/png;base64," + base64.b64encode(png.read_bytes()).decode("ascii")


def figure_html(cap: dict) -> str:
    imgs = []
    for fname, alt in cap["imgs"]:
        p = FIGS / fname
        if not p.is_file():
            raise SystemExit(f"MISSING IMAGE: {p}")
        imgs.append(
            f'<img src="{data_uri(p)}" alt="{alt}" '
            f'style="max-width:100%;height:auto;display:block;margin:0 auto 6pt auto;'
            f'border:0.5pt solid #c9ccd4;border-radius:3pt;">'
        )
    return '<figure class="fig">' + "".join(imgs) + f'<figcaption>{cap["caption"]}</figcaption></figure>'


def main() -> None:
    html = REPORT.read_text(encoding="utf-8", newline="")  # conservar CRLF
    found = SHOT_RE.findall(html)
    print(f"placeholders encontrados: {len(found)}")
    if len(found) != len(CAPTURAS):
        raise SystemExit(f"se esperaban {len(CAPTURAS)} placeholders — no se escribió nada")

    it = iter(CAPTURAS)
    html = SHOT_RE.sub(lambda m: figure_html(next(it)), html)

    assert 'class="shot"' not in html, "sobrevivió un placeholder"
    REPORT.write_text(html, encoding="utf-8", newline="")
    print(f"escrito: {REPORT} ({REPORT.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
