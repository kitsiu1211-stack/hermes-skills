# Token synthesis: from DESIGN.md to working theme

A worked example from the "AI Atlas" redesign session, validating the pipeline in
Section 7.A of the parent skill. Six design systems → one cohesive dark dashboard.

## Step 1: Select reference systems (3-6)

Pick systems relevant to the page kind and audience:

| System | Why selected |
|--------|-------------|
| Resend | Dark canvas, atmospheric depth, typographic confidence |
| Vercel | Aggressive negative tracking, multi-stop mesh gradient, mono labels |
| Superhuman | Three-canvas rhythm, warm greys, sub-default weights, single-action-per-band |
| Sentry | Bold accent colors with developer-tool energy |
| Warp | Warm charcoal (not pure black), serif moments |
| Stripe | Precise spacing, subtle stacked shadows, hairline borders |

## Step 2: Extract tokens into comparison

Read each `design-md/<company>/DESIGN.md` and pull tokens into this grid:

| Token class | Resend | Vercel | Superhuman | Sentry | Warp | Stripe |
|-------------|--------|--------|------------|--------|------|--------|
| Canvas | `#000000` | `#fafafa` | `#ffffff` (body) | `#150f23` (dark) | `#2b2622` | `#ffffff` |
| Surface | `#0a0a0c` | `#f5f5f5` | `#fafaf8` | `#1f1633` | `#383330` | `#f6f9fc` |
| Ink | `#fcfdff` | `#171717` | `#292827` | `#1f1633` | `#f7f5f0` | `#0d253d` |
| Primary accent | orange glow | black-ink | indigo `#1b1938` | electric lime | cream `#f7f5f0` | indigo `#533afd` |
| Secondary accent | blue glow | cyan `#50e3c2` | teal `#0e3030` | pink `#fa7faa` | — | ruby `#ea2261` |
| Display weight | 400 (serif) | 600 (Geist) | 460/540 | 700 | 400 (Inter) | 300 (Sohne) |
| Display tracking | -0.96px | -2.4px | -1.32px | 0 | -1.6px | -1.4px |
| Body size | 16px | 16px | 16px | 16px | 16px | 15px |
| Border radius | — | 8px md | 8px md | — | — | 12px lg |
| Shadow style | subtle glow | stacked (3 layers) | box-shadow | — | — | subtle blue-tinted |
| Card padding | — | 24px | 32px | — | — | 32px |
| Spacing base | — | 4px | 8px | — | — | 8px |
| Mono for labels | — | YES | — | — | — | — |

## Step 3: Synthesize — pick best per dimension

Don't mechanically average. Make deliberate choices per dimension:

| Dimension | Choice | From | Rationale |
|-----------|--------|------|-----------|
| Canvas | `#0d0d12` | Resend + Warp | Dark base, warm charcoal (not pure black) |
| Surface hierarchy | `#14141a` → `#1a1a24` → `#20202c` | Resend surface ladder | Subtle luminance shifts for depth |
| Primary accent | `#7c5cfc` (indigo-violet) | Sentry + Stripe | Developer-tool energy, rich enough for dark bg |
| Secondary accent | `#00d4aa` (teal) | Vercel cyan + Superhuman teal | Contrast against violet, fresh |
| Ink | `#f0f0f5` | Resend off-white | Warmer than pure white, easier on eyes |
| Ink secondary | `#8a8a95` | Vercel body + Resend muted | Enough contrast, not harsh |
| Hairline | `rgba(255,255,255,.06)` | Resend translucent borders | Depth without heavy outlines |
| Font | Inter | Vercel/Warp | Open-source, geometric, works for CJK |
| Display weight | 700 | — | Bold for dark backgrounds, more legible |
| Display tracking | -0.035em | Vercel aggressive | Editorial tightness on hero |
| Body weight/size | 400/16px | Vercel | Clean reading |
| Mono for labels | JetBrains Mono 10-11px | Vercel mono pattern | Technical voice for nav/section labels/captions |
| Border radius | 10-14px | Stripe | Rounded enough to feel modern, not pill-shaped |
| Shadows | `0 4px 12px rgba(0,0,0,.25)` + `0 1px 3px rgba(0,0,0,.2)` | Vercel stacked | Depth without floating |
| Spacing base | 8px | Superhuman/Stripe | Predictable rhythm |
| Card padding | 24px | Vercel card | Tight enough for dashboard, generous enough for breathing room |
| Section padding | 80-88px | Vercel generous | Space between content bands |

## Step 4: Build CSS custom properties

```css
:root {
  --canvas: #0d0d12;
  --surface: #14141a;
  --surface-elevated: #1a1a24;
  --surface-high: #20202c;
  --ink: #f0f0f5;
  --ink-secondary: #8a8a95;
  --ink-muted: #5c5c66;
  --accent: #7c5cfc;
  --accent-glow: rgba(124,92,252,.25);
  --accent-2: #00d4aa;
  --hairline: rgba(255,255,255,.06);
  --radius: 10px;
  --radius-lg: 14px;
  --shadow: 0 4px 12px rgba(0,0,0,.25), 0 1px 3px rgba(0,0,0,.2);
}
```

## Step 5: Build components from tokens

Every component references CSS custom properties, never hardcoded values.
Cards use `var(--surface)`, hover states shift to `var(--surface-elevated)`.
Borders use `var(--hairline)`. Text uses `var(--ink)` / `var(--ink-secondary)`.

## Result

This pipeline produced an 8.5/10 dark dashboard from "still ugly" in one pass.
Compare to 4 rounds of ad-hoc iteration that never exceeded "一般般".
Token-first synthesis ≤ 1 pass; ad-hoc iteration ≥ 4 passes with worse results.
