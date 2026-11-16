# SEO & GEO Analyzer – Agency USP Tool

**Project Specification & Cursor Instructions**

**Version:** 1.6  
**Date:** 15 November 2026  
**Purpose:** Complete guide for developing a mature SEO and GEO analysis tool as an agency unique selling proposition.

**Changelog:** 1.1 — Full English translation; added Section 3 “Design System & UI Guidelines,” integrating the Sannetic design system.  
**Changelog:** 1.2 — Brand tokens updated to the logo-aligned palette (SanneticDesign commit `929dbad`).  
**Changelog:** 1.3 — Self-hosted fonts and updated focus ring (SanneticDesign commit `671ff75`).  
**Changelog:** 1.4 — Dark default theme, light opt-in, WCAG 2.2 AA contrast, new on-brand/text tokens (SanneticDesign commit `d9dbd65`).  
**Changelog:** 1.5 — Logo clear space and minimum sizes (SanneticDesign commit `80b0f22`).  
**Changelog:** 1.6 — Component library (tables, severity pills, app shell, chips, calendar, danger buttons) from SanneticDesign commit `bf77fa7`.

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
| Web tokens & base styles (sections 1–8) | `SanneticDesign/sannetic-styleguide.css` |
| Component library (sections 9–23; load after the styleguide) | `SanneticDesign/sannetic-components.css` |
| Design-system README (tokens, Tailwind/shadcn notes, class index) | `SanneticDesign/README.md` |
| Human-readable styleguide (companion PDF) | `SanneticDesign/Sannetic-Styleguide.pdf` |
| Logo, symbol, favicon, animated mark | `SanneticDesign/logo/` |
| Logo identity notes | `SanneticDesign/logo/README.md` |

**CSS wins.** If the PDF, the README, or any project document disagrees with the CSS, implement the CSS. Token and component values in this section are taken from `sannetic-styleguide.css` and `sannetic-components.css` only. Component tokens (section 9) live in the components file, not in the styleguide.

**Integration with Next.js + Tailwind CSS + shadcn/ui:**

**Stack note.** The product frontend stays **Next.js + Tailwind CSS + shadcn/ui**. `sannetic-components.css` is a standalone stylesheet whose class names follow Bootstrap 5 where sensible (`.btn`, `.table`, `.modal`, and so on); it does **not** import or require Bootstrap (the file header: “CSS only”). Load `fonts/fonts.css`, then the styleguide, then the components file, and use those classes directly in JSX where they fit (tables, severity pills, app shell, chips, calendar, danger buttons, alerts). For shadcn primitives already in the app (dialogs, dropdowns, and similar overlays), restyle them with Sannetic tokens so they match the library visuals — do not ship two parallel overlay systems, and do not add Bootstrap CSS or JS as a dependency. Collapse toggling, dropdown placement beyond below/end, and some navbar behavior still need application JavaScript (Popper only where the SanneticDesign coverage table says so).

1. Import `fonts/fonts.css`, then `sannetic-styleguide.css`, then `sannetic-components.css` into the global stylesheet (for example `app/globals.css`). Alternatively, re-declare the same custom properties and map them 1:1 — do not retokenize by eye.
2. Extend the Tailwind theme with those custom properties (`colors`, `fontFamily`, `fontSize`, `fontWeight`, `lineHeight`, `spacing`, `borderRadius`, `boxShadow`, `transitionDuration` / `transitionTimingFunction`, `maxWidth`, plus the component tokens in 3.2 where useful).
3. Map Sannetic tokens onto shadcn/ui CSS variables in `:root` (dark is the default) and in `[data-theme="light"]` / `.light`. Do not use the previous dark-mode class or data-theme value — those selectors were removed from the styleguide. If a shadcn preset still emits a dark-mode class, either drop it or alias it to the default (dark) tokens; light must be opt-in via the styleguide’s light selectors.

Recommended shadcn/ui mapping (Sannetic name → shadcn variable):

