---
name: yt-to-blog
description: >
  Transform YouTube videos or channels into long-form blog posts and publish to Substack via browser
  automation (Substack has no API). Fetches transcripts, analyzes source material, crafts polished
  essays in a configurable author voice, and posts drafts directly to Substack. Use when asked to:
  write a blog post from a YouTube video, turn a video into a Substack article, draft a blog from
  a transcript, "write this up", "make a post from this video", bulk-fetch channel transcripts,
  or any video-to-written-content request. Also works for podcast-to-blog and lecture-to-blog.
---

# YT-to-Blog

YouTube → transcript → blog post → Substack draft. End-to-end, no API needed.

## First-Time Setup

Before using this skill, complete these one-time steps:

### 1. Install Dependencies

```bash
brew install steipete/tap/summarize   # Transcript extraction (primary)
brew install yt-dlp                    # Channel listing + fallback
pip3 install youtube-transcript-api    # Bulk transcript fetch
```

### 2. Configure Your Substack

Create `references/config.md` in this skill's directory with your Substack details:

```markdown
# Substack Configuration

- **URL:** https://YOURNAME.substack.com
- **Editor URL:** https://YOURNAME.substack.com/publish/post
- **Publication name:** Your Publication Name
```

Replace `YOURNAME` with your actual Substack subdomain.

### 3. Log Into Substack in OpenClaw Browser

Substack has no API — posting requires browser automation, which means OpenClaw's managed browser must be logged into your Substack account.

```
1. Open OpenClaw managed browser: use browser tool with profile="openclaw"
2. Navigate to https://substack.com/sign-in
3. Log in with your Substack credentials
4. Verify you can access your dashboard at https://YOURNAME.substack.com/publish
```

The browser session persists across OpenClaw restarts. You only need to do this once (unless cookies expire).

### 4. Create Your Voice Guide

The skill writes in YOUR voice. Create `references/voice-guide.md` with your writing style. See `references/voice-guide-template.md` for the template.

**Fastest method:** Paste 2-3 of your best existing blog posts and ask your agent:
> "Read these posts and create a voice guide for my writing style. Save it to the yt-to-blog skill's references/voice-guide.md"

## Quick Start

Once setup is complete:

```
User: "Write a blog post from this video: https://youtu.be/XXXXX"
Agent: Fetches transcript → analyzes → drafts post → opens Substack → saves draft

User: "Pull the last 20 videos from this channel and write a post from the best material"
Agent: Bulk-fetches → scans topics → asks which thread → drafts → posts

User: "Just get me the transcript from this video"
Agent: Fetches and returns raw transcript text
```

## Workflow

### Step 1: Fetch Transcripts

**Single video** (preferred):
```bash
summarize --extract "YOUTUBE_URL" > /tmp/transcript.txt
```
Handles captions, auto-generated subs, edge cases. Output includes duration and word count.

**Bulk/channel mode**:
```bash
python3 scripts/fetch_transcripts.py --channel "CHANNEL_URL" --count 20 --output /tmp/transcripts.json
python3 scripts/fetch_transcripts.py --video "URL1" --video "URL2"
```
Output: JSON array with `id`, `title`, `upload_date`, `transcript`, `url` per video.

**Additional context sourcing** — `summarize` also works on web pages, PDFs, and local files:
```bash
summarize "https://example.com/article"
summarize --extract "report.pdf"
```

### Step 1b: Scan & Select (Channel Mode)

When working from a channel with multiple transcripts:
1. Scan titles, dates, and first ~500 chars of each
2. Identify the strongest topic cluster
3. Ask the user which thread to write about (or auto-select)
4. Read full transcripts of only the selected 1-5 videos

### Step 2: Analyze Source Material

Before writing, extract:
- **Core thesis** — the single strongest argument or revelation
- **Key data points** — statistics, quotes, dates, names that anchor credibility
- **Narrative moments** — anecdotes, examples, scenes to dramatize
- **Source links** — URLs, studies, references mentioned (verify independently)
- **Missing context** — what does the reader need that the video assumed?

