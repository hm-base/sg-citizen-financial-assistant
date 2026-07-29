# Multi-Theme Design System

A data-first, multi-theme design system covering three product formats — Web/App UI, Presentation Decks, and Dashboards/Data Viz — built around 8 original color themes.

## Themes

| Theme | Mood | Shape family | Fonts |
|---|---|---|---|
| Cyber Neon | Dark, high-tech | `glow-dark` | Inter |
| Darcula | Dark, IDE classic | `terminal` (editor chrome, tab bar) | Barlow Condensed / Barlow / JetBrains Mono |
| Pastel Calm | Light, soft | `pill` | Figtree |
| Scandinavian Minimal | Light, monochrome | `flat` (no boxes, open editorial) | Inter |
| Warm Earth | Light, organic | `pill` | Figtree |
| Midnight Luxury | Dark, metallic | `glass` (translucent panels) | Inter |
| Ledger Navy *(new — financial/data)* | Dark, corporate-trust | `corporate` | Inter |
| Monochrome Signal *(new — dense analytical)* | Light, grayscale + 2 signal colors | `dense` | Inter |

Each theme is a token file under `tokens/`, scoped to `[data-theme="<name>"]` (not `:root`) so all 8 can coexist in the same compiled bundle. Activate one by setting `data-theme` on a wrapping element.

## Architecture — why components aren't 1:1 with themes

Only *color* is swappable via CSS variables; *shape* (radius, button geometry, decorative motifs like blueprint corners, glass panels, or editor chrome) differs meaningfully between themes and can't be faked with variables alone. So:

- **Colors** always come from the active theme's token file (`var(--color-accent)`, `var(--color-series-1)`, etc.)
- **Shape** is an explicit `shape` prop on core components (`glow-dark | terminal | pill | flat | glass | corporate | dense`) matching the active theme's `--shape` token
- **Bespoke motifs** that no shape-prop can express live in their own components: `components/terminal/` (Darcula's window chrome + tab bar) and `components/glass/` (Midnight Luxury's glass panel)

This means core components (Button, Tag, Card, KpiCard, DataTable, FilterBar) are written **once** and reused across all 8 themes — only Darcula and Midnight Luxury need extra theme-specific pieces.

## Functional color rules (all themes)

- **Series 1–5** always rotate in fixed order (`--color-series-1` → `--color-series-5`) — never reassign which series gets which position.
- **Status colors** (success/warning/alert) are reserved strictly for thresholds, conditional formatting, and trend flags — never decorative.
- **Positive/negative deltas** are never color-only — always paired with a ▲/▼ glyph (see `KpiCard`), so they read correctly under Deuteranopia/Protanopia.
- **Monochrome Signal** takes this furthest: its 5-series ramp is pure grayscale (lightness-only, colorblind-proof by construction) and only 2 chromatic accents exist in the whole theme, reserved for highlight and alert.
- Gridlines/dividers: `color-mix(in srgb, var(--color-text) 12-15%, transparent)`.

## Components

- `components/core/` — Button, Tag, StatusBadge, Card (shape-driven, all 8 themes)
- `components/data/` — KpiCard (sparkline + delta), DataTable (paginated), FilterBar, ChartSeries (colorblind-safe multi-series bar chart, fixed Series 1→5 order)
- `components/terminal/` — WindowChrome, TabBar (Darcula only)
- `components/glass/` — GlassPanel (Midnight Luxury only; use sparingly — translucent panels are expensive to render in bulk)

## Templates (starting folders for consuming projects)

Each is a Design Component under `templates/<slug>/`, with a `theme` tweak switching all 8 themes live:

- `templates/app-shell/AppShell.dc.html` — sidebar nav + top bar + members table + settings panel (default `ledger-navy`).
- `templates/dashboard/Dashboard.dc.html` — KPI row, Series 1·2·3 bar chart, status strip, data table (default `cyber-neon`).
- `templates/deck/Deck.dc.html` — five slide layouts at 1280×720 on `<deck-stage>`: Title, Executive Summary Grid, Big Stat Callout, Insight vs. Data, Chart + Commentary (default `ledger-navy`). Prints straight to PDF.

Each folder carries `ds-base.js`, which links `styles.css` and `_ds_bundle.js` — in a consuming project, point its `base` line at the bound `_ds/<folder>` tree.

## Presentation deck layouts

Title · Executive Summary Grid · Big Stat Callout · Insight vs. Data split · Chart + Commentary · Bridge/Waterfall. The first five are built in `templates/deck/`; Bridge/Waterfall is not — compose it from `ChartSeries` and `Card` per theme's tokens.

## UI kits

- `ui_kits/dashboard/` — `Dashboard.jsx` + static `index.html` preview (cyber-neon). Analytics dashboard: KPI row, chart, status strip, table.
- `ui_kits/deck/` — `Slides.jsx` + static `index.html`. Executive Summary, Big Stat, Insight vs. Data slide layouts at 960×540.
- `ui_kits/app/` — `AppShell.jsx` (`LoginScreen`, `AppShell`, `SettingsPanel`) + static `index.html` preview (ledger-navy). The Web/App UI surface.

