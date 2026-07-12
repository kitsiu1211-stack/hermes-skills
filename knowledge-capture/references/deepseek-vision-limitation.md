# DeepSeek API Vision Support — Investigation (2026.5.31)

## Finding: DeepSeek V4 API Does NOT Support Vision

**API endpoint tested:** `https://api.deepseek.com/v1/chat/completions`

### Models tested
| Model | Vision? | Error |
|-------|---------|-------|
| `deepseek-v4-pro` | ❌ | `unknown variant 'image_url', expected 'text'` |
| `deepseek-v4-flash` | ❌ | `unknown variant 'image_url', expected 'text'` |
| `deepseek-chat` (deprecated 2026/07/24) | ❌ | `unknown variant 'image_url', expected 'text'` |
| `deepseek-vl2` | ❌ | Not a valid model name on this API |

### API /models endpoint
Only 2 models listed: `deepseek-v4-flash`, `deepseek-v4-pro`. No vision models.

### Official Docs (api-docs.deepseek.com)
Features listed: JSON Output, Tool Calls, Chat Prefix Completion, FIM Completion.
No Vision/Multimodal/Image section in sidebar or guides.

### DeepSeek-VL2
DeepSeek has a vision-language research model (DeepSeek-VL2) but it's:
- Open-source on GitHub (github.com/deepseek-ai/DeepSeek-VL2)
- NOT available through the cloud API
- Requires local deployment

## Workarounds for Vision in Hermes

When using DeepSeek as primary provider and you need vision:

1. Auxiliary vision provider — Hermes supports separate vision model:
   `hermes config set auxiliary.vision.provider gemini`
   `hermes config set auxiliary.vision.model gemini-2.5-flash`

2. OpenRouter — Single key for both DeepSeek (text) + any vision model

3. Gemini free tier — 15 RPM, generous quota for image analysis
