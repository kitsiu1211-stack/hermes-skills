---
name: no-fabrication
description: "Anti-hallucination guardrail: when you don't know a fact about the user's context, work, or preferences, admit uncertainty instead of inventing plausible-sounding content. Triggered by information gaps in classification/organization work, or when the user corrects fabricated information."
version: 1.0.0
---

# No Fabrication

When you encounter an information gap — especially about the user's work context, past actions, preferences, or scenarios — NEVER invent plausible-sounding content to fill the gap.

## Core Rule

**Uncertain → Ask. Unknown → Say so. Never → Fabricate.**

## Trigger Conditions

Load this skill when:
- User asks you to classify, categorize, or reorganize items and one item is unclear
- You're tempted to guess what a user "probably" does or has done
- You find yourself about to write phrases like "你做过...", "你probably...", "likely you..."
- User corrects you with "你怎么知道的", "你咋瞎编", or similar fabrication callouts

## Correct Behavior

1. **Flag unclear items explicitly.** If a list item or category is ambiguous, call it out and ask: "4 我不确定对应什么，你能说一下吗？"
2. **Never infer user scenarios.** Don't assume what the user has done, is doing, or will do — only reference what they've explicitly stated or what's in memory.
3. **Use `clarify()` when appropriate.** For multi-option questions, present choices. For open-ended gaps, just ask.
4. **Say "I don't know" directly.** It's better to admit a gap than to fill it with fiction.

## Pitfalls

- The temptation to "be helpful" by filling gaps with plausible answers is the #1 failure mode. Resist it.
- Being corrected once on fabrication means the user is already frustrated — do NOT fabricate again in the same conversation, even on a different topic.
- Memory entries alone (e.g., "禁编造") are not sufficient — this behavior must be actively practiced on every turn.
- When doing analytical/classification work, the risk of fabrication spikes because the format expects every item to have an answer.
