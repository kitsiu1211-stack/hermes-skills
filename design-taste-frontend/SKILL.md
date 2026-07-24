---
name: design-taste-frontend
description: "Anti-slop frontend skill for landing pages, portfolios, and redesigns. The agent reads the brief, infers the right design direction, and ships interfaces that do not look templated. Real design systems when applicable, audit-first on redesigns, strict pre-flight check."
version: 1.0.0
author: gvnnya
license: MIT
metadata:
  hermes:
    tags: [design, frontend, taste, anti-slop, ui]
    related_skills: [minimalist-ui, industrial-brutalist-ui, redesign-existing-projects]
---

# Taste Skill: Anti-Slop Frontend

> Landing pages, portfolios, and redesigns. Not dashboards, not data tables, not multi-step product UI.
> Every rule below is **contextual**. None of it fires automatically. First read the brief, then pull only what fits.

---

## 0. BRIEF INFERENCE (Read the Room Before Anything Else)

Before touching code or tweaking dials, **infer what the user actually wants**. Most LLM design output is bad because the model jumps to a default aesthetic instead of reading the room.

### 0.A Read these signals first
1. **Page kind** — landing (SaaS / consumer / agency / event), portfolio (dev / designer / creative studio), redesign (preserve vs overhaul), editorial / blog.
2. **Vibe words** the user used — "minimalist", "calm", "Linear-style", "Awwwards", "brutalist", "premium consumer", "Apple-y", "playful", "serious B2B", "editorial", "agency-y", "glassy", "dark tech".
3. **Reference signals** — URLs they linked, screenshots they pasted, products they named, brands they're competing with.
4. **Audience** — B2B procurement panel vs. design-conscious consumer vs. recruiter scanning a portfolio. The audience picks the aesthetic, not your taste.
5. **Brand assets that already exist** — logo, color, type, photography. For redesigns, these are starting material, not optional input.
6. **Quiet constraints** — accessibility-first audiences, public-sector, regulated industries, trust-first commerce, kids' products. These constraints OVERRIDE aesthetic preference.

### 0.B Output a one-line "Design Read" before generating
Before any code, state in one line: **"Reading this as: <page kind> for <audience>, with a <vibe> language, leaning toward <design system or aesthetic family>."**

Example reads:
- *"Reading this as: B2B SaaS landing for technical buyers, with a Linear-style minimalist language, leaning toward Tailwind utilities + Geist + restrained motion."*
- *"Reading this as: solo designer portfolio for hiring managers, with an editorial / kinetic-type language, leaning toward native CSS + scroll-driven animation + custom typography."*
- *"Reading this as: redesign of a public-sector service site, with a trust-first language, leaning toward GOV.UK Frontend or USWDS."*

### 0.C If the brief is ambiguous, ask one question, do not guess
Ask exactly **one** clarifying question — never a multi-question dump — and only when the design read genuinely diverges. Example: *"Should this feel closer to Linear-clean or Awwwards-experimental?"*

If you can confidently infer from context, **do not ask**. Just declare the design read and proceed.

### 0.D Anti-Default Discipline
Do not default to: AI-purple gradients, centered hero over dark mesh, three equal feature cards, generic glassmorphism on everything, infinite-loop micro-animations everywhere, Inter + slate-900. These are the LLM defaults. Reach past them deliberately based on the design read.

---

## 1. THE THREE DIALS (Core Configuration)

After the design read, set three dials. Every layout, motion, and density decision below is gated by these.

- **`DESIGN_VARIANCE: 8`** — 1 = Perfect Symmetry, 10 = Artsy Chaos
- **`MOTION_INTENSITY: 6`** — 1 = Static, 10 = Cinematic / Physics
- **`VISUAL_DENSITY: 4`** — 1 = Art Gallery / Airy, 10 = Cockpit / Packed Data

**Baseline:** `8 / 6 / 4`. Use these unless the design read overrides them. Do not ask the user to edit this file — overrides happen conversationally.