For multi-video posts: find the connective thread. Weave, don't summarize sequentially.

### Step 3: Draft the Post

Load `references/voice-guide.md` for the author's writing style. If no voice guide exists, ask the user to describe their voice or provide 2-3 sample posts to analyze.

#### Structure Template

1. **Cold open (1-3 paragraphs):** Scene-setting. Specific time, place, sensory details. Emotional hook before data.
2. **Thesis pivot (1 paragraph):** Connect scene to bigger story.
3. **Data body (5-15 paragraphs):** Alternate data and editorial. Each stat gets a punch line. Inline links. Subheadings only for major breaks. Include `[CHART: description]` placeholders where visualization helps.
4. **Callback (1-2 paragraphs):** Return to opening scene/metaphor.
5. **Closing (3-6 short paragraphs):** Escalating fragments. Final hammer line. Moral clarity, not hedging.

#### Writing Rules

- Vary sentence length dramatically — long data sentences, then one-word punches
- Em dashes for asides, not parentheses
- Sentence fragments for emphasis
- No bullet lists in the body — narrative flow only
- Link sources inline, don't footnote
- No "in conclusion" or "to summarize"
- Strong metaphors > abstract language
- Credit video sources naturally: "As [Name] put it in a recent interview..." with link
- Target: 1,500-3,000 words (match source depth)

### Step 4: Headlines

Generate 3-5 options with distinct strategies:
- **Contrast/irony:** "The Lights Are Still On, But Nobody's Shopping"
- **Revelation:** "New Study Reveals WHY..."
- **Moral framing:** "They Planned It: How..."
- **Anniversary/callback:** "Six Years Ago Today..."

Each with a one-line subtitle stating the thesis. Let the user pick.

### Step 5: Deliver as Markdown

```markdown
# Title
> Subtitle

Body paragraphs...

---
*Source: [Video Title](url)*
```

All source links inline. Image placeholders as `[IMAGE: description]`.

### Step 6: Post to Substack

Read the Substack URL from `references/config.md`. Use OpenClaw browser automation:

1. Open managed browser (`profile="openclaw"`)
2. Navigate to the editor URL (e.g. `https://YOURNAME.substack.com/publish/post`)
3. Click the title field (first large text area at top), type the title
4. Click the subtitle area (below title, lighter placeholder text), type the subtitle
5. Click the body area (main content region below subtitle)
6. Paste the post body — use clipboard: write markdown to a temp file, `pbcopy < /tmp/post.md`, then send Meta+v to the browser
7. Substack auto-saves as draft within seconds

**Known issues & workarounds:**
- Em dashes (`—`) garble as `,Äî` during clipboard paste → find/replace after paste, or type content directly for short posts
- Large posts may need a brief pause between paste and verification
- Always verify the draft at `https://YOURNAME.substack.com/publish` before publishing

**Publishing:** Author reviews and clicks Publish manually (recommended). For trusted pipelines, the Publish button can be automated too.

## Customization

### Voice Guide

The voice guide is what makes this skill produce YOUR writing, not generic AI slop. See `references/voice-guide-template.md` for the full template.

Key sections to fill in:
- **Tone** — How do you sound? (authoritative, casual, angry, witty, academic?)
- **Structure** — What's your typical post structure?
- **Sentence style** — Short and punchy? Long and flowing? Mixed?
- **What you DON'T do** — Hedge language? Bullet lists? Both-sides-ism?
- **Topics & themes** — What do you write about?
- **Constraints** — Factual standards, audience expectations, things to avoid

### Multiple Publications

For multiple Substacks, create separate configs and voice guides:
```
references/config-publication-a.md
references/config-publication-b.md
references/voice-publication-a.md
references/voice-publication-b.md
```

Tell the agent which publication when requesting a post.
