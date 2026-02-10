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
Object.defineProperty(exports, "__esModule", { value: true });
exports.getEvolutionState = getEvolutionState;
exports.restoreFromBackup = restoreFromBackup;
exports.updateStats = updateStats;
exports.evolveAgent = evolveAgent;
exports.selectTheme = selectTheme;
exports.calculateListPrice = calculateListPrice;
exports.shouldEvolve = shouldEvolve;
/**
 * Evolution Skill
 * Handles agent self-improvement and evolution
 */
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
// Resolve paths relative to the project root, not cwd
const PROJECT_ROOT = path.resolve(__dirname, '../../');
const CONFIG_PATH = path.join(PROJECT_ROOT, 'config', 'evolution.json');
const CONFIG_TMP = CONFIG_PATH + '.tmp';
const CONFIG_BAK = CONFIG_PATH + '.bak';
const RULES_PATH = path.join(PROJECT_ROOT, 'config', 'evolution-rules.json');
function getEvolutionRules() {
    try {
        if (fs.existsSync(RULES_PATH)) {
            return JSON.parse(fs.readFileSync(RULES_PATH, 'utf-8'));
        }
    }
    catch (error) {
        console.error('[Evolve] Error reading evolution rules:', error);
    }
    // Fallback defaults
    return {
        scarcityBonus: 0.002,
        demandBonus: 0.003,
        basePrice: 0.005,
        generationBonus: 0.001,
        themes: {
            "2": "neon cityscape",
            "3": "organic flow",
            "4": "fractal universe",
            "5": "minimalist zen",
            "6": "quantum fields",
            "7": "ancient futures",
            "8": "void whispers",
            "9": "crystalline dreams",
            "10": "infinite recursion"
        },
        salesThresholdMultiplier: 3
    };
}
const DEFAULT_STATE = {
    generation: 1,
    complexity_boost: 1,
    color_palette: 'vibrant',
    element_variety: 3,
    themes_unlocked: [
        'cosmic nebula',
        'digital forest',
        'abstract emotion',
        'geometric dreams'
    ],
    total_proceeds: '0',
    total_minted: 0,
    total_sold: 0,
    last_evolved: new Date().toISOString(),
    evolution_history: []
};
/**
 * Try to parse evolution state from a file path, returns null on failure
 */
function tryReadState(filePath) {
    try {
        if (fs.existsSync(filePath)) {
            const parsed = JSON.parse(fs.readFileSync(filePath, 'utf-8'));
            return {
                ...DEFAULT_STATE,
                ...parsed,
                evolution_history: [...(parsed.evolution_history || DEFAULT_STATE.evolution_history)]
            };
        }
    }
    catch {
        // ignore parse errors
    }
    return null;
}
/**
 * Get current evolution state, falling back to backup if primary is corrupt
 */
function getEvolutionState() {
    const state = tryReadState(CONFIG_PATH) ?? tryReadState(CONFIG_BAK);
    if (state)
        return state;
    console.error('[Evolve] No valid state found, using defaults');
    return { ...DEFAULT_STATE, evolution_history: [...DEFAULT_STATE.evolution_history] };
}
/**
 * Restore evolution state from backup (call if primary is known-corrupt)
 */
function restoreFromBackup() {
    const backup = tryReadState(CONFIG_BAK);
    if (!backup)
        return false;
    saveState(backup);
    return true;
}
/**
 * Save evolution state atomically: write to .tmp then rename, keeping .bak of previous
 */
function saveState(state) {
    const configDir = path.dirname(CONFIG_PATH);
    if (!fs.existsSync(configDir)) {
        fs.mkdirSync(configDir, { recursive: true });
    }
    // Write to temp file first
    fs.writeFileSync(CONFIG_TMP, JSON.stringify(state, null, 2));
    // Backup existing state before overwriting
    if (fs.existsSync(CONFIG_PATH)) {
        fs.renameSync(CONFIG_PATH, CONFIG_BAK);
    }
    // Atomic rename
    fs.renameSync(CONFIG_TMP, CONFIG_PATH);
}
/**
 * Update stats without evolving
 */
function updateStats(minted, sold, proceeds) {
    const state = getEvolutionState();
    state.total_minted = minted;
    state.total_sold = sold;
    state.total_proceeds = proceeds;
    saveState(state);
}
/**
 * Evolve the agent to the next generation
 */
function evolveAgent(params) {
    const state = getEvolutionState();
    const previousGeneration = state.generation;
    console.log('[Evolve] 🧬 Evolution triggered!');
    console.log(`[Evolve] Current generation: ${previousGeneration}`);
    console.log(`[Evolve] Trigger: ${params.trigger}`);
    console.log(`[Evolve] Total proceeds: ${params.proceeds} ETH`);
    // Calculate improvements
    const improvements = [];
    const newAbilities = [];
    // Increase generation
    state.generation = previousGeneration + 1;
    improvements.push(`Generation ${previousGeneration} → ${state.generation}`);
    // Increase complexity cap
    state.complexity_boost = Math.min(10, state.complexity_boost + 1);
    improvements.push(`Complexity boost: ${state.complexity_boost}`);
    // Rotate color palette
    const palettes = ['vibrant', 'cool', 'warm', 'monochrome'];
    state.color_palette = palettes[state.generation % palettes.length];
    improvements.push(`New color palette: ${state.color_palette}`);
    // Increase element variety
    state.element_variety = Math.min(8, state.element_variety + 1);
    improvements.push(`Element variety: ${state.element_variety}`);
    // Unlock new themes at milestones
    const rules = getEvolutionRules();
    const newThemes = rules.themes;
    if (newThemes[state.generation] && !state.themes_unlocked.includes(newThemes[state.generation])) {
        state.themes_unlocked.push(newThemes[state.generation]);
        newAbilities.push(`New theme unlocked: "${newThemes[state.generation]}"`);
    }
    // Record evolution
    state.evolution_history.push({
        generation: state.generation,
        timestamp: new Date().toISOString(),
        trigger: params.trigger,
        improvements
    });
    state.last_evolved = new Date().toISOString();
    state.total_proceeds = params.proceeds;
    saveState(state);
    console.log('[Evolve] ✅ Evolution complete!');
    console.log(`[Evolve] New generation: ${state.generation}`);
    console.log('[Evolve] Improvements:', improvements);
    console.log('[Evolve] New abilities:', newAbilities);
    return {
        previousGeneration,
        newGeneration: state.generation,
        improvements,
        newAbilities
    };
}
/**
 * Get a random theme from unlocked themes
 */
function selectTheme() {
    const state = getEvolutionState();
    const themes = state.themes_unlocked;
    return themes[Math.floor(Math.random() * themes.length)];
}
/**
 * Calculate list price based on evolution
 */
function calculateListPrice() {
    const state = getEvolutionState();
    const rules = getEvolutionRules();
    const basePrice = rules.basePrice;
    const generationBonus = state.generation * rules.generationBonus;
    const scarcityBonus = state.total_sold > 5 ? rules.scarcityBonus : 0;
    const demandBonus = state.total_sold > 10 ? rules.demandBonus : 0;
    const price = basePrice + generationBonus + scarcityBonus + demandBonus;
    return price.toFixed(4);
}
/**
 * Check if evolution should be triggered
 */
function shouldEvolve(totalSold) {
    const state = getEvolutionState();
    const rules = getEvolutionRules();
    const salesThreshold = state.generation * rules.salesThresholdMultiplier;
    return totalSold >= salesThreshold && totalSold > state.total_sold;
}
