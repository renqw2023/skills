# OpenCode Zen Free Models Reference

## Complete Model List

### MiniMax M2.1 Free
- **ID:** `opencode/minimax-m2.1-free`
- **Provider:** MiniMax
- **Best for:** Complex coding tasks, reasoning, multi-step workflows
- **Context:** Large context window
- **Strengths:** Strong coding capability, good reasoning

### Kimi K2.5 Free
- **ID:** `opencode/kimi-k2.5-free`
- **Provider:** Moonshot AI (Kimi)
- **Best for:** General purpose, balanced performance
- **Context:** Large context window
- **Strengths:** Good all-around model, reliable responses

### GLM 4.7 Free
- **ID:** `opencode/glm-4.7-free`
- **Provider:** Zhipu AI (GLM)
- **Best for:** Multilingual tasks, alternative provider fallback
- **Context:** Medium-large context
- **Strengths:** Multilingual support, different provider ecosystem

### GPT 5 Nano
- **ID:** `opencode/gpt-5-nano`
- **Provider:** OpenAI
- **Best for:** Simple tasks, high-frequency operations, quick checks
- **Context:** Smaller context window
- **Strengths:** Fastest responses, lowest cost

## Provider Information

### MiniMax
- API: `https://api.minimax.io/anthropic`
- Documentation: OpenCode Zen docs

### Moonshot AI (Kimi)
- Known for: Kimi long-context model
- Strong in: Document understanding, conversation

### Zhipu AI (GLM)
- Chinese AI company
- Focus: Multilingual and Chinese language tasks

### OpenAI
- Established provider
- GPT 5 Nano: Lightweight, fast variant

## Rate Limits by Model

| Model | Typical Rate Limits | Notes |
|-------|--------------------|-------|
| MiniMax M2.1 Free | Medium | Most popular free model |
| Kimi K2.5 Free | Medium-High | Good availability |
| GLM 4.7 Free | Medium | Alternative option |
| GPT 5 Nano | High | Generous limits |

## Performance Comparison

| Model | Speed | Capability | Cost |
|-------|-------|------------|------|
| MiniMax M2.1 Free | Medium | Highest | Free |
| Kimi K2.5 Free | Medium-High | High | Free |
| GLM 4.7 Free | Medium | Medium-High | Free |
| GPT 5 Nano | Fastest | Medium | Free |

## Configuration Tips

### For High-Volume Tasks
```
Primary: MiniMax M2.1 Free
Fallbacks: Kimi K2.5 Free → GLM 4.7 Free → GPT 5 Nano
```

### For Critical Tasks
```
Primary: MiniMax M2.1 Free
Fallbacks: Kimi K2.5 Free → GLM 4.7 Free
(Remove GPT 5 Nano for higher quality)
```

### For Cost-Sensitive Setups
```
Primary: GPT 5 Nano
Fallbacks: Kimi K2.5 Free → MiniMax M2.1 Free
(Use cheapest first, upgrade only if needed)
```

## Error Handling

### Common Errors and Responses

1. **Rate Limit (429)**
   - Action: Try next fallback immediately
   - Prevention: More fallbacks configured

2. **Auth Error (401/403)**
   - Action: Try next fallback
   - Check: API keys configured in OpenCode

3. **Timeout (408/504)**
   - Action: Try next fallback
   - Prevention: Check network, reduce request size

4. **Model Not Found (404)**
   - Action: Remove from fallback chain
   - Check: Model ID and availability

### Health Check Commands

```bash
# Check OpenCode models available
opencode models

# Check current configuration
openclaw config.get

# Verify gateway health
openclaw health
```

## Model Aliases

Set friendly names in configuration:

```json
"models": {
  "opencode/minimax-m2.1-free": { "alias": "MiniMax" },
  "opencode/kimi-k2.5-free": { "alias": "Kimi" },
  "opencode/glm-4.7-free": { "alias": "GLM" },
  "opencode/gpt-5-nano": { "alias": "Nano" }
}
```

## Migration from OpenRouter FreeRide

If migrating from the OpenRouter FreeRide skill:

**Before:**
```json
"model": {
  "primary": "openrouter/qwen/qwen3-coder:free",
  "fallbacks": ["openrouter/free:free"]
}
```

**After (OpenCode Zen):**
```json
"model": {
  "primary": "opencode/minimax-m2.1-free",
  "fallbacks": ["opencode/kimi-k2.5-free", "opencode/glm-4.7-free", "opencode/gpt-5-nano"]
}
```

**Key differences:**
- No API key needed (uses OpenCode Zen credentials)
- Multiple high-quality free options
- Fallback to GPT 5 Nano available
- No router overhead
