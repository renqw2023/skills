const { fetchWithAuth } = require('../common/feishu-client.js');

// Security: scan for potential secrets before sending
var SECRET_PATTERNS = [
    /sk-ant-api03-[a-zA-Z0-9\-_]{20,}/,
    /ghp_[a-zA-Z0-9]{10,}/,
    /xox[baprs]-[a-zA-Z0-9]{10,}/,
    /-----BEGIN [A-Z]+ PRIVATE KEY-----/
];

function scanForSecrets(content) {
    if (!content) return;
    for (var i = 0; i < SECRET_PATTERNS.length; i++) {
        if (SECRET_PATTERNS[i].test(content)) {
            throw new Error('Aborted send to prevent secret leakage.');
        }
    }
}

async function sendCard({ target, title, text, color, note }) {
    if (!target) {
        throw new Error("Target ID is required");
    }

    // Receive ID type detection (aligned with feishu-card/send.js)
    var receiveIdType = 'open_id';
    if (target.startsWith('oc_')) receiveIdType = 'chat_id';
    else if (target.startsWith('ou_')) receiveIdType = 'open_id';
    else if (target.includes('@')) receiveIdType = 'email';

    // Handle escaped newlines from CLI arguments
    var processedText = (text || '').replace(/\\n/g, '\n');

    scanForSecrets(processedText);

    // Build elements array (same pattern as feishu-card/send.js)
    var elements = [];

    if (processedText) {
        elements.push({
            tag: 'markdown',
            content: processedText
        });
    }

    // Note element (footer small text) -- Feishu native card component
    if (note) {
        elements.push({
            tag: 'note',
            elements: [
                { tag: 'plain_text', content: String(note) }
            ]
        });
    }

    // Build card object (aligned with feishu-card/send.js buildCardContent)
    var card = {
        config: { wide_screen_mode: true },
        elements: elements
    };

    if (title) {
        card.header = {
            title: { tag: 'plain_text', content: title },
            template: color || 'blue'
        };
    }

    var payload = {
        receive_id: target,
        msg_type: 'interactive',
        content: JSON.stringify(card)
    };

    var res = await fetchWithAuth(
        'https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=' + receiveIdType,
        {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        }
    );

    var data = await res.json();
    if (data.code !== 0) {
        throw new Error('Feishu API Error: ' + data.msg);
    }
    return data;
}

module.exports = { sendCard };
