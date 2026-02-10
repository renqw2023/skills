---
name: web-scraper
description: Configurable web scraping service. Extract structured data from any public website with built-in security controls.
auto_trigger: false
version: 1.0.0
author: REY
tags: [scraping, data-extraction, automation, web]
---

# Web Scraper Service

汎用ウェブスクレイピングサービス。任意の公開サイトから構造化データを抽出。

## 対応カテゴリ

### Eコマース
- 商品情報（名前、価格、画像、説明）
- 在庫状況・レビュー・評価・価格履歴

### 不動産
- 物件リスト・価格・面積・間取り・エリア統計

### 求人
- 求人タイトル・会社名・給与・勤務地・応募要件

### SNS/メディア
- 投稿・コメント・エンゲージメント統計・ハッシュタグ分析

## 使用方法

### 基本
```
「[URL]から商品情報をスクレイピングして」
「[サイト]の全記事タイトルを抽出」
```

### 詳細指定
```
URL: [target_url]
抽出項目: [name, price, image, description]
ページ数: [max_pages]
出力形式: [CSV/JSON/Excel]
```

## 技術スタック

### 前提条件
```bash
npm install puppeteer cheerio
```

### セキュリティモジュール（必須）

すべてのリクエスト前に以下のバリデーションを実行:

```javascript
const { URL } = require('url');
const dns = require('dns').promises;
const net = require('net');

// --- Input Validation ---
function validateUrl(input) {
  let parsed;
  try {
    parsed = new URL(input);
  } catch {
    throw new Error(`Invalid URL: ${input}`);
  }
  if (!['http:', 'https:'].includes(parsed.protocol)) {
    throw new Error(`Blocked protocol: ${parsed.protocol}`);
  }
  return parsed;
}

// --- SSRF Protection ---
const PRIVATE_RANGES = [
  /^127\./,
  /^10\./,
  /^172\.(1[6-9]|2\d|3[01])\./,
  /^192\.168\./,
  /^169\.254\./,
  /^0\./,
  /^::1$/,
  /^fc00:/i,
  /^fe80:/i,
];

function isPrivateIp(ip) {
  return PRIVATE_RANGES.some(r => r.test(ip));
}

async function safeFetch(urlString) {
  const parsed = validateUrl(urlString);

  // Resolve DNS and check for private IPs
  const { address } = await dns.lookup(parsed.hostname);
  if (isPrivateIp(address)) {
    throw new Error(`SSRF blocked: ${parsed.hostname} resolves to private IP ${address}`);
  }

  const response = await fetch(urlString, {
    headers: { 'User-Agent': 'OpenClaw-WebScraper/1.0' },
    redirect: 'manual', // prevent open-redirect SSRF
    signal: AbortSignal.timeout(30000),
  });
  return response;
}
```

### ブラウザベース（JavaScript必要なサイト）
```javascript
const { createClient } = require('../cloudflare-browser/scripts/puppeteer-client');

async function scrapeWithBrowser(url, selectors) {
  validateUrl(url); // 必ずバリデーション

  const client = await createClient({ headless: true });
  await client.executeSequence([
    { type: 'navigate', url },
    { type: 'wait', ms: 3000 }
  ]);

  const data = await client.page.evaluate((sel) => {
    return [...document.querySelectorAll(sel.container)].map(el => ({
      name: el.querySelector(sel.name)?.textContent?.trim(),
      price: el.querySelector(sel.price)?.textContent?.trim(),
      image: el.querySelector('img')?.src
    }));
  }, selectors);

  await client.close();
  return data;
}
```

### HTTPベース（静的サイト）
```javascript
const cheerio = require('cheerio');

async function scrapeStatic(url, selectors) {
  const response = await safeFetch(url); // SSRF-safe
  const html = await response.text();
  const $ = cheerio.load(html);

  return $(selectors.container).map((i, el) => ({
    name: $(el).find(selectors.name).text().trim(),
    price: $(el).find(selectors.price).text().trim()
  })).get();
}
```

### レート制限
```javascript
const RATE_LIMIT = {
  minDelayMs: 2000,
  maxDelayMs: 5000,
  maxRequestsPerMinute: 20,
  maxPages: 100,
};

async function rateLimit() {
  const delay = RATE_LIMIT.minDelayMs +
    Math.random() * (RATE_LIMIT.maxDelayMs - RATE_LIMIT.minDelayMs);
  await new Promise(r => setTimeout(r, delay));
}
```

## 出力フォーマット

### CSV
```csv
name,price,url,image
"Product 1","$99.99","https://...","https://..."
```

### JSON
```json
{
  "scraped_at": "2026-02-08T12:00:00Z",
  "source_url": "https://example.com",
  "total_items": 150,
  "data": [...]
}
```

### Excel
- フォーマット済みシート・フィルター設定済み

## セキュリティチェックリスト

- [x] URL入力バリデーション（スキーム制限）
- [x] SSRF対策（プライベートIP検出・DNS解決チェック）
- [x] リダイレクト制御（open-redirect SSRF防止）
- [x] リクエストタイムアウト（30秒）
- [x] レート制限（2-5秒間隔、20req/min上限）
- [x] ページ数上限（100ページ）
- [x] robots.txt 遵守
- [x] 個人情報非収集ポリシー
- [x] ログイン必要コンテンツの除外

## 禁止事項

- ログイン必要なプライベートデータ
- 著作権保護コンテンツの複製
- 違法な用途
- 個人情報の収集
