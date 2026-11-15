# SEO & GEO Analyzer – Agency USP Tool

**Project Specification & Cursor Instructions**

**Version:** 1.2  
**Date:** 15 November 2026  
**Purpose:** Complete guide for developing a mature SEO and GEO analysis tool as an agency unique selling proposition.

**Changelog:** 1.1 — Full English translation; added Section 3 “Design System & UI Guidelines,” integrating the Sannetic design system.  
**Changelog:** 1.2 — Brand tokens updated to the logo-aligned palette (SanneticDesign commit `929dbad`).

---

## 1. Project Goal & Vision

Development of a **comprehensive, mature analysis tool** for websites that combines classic **SEO audits** and **GEO (Generative Engine Optimization)** in a single system.

The tool is intended to serve as the **agency’s USP**:

- Differentiates itself from standard tools (Screaming Frog, Ahrefs, Semrush, Sitebulb)
- Delivers **prioritized, actionable recommendations** instead of raw data dumps
- Supports **multi-client workspaces** and **white-label reports**
- Enables professional, client-ready reports
- Focus on **AI search engine readiness** (ChatGPT, Perplexity, Google AI Overviews, Gemini, Claude, etc.) in addition to classic SEO

**Target audience:** Internal agency use + client reporting.

---

## 2. Tech Stack

| Layer                  | Technology                                   | Rationale |
|------------------------|----------------------------------------------|----------|
| Language               | Python 3.11+                                 | Best SEO libraries, pandas, LLM integration |
| Backend / API          | **FastAPI**                                  | Async, fast, automatic OpenAPI docs |
| Background jobs        | **Celery** or Dramatiq + **Redis**           | Long crawls, recurring audits |
| Crawler                | Custom system based on Scrapy or advertools + optional **Playwright** | Full control, SEO extraction, JS rendering |
| Database               | **PostgreSQL**                               | Multi-client, history, complex queries |
| Cache / Queue          | **Redis**                                    | Sessions, job queue |
| Object storage         | S3-compatible (MinIO locally / cloud)        | Raw HTML, screenshots, reports |
| Frontend               | **Next.js** + Tailwind CSS + shadcn/ui       | Modern, professional dashboard |
| Reports                | Jinja2 HTML templates + WeasyPrint or Playwright PDF | White-label PDFs & interactive reports |
| AI layer (optional)    | OpenAI / Anthropic / Groq                    | Citability scoring, executive summaries, recommendations |
| Integrations           | Google Search Console API, PageSpeed Insights API / CrUX | Real performance data |

**Development principles:**
- Modular architecture (Crawler → Extractor → Analyzer → Scorer → Reporter)
- Deterministic checks wherever possible (no pure LLM black boxes for scoring)
- Politeness: respect robots.txt, rate limiting, a sensible user agent
- Extensibility for later features

---

## 3. Design System & UI Guidelines

All product UI (dashboard, interactive reports, and the default white-label PDF theme) must follow the **Sannetic design system**. Do not introduce a parallel palette, type scale, or spacing system.

### 3.1 Source of truth

