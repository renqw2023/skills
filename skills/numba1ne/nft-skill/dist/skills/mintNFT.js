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
exports.mintNFT = mintNFT;
exports.getWalletBalance = getWalletBalance;
exports.getWalletAddress = getWalletAddress;
exports.getTokenCount = getTokenCount;
/**
 * NFT Minting Skill
 * Handles minting NFTs on Base network
 */
const ethers_1 = require("ethers");
const fs = __importStar(require("fs"));
const dotenv = __importStar(require("dotenv"));
dotenv.config();
function getPrivateKey() {
    if (process.env.PRIVATE_KEY_FILE) {
        return fs.readFileSync(process.env.PRIVATE_KEY_FILE, 'utf8').trim();
    }
    return process.env.BASE_PRIVATE_KEY;
}
// Minimal ERC721 ABI for minting
const NFT_ABI = [
    'function safeMint(address to, string memory uri) public returns (uint256)',
    'function tokenCounter() public view returns (uint256)',
    'event Transfer(address indexed from, address indexed to, uint256 indexed tokenId)',
    'event ArtMinted(address indexed to, uint256 indexed tokenId, string uri)'
];
async function retryWithBackoff(fn, retries = 3, delay = 1000, factor = 2) {
    try {
        return await fn();
    }
    catch (error) {
        if (retries <= 0)
            throw error;
        // Check for specific retryable errors (optional hardcoding common RPC errors)
        const isNetworkError = error.code === 'NETWORK_ERROR' ||
            error.code === 'TIMEOUT' ||
            error.message.includes('rate limit') ||
            error.message.includes('503');
        if (!isNetworkError && !error.message.includes('nonce')) {
            // If it's a logic error (e.g., revert), maybe don't retry? 
            // But gas spikes can look like reverts sometimes.
            // We'll retry anyway for robustness in this simple agent.
        }
        console.log(`[Mint] Error: ${error.message}. Retrying in ${delay}ms... (${retries} left)`);
        await new Promise(resolve => setTimeout(resolve, delay));
        return retryWithBackoff(fn, retries - 1, delay * factor, factor);
    }
}
async function mintNFT(metadataUri) {
    const provider = new ethers_1.ethers.JsonRpcProvider(process.env.BASE_RPC_URL);
    const wallet = new ethers_1.ethers.Wallet(getPrivateKey(), provider);
    const contract = new ethers_1.ethers.Contract(process.env.NFT_CONTRACT_ADDRESS, NFT_ABI, wallet);
    console.log(`[Mint] Minting NFT with metadata: ipfs://${metadataUri}`);
    console.log(`[Mint] Wallet: ${wallet.address}`);
    // Estimate gas first (with retry)
    const gasEstimate = await retryWithBackoff(async () => {
        return await contract.safeMint.estimateGas(wallet.address, `ipfs://${metadataUri}`);
    });
    console.log(`[Mint] Estimated gas: ${gasEstimate.toString()}`);
    // Send transaction with 20% buffer (with retry)
    const tx = await retryWithBackoff(async () => {
        return await contract.safeMint(wallet.address, `ipfs://${metadataUri}`, { gasLimit: (gasEstimate * 120n) / 100n });
    });
    console.log(`[Mint] Transaction sent: ${tx.hash}`);
    const receipt = await tx.wait();
    // Parse Transfer event to get tokenId
    const transferEvent = receipt.logs.find((log) => log.topics[0] === ethers_1.ethers.id('Transfer(address,address,uint256)'));
    const tokenId = transferEvent
        ? ethers_1.ethers.toBigInt(transferEvent.topics[3]).toString()
        : 'unknown';
    console.log(`[Mint] Success! Token #${tokenId} minted in block ${receipt.blockNumber}`);
    return {
        tokenId,
        txHash: tx.hash,
        blockNumber: receipt.blockNumber,
        gasUsed: receipt.gasUsed.toString()
    };
}
async function getWalletBalance() {
    const provider = new ethers_1.ethers.JsonRpcProvider(process.env.BASE_RPC_URL);
    const wallet = new ethers_1.ethers.Wallet(getPrivateKey(), provider);
    const balance = await provider.getBalance(wallet.address);
    return ethers_1.ethers.formatEther(balance);
}
async function getWalletAddress() {
    const wallet = new ethers_1.ethers.Wallet(getPrivateKey());
    return wallet.address;
}
async function getTokenCount() {
    const provider = new ethers_1.ethers.JsonRpcProvider(process.env.BASE_RPC_URL);
    const contract = new ethers_1.ethers.Contract(process.env.NFT_CONTRACT_ADDRESS, NFT_ABI, provider);
    const count = await contract.tokenCounter();
    return Number(count);
}
