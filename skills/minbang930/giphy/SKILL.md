---
name: giphy-gif
description: Search and send contextual GIFs from Giphy in Discord conversations. Use when the user wants to react with a GIF, express emotions with a GIF, or when you determine a GIF would enhance the conversation (celebrations, reactions, emotions, humor). Triggers on requests like "send a GIF", "show me a GIF", or when context suggests a GIF reaction would be appropriate.
---

# Giphy GIF Search

This skill enables searching for and sending contextually appropriate GIFs from Giphy's library in Discord conversations.

## Setup

Before using this skill, you need a Giphy API key:

1. Go to [Giphy Developers Dashboard](https://developers.giphy.com/dashboard/)
2. Sign up or log in
3. Create a new app (select "API" not "SDK")
4. Copy your API key
5. Set the environment variable: `export GIPHY_API_KEY="your-api-key-here"`

Alternatively, add it to your OpenClaw config or shell profile for persistence.

## Usage

### Search for a GIF

Use the `search_gif.py` script to find relevant GIFs:

```bash
python3 scripts/search_gif.py <search_query>
```

Example:
```bash
python3 scripts/search_gif.py excited
python3 scripts/search_gif.py happy dance
python3 scripts/search_gif.py crying
```

The script returns a Giphy URL that Discord will automatically embed as a GIF.

### Sending GIFs in Discord

When a GIF URL is obtained:

1. Simply send the URL in the Discord channel
2. Discord will automatically embed the GIF
3. The GIF will display inline in the conversation

Example workflow:
```python
# Search for a GIF
gif_url = exec("python3 scripts/search_gif.py excited")

# Send it to Discord (current channel)
message(action="send", message=gif_url)
```

## When to Use

Send GIFs in these situations:

- **User requests**: "send me a GIF", "show me something funny"
- **Celebrations**: achievements, good news, milestones
- **Reactions**: surprise, shock, agreement, disagreement
- **Emotions**: happy, sad, excited, confused, thinking
- **Humor**: to lighten the mood or add comedic timing
- **Emphasis**: to reinforce a point with visual impact

## Best Practices

1. **Match the context**: Choose search terms that match the conversation tone
2. **Keep it appropriate**: The script uses 'g' rating (safe for work) by default
3. **Don't overuse**: GIFs are most effective when used sparingly
4. **Search terms matter**: Use specific, descriptive terms for better results
   - Good: "celebration dance", "facepalm reaction", "mind blown"
   - Poor: "thing", "stuff", "it"

## Common Search Terms

- Reactions: `thumbs up`, `facepalm`, `eye roll`, `shocked`, `confused`
- Emotions: `excited`, `happy`, `sad`, `angry`, `love`, `crying`
- Actions: `dance`, `clap`, `wave`, `thinking`, `working`
- Celebrations: `party`, `celebrate`, `success`, `winner`
- Humor: `funny`, `lol`, `wtf`, `awkward`, `fail`

## Technical Details

- API: Giphy v1
- Rate limits: 
  - Beta keys: 100 requests per hour
  - Production keys: Higher limits available
- Response format: Giphy page URLs (Discord auto-embeds)
- Language: Python 3 (no external dependencies beyond stdlib)
- Default rating: 'g' (safe for work)

## API Key Tiers

- **Beta Key** (Free): 100 requests/hour, good for personal use
- **Production Key**: Higher limits, requires approval for specific use cases

Get started with a free beta key at [developers.giphy.com](https://developers.giphy.com/).
