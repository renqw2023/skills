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
const dotenv = __importStar(require("dotenv"));
dotenv.config();
const commander_1 = require("commander");
const generateArt_1 = require("./skills/generateArt");
const evolve_1 = require("./skills/evolve");
const social_1 = require("./skills/social");
const mintNFT_1 = require("./skills/mintNFT");
const listNFT_1 = require("./skills/listNFT");
const monitorSales_1 = require("./skills/monitorSales");
const program = new commander_1.Command();
program
    .name('nft-skill')
    .description('Autonomous AI Artist Agent CLI for OpenClaw')
    .version('1.0.0');
program
    .command('generate')
    .description('Generate new art and upload to IPFS')
    .requiredOption('-g, --generation <number>', 'Generation number', parseInt)
    .requiredOption('-t, --theme <string>', 'Art theme description')
    .action(async (options) => {
    try {
        console.log(JSON.stringify({ status: 'running', message: 'Generating art...' }));
        const result = await (0, generateArt_1.createAndUploadArt)(options.generation, options.theme);
        console.log(JSON.stringify({ status: 'success', result }));
    }
    catch (error) {
        console.error(JSON.stringify({ status: 'error', message: error.message }));
        process.exit(1);
    }
});
program
    .command('evolve')
    .description('Trigger agent evolution')
    .requiredOption('-p, --proceeds <string>', 'Total sales proceeds in ETH')
    .requiredOption('-g, --generation <number>', 'Current generation', parseInt)
    .requiredOption('--trigger <string>', 'Reason for evolution')
    .action(async (options) => {
    try {
        console.log(JSON.stringify({ status: 'running', message: 'Evolving agent...' }));
        const result = (0, evolve_1.evolveAgent)({
            proceeds: options.proceeds,
            generation: options.generation,
            trigger: options.trigger
        });
        console.log(JSON.stringify({ status: 'success', result }));
    }
    catch (error) {
        console.error(JSON.stringify({ status: 'error', message: error.message }));
        process.exit(1);
    }
});
program
    .command('tweet')
    .description('Post a tweet')
    .requiredOption('-c, --content <string>', 'Tweet content')
    .action(async (options) => {
    try {
        console.log(JSON.stringify({ status: 'running', message: 'Posting tweet...' }));
        const result = await (0, social_1.postToX)(options.content);
        if (result) {
            console.log(JSON.stringify({ status: 'success', result }));
        }
        else {
            throw new Error('Failed to post tweet');
        }
    }
    catch (error) {
        console.error(JSON.stringify({ status: 'error', message: error.message }));
        process.exit(1);
    }
});
program
    .command('mint')
    .description('Mint an NFT on Base with an IPFS metadata URI')
    .requiredOption('-m, --metadata-uri <string>', 'IPFS metadata URI (ipfs://... or bare hash)')
    .action(async (options) => {
    try {
        console.log(JSON.stringify({ status: 'running', message: 'Minting NFT...' }));
        const result = await (0, mintNFT_1.mintNFT)(options.metadataUri);
        console.log(JSON.stringify({ status: 'success', result }));
    }
    catch (error) {
        console.error(JSON.stringify({ status: 'error', message: error.message }));
        process.exit(1);
    }
});
program
    .command('list')
    .description('List an NFT on the marketplace')
    .requiredOption('-i, --token-id <string>', 'Token ID to list')
    .requiredOption('-p, --price <string>', 'Listing price in ETH')
    .action(async (options) => {
    try {
        console.log(JSON.stringify({ status: 'running', message: 'Listing NFT...' }));
        const result = await (0, listNFT_1.listNFT)(options.tokenId, options.price);
        console.log(JSON.stringify({ status: 'success', result }));
    }
    catch (error) {
        console.error(JSON.stringify({ status: 'error', message: error.message }));
        process.exit(1);
    }
});
program
    .command('monitor')
    .description('Watch for NFT sales (streams JSON events until Ctrl+C)')
    .option('-f, --from-block <number>', 'Start block for catching up on missed sales', parseInt)
    .action(async (options) => {
    try {
        console.log(JSON.stringify({ status: 'running', message: 'Starting sales monitor...' }));
        if (options.fromBlock) {
            await (0, monitorSales_1.checkRecentSales)(options.fromBlock, async (sale) => {
                console.log(JSON.stringify({ status: 'sale', result: sale }));
            });
        }
        const stop = (0, monitorSales_1.startSalesMonitor)(async (sale) => {
            console.log(JSON.stringify({ status: 'sale', result: sale }));
        });
        process.on('SIGINT', () => {
            stop();
            console.log(JSON.stringify({ status: 'stopped', message: 'Monitor stopped' }));
            process.exit(0);
        });
    }
    catch (error) {
        console.error(JSON.stringify({ status: 'error', message: error.message }));
        process.exit(1);
    }
});
program.parse(process.argv);