The canonical source is the [SanneticDesign](https://github.com/vASanne/SanneticDesign) repository:

| Asset | Path |
|-------|------|
| Web tokens & component CSS | `SanneticDesign/sannetic-styleguide.css` |
| Human-readable styleguide (companion PDF) | `SanneticDesign/Sannetic-Styleguide.pdf` |
| Logo, symbol, favicon, animated mark | `SanneticDesign/logo/` |
| Logo identity notes | `SanneticDesign/logo/README.md` |

**CSS wins.** If the PDF’s ranges or examples disagree with `sannetic-styleguide.css`, implement the CSS custom properties and component rules. The values in this section are taken from that stylesheet only.

**Integration with Next.js + Tailwind CSS + shadcn/ui:**

1. Import `sannetic-styleguide.css` into the global stylesheet (for example `app/globals.css`), *or* re-declare the same custom properties and map them 1:1 — do not retokenize by eye.
2. Extend the Tailwind theme with those custom properties (`colors`, `fontFamily`, `fontSize`, `fontWeight`, `lineHeight`, `spacing`, `borderRadius`, `boxShadow`, `transitionDuration` / `transitionTimingFunction`, `maxWidth`).
3. Map Sannetic tokens onto shadcn/ui CSS variables in `:root` and `.dark` (shadcn’s dark class is already supported; the styleguide also uses `[data-theme="dark"]`).

Recommended shadcn/ui mapping (Sannetic name → shadcn variable):

| Sannetic token | shadcn/ui variable | Notes |
|----------------|--------------------|-------|
| `--color-bg` | `--background` | Light default `#ffffff`; dark `#0f172a` |
| `--color-text` | `--foreground` | Light `var(--color-gray-900)` / `#0f172a`; dark `#f1f5f9` |
| `--color-surface` | `--card`, `--popover` | Light `#ffffff`; dark `#1e293b` |
| `--color-text` | `--card-foreground`, `--popover-foreground` | |
| `--color-primary` (`#1CC4A0`) | `--primary` | |
| `--color-white` (`#ffffff`) | `--primary-foreground` | Matches `.btn-primary` text (`white`) |
| `--color-bg-secondary` | `--secondary`, `--muted` | Light `var(--color-gray-50)` / `#f8fafc`; dark `#1e293b` |
| `--color-text` | `--secondary-foreground` | |
| `--color-text-secondary` | `--muted-foreground` | Light `#64748b`; dark `#94a3b8` |
| `--color-error` (`#ef4444`) | `--destructive` | |
| `--color-white` | `--destructive-foreground` | |
| `--color-border` | `--border`, `--input` | Light `#e2e8f0`; dark `#334155` |
| `--color-accent` (`#08C2D4`) | `--ring` | Focus color in the styleguide |
| `--radius-md` (`0.5rem`) or `--radius-lg` (`0.75rem`) | `--radius` | Buttons use `--radius-lg`; inputs use `--radius-md`; cards use `--radius-xl` (`1rem`) |

**Naming collision:** Sannetic `--color-accent` is brand cyan (`#08C2D4`). shadcn’s `--accent` is typically a subtle hover surface, not a brand color. Do **not** map `--color-accent` onto shadcn `--accent`. Expose cyan as a dedicated token (for example `--sannetic-accent` / Tailwind `accent`) and, if a muted hover surface is needed, use `--color-bg-secondary` or `--color-surface-elevated`.

Light mode is the typography/base default in `:root`. Dark mode is activated with `[data-theme="dark"]` or `.dark`.

### 3.2 Color tokens

**Brand (from logo, as defined in the CSS):**

| Token | Value | CSS comment / role |
|-------|-------|--------------------|
| `--color-primary` | `#1CC4A0` | Teal (logo gradient mid) |
| `--color-primary-hover` | `#17A183` | Primary hover (`.btn-primary:hover`) |
| `--color-primary-light` | `#40E4C0` | Lighter primary |
| `--color-accent` | `#08C2D4` | Cyan (logo gradient end); links, focus |
| `--color-accent-hover` | `#079FAE` | Link / accent hover |
| `--color-accent-light` | `#27E5F7` | Lighter cyan |
| `--color-gradient` | `linear-gradient(135deg, #8FD11B 0%, #1CC4A0 50%, #08C2D4 100%)` | Brand gradient (`.btn-gradient`, `.text-gradient`) |

**Neutrals:**

| Token | Value |
|-------|-------|
| `--color-white` | `#ffffff` |
| `--color-black` | `#0f172a` |
| `--color-gray-50` | `#f8fafc` |
| `--color-gray-100` | `#f1f5f9` |
| `--color-gray-200` | `#e2e8f0` |
| `--color-gray-300` | `#cbd5e1` |
| `--color-gray-400` | `#94a3b8` |
| `--color-gray-500` | `#64748b` |
| `--color-gray-600` | `#475569` |
| `--color-gray-700` | `#334155` |
| `--color-gray-800` | `#1e293b` |
| `--color-gray-900` | `#0f172a` |

`--color-black` and `--color-gray-900` share the same value (`#0f172a`).

**Semantic:**

| Token | Value |
|-------|-------|
| `--color-success` | `#10b981` |
| `--color-warning` | `#f59e0b` |
| `--color-error` | `#ef4444` |
| `--color-info` | `#06b6d4` |

`--color-success` equals `--color-primary`. `--color-info` equals `--color-accent`.

**Theme surfaces (light default → dark override):**

| Token | Light (`:root`) | Dark (`[data-theme="dark"]`, `.dark`) |
|-------|-----------------|----------------------------------------|
| `--color-bg` | `var(--color-white)` (`#ffffff`) | `#0f172a` |
| `--color-bg-secondary` | `var(--color-gray-50)` (`#f8fafc`) | `#1e293b` |
| `--color-surface` | `var(--color-white)` (`#ffffff`) | `#1e293b` |
| `--color-surface-elevated` | `var(--color-gray-50)` (`#f8fafc`) | `#334155` |
| `--color-text` | `var(--color-gray-900)` (`#0f172a`) | `#f1f5f9` |
| `--color-text-secondary` | `var(--color-gray-500)` (`#64748b`) | `#94a3b8` |
| `--color-text-muted` | `var(--color-gray-400)` (`#94a3b8`) | `#64748b` |
| `--color-border` | `var(--color-gray-200)` (`#e2e8f0`) | `#334155` |
| `--color-border-strong` | `var(--color-gray-300)` (`#cbd5e1`) | `#475569` |

Brand and semantic colors do not change between themes. The optional `.theme-toggle` control uses `--color-surface`, a `1px` `--color-border`, `--radius-full`, `--space-2` padding, and `--color-text`.

### 3.3 Typography

| Token | Value |
|-------|-------|
| `--font-family` | `"Inter", system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif` |
| `--font-family-mono` | `"JetBrains Mono", "Fira Code", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace` |

Load **Inter** and **JetBrains Mono** in the Next.js app (for example via `next/font/google`) so the declared families actually render. The stylesheet does not include `@font-face` or `@import` rules.

**Sizes** (`html` root font size is `16px`):

| Token | Value | px at 16px root |
|-------|-------|-----------------|
| `--font-size-xs` | `0.75rem` | 12px |
| `--font-size-sm` | `0.875rem` | 14px |
| `--font-size-base` | `1rem` | 16px |
| `--font-size-lg` | `1.125rem` | 18px |
| `--font-size-xl` | `1.25rem` | 20px |
| `--font-size-2xl` | `1.5rem` | 24px |
| `--font-size-3xl` | `1.875rem` | 30px |
| `--font-size-4xl` | `2.25rem` | 36px |
| `--font-size-5xl` | `3rem` | 48px |

**Weights:** `--font-weight-normal: 400`; `--font-weight-medium: 500`; `--font-weight-semibold: 600`; `--font-weight-bold: 700`.

**Line heights:** `--line-height-tight: 1.2`; `--line-height-normal: 1.5`; `--line-height-relaxed: 1.6`.

Body text uses `--font-size-base` and `--line-height-relaxed`. Headings use `--font-weight-bold` by default, `--line-height-tight`, and a bottom margin of `--space-4`:

| Element | Size token | Weight |
|---------|------------|--------|
| `h1` | `--font-size-5xl` (36px / `--font-size-4xl` below 768px) | `--font-weight-bold` (700) |
| `h2` | `--font-size-4xl` (30px / `--font-size-3xl` below 768px) | `--font-weight-semibold` (600) |
| `h3` | `--font-size-3xl` | `--font-weight-semibold` (600) |
| `h4` | `--font-size-2xl` | `--font-weight-semibold` (600) |
| `h5` | `--font-size-xl` | `--font-weight-medium` (500) |
| `h6` | `--font-size-lg` | `--font-weight-medium` (500) |

Links use `--color-accent`, no underline by default, and `--color-accent-hover` plus underline on hover (`--transition-fast`). Small / `.text-sm` text uses `--font-size-sm` and `--color-text-secondary`. `.text-muted` uses `--color-text-muted`. `.text-gradient` applies `--color-gradient` as clipped text. `code` / `.code` uses `--font-family-mono`, `0.9em`, `--color-bg-secondary` background, `--color-accent` text, `--radius-sm`, and padding `0.15em 0.4em`.

### 3.4 Spacing, radius, shadows, motion, and layout

Spacing is an **8px base** scale:

| Token | Value | px |
|-------|-------|----|
| `--space-1` | `0.25rem` | 4px |
| `--space-2` | `0.5rem` | 8px |
| `--space-3` | `0.75rem` | 12px |
| `--space-4` | `1rem` | 16px |
| `--space-5` | `1.25rem` | 20px |
| `--space-6` | `1.5rem` | 24px |
| `--space-8` | `2rem` | 32px |
| `--space-10` | `2.5rem` | 40px |
| `--space-12` | `3rem` | 48px |
| `--space-16` | `4rem` | 64px |
| `--space-20` | `5rem` | 80px |
| `--space-24` | `6rem` | 96px |

**Radius:** `--radius-sm: 0.375rem` (6px); `--radius-md: 0.5rem` (8px); `--radius-lg: 0.75rem` (12px); `--radius-xl: 1rem` (16px); `--radius-2xl: 1.5rem` (24px); `--radius-full: 9999px`.

**Shadows:**

| Token | Light | Dark |
|-------|-------|------|
| `--color-shadow` | `0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)` | `0 4px 6px -1px rgb(0 0 0 / 0.4), 0 2px 4px -2px rgb(0 0 0 / 0.3)` |
| `--color-shadow-lg` | `0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)` | `0 10px 15px -3px rgb(0 0 0 / 0.5), 0 4px 6px -4px rgb(0 0 0 / 0.4)` |

**Motion:** `--transition-fast: 150ms ease`; `--transition-base: 200ms ease`; `--transition-slow: 300ms ease`.

**Layout:** `--container-max: 1280px`; `--container-padding: var(--space-6)` (24px). `.container` is width 100%, centered, with that max width and inline padding. `.section` uses `padding-block: var(--space-16)`; `.section-sm` uses `var(--space-12)`. `.grid` uses `gap: var(--space-6)`; `.grid-2` / `.grid-3` / `.grid-4` are equal columns and collapse to one column at `max-width: 768px`. Utility classes include `.flex`, `.flex-center`, `.flex-between`, `.gap-2`, `.gap-4`, `.gap-6`, and margin helpers `.mt-4`, `.mt-8`, `.mb-4`, `.mb-8`.

### 3.5 Component guidance

Use the styleguide component patterns when building shadcn/ui or custom components. Do not restyle them with hard-coded values.

**Buttons** (`.btn`): inline-flex, centered, `gap: var(--space-2)`, padding `var(--space-3) var(--space-6)`, inherited font family, `--font-size-base`, `--font-weight-semibold`, `line-height: 1`, no border, `--radius-lg`, `transition: all var(--transition-base)`.

| Variant | Style |
|---------|-------|
| `.btn-primary` | Background `--color-primary`, text `white`; hover `--color-primary-hover`, `translateY(-1px)`, `--color-shadow` |
| `.btn-accent` | Background `--color-accent`, text `white`; hover `--color-accent-hover` |
| `.btn-gradient` | Background `--color-gradient`, text `white`; hover `filter: brightness(1.1)` and `translateY(-1px)` |
| `.btn-outline` | Transparent, text and `2px` border `--color-primary`; hover fills `--color-primary` with text `white` |
| `.btn-ghost` | Transparent, text `--color-text`; hover background `--color-bg-secondary` |
| `.btn-sm` | Padding `var(--space-2) var(--space-4)`, `--font-size-sm` |
| `.btn-lg` | Padding `var(--space-4) var(--space-8)`, `--font-size-lg` |

Primary actions (run audit, export report) use `.btn-primary` or `.btn-gradient`. Secondary / less emphatic actions use `.btn-outline` or `.btn-ghost`.

**Cards** (`.card`): `--color-surface` background, `1px solid var(--color-border)`, `--radius-xl`, padding `--space-6`, `--color-shadow`. Hover: `translateY(-2px)` and `--color-shadow-lg` (`--transition-base`). `.card-elevated` uses `--color-surface-elevated`. Use cards for score KPIs, audit summaries, and report sections. Disable the hover lift on static PDF/report cards if it is not meaningful in print.

**Forms:** `.form-group` has `margin-bottom: var(--space-5)`. Labels are block, `--font-weight-medium`, `--color-text`, with `margin-bottom: var(--space-2)`. Inputs, textareas, and selects are full width, padding `var(--space-3) var(--space-4)`, `--font-size-base`, `--color-text` on `--color-bg`, `1px solid var(--color-border)`, `--radius-md`. On focus: `outline: none`, `border-color: var(--color-accent)`, `box-shadow: 0 0 0 3px rgb(6 182 212 / 0.2)` (cyan `#06b6d4` at 20% opacity), transitioning with `--transition-fast`.

**Tables:** The stylesheet does not define table components. Build issue and URL tables from existing tokens only: `--color-border` / `--color-border-strong` for rules and outlines, `--color-bg-secondary` or `--color-surface-elevated` for header fills, `--color-text` / `--color-text-secondary` for text, `--font-size-sm` for dense data, `--font-family-mono` plus `.code` styling for check IDs and URLs, and `--radius-lg` or `--radius-xl` for the table container. Row padding should come from the spacing scale (for example `--space-2` / `--space-3` / `--space-4`).

### 3.6 Severity badges, statuses, and scores

The styleguide has no dedicated badge component and no tokens named Critical / High / Medium / Low. Map product statuses onto the existing semantic and neutral palette:

| Severity | Token | Value |
|----------|-------|-------|
| Critical | `--color-error` | `#ef4444` |
| High | `--color-warning` | `#f59e0b` |
| Medium | `--color-info` | `#06b6d4` |
| Low | `--color-gray-500` | `#64748b` |

`--color-gray-500` is also `--color-text-secondary` in light mode. In dark mode, prefer the same `--color-gray-500` (`#64748b`) for Low so the badge color stays stable; do not switch Low to `--color-text-secondary` (which becomes `#94a3b8` in dark mode).

| Check status | Token | Value |
|--------------|-------|-------|
| Pass | `--color-success` | `#10b981` |
| Warning | `--color-warning` | `#f59e0b` |
| Fail | `--color-error` | `#ef4444` |

Use `--color-white` for label text on these solid fills and verify contrast (see 3.10). Badge shape and type may use `--radius-full` or `--radius-sm` and `--font-size-xs` / `--font-weight-medium` or `--font-weight-semibold`. Do not invent additional severity colors.

### 3.7 Dashboard layout

There is no sidebar or app-shell component in the CSS. Compose the dashboard from the layout tokens in 3.4:

- Centered content in `.container` (`max-width: 1280px`, padding `--space-6`).
- Page or section blocks: `.section` / `.section-sm`.
- Top-level score overview (Overall, SEO, GEO, and key counts) as a `.grid-2` / `.grid-3` / `.grid-4` of `.card`s; stacks to one column below 768px.
- Issue lists and crawl tables in a surface/card container (3.5).
- Primary actions in the header or toolbar using `.btn` variants; optional theme control styled like `.theme-toggle`.
- App shell backgrounds: `--color-bg` / `--color-bg-secondary`; panels and nav surfaces: `--color-surface` or `--color-surface-elevated`, with `--color-border` dividers.
- Default lockup in the chrome: `SanneticDesign/logo/lockup.svg` (see 3.9).

### 3.8 Charts and score visuals

The stylesheet does not define chart or score-ring components. Style them with tokens only:

- Brand emphasis and overall-score highlights: `--color-primary`, `--color-accent`, and `--color-gradient`.
- Good / mid / poor quantitative states: `--color-success`, `--color-warning`, `--color-error` (same mapping idea as Pass / Warning / Fail). Do not invent extra threshold colors; numeric cutoffs belong in the scoring docs, not in a new palette.
- Axes, gridlines, and legends: `--color-border`, `--color-text-secondary`, `--color-text-muted`; legend labels in `--font-size-sm` / `--font-size-xs`.
- Track or empty-ring backgrounds: `--color-bg-secondary` or `--color-border`.
- Large score numerals: heading sizes (for example `--font-size-3xl`–`--font-size-5xl`), `--font-weight-bold` or `--font-weight-semibold`, `--font-family` (use `--font-family-mono` only for raw identifiers, not for headline scores).

### 3.9 Logo and favicon usage

Reference files by path in [SanneticDesign](https://github.com/vASanne/SanneticDesign). Use these assets; do not redraw the mark.

| Use | Path |
|-----|------|
| Horizontal lockup (symbol + wordmark + tagline) | `SanneticDesign/logo/lockup.svg` |
| Raster lockup fallbacks | `SanneticDesign/logo/lockup.png`, `lockup-512.png`, `lockup-1024.png` |
| Stacked lockup (symbol above the wordmark) | `SanneticDesign/logo/lockup-stacked.svg` (+ `lockup-stacked.png`, `lockup-stacked-512.png`, `lockup-stacked-1024.png`) |
| Symbol only | `SanneticDesign/logo/symbol.svg` (+ `symbol.png`, `symbol-512.png`, `symbol-1024.png`) |
| Monochrome symbol (`currentColor`) | `SanneticDesign/logo/symbol-mono.svg` |
| Brain tissue only (no pixels or rain) | `SanneticDesign/logo/symbol-brain-only.svg` |
| Favicon | `SanneticDesign/logo/favicon.svg`, `favicon-32.png`, `favicon-16.png` |
| Theme-preview composites | `lockup-dark.png`, `lockup-light.png`, `lockup-stacked-dark.png`, `lockup-stacked-light.png`, `symbol-dark.png`, `symbol-light.png` |
| Family overview sheet | `SanneticDesign/logo/overview.png` |
| Animated symbol / lockup | `SanneticDesign/logo/animated/` (`sannetic-symbol.js`, `sannetic-symbol-animated.html`, `sannetic-lockup-animated.html`, plus `previews/`) |

**Usage rules that follow from those files and `SanneticDesign/logo/README.md`:**

- Prefer SVG in UI and digital reports; use the PNG size variants where a raster is required (PDF, emails, OS favicons).
- Use the horizontal lockup in headers, report covers, and wide chrome; the stacked lockup in narrow columns; the symbol (or favicon set) for the app icon, compact nav, and browser tab.
- `symbol-mono.svg` is the monochrome / on-color variant. Do not recolor the full-color SVGs ad hoc.
- The `-dark` / `-light` PNGs are **preview composites** on the logo identity grounds, not drop-in UI assets for the web theme surfaces. Prefer the transparent SVG/PNG lockups and symbols on `--color-bg` / `--color-surface`.
- The lockup includes the wordmark “Sannetic” and the tagline “Software. Intelligence.” Letterforms in the logo files are path outlines; they have no live font dependency.
- Animated usage: mount `SanneticDesign/logo/animated/sannetic-symbol.js` only where motion adds value (marketing or an empty/loading state), and honor `prefers-reduced-motion` (the bundle’s `reducedMotion: 'auto'` default already does this).

**Logo mark vs. UI tokens:** Since SanneticDesign commit `929dbad`, the web brand tokens are aligned with the logo mark gradient `#8FD11B → #1CC4A0 → #08C2D4` (`--color-primary` `#1CC4A0`, `--color-accent` `#08C2D4`, `--color-gradient`). The semantic tokens `--color-success` (`#10b981`) and `--color-info` (`#06b6d4`) intentionally keep their previous values, so status colors stay distinct from brand colors. The logo preview grounds `#1A1714` / `#F4F1EC` are not part of `sannetic-styleguide.css`; do not mix them into the application palette.

### 3.10 Accessibility

- Target **WCAG 2.2 AA** contrast for text and essential UI (including badges, links, and score labels). Confirm contrast in both themes, especially `--color-text-secondary` and `--color-text-muted` on `--color-bg` / `--color-surface`, and light text on `--color-warning` (`#f59e0b`) or `--color-gray-500`.
- Use the styleguide focus styles; do not remove outlines. `:focus-visible` is `outline: 2px solid var(--color-accent); outline-offset: 2px`. Form controls additionally use the cyan focus ring in 3.5.
- Do not rely on color alone for severity or Pass / Warning / Fail; keep the text label (and consider an icon or prefix).
- Honor `prefers-reduced-motion` for the animated logo and for non-essential motion (`translateY` hovers on buttons/cards may be reduced or disabled).
- Images, SVGs, and the logo must have appropriate `alt` text (or empty `alt` when decorative). The CSS sets `img, svg { max-width: 100%; height: auto; display: block; }`.

### 3.11 White-label PDF and report styling

Default client-facing HTML and PDF reports use the **Sannetic theme** (same tokens, typography, cards, severity colors, and default lockup as the dashboard). Generate reports from HTML (Jinja2 + WeasyPrint or Playwright) so CSS variables can be applied consistently.

White-label is **token- and asset-based**, not a one-off CSS fork per client:

- Override CSS custom properties (brand colors, surfaces, typography if required) per client — store them in the client `settings` JSON (see 5.2) and inject them into the report stylesheet.
- Replace the default lockup with the client `logo_url` where white-label is enabled; otherwise use `SanneticDesign/logo/lockup.svg`.
- Keep spacing, radius, shadow, and component structure on the Sannetic scale unless a client token override explicitly changes them.
- Prefer static layout for print (avoid hover-only affordances); use `--color-border` and `--color-shadow` for separation. In the MVP, basic white-label may be logo-only (see 6.1); full token theming is the target for later white-label work.

---

## 4. Key Checks (SEO + GEO)

Goal: 45–50 high-quality, explainable checks with clear fix guidance and severity.

### 4.1 Technical SEO (foundation)

| ID | Check | Severity | Description / success criterion |
|----|-------|----------|---------------------------------|
| T01 | HTTP status code | Critical | 200 OK for indexable pages; no 4xx/5xx on important URLs |
| T02 | Redirect chains | High | Max. 1 redirect; no chains or loops |
| T03 | Canonical tags | High | Self-referencing or correct; no conflicts |
| T04 | noindex / robots meta | Critical | No unintended noindex on important pages |
| T05 | robots.txt | High | Allows important paths; sitemap declared; AI bots handled deliberately |
| T06 | XML sitemap | Medium | Present, valid, current URLs, no noindex URLs |
| T07 | HTTPS | Critical | Entire site on HTTPS; no mixed content |
| T08 | Mobile-friendly / viewport | High | Viewport meta present and correct |
| T09 | Page speed / Core Web Vitals | High | PSI API: LCP, INP, CLS in the good range (CrUX where possible) |
| T10 | HTML size | Medium | Reasonable size; no extreme bloat |
| T11 | JavaScript dependency | High | Important content present in the initial HTML |
| T12 | Hreflang (if relevant) | Medium | Correct implementation for multilingual sites |
| T13 | Internal links | Medium | Sufficient internal linking; no orphans |
| T14 | Broken links | High | No internal 404s |
| T15 | Duplicates (title/description) | Medium | No mass duplicates |

### 4.2 On-page SEO

| ID | Check | Severity | Description |
|----|-------|----------|-------------|
| O01 | Title tag | High | Present, 50–60 characters ideal, keyword-relevant |
| O02 | Meta description | Medium | Present, 120–160 characters, compelling |
| O03 | H1 | High | Exactly one H1, relevant, not too long |
| O04 | Heading hierarchy | Medium | Logical H1–H6 structure |
| O05 | Image alt text | Medium | All relevant images have meaningful alt text |
| O06 | Content length | Medium | Sufficient text volume for the page-type intent |
| O07 | Open Graph / Twitter Cards | Low | Complete social tags |
| O08 | Structured data (Schema) | High | Valid JSON-LD matching the page type |
| O09 | Schema validity | High | No critical errors in schema |
| O10 | Keyword usage | Low | Natural usage (no stuffing) |

### 4.3 GEO / Generative Engine Optimization

| ID | Check | Severity | Description |
|----|-------|----------|-------------|
| G01 | AI crawler access | Critical | robots.txt allows OAI-SearchBot, PerplexityBot, Claude-SearchBot, Google-Extended (search bots) |
| G02 | Training vs. search bots | Medium | Separation possible (e.g. block GPTBot, allow search bots) |
| G03 | llms.txt | Medium | Present and usefully populated (optional, but a plus) |
| G04 | Server-rendered content | Critical | Core content present in the raw HTML (not only after JS) |
| G05 | Answer-first structure | High | Direct answers in the first sections / paragraphs |
| G06 | Extractable sections | High | Self-contained, citable passages (40–100 words) |
| G07 | Statistical density | Medium | At least one verifiable figure/source per relevant section |
| G08 | Entity clarity | High | Clear, consistent mention of the brand/organization |
| G09 | Schema for entities | High | Organization, WebSite, Article, FAQPage, etc. cleanly implemented |
| G10 | FAQ structure | Medium | FAQ schema or clear question-answer structures |
| G11 | Freshness / recency | Medium | Date signals, current content |
| G12 | E-E-A-T signals | Medium | Authors, sources, expertise cues |
| G13 | AI discovery files | Low | ai.txt / llms.txt / similar files |
| G14 | Citability score (heuristic) | High | Aggregated score from G05–G08 |

### 4.4 Further / cross-cutting checks

| ID | Check | Severity | Description |
|----|-------|----------|-------------|
| X01 | Overall indexability | Critical | Combination of status, robots, canonical, noindex |
| X02 | Security headers | Medium | HSTS, CSP (basic), X-Content-Type-Options, etc. |
| X03 | Accessibility (basic) | Low | Alt text, heading structure (overlap with on-page) |
| X04 | Content quality (heuristic) | Medium | Readability, structure, thinness |

**Total:** approx. 45 checks. Each check provides:
- Status (Pass / Warning / Fail)
- Severity
- Brief explanation
- Concrete fix guidance
- Affected URLs (for site crawls)

---

## 5. Architecture & Data Model

### 5.1 High-level architecture

```
[Frontend (Next.js)] 
        ↓
[FastAPI Backend]
        ↓
[Celery Workers] ←→ [Redis]
        ↓
[Crawler Module] → [Extractor] → [Analyzer (SEO + GEO)] → [Scorer]
        ↓
[PostgreSQL] + [Object Storage]
        ↓
[Report Generator] → PDF / HTML / Dashboard
```

### 5.2 Core entities (data model)

```sql
-- Clients (multi-tenant)
clients
  id, name, domain, logo_url, settings (JSON), created_at

-- Audits
audits
  id, client_id, url (start), status (pending/running/completed/failed),
  started_at, finished_at, pages_crawled, overall_score, seo_score, geo_score,
  config (JSON: max_pages, follow_links, etc.)

-- Pages
pages
  id, audit_id, url, status_code, title, meta_description,
  content_hash, html_storage_path, crawled_at

-- Issues
issues
  id, audit_id, page_id (nullable), check_id (e.g. T01), severity,
  title, description, recommendation, affected_urls (JSON), status

-- Scores
scores
  id, audit_id, category (seo/geo/technical/onpage), score (0-100), details (JSON)

-- Historical snapshots (for trends)
audit_history (or simply via audits with client_id)
```

### 5.3 Module structure (backend)

```
app/
├── api/                 # FastAPI routes
├── core/                # Config, DB, security
├── crawler/             # Crawl logic (Scrapy-based or custom)
├── extractors/          # HTML parsing, schema, meta
├── analyzers/
│   ├── seo/
│   └── geo/
├── scoring/             # Score calculation & prioritization
├── reports/             # PDF/HTML generation
├── tasks/               # Celery tasks
├── models/              # SQLAlchemy models
└── services/            # Business logic
```

### 5.4 Prioritization logic

- Critical issues always at the top
- Impact estimate: combination of severity + number of affected pages + page importance (e.g. homepage, money pages)
- Flag “Quick Wins” (easy to implement + high impact)

---

## 6. MVP Scope & Prioritization

### 6.1 MVP definition (Phase 1)

**Goal:** A usable single-URL + limited-crawl tool with strong scoring and clear reports.

**Must-have for the MVP:**
- URL input → crawl (max. 50–100 pages or configurable)
- All checks from Section 4 (at least Critical + High)
- Overall / SEO / GEO score
- Issue list with severity, explanation, and fix
- Simple dashboard (Next.js, or Streamlit initially as a transitional step)
- HTML report export
- Polite crawling + Playwright option for JS pages

**Nice-to-have in the MVP:**
- PageSpeed Insights integration
- Basic white-label (logo)

**Not in the MVP:**
- Multi-client login system (can start hardcoded / single-tenant)
- GSC integration
- Automatic recurring jobs
- LLM-based content evaluation

### 6.2 Implementation prioritization

1. **Data model + FastAPI foundation**
2. **Crawler + extractor** (title, meta, headings, schema, robots.txt, status)
3. **Analyzer modules** (SEO + GEO checks)
4. **Scoring engine**
5. **Report generation (HTML)**
6. **Simple frontend**
7. **PageSpeed integration**
8. **Expansion to site crawl + prioritization**

### 6.3 Roadmap overview

| Phase | Focus | Estimated duration |
|-------|-------|------------------|
| 1     | MVP (single/limited crawl + scores + report) | 4–6 weeks |
| 2     | Full site crawl + prioritization + PDF | 4–6 weeks |
| 3     | Multi-client + white-label + history | 3–5 weeks |
| 4     | GSC + AI recommendations + monitoring | ongoing |

---

## 7. Cursor-Specific Instructions

### General development rules

- Write clean, typed Python code (type hints everywhere)
- Use Pydantic models for request/response
- Async where it makes sense (FastAPI, HTTP requests)
- Unit tests for analyzers and scoring
- Documentation in docstrings
- Configuration via environment variables (`.env`)
- Error handling and logging (structlog or similar)

### Design system rules (frontend & reports)

- Follow Section 3. The source of truth is `SanneticDesign/sannetic-styleguide.css`.
- **Use design tokens only.** Do not hard-code hex/RGB colors, font sizes, spacing, radii, or shadows in UI or report CSS. Reference custom properties (or the Tailwind/shadcn mappings described in 3.1).
- Do not introduce a parallel palette or type scale. If a value is missing from the styleguide, extend it by adding a named token — do not sprinkle a one-off literal.
- Support light (default) and dark themes via `[data-theme="dark"]` and `.dark`.
- Map Sannetic `--color-accent` to a dedicated brand/ring token, not to shadcn’s `--accent` hover surface (see 3.1).
- Use the typography, button, card, form, and focus patterns in Section 3; load Inter and JetBrains Mono to match `--font-family` and `--font-family-mono`.
- Map severity and check status to the tokens in 3.6; do not invent additional colors.
- Default logos and favicons must come from `SanneticDesign/logo/` (see 3.9). White-label reports restyle through client token/logo overrides, not a separate CSS fork.
- Honor `prefers-reduced-motion` for the animated mark and decorative motion.

### Recommended first steps in Cursor

1. Set up the project structure (see 5.3)
2. FastAPI + SQLAlchemy + Alembic setup
3. Implement a basic crawler (httpx + BeautifulSoup/selectolax for the MVP)
4. Implement the first 10 checks (T01–T05, O01–O03, G01, G04)
5. Basic scoring logic
6. Create a simple `/audit` endpoint

### Important notes

- **Always check and respect robots.txt**
- Clearly identify the user agent (e.g. `AgencySEOBot/1.0 (+https://agency.com/bot)`)
- Implement rate limiting and a download delay
- For JS pages: use Playwright optionally and sparingly
- Make scores transparent (document the weighting)
- Reports must be client-ready (clear language, no internal codes)

---

## 8. Next Concrete Steps

1. Initialize the repository and set up the basic structure
2. Define database models (Clients, Audits, Pages, Issues)
3. Implement the MVP crawler + first checks
4. Build scoring and a simple report
5. Connect the frontend dashboard

---

**End of specification**

This document is the central reference for development. All changes to scope or checks should be documented here.
