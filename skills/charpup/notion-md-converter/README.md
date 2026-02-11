# notion-md-converter

Convert Markdown to Notion blocks using Martian library.

## Installation

```bash
npm install
```

## Usage

### As a Library

```javascript
const { convertMarkdownToBlocks, createNotionPageFromMarkdown } = require('./src/converter');

// Convert markdown to blocks
const blocks = convertMarkdownToBlocks(`
## Journal Entry

Today I completed:
- [x] Task 1
- [x] Task 2
- [ ] Task 3

> [!NOTE]
> This is an important note.
`);

// Create Notion page
const result = await createNotionPageFromMarkdown({
  parentId: 'page-id-or-database-id',
  title: 'My Journal Entry',
  markdown: content,
  notionToken: process.env.NOTION_TOKEN
});
```

### CLI Tool

```bash
# Convert markdown file to Notion page
node tools/md2notion.js --parent-id "xxx" --title "Page Title" --file content.md
```

## Supported Markdown

- Headers (H1-H3)
- Paragraphs with inline formatting
- Lists (bulleted, numbered, checkboxes)
- Code blocks with language
- Tables
- Blockquotes → Callouts (with emoji support)
- GFM Alerts ([!NOTE], [!WARNING], etc.)
- Images (external URLs)

## Environment Variables

```bash
NOTION_TOKEN=ntn_xxx  # Required for page creation
```

## Testing

```bash
npm test
```

## License

MIT