| Sannetic token | shadcn/ui variable | Notes |
|----------------|--------------------|-------|
| `--color-bg` | `--background` | Dark default `#0f172a`; light `#ffffff` |
| `--color-text` | `--foreground` | Dark `#f1f5f9`; light `var(--color-gray-900)` / `#0f172a` |
| `--color-surface` | `--card`, `--popover` | Dark `#1e293b`; light `#ffffff` |
| `--color-text` | `--card-foreground`, `--popover-foreground` | |
| `--color-primary` (`#1CC4A0`) | `--primary` | |
| `--color-on-brand` (`#0f172a`) | `--primary-foreground` | Matches `.btn-primary`, `.btn-accent`, and `.btn-gradient` text |
| `--color-bg-secondary` | `--secondary`, `--muted` | Dark `#1e293b`; light `var(--color-gray-50)` / `#f8fafc` |
| `--color-text` | `--secondary-foreground` | |
| `--color-text-secondary` | `--muted-foreground` | Dark `#94a3b8`; light `#64748b` |
| `--color-error` | `--destructive` | Dark default `#F15D5D`; light `#dc2626` |
| `--color-on-danger` | `--destructive-foreground` | Dark `var(--color-black)` / `#0f172a` (white fails on `#F15D5D`); light `var(--color-white)` / `#ffffff` |
| `--color-border` | `--border` | Dark `#334155`; light `#e2e8f0`. Decorative dividers and card borders. |
| `--color-border-strong` | `--input` | Dark `#60738E`; light `#7A93B2`. Form controls use this, not `--color-border`. |
| `--color-accent-text` | `--ring` | Focus color: dark equals `--color-accent` (`#08C2D4`); light `#057E8A` |
| `--radius-md` (`0.5rem`) or `--radius-lg` (`0.75rem`) | `--radius` | Buttons use `--radius-lg`; inputs use `--radius-md`; cards use `--radius-xl` (`1rem`) |

**Naming collision:** Sannetic `--color-accent` is brand cyan (`#08C2D4`). shadcn’s `--accent` is typically a subtle hover surface, not a brand color. Do **not** map `--color-accent` onto shadcn `--accent`. Expose cyan as a dedicated token (for example `--sannetic-accent` / Tailwind `accent`), use `--color-accent-text` for links, code, and focus, and, if a muted hover surface is needed, use `--color-bg-secondary` or `--color-surface-elevated`.

Dark mode is the typography/base default in `:root`. Light mode is opt-in with `[data-theme="light"]` or `.light`. The styleguide ships no runtime theme toggle.

### 3.2 Color tokens

**Brand (from logo, as defined in the CSS):**

| Token | Value | CSS comment / role |
|-------|-------|--------------------|
| `--color-primary` | `#1CC4A0` | Teal (logo gradient mid) |
| `--color-primary-hover` | `#17A183` | Primary hover (`.btn-primary:hover`) |
| `--color-primary-light` | `#40E4C0` | Lighter primary |
| `--color-accent` | `#08C2D4` | Cyan (logo gradient end) |
| `--color-accent-hover` | `#079FAE` | Accent fill hover (`.btn-accent:hover`) |
| `--color-accent-light` | `#27E5F7` | Lighter cyan |
| `--color-gradient` | `linear-gradient(135deg, #8FD11B 0%, #1CC4A0 50%, #08C2D4 100%)` | Brand gradient (`.btn-gradient`, `.text-gradient`) |

**Text-safe brand colors and text on brand fills (WCAG AA):**

| Token | Dark (`:root`) | Light (`[data-theme="light"]`, `.light`) | Role |
|-------|----------------|------------------------------------------|------|
| `--color-on-brand` | `#0f172a` | `#0f172a` (unchanged) | Text on primary, accent, and gradient fills |
| `--color-primary-text` | `var(--color-primary)` (`#1CC4A0`) | `#12816A` | Brand teal used as text; light value is darkened because `#1CC4A0` is too light on white |
| `--color-accent-text` | `var(--color-accent)` (`#08C2D4`) | `#057E8A` | Brand cyan used as text; also links, `code` / `.code`, and focus outlines |

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
| `--color-success` | `#10b981` (both themes) |
| `--color-warning` | `#f59e0b` (both themes) |
| `--color-error` | Dark `#F15D5D`; light `#dc2626` |
| `--color-info` | `#06b6d4` (both themes) |

`--color-success` (`#10b981`) and `--color-info` (`#06b6d4`) keep the earlier semantic values and stay distinct from `--color-primary` (`#1CC4A0`) and `--color-accent` (`#08C2D4`). `--color-error` is the only semantic token that changes between themes.

**Theme surfaces (dark default → light opt-in):**

