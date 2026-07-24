# Hook Enforcement Pattern for Design Systems

## The Problem

LLM-level design constraints (prompts, skill instructions, "please use Apple colors") fail at scale:

- The LLM forgets or ignores soft constraints after 3+ pages
- Each page generation is an independent decision — no shared state
- "苹果风格" in a prompt means different things on different pages
- AI coding agents (kimi code, trae, claude code) have zero design context

## The Hook Solution

**Move design rules from the LLM layer to the framework layer.** The LLM can still choose *which* token to use, but it cannot invent values outside the token set.

### Three enforcement tiers

| Tier | What | Where | LLM's role |
|------|------|-------|------------|
| **Hard Hook** | Token file (CSS variables, Swift constants, JSON) | Compiled/injected before every generation | Chooses which token, CANNOT invent new values |
| **Verify Hook** | Stylelint / SwiftLint / custom validator | Runs on output, rejects violations | Must pass or retry |
| **Converge Hook** | Neat-Freak audit | Post-generation, checks all visual facts point to ONE source | Fixes duplication |

### Concrete implementation

**For web (Hermes generating HTML):**
1. Load `apple-tokens.css` before writing any CSS
2. All `color`, `spacing`, `radius`, `font` values MUST be `var(--apple-*)` references
3. Hardcoded values rejected — no `#333`, no `padding: 15px`, no `font-size: 16px`

**For native (kimi code generating Swift):**
1. Create `Theme.swift` with all token values as static constants
2. All views reference `Theme.spacing.md` not `16.0`
3. All colors reference `Theme.Color.background` not `Color(white: 0.95)`

**For coding agents (trae, claude code):**
1. Place token file in repo root (`design-tokens.css` or `Theme.swift`)
2. CI runs validator — any hardcoded value fails the build
3. Agent prompt: "All styles must reference design tokens. Hardcoded values will be rejected by CI."

### Anti-patterns (things that LOOK like enforcement but aren't)

- ❌ "Remember to use Apple colors" in a skill prompt → LLM will forget
- ❌ "The design should feel like iOS" → too vague, different every time
- ❌ Writing token values inline in component code → duplicates the truth
- ✅ Token file is `@import`-ed, components only reference variables
- ✅ CI validates no raw hex codes or magic numbers in CSS/Swift

## Why This Works

The article's core insight: "AI generates unstable pages because it starts from pages, not from a system."

Hook enforcement inverts this: the system (token file) is loaded FIRST, and every page is generated FROM the system. The LLM cannot "forget" the system because the framework won't let it output without referencing it.