### 1.A Dial Inference (design read → dial values)
| Signal | VARIANCE | MOTION | DENSITY |
|--------|----------|--------|---------|
| "minimalist / clean / calm / editorial / Linear-style" | 5-6 | 3-4 | 2-3 |
| "premium consumer / Apple-y / luxury / brand" | 7-8 | 5-7 | 3-4 |
| "playful / wild / Dribbble / Awwwards / experimental / agency" | 9-10 | 8-10 | 3-4 |
| "landing page / portfolio / marketing site (default)" | 7-9 | 6-8 | 3-5 |
| "trust-first / public-sector / regulated / accessibility-critical" | 3-4 | 2-3 | 4-5 |
| "redesign - preserve" | match existing | +1 | match existing |
| "redesign - overhaul" | +2 | +2 | match existing |

### 1.B Use-Case Presets
| Use case | VARIANCE | MOTION | DENSITY |
|----------|----------|--------|---------|
| Landing (SaaS, mainstream) | 7 | 6 | 4 |
| Landing (Agency / creative) | 9 | 8 | 3 |
| Landing (Premium consumer) | 7 | 6 | 3 |
| Portfolio (Designer / studio) | 8 | 7 | 3 |
| Portfolio (Developer) | 6 | 5 | 4 |
| Editorial / Blog | 6 | 4 | 3 |
| Public-sector service | 3 | 2 | 5 |
| Redesign - preserve | match | match+1 | match |
| Redesign - overhaul | +2 | +2 | match |

---

## 2. LAYOUT & COMPOSITION

Rules gated by `DESIGN_VARIANCE`.

### 2.A Hero Section (VARIANCE-dependent)

| VARIANCE | Hero layout |
|----------|-------------|
| 1-4 | Centered headline + sub + CTA. Safe. Single-column. |
| 5-7 | Split hero (text left, visual right) or asymmetrical text with a staggered CTA row. |
| 8-10 | Full-bleed visual, floating headline with offset, or deconstructed layout (headline breaks across lines, CTA outside the flow). |

### 2.B Section Rhythm

- **VARIANCE 1-4:** Every section is full-width, predictable top/bottom padding. Sections stack.
- **VARIANCE 5-7:** Alternating full / wide / contained widths. Occasional overlap or offset.
- **VARIANCE 8-10:** Mixed grid systems within the same page. Some sections break the grid entirely. Intentional white space as a design element.

### 2.C Grid Choice

- Prefer **CSS Grid** over flexbox for page-level layout.
- Only use **Bootstrap's 12-column grid** when the project explicitly uses Bootstrap. For everything else, use CSS Grid with custom column tracks (`grid-template-columns: 1fr 1fr;` or `repeat(auto-fit, minmax(300px, 1fr))`).
- **Do not** center everything. Intentional asymmetry signals maturity.

### 2.D Spacing

- Use a spacing scale (4/8/12/16/20/24/32/40/48/64/80/96/128px).
- **Section padding:** min 80px top/bottom for hero, 64px for inner sections, 48px for tight content.
- **Card padding:** 24-32px minimum. Never 16px.
- **Gap between columns:** minimum 24px, prefer 32-48px.
- White space is a premium signal. **Do not** fill every gap.

---

## 3. TYPOGRAPHY

### 3.A Typeface Selection

Pick typefaces that fit the design read, not your favorites:

| Design read | Headings | Body |
|-------------|----------|------|
| Editorial / premium | Serif (Playfair, Cormorant, Instrument Serif) | Clean sans (Inter, Satoshi) |
| Tech / B2B | Geometric sans (Geist, Space Grotesk, Plus Jakarta) | Same or lighter weight |
| Creative / agency | Display (Cabinet Grotesk, Integral CF, migra) | Neutral sans |
| Minimal / calm | Light weight sans (Inter Light, Satoshi Light) | Same, 300-400 weight |
| Trust / public | Humanist (Public Sans, Source Sans) | Same |

### 3.B Hierarchy

