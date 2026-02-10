---
name: wordpress-mcp
description: Manage WordPress sites via MCP (Model Context Protocol) through AI Engine. Use for creating/editing posts, SEO analysis, analytics, media management, taxonomy operations, social media scheduling, multilingual content (Polylang), and any WordPress admin task. Requires AI Engine plugin (free) with MCP Server enabled. Also use when asked about WordPress site management, content workflows, or WP-related tasks.
---

# WordPress MCP

Manage WordPress sites through AI Engine's MCP Server. AI Engine is a free WordPress plugin that exposes a comprehensive MCP interface for content, SEO, analytics, media, users, and more.

## Setup

The user needs:
1. **AI Engine** plugin installed (free: https://wordpress.org/plugins/ai-engine/)
2. MCP Server enabled in AI Engine → Settings → MCP
3. A **Bearer Token** set in MCP settings

Connection details should be stored in the user's `TOOLS.md`:
```
## WordPress MCP
- **URL:** https://example.com/wp-json/mcp/v1/http
- **Bearer Token:** <token from AI Engine MCP settings>
```

## How to Call MCP Tools

All calls use JSON-RPC 2.0 over HTTP POST:

```bash
curl -s -X POST <MCP_URL> \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"<tool_name>","arguments":{...}}}'
```

Use `exec` to run curl commands. Parse JSON responses with `python3 -c "import sys,json; ..."` or `jq`.

### Discovery

List all available tools (varies by installed plugins):
```json
{"jsonrpc":"2.0","id":1,"method":"tools/list"}
```

### Connectivity Check

Always start with a ping to verify the connection:
```json
{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"mcp_ping","arguments":{}}}
```

## Available Tool Categories (143 tools as of v3.3)

### Core WordPress (`wp_*`) — 64 tools

Content management, media, taxonomies, users, options, plus theme/plugin file management and database queries.

Key tools: `wp_get_posts`, `wp_get_post`, `wp_create_post`, `wp_update_post`, `wp_alter_post` (search-replace in content), `wp_get_post_snapshot` (complete post data in one call), `wp_upload_media`, `wp_get_terms`, `wp_add_post_terms`.

Developer tools: `wp_theme_get_file`, `wp_theme_put_file`, `wp_plugin_get_file`, `wp_plugin_put_file`, `wp_db_query`.

See `references/core-tools.md` for content/media/taxonomy tools, `references/dev-tools.md` for theme/plugin/database tools.

### SEO Engine (`mwseo_*`) — 32 tools

SEO analysis, scoring, analytics, AI bot traffic tracking. Requires **SEO Engine** plugin (free).

Key tools: `mwseo_get_seo_score`, `mwseo_do_seo_scan`, `mwseo_get_analytics_data`, `mwseo_get_posts_needing_seo`, `mwseo_get_seo_statistics`, `mwseo_query_bot_traffic`, `mwseo_bot_profile`.

See `references/seo-tools.md` for full parameter details.

### WooCommerce (`wc_*`) — 25 tools

Product management, orders, stock, customers, reviews, sales reports. Available when WooCommerce is installed.

Key tools: `wc_list_products`, `wc_create_product`, `wc_list_orders`, `wc_update_order_status`, `wc_get_sales_report`, `wc_get_top_sellers`, `wc_get_low_stock_products`.

See `references/woocommerce-tools.md` for full parameter details.

### Social Engine (`sclegn_*`) — 8 tools

Social media scheduling and publishing. Requires **Social Engine** plugin.

Key tools: `sclegn_list_accounts`, `sclegn_post`, `sclegn_publish_now`, `sclegn_get_posts`.

### Polylang (`pll_*`) — 11 tools

Multilingual content management. Requires **Polylang** plugin.

Key tools: `pll_get_languages`, `pll_get_posts_missing_translation`, `pll_create_translation`, `pll_translation_status`.

### AI Features (`mwai_*`) — 2 tools

- `mwai_vision` — Analyze images via AI
- `mwai_image` — Generate images and store in Media Library

## Common Workflows

### Content Audit
1. `mwseo_get_seo_statistics` — Overall site health
2. `mwseo_get_posts_needing_seo` — Posts with actual SEO problems
3. `mwseo_get_posts_missing_seo` — Posts without custom SEO titles/descriptions
4. Loop: `mwseo_do_seo_scan` + `mwseo_get_issues` per post → fix with `mwseo_set_seo_title`, `mwseo_set_seo_excerpt`

### Publish a Post
1. `wp_create_post` with `post_title`, `post_content` (Markdown accepted), `post_status: "draft"`
2. `mwseo_set_seo_title` + `mwseo_set_seo_excerpt` — Set SEO metadata
3. `mwseo_do_seo_scan` — Verify SEO score
4. `wp_update_post` with `post_status: "publish"` when ready

### Analytics Check
1. `mwseo_get_analytics_data` with `start_date`, `end_date`, `metrics` (visits, unique_visitors, etc.)
2. `mwseo_get_post_analytics` — Per-post traffic
3. `mwseo_get_analytics_top_countries` — Geographic breakdown

### Translation Workflow (Polylang)
1. `pll_translation_status` — See coverage gaps
2. `pll_get_posts_missing_translation` with target language
3. `pll_create_translation` — Create translated post linked to original

### Multi-Site Management
Store multiple sites in `TOOLS.md` and select by name:
```
## WordPress Sites
### My Blog
- **URL:** https://blog.example.com/wp-json/mcp/v1/http
- **Token:** abc123

### My Shop
- **URL:** https://shop.example.com/wp-json/mcp/v1/http
- **Token:** xyz789
```

## Tips

- Use `wp_get_post_snapshot` instead of multiple calls — gets post + meta + terms in one request
- Use `wp_alter_post` for search-replace edits instead of re-uploading entire content
- `wp_get_posts` returns no full content by default (just ID, title, status, excerpt, link) — use `wp_get_post` for content
- Analytics date params use `start_date` / `end_date` format (not camelCase)
- `mwseo_get_posts_needing_seo` finds posts with actual problems; `mwseo_get_posts_missing_seo` finds posts without custom SEO fields (which may still have auto-generated SEO)
- AI Engine is free at https://wordpress.org/plugins/ai-engine/ — MCP Server is included