| Token | Dark (`:root`) | Light (`[data-theme="light"]`, `.light`) |
|-------|----------------|------------------------------------------|
| `--color-bg` | `#0f172a` | `var(--color-white)` (`#ffffff`) |
| `--color-bg-secondary` | `#1e293b` | `var(--color-gray-50)` (`#f8fafc`) |
| `--color-surface` | `#1e293b` | `var(--color-white)` (`#ffffff`) |
| `--color-surface-elevated` | `#334155` | `var(--color-gray-50)` (`#f8fafc`) |
| `--color-text` | `#f1f5f9` | `var(--color-gray-900)` (`#0f172a`) |
| `--color-text-secondary` | `#94a3b8` | `var(--color-gray-500)` (`#64748b`) |
| `--color-text-muted` | `#8190A5` (AA on bg and surface) | `#5F7390` (AA on white) |
| `--color-border` | `#334155` (decorative dividers) | `var(--color-gray-200)` (`#e2e8f0`) |
| `--color-border-strong` | `#60738E` (form controls, 3:1 on bg and surface) | `#7A93B2` (form controls, 3:1 on white) |

Brand fill colors (`--color-primary`, `--color-accent`, `--color-gradient`) and `--color-on-brand` do not change between themes. These contrast-related tokens do: `--color-text-muted`, `--color-border-strong`, `--color-error`, `--color-primary-text`, and `--color-accent-text`.

**Component tokens** (defined in `sannetic-components.css`, section 9; light overrides as noted):

| Token | Dark (`:root`) | Light (`[data-theme="light"]`, `.light`) | Role |
|-------|----------------|------------------------------------------|------|
| `--color-on-danger` | `var(--color-black)` (`#0f172a`) | `var(--color-white)` (`#ffffff`) | Text on solid danger fills (`.btn-danger`, `.pill-critical`). White fails on dark `#F15D5D`. |
| `--color-error-hover` | `color-mix(in srgb, var(--color-error) 80%, var(--color-white))` | `#b91c1c` | `.btn-danger:hover` |
| `--color-error-text` | `#FCA5A5` | `#b91c1c` | Error as text, also on error tints (`.pill-danger`, outline/ghost danger) |
| `--color-success-text` | `#34D399` | `#047857` | Success as text (AA on bg, surface, and own tint) |
| `--color-warning-text` | `#FBBF24` | `#92400e` | Warning as text |
| `--color-info-text` | `#22D3EE` | `#0e7490` | Info as text |
| `--color-high` | `#FB923C` | `#ea580c` | Severity “high” (orange) fill |
| `--color-high-text` | `#FDBA74` | `#9a3412` | High as text |
| `--color-low` | `#60A5FA` | `#3b82f6` | Severity “low” (blue) fill |
| `--color-low-text` | `#93C5FD` | `#1d4ed8` | Low as text |
| `--color-on-primary-text` | `var(--color-bg)` | `var(--color-bg)` (unchanged; follows the theme background) | Marks on `--color-primary-text` fills (check marks, switch knob, default `.progress-bar` text) |

Tint, row, fill, overlay, and focus tokens (formulas are in the CSS; light uses lighter tint percentages so the dark text variants stay above 4.5:1):

| Token | Role |
|-------|------|
| `--color-primary-tint`, `--color-accent-tint`, `--color-error-tint`, `--color-success-tint`, `--color-warning-tint`, `--color-info-tint`, `--color-high-tint`, `--color-low-tint` | Transparent tints that sit on bg or surface (`color-mix` with the corresponding color at 14–16% in dark, 6–12% in light) |
| `--color-row-hover` | Table/nav hover fill (`color-mix` of `--color-text` at 6% dark, 5% light) |
| `--color-row-stripe` | Striped table rows (`color-mix` of `--color-text` at 3%; not overridden in light) |
| `--color-fill-neutral` | Neutral badge, counter, and progress-track fill (dark `var(--color-surface-elevated)`; light `var(--color-gray-100)`) |
| `--color-skeleton` | Skeleton/placeholder fill (dark `var(--color-surface-elevated)`; light `var(--color-gray-200)`) |
| `--color-overlay` | Modal/offcanvas overlay (`color-mix` of `--color-black` at 72% dark, 45% light) |
| `--color-tooltip-bg` / `--color-tooltip-text` | Dark: `--color-gray-100` / `--color-gray-900`; light: `--color-gray-900` / `--color-gray-50` |
| `--shadow-focus` | `0 0 0 3px rgb(8 194 212 / 0.2)` (both themes) |
| `--shadow-focus-danger` | `0 0 0 3px color-mix(in srgb, var(--color-error) 25%, transparent)` |
| `--icon-chevron`, `--icon-check`, `--icon-dash` | Data-URI SVGs for form controls. Strokes are baked in (data URIs cannot read CSS variables) and mirror `--color-text-muted` and `--color-on-primary-text`. |
| `--topbar-height` | `3.5rem` |
| `--sidebar-width` | `16rem` |
| `--sidebar-width-collapsed` | `4.25rem` |
| `--z-dropdown`, `--z-sticky`, `--z-offcanvas`, `--z-modal`, `--z-popover`, `--z-tooltip`, `--z-toast` | `1000`, `1020`, `1045`, `1055`, `1070`, `1080`, `1090` |

