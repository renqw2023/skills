#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const { createNotionPageFromMarkdown } = require('../src/converter');

function showHelp() {
  console.log(`
Usage: md2notion [options]

Options:
  --parent-id <id>     Parent page or database ID (required)
  --title <title>      Page title (required)
  --file <path>        Markdown file path (required)
  --token <token>      Notion API token (or set NOTION_TOKEN env var)
  -h, --help          Show this help

Example:
  md2notion --parent-id "abc123" --title "My Page" --file content.md
`);
}

async function main() {
  const args = process.argv.slice(2);
  
  // Parse arguments
  const params = {};
  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case '--parent-id':
        params.parentId = args[++i];
        break;
      case '--title':
        params.title = args[++i];
        break;
      case '--file':
        params.file = args[++i];
        break;
      case '--token':
        params.token = args[++i];
        break;
      case '-h':
      case '--help':
        showHelp();
        process.exit(0);
        break;
    }
  }

  // Validate required params
  if (!params.parentId || !params.title || !params.file) {
    console.error('Error: --parent-id, --title, and --file are required');
    showHelp();
    process.exit(1);
  }

  // Read markdown file
  let markdown;
  try {
    markdown = fs.readFileSync(params.file, 'utf-8');
  } catch (err) {
    console.error(`Error reading file: ${err.message}`);
    process.exit(1);
  }

  // Create page
  console.log('Creating Notion page...');
  const result = await createNotionPageFromMarkdown({
    parentId: params.parentId,
    title: params.title,
    markdown,
    notionToken: params.token
  });

  if (result.success) {
    console.log('✅ Page created successfully!');
    console.log(`   ID: ${result.pageId}`);
    console.log(`   URL: ${result.url}`);
    console.log(`   Blocks: ${result.blocksCreated}`);
    if (result.warning) {
      console.log(`   Warning: ${result.warning}`);
    }
  } else {
    console.error('❌ Failed to create page:');
    console.error(`   ${result.error}`);
    process.exit(1);
  }
}

main().catch(err => {
  console.error('Unexpected error:', err);
  process.exit(1);
});
