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
exports.listNFT = listNFT;
exports.checkListing = checkListing;
/**
 * List NFT Skill
 * Handles listing NFTs on the marketplace
 */
const ethers_1 = require("ethers");
const fs = __importStar(require("fs"));
function getPrivateKey() {
    if (process.env.PRIVATE_KEY_FILE) {
        return fs.readFileSync(process.env.PRIVATE_KEY_FILE, 'utf8').trim();
    }
    return process.env.BASE_PRIVATE_KEY;
}
const MARKETPLACE_ABI = [
    'function listItem(address nftAddress, uint256 tokenId, uint256 price) external',
    'function getListing(address nftAddress, uint256 tokenId) external view returns (tuple(address seller, uint256 price, bool active))'
];
const NFT_ABI = [
    'function approve(address to, uint256 tokenId) external',
    'function setApprovalForAll(address operator, bool approved) external',
    'function isApprovedForAll(address owner, address operator) external view returns (bool)',
    'function ownerOf(uint256 tokenId) external view returns (address)'
];
async function listNFT(tokenId, priceInEth) {
    const provider = new ethers_1.ethers.JsonRpcProvider(process.env.BASE_RPC_URL);
    const wallet = new ethers_1.ethers.Wallet(getPrivateKey(), provider);
    const nftContract = new ethers_1.ethers.Contract(process.env.NFT_CONTRACT_ADDRESS, NFT_ABI, wallet);
    const marketplaceContract = new ethers_1.ethers.Contract(process.env.MARKETPLACE_ADDRESS, MARKETPLACE_ABI, wallet);
    const priceWei = ethers_1.ethers.parseEther(priceInEth);
    console.log(`[List] Listing Token #${tokenId} for ${priceInEth} ETH`);
    try {
        // Check ownership
        const owner = await nftContract.ownerOf(tokenId);
        if (owner.toLowerCase() !== wallet.address.toLowerCase()) {
            return { success: false, price: priceInEth, error: 'Not the owner' };
        }
        // Check if marketplace is approved
        const isApproved = await nftContract.isApprovedForAll(wallet.address, process.env.MARKETPLACE_ADDRESS);
        if (!isApproved) {
            console.log('[List] Approving marketplace...');
            const approveTx = await nftContract.setApprovalForAll(process.env.MARKETPLACE_ADDRESS, true);
            await approveTx.wait();
            console.log('[List] Marketplace approved');
        }
        // List the item
        const listTx = await marketplaceContract.listItem(process.env.NFT_CONTRACT_ADDRESS, tokenId, priceWei);
        console.log(`[List] Listing transaction: ${listTx.hash}`);
        const receipt = await listTx.wait();
        console.log(`[List] ✅ Listed successfully in block ${receipt.blockNumber}`);
        return {
            success: true,
            price: priceInEth,
            txHash: listTx.hash
        };
    }
    catch (error) {
        console.error('[List] Error listing NFT:', error.message);
        return { success: false, price: priceInEth, error: error.message };
    }
}
async function checkListing(tokenId) {
    const provider = new ethers_1.ethers.JsonRpcProvider(process.env.BASE_RPC_URL);
    const marketplaceContract = new ethers_1.ethers.Contract(process.env.MARKETPLACE_ADDRESS, MARKETPLACE_ABI, provider);
    try {
        const listing = await marketplaceContract.getListing(process.env.NFT_CONTRACT_ADDRESS, tokenId);
        return {
            listed: listing.active,
            price: listing.active ? ethers_1.ethers.formatEther(listing.price) : '0',
            seller: listing.seller
        };
    }
    catch (error) {
        return { listed: false, price: '0', seller: '' };
    }
}