### 3.3 Typography

| Token | Value |
|-------|-------|
| `--font-family` | `"Inter", system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif` |
| `--font-family-mono` | `"JetBrains Mono", "Fira Code", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace` |

Since SanneticDesign commit `671ff75`, the fonts are self-hosted in the design repo: `SanneticDesign/fonts/fonts.css` declares `@font-face` rules for **Inter** (variable, weight 100–900) and **JetBrains Mono** (variable, weight 100–800), backed by `inter-latin-wght-normal.woff2` and `jetbrains-mono-latin-wght-normal.woff2` (Latin subset, OFL licensed). Import `fonts.css` (or copy the woff2 files into the app and use `next/font/local`); do not load the fonts from Google Fonts. See `SanneticDesign/README.md` for setup.

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

Links use `--color-accent-text`, no underline by default, and the same `--color-accent-text` plus underline on hover (`--transition-fast`). Do not use `--color-accent-hover` for link color. Small / `.text-sm` text uses `--font-size-sm` and `--color-text-secondary`. `.text-muted` uses `--color-text-muted`. `.text-gradient` applies `--color-gradient` as clipped text. `code` / `.code` uses `--font-family-mono`, `0.9em`, `--color-bg-secondary` background, `--color-accent-text` text, `--radius-sm`, and padding `0.15em 0.4em`.

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

| Token | Dark (default) | Light (opt-in) |
|-------|----------------|----------------|
| `--color-shadow` | `0 4px 6px -1px rgb(0 0 0 / 0.4), 0 2px 4px -2px rgb(0 0 0 / 0.3)` | `0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)` |
| `--color-shadow-lg` | `0 10px 15px -3px rgb(0 0 0 / 0.5), 0 4px 6px -4px rgb(0 0 0 / 0.4)` | `0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)` |

**Motion:** `--transition-fast: 150ms ease`; `--transition-base: 200ms ease`; `--transition-slow: 300ms ease`.

**Control heights** (WCAG 2.2 target size; md is the default), in `sannetic-styleguide.css`: `--control-height-sm: 2.25rem` (36px); `--control-height-md: 2.75rem` (44px); `--control-height-lg: 3.25rem` (52px). Default `.btn` and form controls use `--control-height-md`; `.btn-sm` / `.form-control-sm` use `--control-height-sm`; `.btn-lg` / `.form-control-lg` use `--control-height-lg`.

**Color scheme:** `:root` sets `color-scheme: dark`; `[data-theme="light"]` / `.light` sets `color-scheme: light`, so native widgets (date pickers, scrollbars) follow the theme.

**Layout:** `--container-max: 1280px`; `--container-padding: var(--space-6)` (24px). `.container` is width 100%, centered, with that max width and inline padding. `.section` uses `padding-block: var(--space-16)`; `.section-sm` uses `var(--space-12)`. `.grid` uses `gap: var(--space-6)`; `.grid-2` / `.grid-3` / `.grid-4` are equal columns and collapse to one column at `max-width: 768px`. Utility classes include `.flex`, `.flex-center`, `.flex-between`, `.gap-2`, `.gap-4`, `.gap-6`, and margin helpers `.mt-4`, `.mt-8`, `.mb-4`, `.mb-8`.

### 3.5 Component guidance

Use the patterns in `sannetic-styleguide.css` (core buttons, cards, forms) and `sannetic-components.css` (extended variants, tables, pills, app shell, chips, calendar, and the rest of sections 9–23). Do not restyle them with hard-coded values. How to load and mix this CSS with Next.js, Tailwind, and shadcn/ui is in 3.1.

**Buttons** (`.btn`): inline-flex, centered, `gap: var(--space-2)`, padding `var(--space-3) var(--space-6)`, inherited font family, `--font-size-base`, `--font-weight-semibold`, `line-height: 1`, no border, `--radius-lg`, `transition: all var(--transition-base)`, and (in the styleguide) `min-height: var(--control-height-md)`. The components file also defines an explicit `.btn-md` at the same height.

