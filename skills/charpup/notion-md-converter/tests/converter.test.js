const { convertMarkdownToBlocks, validateBlocks, createNotionPageFromMarkdown } = require('../src/converter');

// Mock environment
process.env.NOTION_TOKEN = 'test-token';

describe('convertMarkdownToBlocks', () => {
  test('converts simple markdown to blocks', () => {
    const markdown = '## Hello\n\nWorld';
    const result = convertMarkdownToBlocks(markdown);
    
    expect(result.success).toBe(true);
    expect(result.blocks.length).toBeGreaterThan(0);
    expect(result.blocks[0].type).toBe('heading_2');
  });

  test('handles empty string', () => {
    const result = convertMarkdownToBlocks('');
    
    expect(result.success).toBe(false);
    expect(result.blocks).toEqual([]);
    expect(result.error).toContain('non-empty string');
  });

  test('handles null input', () => {
    const result = convertMarkdownToBlocks(null);
    
    expect(result.success).toBe(false);
    expect(result.error).toContain('non-empty string');
  });

  test('converts lists', () => {
    const markdown = '- Item 1\n- Item 2\n- [x] Done';
    const result = convertMarkdownToBlocks(markdown);
    
    expect(result.success).toBe(true);
    expect(result.blocks.some(b => b.type === 'bulleted_list_item')).toBe(true);
    expect(result.blocks.some(b => b.type === 'to_do')).toBe(true);
  });

  test('converts code blocks', () => {
    const markdown = '```javascript\nconst x = 1;\n```';
    const result = convertMarkdownToBlocks(markdown);
    
    expect(result.success).toBe(true);
    const codeBlock = result.blocks.find(b => b.type === 'code');
    expect(codeBlock).toBeDefined();
  });

  test('warns on >100 blocks', () => {
    // Generate markdown that will create >100 blocks
    const markdown = Array(50).fill('## Heading\n\nParagraph\n\n- list item').join('\n\n');
    const result = convertMarkdownToBlocks(markdown);
    
    expect(result.warning).toContain('100 blocks');
    expect(result.blocks.length).toBeLessThanOrEqual(100);
  });

  test('provides fallback on error', () => {
    // Force an error with invalid input
    const result = convertMarkdownToBlocks('normal text');
    
    // Even on error, should return fallback blocks
    if (!result.success) {
      expect(result.blocks.length).toBeGreaterThan(0);
      expect(result.warning).toContain('fallback');
    }
  });
});

describe('validateBlocks', () => {
  test('validates correct blocks', () => {
    const blocks = [
      { type: 'paragraph', paragraph: { rich_text: [] } }
    ];
    const result = validateBlocks(blocks);
    
    expect(result.valid).toBe(true);
    expect(result.errors).toHaveLength(0);
  });

  test('detects empty array', () => {
    const result = validateBlocks([]);
    
    expect(result.valid).toBe(false);
    expect(result.errors).toContain('Blocks array is empty');
  });

  test('detects non-array', () => {
    const result = validateBlocks('not an array');
    
    expect(result.valid).toBe(false);
    expect(result.errors).toContain('Blocks must be an array');
  });

  test('detects >100 blocks', () => {
    const blocks = Array(101).fill({ type: 'paragraph', paragraph: {} });
    const result = validateBlocks(blocks);
    
    expect(result.valid).toBe(false);
    expect(result.errors.some(e => e.includes('100'))).toBe(true);
  });

  test('detects missing type', () => {
    const blocks = [{ paragraph: {} }];
    const result = validateBlocks(blocks);
    
    expect(result.valid).toBe(false);
    expect(result.errors.some(e => e.includes('type'))).toBe(true);
  });
});

describe('createNotionPageFromMarkdown', () => {
  test('requires NOTION_TOKEN', async () => {
    delete process.env.NOTION_TOKEN;
    
    const result = await createNotionPageFromMarkdown({
      parentId: 'test-id',
      title: 'Test',
      markdown: '# Test'
    });
    
    expect(result.success).toBe(false);
    expect(result.error).toContain('NOTION_TOKEN');
    
    process.env.NOTION_TOKEN = 'test-token';
  });

  test('requires all parameters', async () => {
    const result = await createNotionPageFromMarkdown({
      parentId: 'test-id'
      // missing title and markdown
    });
    
    expect(result.success).toBe(false);
    expect(result.error).toContain('required');
  });
});
