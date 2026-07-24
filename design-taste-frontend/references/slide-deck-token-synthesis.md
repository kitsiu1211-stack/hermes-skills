# Token Synthesis for Slide Decks

Applying the Section 7.A pipeline (from parent SKILL.md) to presentation slide decks
rather than dashboards or landing pages.

## Slide Deck vs. Web Page: Key Differences

| Constraint | Web Page | Slide Deck |
|------------|----------|------------|
| Canvas | Fluid viewport, scrolls | Fixed ratio (16:9), no scroll |
| Background | Usually one per page | Alternating dark/light for rhythm |
| Navigation | Scroll, links, tabs | Arrow keys, swipe, wheel — forward/back only |
| Content density | Can scroll for more | Must fit in one viewport — tighter |
| Interactivity | Links, hover, forms | Minimal — prev/next, maybe reveal animations |
| Typography | Body 16-18px, headings scale | Display-heavy, 40-84px headlines |
| Depth | Shadows, sticky elements | Cards with subtle elevation, grid textures |

## Pipeline Adaptation

### Step 1: Select Systems (3-4 is enough for slide decks)

Pick systems that inform different aspects:
- **Atmosphere system** — for background treatment (dark/light canvas, grid texture)
- **Depth system** — for card elevation on a fixed canvas (shadow layering)
- **Accent system** — for the single brand color that carries the deck
- **Typography system** — for display headline punch (tracking, weight, serif/sans)

Example (this session): Superhuman (atmosphere + warmth) × Stripe (shadow depth) × Linear (translucent borders, hover states)

### Step 2: Tokens to Extract (Slide Deck Specific)

Focus on these token classes, skip ones irrelevant to fixed-canvas presentations:
- ✅ Canvas colors (dark + light alternating)
- ✅ Surface hierarchy (cards, callouts, alert blocks)
- ✅ Accent color (one strong brand accent)
- ✅ Border treatment (translucent for dark slides, shadow-as-border for light)
- ✅ Display typography (size, tracking, line-height, weight)
- ✅ Card padding (more generous than web — 28-32px minimum)
- ✅ Shadow layering (subtle on fixed canvas — avoid heavy floating)
- ❌ Responsive breakpoints (irrelevant for fixed 1920×1080)
- ❌ Scroll behavior, sticky elements
- ❌ Form inputs, complex interactivity

### Step 3: Slide Deck Color Rhythm

Most successful slide decks alternate backgrounds:
- **Odd slides (dark):** Deep navy/base color, grid texture, warm ink text
- **Even slides (light):** Cream/off-white, shadow-as-border cards, dark ink
- **Accent:** Same color on both backgrounds for cohesion — adjust opacity/brightness

The alternating rhythm prevents monotony without introducing arbitrary color.

### Step 4: Navigation Controls

Slide deck controls sit in a fixed position (usually bottom center). Treat them as
their own micro-component:
- Translucent backdrop with blur (backdrop-filter) to float over slide content
- Thin border matching the deck's accent
- Mono font for page counter
- Subtle hover lift (1-2px translateY) for buttons
- Divider lines between prev/page-num/next for structure

### Step 5: Grid Texture on Dark Slides

Dark slide backgrounds benefit from a subtle grid pattern to add atmospheric depth
without competing with content:
- `rgba(255,255,255,0.018)` grid lines at 96px intervals
- Radial gradient mask (`mask-image: radial-gradient(...)`) for vignette effect
- Keeps center focused while edges fade to solid color

## Common Slide Deck Pitfalls

1. **Card borders too visible** — on dark slides, use `rgba(255,255,255,0.06)` not solid colors. Translucent borders breathe.
2. **Stat cards as border-top only** — full bordered cards with rounded corners and subtle shadows look much more polished.
3. **Text arrows (→) as flow connectors** — replace with SVG arrow icons for precision.
4. **Muted gold/bronze accents** — slightly boost saturation. #C8A870 → #D4A853 makes a noticeable difference.
5. **Uniform grid texture** — add a radial mask so the grid fades at edges, creating natural focus on center content.
6. **No hover states** — even passive slides benefit from subtle hover effects (border highlight, slight bg shift) — it signals polish.

## Worked Example: Meeting Listen v5 Deck

| Dimension | Before | After | From |
|-----------|--------|-------|------|
| Navy background | #1C2644 | #141b2d (deeper) | Linear near-black |
| Cream background | #F0ECE3 | #F4F0E6 (warmer) | Superhuman warm cream |
| Gold accent | #C8A870 (mustard) | #D4A853 (brighter) | Stripe precision |
| Dark borders | #2E3D5C solid | rgba(255,255,255,0.06) | Linear translucent |
| Cream borders | #CAC4B4 solid | shadow-as-border | Vercel technique |
| Card padding | ~2.5vh | 32px | Stripe/Superhuman |
| Stat cards | border-top only | full bordered + shadows | Stripe card depth |
| Flow arrows | text "→" | SVG arrow icons | — |
| Grid mask | none | radial gradient vignette | — |
| Navigation | simple outline buttons | backdrop-blur pill + dividers | Linear precision |
| Display tracking | default | -0.025em (cover) / -0.012em (headlines) | Vercel compression |

Result: 8-slide presentation deck, dark/cream alternating, keyboard/swipe/wheel navigation.