| Variant | Style |
|---------|-------|
| `.btn-primary` | Background `--color-primary`, text `--color-on-brand`; hover `--color-primary-hover`, `translateY(-1px)`, `--color-shadow` |
| `.btn-accent` | Background `--color-accent`, text `--color-on-brand`; hover `--color-accent-hover` |
| `.btn-gradient` | Background `--color-gradient`, text `--color-on-brand`; hover `filter: brightness(1.1)` and `translateY(-1px)` |
| `.btn-outline` | Transparent, text `--color-primary-text`, `2px` border `--color-primary`; hover fills `--color-primary` with text `--color-on-brand` |
| `.btn-ghost` | Transparent, text `--color-text`; hover background `--color-bg-secondary` |
| `.btn-sm` | Padding `var(--space-2) var(--space-4)`, `--font-size-sm`, `min-height: var(--control-height-sm)` |
| `.btn-lg` | Padding `var(--space-4) var(--space-8)`, `--font-size-lg`, `min-height: var(--control-height-lg)` |

Primary actions (run audit, export report) use `.btn-primary` or `.btn-gradient`. Secondary / less emphatic actions use `.btn-outline`, `.btn-secondary`, or `.btn-ghost`. Destructive actions (delete, cancel, close) use the danger variants from the components file: `.btn-danger` (background `--color-error`, text `--color-on-danger`, hover `--color-error-hover`, focus `--shadow-focus-danger`); `.btn-danger-outline` / `.btn-outline-danger` and `.btn-danger-ghost` / `.btn-ghost-danger` (text `--color-error-text`; outline has a `2px` `--color-error` border; hover `--color-error-tint`). `.btn-close` / `.btn-close-sm` are neutral at rest and turn alarm-colored on hover/focus. Other component variants include `.btn-success`, `.btn-warning`, `.btn-info`, `.btn-light`, `.btn-dark`, `.btn-link`, `.btn-outline-primary`, `.btn-outline-secondary`, `.btn-icon`, `.btn-block`, `.btn-loading` / `[aria-busy="true"]`, `.btn-group`, and `.btn-toolbar`.

**Cards** (`.card`): `--color-surface` background, `1px solid var(--color-border)`, `--radius-xl`, padding `--space-6`, `--color-shadow`. Hover: `translateY(-2px)` and `--color-shadow-lg` (`--transition-base`). `.card-elevated` uses `--color-surface-elevated`. Use cards for score KPIs, audit summaries, and report sections. Disable the hover lift on static PDF/report cards if it is not meaningful in print.

**Forms:** `.form-group` has `margin-bottom: var(--space-5)`. Labels are block, `--font-weight-medium`, `--color-text`, with `margin-bottom: var(--space-2)`. Inputs, textareas, and selects are full width, padding `var(--space-3) var(--space-4)`, `--font-size-base`, `--color-text` on `--color-bg`, `1px solid var(--color-border-strong)`, `--radius-md`. On focus: `outline: none`, `border-color: var(--color-accent-text)`, `box-shadow: 0 0 0 3px rgb(8 194 212 / 0.2)` (accent cyan `#08C2D4` at 20% opacity; also available as `--shadow-focus`), transitioning with `--transition-fast`. The components file adds Bootstrap-like controls you should prefer in the app: `.form-label`, `.form-text`, `.form-control` / `.form-control-sm` / `.form-control-lg`, `.form-select` (and `-sm`/`-lg`), `.input-group` / `.input-group-text`, `.form-floating`, `.form-check` / `.form-switch` / `.form-range`, and validation (`.is-invalid`, `.is-valid`, `.invalid-feedback`, `.valid-feedback`, `.required`).

**Tables** (`.table` in `sannetic-components.css`): `--font-size-sm`, `--color-text`, collapsed borders, cell padding `--space-3` `--space-4`, row rules `--color-border`. Thead cells use `--color-bg-secondary`, `--color-text-secondary`, `--font-size-xs`, `--font-weight-semibold`, uppercase, and a `2px` `--color-border-strong` bottom border (headers are never white in dark mode). Wrap tables in `.table-responsive` (`1px` `--color-border`, `--radius-lg`, horizontal scroll). Modifiers: `.table-sm` (padding `--space-2` `--space-3`), `.table-bordered`, `.table-striped` (`--color-row-stripe`), `.table-hover` (`--color-row-hover`). Highlight or key rows: `tr.table-highlight` or `tr.is-highlight` (`--color-primary-tint`, inset `--color-primary` bar; `.num` / `.value` use `--color-primary-text`). Totals: `tfoot` or `tr.table-total`. Active row: `.table-active` (`--color-accent-tint`). Numeric cells: `.num` / `.text-num` (right-aligned, tabular nums); `.font-mono` / `.num-mono` for check IDs and URLs; `.num-negative` uses `--color-error-text`; `.unit` is muted secondary text.