Each kit's `index.html` is a hand-kept static mirror of its JSX — the CDN React + Babel route hangs the preview sandbox, so the markup is duplicated deliberately. Keep both sides in sync when editing.

## Foundation cards

`guidelines/*.html` — 21 specimen cards feeding the Design System tab, grouped **Colors** (accents, primary + states, surfaces, status, status fills, Series 1–5, input states, disabled, text-on-background), **Type** (scale per theme, families, weights/line-height/tracking, mono in use), **Spacing** (8px scale, 4px dense scale, padding + grid gap in use), **Shape** (radii per theme, shape families, elevation light, elevation dark, focus ring), **Brand** (theme index, theme activation). Every card renders all 8 themes side by side where the token differs per theme.

## Files

- `styles.css` — import list (base + all 8 token files). Link this one file from any consuming page.
- `base.css` — resets + shared @font-face imports.
- `tokens/*.css` — one file per theme.
- `components/` — see above; every component has a `.d.ts` contract and a `.prompt.md` usage guide.
- `templates/` — three DC templates (see above).
- `guidelines/` — foundation specimen cards.
- `thumbnail.html` — the project tile.
- `Visual Context.dc.html` — per-theme slide / mobile / dashboard pattern reference. `Style Guide.dc.html` — print reference document.
- `assets/reference/` — the two supplied Cyber Neon cross-format reference images.

## Sources

Original theme markdown, Adobe Color palette references, and a Cyber Neon cross-format reference image were supplied by the user. The 4 previously-attached systems (Industry, Organic, Broadsheet, Nocturne) were used only as **structural** inspiration for shape families — no colors or branding were reused from them.

## Content fundamentals

Copy is **operator voice** — the tone of someone reporting numbers to people who already know the domain.

- **Declarative, past or present tense, verb-first.** "Revenue held. The mix moved." · "Aging concentrated in two accounts." Never a question as a headline, never "Let's dive in".
- **Second person only for actions the reader takes** ("Use your workspace account"), no first person plural anywhere. No "we're excited", no "journey", no "unlock".
- **Sentence case everywhere** except the uppercase kicker/eyebrow (`--tracking-caption: .12em`) and table column headers, which are uppercase at 10px. Never Title Case A Whole Headline.
- **Numbers carry a unit and a comparison.** "$4.82M" alone is incomplete; "▲ 12.4% vs prior period" is the pattern. Deltas always lead with ▲/▼ so they survive colourblindness and greyscale printing.
- **Status labels state the condition, not the severity.** "Above threshold", "62 days overdue", "2 accounts near credit cap" — not "Warning" or "Attention needed".
- **Recommendations are hedged and specific**: "Recommend shifting Q4 quota weighting toward services attach." Named systems, named quarters, named accounts (fictional: Northwind, Contoso, Fabrikam, Tailspin, Proseware, Wingtip).
- **No emoji.** The only non-alphanumeric glyphs are ▲ ▼ · — and the status dot. `·` separates metadata ("Q3 · FY26"), `—` sets off an aside.
- Empty states and helper text stay flat and factual: "Sent Mondays, 07:00 UTC." Length ceiling for helper text is one short sentence.

## Visual foundations

**Colour.** Every value comes from a theme token; nothing is hand-mixed. Each theme carries brand (primary + hover/active/soft/on-primary, secondary, accent 1–3), surfaces (bg → surface → card → border), text (text/muted/inverse), four semantics with 16%-alpha tinted backgrounds, a fixed 5-colour series ramp, plus input, disabled and focus tokens. Dividers and gridlines are never a border token — always `color-mix(in srgb, var(--color-text) 8–15%, transparent)`, so they follow the theme's own contrast. Five dark themes (Cyber Neon, Darcula, Midnight Luxury, Ledger Navy) and four light (Pastel Calm, Scandinavian Minimal, Warm Earth, Monochrome Signal) — a surface is never a gradient.

**Type.** Five families, all Google-hosted: Inter (5 themes), Figtree (Pastel Calm, Warm Earth), Barlow Condensed + Barlow (Darcula), JetBrains Mono (all themes). Scale is per theme — H1 ranges 32px (Monochrome Signal, dense) to 42px (Cyber Neon, Warm Earth); body 14–16px; caption 11–12px. `--lh-heading: 1.12`, `--lh-body: 1.6` in every theme. **Every figure, delta, timestamp and token reference is set in mono** — that is the single strongest cross-theme signature. Headings are 600 or 700 depending on theme; there is no light or thin weight anywhere.

**Spacing.** Two base units: 8px (six themes) and 4px (Darcula, Monochrome Signal). Card padding 16–24px, section padding 32–48px, grid gap 12–20px — all tokenised as `--pad-card`, `--pad-section`, `--gap-grid`, so a "dense" layout is a theme swap, not a rewrite.

