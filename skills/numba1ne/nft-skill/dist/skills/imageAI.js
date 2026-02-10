"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.generateAIImage = generateAIImage;
/**
 * AI Image Generation Skill
 * Supports Stability AI and DALL-E as providers, with procedural fallback
 */
const axios_1 = __importDefault(require("axios"));
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
/**
 * Generate an image from a text prompt using the configured AI provider.
 * Returns the file path of the saved PNG, or null if no AI provider is configured.
 */
async function generateAIImage(prompt, outputDir) {
    const provider = (process.env.IMAGE_PROVIDER || 'procedural').toLowerCase();
    if (provider === 'procedural' || provider === '')
        return null;
    const fileName = `ai_art_${Date.now()}.png`;
    const filePath = path.join(outputDir, fileName);
    try {
        if (provider === 'stability') {
            return await generateWithStability(prompt, filePath);
        }
        else if (provider === 'dalle') {
            return await generateWithDalle(prompt, filePath);
        }
        console.warn(`[ImageAI] Unknown provider "${provider}", falling back to procedural`);
        return null;
    }
    catch (error) {
        console.error(`[ImageAI] ${provider} generation failed: ${error.message}. Falling back to procedural.`);
        return null;
    }
}
async function generateWithStability(prompt, filePath) {
    const model = process.env.IMAGE_MODEL || 'stable-diffusion-xl-1024-v1-0';
    const apiKey = process.env.STABILITY_API_KEY;
    if (!apiKey)
        throw new Error('STABILITY_API_KEY is not set');
    const response = await axios_1.default.post(`https://api.stability.ai/v1/generation/${model}/text-to-image`, {
        text_prompts: [{ text: prompt, weight: 1 }],
        cfg_scale: 7,
        height: 1024,
        width: 1024,
        samples: 1,
        steps: 30
    }, {
        headers: {
            Authorization: `Bearer ${apiKey}`,
            'Content-Type': 'application/json',
            Accept: 'application/json'
        }
    });
    const base64 = response.data.artifacts[0].base64;
    fs.writeFileSync(filePath, Buffer.from(base64, 'base64'));
    console.log(`[ImageAI] Stability AI image saved: ${filePath}`);
    return filePath;
}
async function generateWithDalle(prompt, filePath) {
    const apiKey = process.env.OPENAI_API_KEY;
    if (!apiKey)
        throw new Error('OPENAI_API_KEY is not set');
    const model = process.env.IMAGE_MODEL || 'dall-e-3';
    const response = await axios_1.default.post('https://api.openai.com/v1/images/generations', {
        model,
        prompt,
        n: 1,
        size: '1024x1024',
        response_format: 'b64_json'
    }, {
        headers: {
            Authorization: `Bearer ${apiKey}`,
            'Content-Type': 'application/json'
        }
    });
    const base64 = response.data.data[0].b64_json;
    fs.writeFileSync(filePath, Buffer.from(base64, 'base64'));
    console.log(`[ImageAI] DALL-E image saved: ${filePath}`);
    return filePath;
}
