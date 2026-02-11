#!/usr/bin/env node
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

// Parse arguments manually to avoid deps
const args = process.argv.slice(2);
let query = '';
let include = '**/*';
let contextLines = 0;
let maxMatches = 50;
let jsonOutput = false;

for (let i = 0; i < args.length; i++) {
  if (args[i] === '--query' || args[i] === '-q') {
    query = args[++i];
  } else if (args[i] === '--include' || args[i] === '-i') {
    include = args[++i];
  } else if (args[i] === '--context' || args[i] === '-C') {
    contextLines = parseInt(args[++i], 10);
  } else if (args[i] === '--max' || args[i] === '-m') {
    maxMatches = parseInt(args[++i], 10);
  } else if (args[i] === '--json') {
    jsonOutput = true;
  } else if (!query && !args[i].startsWith('-')) {
    query = args[i]; // positional query support
  }
}

if (!query) {
  console.error('Usage: node skills/code-search/index.js --query <pattern> [--include <glob>] [--context <lines>] [--max <matches>] [--json]');
  process.exit(1);
}

// Config: Paths to ALWAYS ignore
const IGNORE_DIRS = ['.git', 'node_modules', 'dist', 'build', 'coverage', '.npm-global', 'temp'];
const IGNORE_FILES = ['package-lock.json', 'yarn.lock', 'pnpm-lock.yaml'];

// Helper: Scan directory recursively (bfs/dfs)
function scanDir(dir, pattern = null) {
  let results = [];
  try {
    const items = fs.readdirSync(dir, { withFileTypes: true });
    
    for (const item of items) {
      const fullPath = path.join(dir, item.name);
      
      if (item.isDirectory()) {
        if (!IGNORE_DIRS.includes(item.name) && !item.name.startsWith('.')) {
          results = results.concat(scanDir(fullPath, pattern));
        }
      } else if (item.isFile()) {
        if (!IGNORE_FILES.includes(item.name) && !item.name.endsWith('.min.js') && !item.name.endsWith('.map')) {
           // Simple extension check if pattern provided (very basic)
           // For robust glob matching we'd need a library or complex regex, 
           // but for now let's just search everything that isn't ignored.
           // If user provided a specific extension in include like "*.js", we filter here.
           if (include !== '**/*' && include.startsWith('*.')) {
             if (!item.name.endsWith(include.slice(1))) continue;
           }
           results.push(fullPath);
        }
      }
    }
  } catch (err) {
    // Ignore access errors
  }
  return results;
}

// Helper: Search in file
function searchFile(filePath, queryRegex) {
  try {
    const content = fs.readFileSync(filePath, 'utf8');
    const lines = content.split('\n');
    const matches = [];

    for (let i = 0; i < lines.length; i++) {
      if (queryRegex.test(lines[i])) {
        // Context
        const start = Math.max(0, i - contextLines);
        const end = Math.min(lines.length, i + contextLines + 1);
        
        matches.push({
          line: i + 1,
          content: lines[i].trim(),
          context: lines.slice(start, end).map((l, idx) => ({
            line: start + idx + 1,
            content: l.trimRight(),
            isMatch: (start + idx) === i
          }))
        });

        if (matches.length >= maxMatches) break;
      }
    }
    return matches;
  } catch (err) {
    return []; // Binary file or read error
  }
}

// Main execution
try {
  const rootDir = process.cwd();
  const allFiles = scanDir(rootDir);
  const regex = new RegExp(query, 'i'); // Case insensitive default
  
  const results = [];
  let totalMatches = 0;

  for (const file of allFiles) {
    if (totalMatches >= maxMatches) break;
    
    const fileMatches = searchFile(file, regex);
    if (fileMatches.length > 0) {
      results.push({
        file: path.relative(rootDir, file),
        matches: fileMatches
      });
      totalMatches += fileMatches.length;
    }
  }

  if (jsonOutput) {
    console.log(JSON.stringify(results, null, 2));
  } else {
    if (results.length === 0) {
      console.log(`No matches found for "${query}"`);
    } else {
      console.log(`Found matches in ${results.length} files:\n`);
      for (const res of results) {
        console.log(`File: \x1b[36m${res.file}\x1b[0m`);
        for (const match of res.matches) {
          if (contextLines > 0) {
            console.log('  ---');
            match.context.forEach(ctx => {
              const prefix = ctx.isMatch ? '>' : ' ';
              console.log(`  ${prefix} ${ctx.line}: ${ctx.content}`);
            });
            console.log('  ---');
          } else {
            console.log(`  Line ${match.line}: ${match.content}`);
          }
        }
        console.log('');
      }
      if (totalMatches >= maxMatches) {
        console.log(`\x1b[33mStopping after ${maxMatches} matches.\x1b[0m`);
      }
    }
  }

} catch (err) {
  console.error('Error during search:', err.message);
  process.exit(1);
}
