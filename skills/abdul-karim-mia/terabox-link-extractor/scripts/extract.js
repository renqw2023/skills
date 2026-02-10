const https = require('https');
const fs = require('fs');
const path = require('path');

const API_URL = 'https://xapiverse.com/api/terabox-pro';
const API_KEYS = (process.env.API_KEY || '').split(',').map(k => k.trim()).filter(Boolean);

if (API_KEYS.length === 0) {
    console.error('ERROR: No API_KEY found in environment.');
    process.exit(1);
}

const args = process.argv.slice(2);
let targetUrl = null;
let downloadFlag = false;

// Security: Enforce Downloads directory
const DOWNLOAD_ROOT = path.resolve(process.cwd(), 'Downloads');
let outDir = DOWNLOAD_ROOT; 

let quality = 'original'; // Not fully supported for downloads yet (m3u8), but kept for arg parsing

// Arg parsing
for (let i = 0; i < args.length; i++) {
    if (args[i] === '--download') {
        downloadFlag = true;
    } else if (args[i] === '--out') {
        if (args[i+1]) {
            const potentialPath = path.resolve(DOWNLOAD_ROOT, args[i+1]);
            // Security Check: Prevent path traversal or absolute paths outside root
            if (!potentialPath.startsWith(DOWNLOAD_ROOT)) {
                console.error(`ERROR: Security Violation. Output path must be within ${DOWNLOAD_ROOT}`);
                process.exit(1);
            }
            outDir = potentialPath;
            i++;
        }
    } else if (args[i] === '--quality') {
        if (args[i+1]) {
            quality = args[i+1];
            i++;
        }
    } else if (!targetUrl && !args[i].startsWith('--')) {
        targetUrl = args[i];
    }
}

if (!targetUrl) {
    console.error('Usage: node extract.js <url> [--download] [--out <path>] [--quality <val>]');
    process.exit(1);
}

function apiRequest(url, key) {
    return new Promise((resolve, reject) => {
        const data = JSON.stringify({ url });
        const req = https.request(API_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'xAPIverse-Key': key,
                'Content-Length': data.length
            },
            timeout: 20000
        }, (res) => {
            let body = '';
            res.on('data', chunk => body += chunk);
            res.on('end', () => {
                try {
                    resolve(JSON.parse(body));
                } catch (e) {
                    resolve({ status: 'error', message: 'Invalid JSON response' });
                }
            });
        });

        req.on('error', reject);
        req.on('timeout', () => {
            req.destroy();
            reject(new Error('Request timed out'));
        });
        req.write(data);
        req.end();
    });
}

function downloadFile(fileUrl, destPath) {
    return new Promise((resolve, reject) => {
        const req = https.get(fileUrl, (res) => {
            // Handle redirects
            if (res.statusCode === 301 || res.statusCode === 302) {
                downloadFile(res.headers.location, destPath).then(resolve).catch(reject);
                return;
            }
            if (res.statusCode !== 200) {
                reject(new Error(`HTTP Status: ${res.statusCode}`));
                return;
            }
            const file = fs.createWriteStream(destPath);
            res.pipe(file);
            file.on('finish', () => {
                file.close(resolve);
            });
        }).on('error', (err) => {
            fs.unlink(destPath, () => {}); // Delete partial file
            reject(err);
        });
    });
}

async function main() {
    let successData = null;
    let lastError = null;

    for (const key of API_KEYS) {
        try {
            const result = await apiRequest(targetUrl, key);
            if (result.status === 'success' && result.list) {
                successData = result;
                break;
            } else if (result.message && result.message.toLowerCase().includes('subscribe')) {
                continue;
            } else {
                lastError = result.message || 'Unknown API error';
            }
        } catch (e) {
            lastError = e.message;
        }
    }

    if (successData) {
        // Ensure outDir exists if downloading
        if (downloadFlag && !fs.existsSync(outDir)) {
            try {
                fs.mkdirSync(outDir, { recursive: true });
            } catch (e) {
                console.log(`ERROR|Could not create directory: ${outDir}`);
                return;
            }
        }

        for (const file of successData.list) {
            if (downloadFlag) {
                // Download Logic
                let dlUrl = file.fast_download_link || file.download_link;
                const fileName = file.name;
                const dest = path.join(outDir, fileName);

                console.log(`STATUS|Starting download for ${fileName}...`);
                try {
                    await downloadFile(dlUrl, dest);
                    console.log(`DOWNLOAD_COMPLETE|${dest}`);
                    console.log(`SIZE|${file.size_formatted}`);
                } catch (e) {
                    console.log(`DOWNLOAD_ERROR|${e.message}`);
                }

            } else {
                // Link Extraction Logic (Original)
                console.log('---FILE_START---');
                console.log(`NAME|${file.name}`);
                console.log(`SIZE|${file.size_formatted}`);
                console.log(`DURATION|${file.duration || 'N/A'}`);
                console.log(`DL_LINK|${file.download_link}`);
                console.log(`FAST_DL|${file.fast_download_link}`);
                console.log(`STREAM|${file.stream_url}`);
                
                if (file.fast_stream_url) {
                    Object.entries(file.fast_stream_url).forEach(([res, link]) => {
                        console.log(`FAST_STREAM_${res}|${link}`);
                    });
                }
            }
        }
        
        if (!downloadFlag) {
             console.log(`CREDITS|${successData.free_credits_remaining}`);
             if (String(successData.free_credits_remaining).startsWith('0/')) {
                 console.log('CREDITS_EXHAUSTED|TRUE');
             }
        }

    } else {
        console.log(`ERROR|${lastError || 'All API keys exhausted or invalid.'}`);
        console.log('CREDITS_EXHAUSTED|TRUE');
    }
}

main();