**Shape.** Radius is the theme's identity, and mixing families is the one hard error: glow-dark 6/8/16px · terminal 3/4/6px · pill 10/16/24px (buttons fully round at 999px) · flat 2/4/6px (buttons square, cards borderless and open) · glass 10/16/20px (buttons round) · corporate 4/6/10px · dense 1/2/3px. Components take an explicit `shape` prop rather than reading radius blindly, because button geometry and card borders differ structurally, not just numerically.

**Elevation and depth.** Three shadow steps per theme. Light themes use low-opacity black at increasing blur; dark themes go further and add a 1px accent-tinted ring at `--elev-3` (e.g. `0 0 0 1px rgba(6,182,212,0.18)` on Cyber Neon) — the "glow" in glow-dark is that ring, not a filter. Scandinavian Minimal barely elevates at all: hairline rules do the work.

**Transparency and blur.** Reserved. `backdrop-filter` appears in exactly one place — `GlassPanel`, Midnight Luxury only, one or two per view. Everywhere else, translucency is limited to `-soft` fills and `color-mix` dividers. No frosted headers, no scrim gradients.

**Backgrounds and imagery.** Flat token colour, full stop — no photography, no illustration, no repeating pattern, no gradient field, and no supplied brand imagery to draw on (see Iconography). Where a deck wants visual interest, it comes from the 5-colour series ramp used as a structural element (the flush colour bar on the title slide) or from the chart itself.

**States.** Hover shifts to `--color-primary-hover` (a lighter tint on dark themes, darker on light); press uses `--color-primary-active` — colour only, never a transform or scale. Focus is `--focus-ring` (3px accent at 45% alpha) paired with `--input-border-focus`, and is never removed. Disabled is `--color-disabled-bg` + `--color-disabled-text`, no opacity trick. Active nav is a `--color-primary-soft` fill with accent text — never a filled primary button.

**Animation.** Effectively none. Data surfaces don't move: no entrance animations, no number roll-ups, no chart draw-on. Only interactive state changes transition, and only colour, ~120–160ms ease-out. No bounce, no spring, no parallax.

**Cards.** `--color-card` fill, 1px `color-mix` hairline at 10%, radius from the family, `--pad-card` inside. No shadow at rest on light themes; shadow is for genuinely floating things (dialogs, menus). Scandinavian Minimal's `flat` card has no fill and no border — only a top hairline — and that is intentional, not an oversight.

## Iconography

**The supplied sources contain no icon set, no icon font, no SVG sprite, and no logo** — so this system does not ship one, and nothing was drawn to fill the gap.

- Wherever a brand mark would go, a plain accent-coloured square (radius from the shape family) sits next to the product name in type. Replace it with a real mark when one exists.
- The only glyphs used are typographic: **▲ ▼** for deltas (always paired with the number, never colour-only), **·** as a metadata separator, **—** for a null value or aside, and a 6px filled circle as the status dot.
- Status is communicated by dot + colour + text, three redundant channels, so no icon is required to read it.
- **No emoji, ever** — not in UI, not in decks, not in copy.
- If a consuming project needs a real icon set, use **Lucide** from CDN at 1.5px stroke and 16/20/24px sizes: it is the closest match to this system's hairline-and-mono register. Flag it as a substitution, since it is not part of the supplied sources.

## Caveats / next steps

- **No logo, no icon set, no imagery** was supplied — see Iconography. The two Cyber Neon reference images sit in `assets/reference/` for context only; they are not brand assets.
- **Fonts load from Google Fonts** via `base.css` (`@import url(...)`), not from bundled `.woff2` files — so the compiler reports zero `@font-face` rules and consumers need network access. Send the real font binaries if you want them self-hosted.
- UI kit `index.html` files are static mirrors of their JSX, kept in sync by hand.
- Bridge/Waterfall is the one recommended deck layout not yet built.
- Legacy `@startingPoint` tags were removed — `templates/` replaces them.

## Index

| Path | What it is |
|---|---|
| `styles.css` | The one file consumers link. `@import` list only. |
| `base.css` | Resets + Google Fonts imports. |
| `tokens/<slug>.css` | One file per theme, scoped to `[data-theme="<slug>"]`. |
| `components/core/` | Button · Card · StatusBadge · Tag |
| `components/data/` | KpiCard · DataTable · FilterBar · ChartSeries |
| `components/terminal/` | WindowChrome · TabBar (Darcula) |
| `components/glass/` | GlassPanel (Midnight Luxury) |
| `templates/app-shell/` · `dashboard/` · `deck/` | Copy-to-start DC templates |
| `ui_kits/app/` · `dashboard/` · `deck/` | Screen recreations per product format |
| `guidelines/*.html` | 21 foundation specimen cards |
| `themes/<slug>.dscard.html` | Per-theme preview card |
| `Visual Context.dc.html` | Per-theme pattern reference |
| `Style Guide.dc.html` | Print reference document |
| `thumbnail.html` | Project tile |
| `SKILL.md` | Agent Skills entry point |

## To make this attachable to future projects

Use the Share menu → set File Type to **Design System**.