**Filter chips:** `.chip-group` (flex wrap, gap `--space-2`). `.chip` is an inline-flex pill (`min-height: 2rem`, padding `0.375rem 0.875rem`, `--font-size-sm`, `--color-text` on `--color-surface`, `1px` `--color-border-strong`, `--radius-full`). Active state: `.chip.active`, `.chip.is-active`, `.chip[aria-pressed="true"]`, or `.chip[aria-current="true"]` (text `--color-on-brand`, fill and border `--color-primary`). `.chip-all` is the reset-filter chip (semibold; a check mark when active). `.chip-remove` is the dismiss control.

**Calendar:** Native `input[type="date"]`, `time`, `datetime-local`, `month`, and `week` follow the theme `color-scheme` (picker indicator is un-inverted). For a custom picker, use `.calendar` (surface, `--radius-lg`, `--color-shadow`, `min-width: 18rem`) with `.calendar-header`, `.calendar-title`, `.calendar-nav`, `.calendar-grid`, `.calendar-weekday`, `.calendar-day`, and `.calendar-footer`. Day states: `.is-today`, `.is-selected` / `[aria-selected="true"]`, `.is-in-range`, `.is-outside`, `.is-weekend`, `.is-disabled`.

### 3.6 Severity pills, statuses, and scores

Use the severity pills in `sannetic-components.css`. A `.pill` is an inline-flex label (`--font-size-xs`, `--font-weight-semibold`, `--radius-full`) with a `0.5rem` `::before` dot in `currentColor`. Do not invent additional severity colors or hand-rolled badges for these states.

| Severity | Classes | Tokens |
|----------|---------|--------|
| Critical | `.pill` `.pill-critical` | Text `--color-on-danger`; background `--color-error` (solid fill) |
| High | `.pill` `.pill-high` | Text `--color-high-text`; background `--color-high-tint`; border `color-mix(in srgb, var(--color-high) 40%, transparent)` |
| Medium | `.pill` `.pill-medium` | Text `--color-warning-text`; background `--color-warning-tint`; border mix of `--color-warning` at 40% |
| Low | `.pill` `.pill-low` | Text `--color-low-text`; background `--color-low-tint`; border mix of `--color-low` at 40% |

| Check status | Classes | Tokens |
|--------------|---------|--------|
| Pass | `.pill` `.pill-success` | Text `--color-success-text`; background `--color-success-tint`; border mix of `--color-success` at 40% |
| Warning | `.pill` `.pill-medium` | Same as Medium (there is no `.pill-warning`; the medium pill uses the warning tokens) |
| Fail | `.pill` `.pill-critical` | Same as Critical. `.pill-danger` is the tinted alternative (text `--color-error-text` on `--color-error-tint`) when a solid error fill is too strong. |

`.pill-info` (`--color-info-text` on `--color-info-tint`) and `.pill-neutral` (`--color-text` on `--color-fill-neutral`) are available for non-severity status. General `.badge`, `.badge-neutral`, `.badge-outline`, `.count-badge`, and `.count-text` cover counts and generic labels — not a substitute for the severity pills above.

### 3.7 Dashboard layout

Build the dashboard with the app shell in `sannetic-components.css`:

- `.app-shell` is a full-viewport grid: columns `var(--sidebar-width)` / `1fr`, rows `var(--topbar-height)` / `1fr`, areas `topbar topbar` / `sidebar main`, background `--color-bg`. Add `.is-collapsed` to shrink the sidebar to `--sidebar-width-collapsed` (icons only; `.label`, `.count-badge`, `.badge`, `.sidebar-sub`, and `.sidebar-heading` hide). Below 768px the sidebar is hidden and the grid becomes topbar + main.
- `.app-topbar` (grid area `topbar`, sticky, `z-index: var(--z-sticky)`), typically wrapping a `.navbar` / `.navbar-brand` / `.navbar-nav` / `.navbar-toggler` / `.navbar-text`. Default lockup in the brand: `SanneticDesign/logo/lockup.svg` (see 3.9).
- `.app-sidebar` (area `sidebar`, `--color-surface`, right border `--color-border`) with `.sidebar-nav`, `.sidebar-link` (`.active` / `[aria-current="page"]`, `.is-parent-active`), `.sidebar-sub`, `.sidebar-heading`, and `.sidebar-toggle`.
- `.app-content` or `.app-main` (area `main`, padding `--space-8`; `--space-4` below 768px on `.app-content`).
- Page chrome: `.page-header` and `.page-title` (`--font-size-3xl`, `--font-weight-bold`).
- Score overview (Overall, SEO, GEO, and key counts) as a `.grid-2` / `.grid-3` / `.grid-4` of `.card`s; stacks to one column below 768px.
- Issue and crawl tables use `.table` (see 3.5); severity uses the pills in 3.6; issue-type or severity filters use `.chip-group` / `.chip`.
- Primary actions use `.btn` variants; destructive actions use the danger buttons in 3.5. The default theme is dark; light is opt-in via `[data-theme="light"]` or `.light` on a root element. The styleguide includes no theme switcher component.

### 3.8 Charts and score visuals

There are still no chart or score-ring components in the CSS. Style custom charts with tokens, and use the progress components where a bar is enough:

- Brand emphasis and overall-score highlights: `--color-primary`, `--color-accent`, and `--color-gradient`.
- Good / mid / poor quantitative states: `--color-success`, `--color-warning`, `--color-error` (and the matching `*-text` / `*-tint` tokens for labels and tracks). Do not invent extra threshold colors; numeric cutoffs belong in the scoring docs, not in a new palette.
- Score bars: `.progress` / `.progress-stacked` / `.progress-lg` / `.progress-label` with `.progress-bar`, optionally `.bg-success`, `.bg-warning`, `.bg-danger`, `.bg-info`, or `.bg-gradient` (plus `.progress-bar-striped` / `.progress-bar-animated`). The default bar uses `--color-primary-text` with text `--color-on-primary-text`; the gradient bar uses `--color-on-brand`. The track is `--color-fill-neutral`.
- Axes, gridlines, and legends: `--color-border`, `--color-text-secondary`, `--color-text-muted`; legend labels in `--font-size-sm` / `--font-size-xs`.
- Large score numerals: heading sizes (for example `--font-size-3xl`–`--font-size-5xl`), `--font-weight-bold` or `--font-weight-semibold`, `--font-family` (use `--font-family-mono` or `.font-mono` / `.num` for tabular identifiers and numeric cells, not for headline scores).

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
- **Clear space** (SanneticDesign commit `80b0f22`, `logo/README.md` › Usage rules): keep 1x on all four sides, measured from the visible artwork, not the SVG artboard edge. For lockups, x is the cap height of the "S" in "Sannetic" (x = 177 × W/1444 for `lockup.svg`, 173.5 × W/1200 for `lockup-stacked.svg`). For symbols, x is one quarter of the visible brain height (x = 57.9 × N/512 for `symbol.svg`).
- **Minimum sizes** (screen width): full symbol 80 px, brain-only symbol 32 px, horizontal lockup 280 px (prefer 320 px), stacked lockup 240 px (prefer 280 px), favicon 32 px preferred with a 16 px floor (use the provided PNGs). There is no tagline-free lockup, so below those widths switch to the symbol instead of shrinking the lockup. In compact navigation and small report headers, use the brain-only symbol between 32 and 79 px.

**Logo mark vs. UI tokens:** Since SanneticDesign commit `929dbad`, the web brand tokens are aligned with the logo mark gradient `#8FD11B → #1CC4A0 → #08C2D4` (`--color-primary` `#1CC4A0`, `--color-accent` `#08C2D4`, `--color-gradient`). The semantic tokens `--color-success` (`#10b981`) and `--color-info` (`#06b6d4`) intentionally keep their previous values, so status colors stay distinct from brand colors. The logo preview grounds `#1A1714` / `#F4F1EC` are not part of `sannetic-styleguide.css`; do not mix them into the application palette.

### 3.10 Accessibility

