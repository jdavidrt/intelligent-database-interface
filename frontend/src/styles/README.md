# Styles

- `tokens.css` — shared design tokens (spacing, radii, font scale, z-index, chart series colors) plus the five `[data-theme]` palette blocks. Imported before `index.css` in `main.tsx`.
- Component-specific rules live in `*.module.css` next to each new component; legacy rules remain in `src/index.css` and migrate incrementally.

No Tailwind, no shadcn (locked decision, MASTERPLAN.md D1). The per-theme `--chart-1/2/3` series colors are CVD-validated (dataviz six-checks).