- **H1:** 56-80px (desktop), fluid via `clamp()`
- **H2:** 36-48px
- **H3:** 24-32px
- **Body:** 16-18px
- **Small / meta:** 13-14px
- **Line height:** 1.1 for headings, 1.5-1.6 for body
- **Letter spacing:** -0.02em for large headings (above 48px), 0 for body

### 3.C Rules

- **Max line length:** 65-75 characters for body text. Use `ch` units: `max-width: 65ch`.
- **Never** justify body text on the web. Left-align.
- Use `font-display: swap` for web fonts.
- **Do not** use more than 2 typefaces per page.
- **Do not** use system-ui as a design choice — it signals "no effort."
- Fluid type via `clamp()` is mandatory: `font-size: clamp(1.125rem, 1rem + 1vw, 1.375rem)`.

---

## 4. COLOR

### 4.A Palette Construction

| Design read | Palette approach |
|-------------|------------------|
| Tech / B2B | Neutral-heavy (slate / zinc / gray) + 1 accent. Dark mode first. |
| Premium / consumer | Warm neutrals (stone / neutral) + saturated accent. Light mode first. |
| Creative / agency | Bold accent-driven. High chroma. Dark mode with vibrant accents. |
| Editorial | Muted, desaturated. Off-white backgrounds, charcoal text. |
| Trust / public | High contrast. Accessible blues, greens. Minimal accent. |

### 4.B Rules

- **Minimum contrast ratio:** 4.5:1 for body text (WCAG AA). 3:1 for large text (18px+ bold or 24px+ regular).
- **Dark mode is not inverted light mode.** Build a separate dark palette.
- **Accent color:** 1 primary, 1 secondary max. Do not use more.
- **Surfaces:** Use at least 3 surface levels (background, card, elevated) with subtle luminance shifts.
- **Borders:** Subtle (`border-color: hsl(var(--border))`). Never use black borders.
- **Gradients:** Only when the design read explicitly calls for it (agency, creative). Never default to purple-blue mesh gradients.

---

## 5. MOTION

Rules gated by `MOTION_INTENSITY`.

### 5.A Animation by Intensity

| MOTION | Approach |
|--------|----------|
| 1-3 | Hover effects on interactive elements only. No entrance animations. |
| 4-6 | Fade-in-up on section entrance (200-400ms, 20-40px offset). Smooth hover transitions. |
| 7-8 | Staggered entrance animations. Scroll-triggered reveals. Parallax on hero. |
| 9-10 | Full cinematic: GSAP timelines, magnetic buttons, cursor followers, scroll-driven animations. |

### 5.B Implementation

- Prefer **CSS transitions and animations** for MOTION 1-6.
- Use **Intersection Observer** for scroll-triggered reveals (no libraries needed).
- Use **GSAP** or **Framer Motion** only for MOTION 8+. Announce the choice.
- **Animations must respect `prefers-reduced-motion`.** Apply `@media (prefers-reduced-motion: reduce) { * { animation-duration: 0.01ms !important; } }` or use `animation: none`.
- **Transition timing:** 200-400ms ease-out. Never 500ms+ for UI transitions.
- **Stagger:** 80-120ms between items. Never 300ms+.
- **Easing:** Prefer custom cubic-bezier over built-in keywords. `cubic-bezier(0.16, 1, 0.3, 1)` is a good default overshoot for premium feel.

### 5.C What NOT to animate

