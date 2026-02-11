const { markdownToBlocks } = require('@tryfabric/martian');
const { Client } = require('@notionhq/client');

/**
 * Convert Markdown string to Notion blocks
 * @param {string} markdown - Markdown content
 * @param {object} options - Conversion options
 * @returns {object} - { success, blocks, error, warning }
 */
function convertMarkdownToBlocks(markdown, options = {}) {
  try {
    if (!markdown || typeof markdown !== 'string') {
      return {
        success: false,
        blocks: [],
        error: 'Input must be a non-empty string',
        warning: null
      };
    }

    const defaultOptions = {
      enableEmojiCallouts: true,
      strictImageUrls: false,
      notionLimits: {
        truncate: true,
        onError: (err) => console.warn('Martian limit warning:', err.message)
      }
    };

    const mergedOptions = { ...defaultOptions, ...options };
    
    // Convert markdown to blocks
    const blocks = markdownToBlocks(markdown, mergedOptions);

    // Validate block count (Notion API limit: 100 blocks per request)
    let warning = null;
    if (blocks.length > 100) {
      warning = `Content exceeds 100 blocks (${blocks.length}). Only first 100 will be used.`;
      return {
        success: true,
        blocks: blocks.slice(0, 100),
        error: null,
        warning
      };
    }

    return {
      success: true,
      blocks,
      error: null,
      warning
    };
  } catch (error) {
    // Fallback: return plain text paragraph
    const fallbackBlock = {
      object: 'block',
      type: 'paragraph',
      paragraph: {
        rich_text: [{
          type: 'text',
          text: { content: markdown }
        }]
      }
    };

    return {
      success: false,
      blocks: [fallbackBlock],
      error: error.message,
      warning: 'Conversion failed, returned fallback text block'
    };
  }
}

/**
 * Create Notion page from Markdown
 * @param {object} params - Page parameters
 * @returns {object} - { success, pageId, url, blocksCreated, error }
 */
async function createNotionPageFromMarkdown(params) {
  const {
    parentId,
    title,
    markdown,
    notionToken = process.env.NOTION_TOKEN
  } = params;

  try {
    if (!notionToken) {
      throw new Error('NOTION_TOKEN is required');
    }

    if (!parentId || !title || !markdown) {
      throw new Error('parentId, title, and markdown are required');
    }

    // Initialize Notion client
    const notion = new Client({ auth: notionToken });

    // Convert markdown to blocks
    const conversion = convertMarkdownToBlocks(markdown);
    if (!conversion.success && conversion.blocks.length === 0) {
      throw new Error(`Conversion failed: ${conversion.error}`);
    }

    // Create page
    const page = await notion.pages.create({
      parent: {
        page_id: parentId.startsWith('-') ? parentId : parentId.replace(/-/g, '')
      },
      properties: {
        title: {
          title: [{
            text: { content: title }
          }]
        }
      },
      children: conversion.blocks
    });

    return {
      success: true,
      pageId: page.id,
      url: page.url,
      blocksCreated: conversion.blocks.length,
      error: null,
      warning: conversion.warning
    };
  } catch (error) {
    return {
      success: false,
      pageId: null,
      url: null,
      blocksCreated: 0,
      error: error.message,
      warning: null
    };
  }
}

/**
 * Validate blocks before sending to Notion API
 * @param {array} blocks - Notion blocks
 * @returns {object} - { valid, errors }
 */
function validateBlocks(blocks) {
  const errors = [];

  if (!Array.isArray(blocks)) {
    errors.push('Blocks must be an array');
    return { valid: false, errors };
  }

  if (blocks.length === 0) {
    errors.push('Blocks array is empty');
  }

  if (blocks.length > 100) {
    errors.push(`Block count (${blocks.length}) exceeds Notion API limit of 100`);
  }

  // Validate each block has required fields
  blocks.forEach((block, index) => {
    if (!block.type) {
      errors.push(`Block ${index} missing 'type' field`);
    }
    if (!block[block.type]) {
      errors.push(`Block ${index} missing data for type '${block.type}'`);
    }
  });

  return {
    valid: errors.length === 0,
    errors
  };
}

module.exports = {
  convertMarkdownToBlocks,
  createNotionPageFromMarkdown,
  validateBlocks
};
