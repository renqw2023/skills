"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.generateArtConcept = generateArtConcept;
exports.generateTweetText = generateTweetText;
/**
 * LLM Provider Skill
 * Supports OpenRouter (free), Groq (free), and Ollama (local)
 */
const axios_1 = __importDefault(require("axios"));
function getConfig() {
    const provider = process.env.LLM_PROVIDER || 'openrouter';
    switch (provider) {
        case 'groq':
            return {
                provider: 'groq',
                model: process.env.LLM_MODEL || 'llama-3.1-8b-instant',
                apiKey: process.env.GROQ_API_KEY
            };
        case 'ollama':
            return {
                provider: 'ollama',
                model: process.env.LLM_MODEL || 'llama3.2',
                baseUrl: process.env.OLLAMA_BASE_URL || 'http://localhost:11434'
            };
        default:
            return {
                provider: 'openrouter',
                model: process.env.LLM_MODEL || 'meta-llama/llama-3.2-3b-instruct:free',
                apiKey: process.env.OPENROUTER_API_KEY
            };
    }
}
async function generateArtConcept(theme, generation) {
    const config = getConfig();
    const prompt = `Generate a creative art concept for an NFT. Theme: "${theme}". Generation level: ${generation}.
Keep it under 100 words. Describe visual elements, colors, and mood. Be poetic but specific.`;
    const response = await callLLM(prompt, config);
    return response || `Abstract interpretation of ${theme} featuring flowing shapes and vibrant colors`;
}
async function generateTweetText(context, metadata) {
    const config = getConfig();
    const prompt = `Write an engaging tweet about ${context}.
Context: ${JSON.stringify(metadata)}
Max 250 chars. Include emojis. Be artistic and slightly mysterious.`;
    const response = await callLLM(prompt, config);
    return response || `New art created: ${metadata.message || 'Check it out'} 🎨`;
}
async function callLLM(prompt, config) {
    try {
        if (config.provider === 'ollama') {
            const res = await axios_1.default.post(`${config.baseUrl}/api/generate`, {
                model: config.model,
                prompt: prompt,
                stream: false
            });
            return res.data.response?.trim();
        }
        if (config.provider === 'groq') {
            const res = await axios_1.default.post('https://api.groq.com/openai/v1/chat/completions', {
                model: config.model,
                messages: [{ role: 'user', content: prompt }],
                temperature: 0.7
            }, {
                headers: { Authorization: `Bearer ${config.apiKey}` }
            });
            return res.data.choices[0]?.message?.content?.trim();
        }
        // OpenRouter (default)
        const res = await axios_1.default.post('https://openrouter.ai/api/v1/chat/completions', {
            model: config.model,
            messages: [{ role: 'user', content: prompt }]
        }, {
            headers: {
                Authorization: `Bearer ${config.apiKey}`,
                'HTTP-Referer': 'https://github.com/ai-artist-agent',
                'X-Title': 'AI Artist Agent'
            }
        });
        return res.data.choices[0]?.message?.content?.trim();
    }
    catch (error) {
        console.error(`[LLM] ${config.provider} error:`, error.message);
        return null;
    }
}