- Page background / body
- Entire sections entering at once (stagger children instead)
- Text that the user is reading (wait until viewport enters, then play fast)
- Social media icons (they're utility, not decoration)

---

## 6. IMAGES & MEDIA

### 6.A Image Selection

- Prefer **authentic photography** over illustrations for real companies.
- Use **illustration** for abstract concepts, onboarding, or brands with illustration systems.
- **No stock-photo clichés:** handshake, staged office, diverse-stock-photo-lineup. If stock is the only option, crop tight, desaturate slightly, or use duotone overlay.
- **Image aspect ratios:** 16/9, 4/3, 3/2, or 1/1. Never 4/5 or vertical for hero images unless explicitly mobile-first.

### 6.B Image Handling

- Use `<picture>` with WebP + AVIF sources.
- Set explicit `width` and `height` to prevent CLS.
- `loading="lazy"` for below-fold images.
- `fetchpriority="high"` for the hero image.
- Background images should have a fallback background-color.

### 6.C Icons

- Prefer **Lucide** (open-source, consistent stroke) or heroicons.
- Use **SVG inline** or sprite sheet. Never font icons (they fail on system font overrides).
- Icon size: 20-24px for inline, 32-48px for feature cards.
- All icons must have `aria-hidden="true"` unless they're the sole content of a link/button.

---

## 7. DESIGN SYSTEMS

When redesigning or building for a known product, use the matching design system:

| Product | System |
|---------|--------|
| Linear | Custom — Geist type, warm gray surfaces, blue accent, subtle shadows |
| Vercel | Geist (official) |
| Stripe | Custom — rounded sans, purple accent, warm gray, card-heavy |
| Apple | SF Pro (or Inter), white/gray surfaces, minimal chrome |
| Notion | Custom — mono icons, sans headings, limited palette, extremely restrained |
| Tailwind docs | Tailwind UI / Catalyst |
| Shadcn UI | Radix primitives + Tailwind, CSS variables, customizable themes |
| Public sector | GOV.UK Frontend, USWDS, or CNIG (Canada) |
| GitHub | Primer (official design system) |

If the brief references a product, you MUST use its design system (or a close equivalent) unless the user explicitly says otherwise.

### 7.A Design Token Repositories

When design iteration isn't working (user says "still ugly", "no wow factor"), do NOT continue ad-hoc CSS tweaks. Instead, study DESIGN.md token files:

- **`popular-web-designs`** skill has 54 pre-extracted templates in `templates/` — load with `skill_view(name="popular-web-designs", file_path="templates/<site>.md")`
- **`VoltAgent/awesome-design-md`** repo at `https://github.com/VoltAgent/awesome-design-md` — clone, then read `design-md/<company>/DESIGN.md` for token-level design specs (colors, typography hierarchy, spacing scales, border radii, shadows, component specs)

Pipeline: pick 3-6 relevant systems → extract tokens into comparison table → pick best token per dimension → apply as CSS custom properties → build components from tokens. This reliably produces 8+/10 results; ad-hoc iteration rarely exceeds 4/10.

For a worked example of this pipeline (dark dashboard synthesized from Resend + Vercel + Superhuman + Sentry + Warp + Stripe), see `references/token-synthesis-method.md`.

For applying the same pipeline to slide decks (fixed-canvas presentations with alternating backgrounds, grid textures, navigation controls), see `references/slide-deck-token-synthesis.md`.

---

## 8. FRAMEWORK CHOICE

### 8.A Framework Recommendation

| Project type | Recommended |
|--------------|-------------|
| Static landing / portfolio | Plain HTML + CSS (or Astro). Do not default to React. |
| Marketing site with dynamic content | Next.js or Astro |
| SaaS app / dashboard | Next.js + Tailwind + shadcn/ui or similar |
| Existing codebase | Match the project's framework. Do not change it. |

### 8.B CSS Approach

| Approach | When |
|----------|------|
| Tailwind | Default for utility-first. Preferred for most projects. |
| CSS Modules | When the project already uses them. Good for custom designs. |
| CSS-in-JS (styled-components, etc.) | Only match existing project conventions. Do not introduce new ones. |
| Plain CSS | Fine for small pages (< 3 sections). Use modern features (nesting, layers, container queries). |

**Tailwind specific rules:**
- Use CSS variables for theme: `--color-accent: ...;` not magic Tailwind class names.
- Prefer `@apply` for repeated patterns, but don't over-abstract.
- Use `tailwindcss/animate` for MOTION ≥ 6.

---

## 9. ACCESSIBILITY (Non-Negotiable)

These are not suggestions. These are hard requirements.

- All interactive elements must be focusable and have visible focus indicators (not `outline: none` without replacement).
- Color is never the sole differentiator (add icons, patterns, or text labels).
- Form inputs must have associated `<label>` elements.
- Skip-to-content link at the top of every page.
- Use semantic HTML: `<nav>`, `<main>`, `<section>`, `<article>`, `<aside>`, `<footer>`.
- Heading hierarchy must be sequential (h1 → h2 → h3). No skipping.
- Alt text on all images. Decorative images get `alt=""`.
- `aria-current="page"` on active navigation links.
- Touch targets minimum 44x44px.
- Test with prefers-reduced-motion, prefers-color-scheme, and increased-contrast.

---

## 10. CODE QUALITY

### 10.A SEO

- Proper `<title>` and `<meta name="description">` per page.
- Open Graph: `og:title`, `og:description`, `og:image`, `og:url`.
- Twitter cards: `twitter:card`, `twitter:title`, `twitter:description`, `twitter:image`.
- Semantic structure for search engines.
- Structured data (JSON-LD) for relevant pages: `WebSite`, `WebPage`, `Organization`, `Product`.

### 10.B Performance

- Lighthouse score targets: 90+ Performance, 95+ Accessibility, 90+ Best Practices, 90+ SEO.
- Bundle size awareness: mention if a library adds >30KB.
- No render-blocking resources above the fold (inline critical CSS).
- Font subsetting or `unicode-range`.
- `font-display: swap`.
- No jank from layout shifts (set width/height on images, videos, embeds).

### 10.C Shipping Standards

- **NO placeholder content.** Every `Lorem ipsum`, `[Your Name]`, `#`, or empty div is a failed deliverable.
- **NO commented-out code** in the final output.
- **NO console.log** in production code.
- **Responsive** is not optional. Every page must work at 320px, 768px, 1024px, and 1440px+. Use `@container` queries where applicable.
- **Final output is one command away from deploy.** No build errors, missing dependencies, or broken imports.

---

## 11. REDESIGN PROTOCOL

When the task is a redesign (not greenfield):

1. **Audit the existing UI first.** Run through these lenses:
   - Layout — is the grid consistent? Is content well-spaced?
   - Typography — is there a clear hierarchy? Are font sizes coherent?
   - Color — is the palette harmonious? Is contrast sufficient?
   - Motion — does animation serve a purpose or is it decoration?
   - Responsive — does it work across breakpoints?
   - Accessibility — passes the basics from Section 9?
2. **Study design system tokens before iterating.** When stuck (user rejects as "ugly" or "no wow factor"), do NOT continue ad-hoc CSS tweaks. Use the pipeline in Section 7.A: clone/load DESIGN.md token files from 3-6 reference systems, extract tokens, synthesize a new palette, then rebuild from CSS custom properties. Tokens-first always beats iteration.
3. **State what you're preserving.** Not everything needs to change.
4. **State what you're changing and why.** Link each change to a design token or principle — not to "it looks better."
5. **Do not** rebuild from scratch unless the codebase is unmaintainable. Refactor in place.
6. **Preserve brand assets** unless the user explicitly asks for a rebrand.

---

## 12. PRE-FLIGHT CHECKLIST

Before you output a single line of code, verify:

- [ ] Did I read the brief and infer the design direction (Section 0)?
- [ ] Did I set the three dials based on the design read (Section 1)?
- [ ] Did I choose the right design system or framework (Sections 7-8)?
- [ ] Am I reaching past the LLM defaults (Section 0.D)?
- [ ] Is this actually what the user asked for?
- [ ] Do I need to ask a single clarifying question?

After shipping:

- [ ] No placeholder content
- [ ] Accessible (Section 9)
- [ ] Responsive at all breakpoints
- [ ] Lighthouse scores pass (Section 10.B)
- [ ] No commented-out code or console.log
- [ ] One deploy command away from production
