# 🕷️ Web Scraper Skill for OpenClaw

Configurable web scraping service for OpenClaw agents. Extract structured data from any public website.

## Features

- **Static & Dynamic** — Cheerio (HTML) + Puppeteer (JS-rendered) support
- **Multiple outputs** — CSV, JSON, Excel
- **E-commerce, Real Estate, Jobs, Media** — pre-built extraction patterns
- **Anti-bot handling** — random delays, UA rotation
- **Security-first** — SSRF protection, input validation, robots.txt compliance

## Installation

```bash
# Copy to your OpenClaw skills directory
cp -r web-scraper ~/.openclaw/skills/

# Install dependencies
npm install puppeteer cheerio
```

## Usage

Tell your agent:
```
「https://example.com から商品情報をスクレイピングして」
```

Or with detailed parameters:
```
URL: https://example.com/products
抽出項目: name, price, image
ページ数: 10
出力形式: JSON
```

## Security

This skill includes:
- **URL validation** — only `http://` and `https://` schemes allowed
- **SSRF protection** — blocks private IPs (10.x, 172.16-31.x, 192.168.x, 127.x, ::1)
- **Domain allowlist** — optional whitelist mode
- **Rate limiting** — configurable delays between requests
- **robots.txt** — respected by default
- **No credentials** — never scrapes login-protected content

## Pricing (Reference)

| Plan | Price | Scope |
|------|-------|-------|
| Single Project | $200–500 | 1 site, up to 1K items |
| Multi-Site | $500–1,000 | Multiple sites, normalized |
| Enterprise | $1,000–2,000 | Complex sites + API |
| Monthly Maintenance | $50–200/mo | Scheduled runs + updates |

## License

MIT

## Author

Self-built skill — no third-party dependencies beyond puppeteer/cheerio.