- Target **WCAG 2.2 AA** contrast for text and essential UI (including pills, links, and score labels). The tokens in SanneticDesign commit `d9dbd65` were adjusted for this: `--color-text-muted` is `#8190A5` in the dark default (AA on bg and surface) and `#5F7390` in light (AA on white); `--color-border-strong` is the 3:1 form-control border (`#60738E` dark, `#7A93B2` light); `--color-on-brand`, `--color-primary-text`, and `--color-accent-text` provide AA-safe text on and of brand colors; `--color-error` is `#F15D5D` dark and `#dc2626` light. Commit `bf77fa7` adds `--color-on-danger`, the `*-text` / `*-tint` status tokens, and `--color-high` / `--color-low`. `contrast-check.py` in the design repo checks tokens from both CSS files in both themes (4.5:1 for text, 3:1 for large text and UI boundaries); the documented result is 199/199 checks passed.
- Confirm contrast in both themes. Do not use `--color-gray-400` for muted text. For brand-colored text (links, code, outline buttons), use `--color-primary-text` / `--color-accent-text`, not the raw fill tokens — especially in light mode, where `#1CC4A0` and `#08C2D4` are too light on white. For status text, use `--color-error-text`, `--color-success-text`, `--color-warning-text`, `--color-info-text`, `--color-high-text`, and `--color-low-text`, not the raw fills.
- Text on primary, accent, and gradient fills must use `--color-on-brand` (`#0f172a`), not white. Text on solid danger fills (`.btn-danger`, `.pill-critical`) must use `--color-on-danger` (dark navy in the default theme — white fails on `#F15D5D`; white in light). Prefer the official pill classes in 3.6 rather than placing white or `--color-on-brand` on warning/success/info fills by hand.
- Use decorative `--color-border` only for dividers and card outlines; input and other component borders that need 3:1 contrast must use `--color-border-strong`.
- Use the styleguide focus styles; do not remove outlines. `:focus-visible` is `outline: 2px solid var(--color-accent-text); outline-offset: 2px` (3:1 in both themes). Form controls additionally use the cyan focus ring in 3.5.
- Do not rely on color alone for severity or Pass / Warning / Fail; keep the text label (and consider an icon or prefix).
- Honor `prefers-reduced-motion` for the animated logo and for non-essential motion (`translateY` hovers on buttons/cards may be reduced or disabled).
- Images, SVGs, and the logo must have appropriate `alt` text (or empty `alt` when decorative). The CSS sets `img, svg { max-width: 100%; height: auto; display: block; }`.

### 3.11 White-label PDF and report styling

Default client-facing HTML and PDF reports use the **Sannetic theme** (same tokens, typography, cards, severity colors, and default lockup as the dashboard). The default theme is dark. For print, applying `[data-theme="light"]` or `.light` on the report root is a reasonable opt-in when a light page is required; do this through the official light selectors, not a custom palette. Generate reports from HTML (Jinja2 + WeasyPrint or Playwright) so CSS variables can be applied consistently.

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

- Follow Section 3. The sources of truth are `SanneticDesign/sannetic-styleguide.css` and `SanneticDesign/sannetic-components.css` (load fonts, then the styleguide, then the components file).
- **Use design tokens only.** Do not hard-code hex/RGB colors, font sizes, spacing, radii, or shadows in UI or report CSS. Reference custom properties (or the Tailwind/shadcn mappings described in 3.1).
- Do not introduce a parallel palette or type scale. If a value is missing from the CSS, extend it by adding a named token — do not sprinkle a one-off literal.
- Dark is the default in `:root`. Light is opt-in via `[data-theme="light"]` or `.light`. Do not use the previous dark-mode selectors or a theme switcher — those were removed from the styleguide, which ships no runtime toggle.
- Use `--color-on-brand` for text on primary, accent, and gradient fills (not white). Use `--color-on-danger` for text on solid danger fills. Use `--color-primary-text` and `--color-accent-text` for brand-colored text, links, code, and focus outlines, and the `*-text` status tokens for success/warning/error/info/high/low text. Use `--color-border-strong` for form-control borders, not decorative `--color-border`.
- Map Sannetic `--color-accent` to a dedicated brand token, not to shadcn’s `--accent` hover surface; map `--color-accent-text` to `--ring` and `--color-on-danger` to `--destructive-foreground` (see 3.1).
- Keep the Next.js + Tailwind + shadcn/ui stack. Load the Sannetic component CSS and use its classes directly where they fit, or restyle shadcn primitives to mirror its tokens and visuals. Do not add Bootstrap as a dependency (see 3.1).
- Use the typography, button, card, form, table, pill, app-shell, chip, calendar, and focus patterns in Section 3; load Inter and JetBrains Mono from `SanneticDesign/fonts/fonts.css` to match `--font-family` and `--font-family-mono`.
- Map severity and check status to the `.pill-*` classes and tokens in 3.6; do not invent additional colors or hand-rolled badges for those states.
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
