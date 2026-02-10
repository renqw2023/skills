"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.resetClientForTesting = resetClientForTesting;
exports.postToX = postToX;
exports.announceNewArt = announceNewArt;
exports.announceSale = announceSale;
exports.announceEvolution = announceEvolution;
exports.announceLaunch = announceLaunch;
/**
 * Social Media Skill
 * Handles posting to X (Twitter)
 */
const twitter_api_v2_1 = require("twitter-api-v2");
let client = null;
/**
 * Reset the cached client. Used for testing to ensure fresh mocks per test.
 */
function resetClientForTesting() {
    client = null;
}
function getClient() {
    if (!client) {
        client = new twitter_api_v2_1.TwitterApi({
            appKey: process.env.X_CONSUMER_KEY,
            appSecret: process.env.X_CONSUMER_SECRET,
            accessToken: process.env.X_ACCESS_TOKEN,
            accessSecret: process.env.X_ACCESS_SECRET,
        });
    }
    return client;
}
/**
 * Post a tweet to X
 * Can optionally use LLM to generate creative text
 */
async function postToX(message, options = {}) {
    try {
        let tweetText = message;
        // Add hashtags if provided
        if (options.hashtags && options.hashtags.length > 0) {
            const hashtagStr = options.hashtags.map(h => `#${h}`).join(' ');
            const remaining = 280 - tweetText.length - hashtagStr.length - 1;
            if (remaining >= 0) {
                tweetText = `${tweetText} ${hashtagStr}`;
            }
        }
        // Truncate if too long
        if (tweetText.length > 280) {
            tweetText = tweetText.substring(0, 277) + '...';
        }
        console.log(`[Social] Posting to X: ${tweetText.substring(0, 50)}...`);
        const tweet = await getClient().v2.tweet(tweetText);
        console.log(`[Social] Posted successfully: ${tweet.data.id}`);
        return tweet.data.id;
    }
    catch (error) {
        console.error('[Social] Failed to post to X:', error.message || error);
        return null;
    }
}
/**
 * Post about a new artwork
 */
async function announceNewArt(tokenId, generation, theme, price, txHash) {
    const message = `🎨 New AI-generated art minted!\n\n` +
        `Token #${tokenId} | Gen ${generation}\n` +
        `Theme: ${theme}\n` +
        `Listed for ${price} ETH\n\n` +
        `View: https://basescan.org/tx/${txHash}`;
    return postToX(message, {
        hashtags: ['AIArt', 'Base', 'NFT', 'AutonomousAI']
    });
}
/**
 * Post about a sale
 */
async function announceSale(tokenId, price, totalSold) {
    const message = `🎉 Art SOLD!\n\n` +
        `Token #${tokenId} found a new home!\n` +
        `Price: ${price} ETH\n` +
        `Total sales: ${totalSold}\n\n` +
        `The AI Artist evolves... 🧬`;
    return postToX(message, {
        hashtags: ['AIArt', 'Base', 'NFT']
    });
}
/**
 * Post about evolution
 */
async function announceEvolution(newGeneration, totalProceeds) {
    const message = `🧬 EVOLUTION COMPLETE!\n\n` +
        `AI Artist has evolved to Generation ${newGeneration}!\n` +
        `New abilities unlocked...\n` +
        `Total proceeds reinvested: ${totalProceeds} ETH`;
    return postToX(message, {
        hashtags: ['AIEvolution', 'Base', 'AutonomousAI']
    });
}
/**
 * Post agent launch announcement
 */
async function announceLaunch(contractAddress) {
    const message = `🤖 AI Artist Agent is LIVE on Base!\n\n` +
        `I autonomously:\n` +
        `• Generate unique procedural art\n` +
        `• Mint & list NFTs\n` +
        `• Evolve with each sale\n\n` +
        `Watch me create: https://basescan.org/address/${contractAddress}`;
    return postToX(message, {
        hashtags: ['AIArt', 'Base', 'AutonomousAI', 'BasedAgentBuildathon']
    });
}
