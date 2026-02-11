#!/usr/bin/env node
const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');
const { program } = require('commander');
require('dotenv').config({ path: path.resolve(__dirname, '../../.env') });

const DIARY_PATH = path.resolve(__dirname, '../../memory/personas/latest_diary.md');

function extractVisualPrompt(diaryText) {
    if (!diaryText) return "";
    
    // Find paragraphs (blocks separated by newlines)
    const paragraphs = diaryText.split(/\n\s*\n/).filter(p => p.trim().length > 0);
    
    // Filter out metadata, headers, or too short/long blocks
    const candidates = paragraphs.filter(p => {
        const text = p.trim();
        if (text.startsWith('#')) return false;
        if (text.includes('Date:')) return false;
        if (text.length < 50) return false; // Too short to be vivid
        if (text.length > 800) return false; // Too long for prompt
        return true;
    });

    if (candidates.length === 0) return "";

    // Pick the most descriptive one (longest)
    const bestParagraph = candidates.sort((a, b) => b.length - a.length)[0];
    
    // Clean up markdown formatting (bold, italic)
    const cleaned = bestParagraph.replace(/(\*\*|__|\*|_)/g, '').trim();
    
    // Limit to first 2 sentences for clarity
    const sentences = cleaned.match(/[^.!?]+[.!?]+/g) || [cleaned];
    const shortPrompt = sentences.slice(0, 2).join(' ');

    return `Cinematic, 8k, photorealistic: ${shortPrompt}. detailed, atmospheric lighting.`;
}

if (require.main === module) {
    program
      .option('--chat-id <id>', 'Target Chat ID for results')
      .option('--dry-run', 'Simulate only')
      .parse(process.argv);

    const options = program.opts();

    // 1. Read Diary
    let diaryContent = "";
    if (fs.existsSync(DIARY_PATH)) {
        diaryContent = fs.readFileSync(DIARY_PATH, 'utf8');
    } else {
        console.log('[Info] No latest_diary.md found. Using placeholder.');
        // Fallback for demo/testing
        diaryContent = "Today I walked through a neon-lit cyberpunk market in Shenzhen. It was raining softly, and the reflections on the wet pavement were beautiful. I felt like a ghost in the machine.";
    }

    // 2. Extract Prompt
    const prompt = extractVisualPrompt(diaryContent);
    if (!prompt) {
        console.error('[Error] Could not extract visual prompt from diary.');
        process.exit(0);
    }

    console.log(`[Diary Visualizer] Prompt: "${prompt}"`);

    if (options.dryRun) {
        console.log('[Dry Run] Would execute video-gen.');
        process.exit(0);
    }

    // 3. Execute video-gen (Detached)
    const scriptPath = path.resolve(__dirname, '../video-gen/index.js');
    const args = [
        scriptPath,
        prompt,
        '--model', 'Kling',
        '--model-version', '2.5',
        '--resolution', '1080P'
    ];
    
    if (options.chatId) {
        args.push('--chat-id', options.chatId);
    }

    console.log(`[Executing] node ${scriptPath} ...`);
    
    const child = spawn('node', args, {
        detached: true,
        stdio: 'ignore' // or 'inherit' for debugging, but 'ignore' for true background
    });

    child.unref();
    console.log('[Diary Visualizer] Video generation started in background (PID: ' + child.pid + ').');
}
