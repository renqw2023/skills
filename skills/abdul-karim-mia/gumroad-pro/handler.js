const { spawnSync } = require('child_process');
const path = require('path');
const fs = require('fs');

const GUMROAD_SCRIPT = path.join(__dirname, 'scripts', 'gumroad-pro.js');
const PENDING_INPUT_FILE = path.join(__dirname, 'pending_input.json');

// Channels with native button support
const BUTTON_CHANNELS = ['telegram', 'discord', 'slack', 'webchat'];

function runGumroad(args) {
  try {
    const result = spawnSync('node', [GUMROAD_SCRIPT, ...args], { encoding: 'utf8', env: process.env });
    if (result.error) throw result.error;
    // Return stdout, fallback to stderr if stdout is empty (for error messages)
    return result.stdout || result.stderr || '';
  } catch (e) {
    return `Error: ${e.message}`;
  }
}

// Regex Parsers
const PRODUCT_REGEX = /- (.*?) \(ID: (.*?)\) \| Price: (.*?) \| Sales: (.*?) \| Published: (.*)/;
const SALE_REGEX = /- (.*?) \| (.*?) \| (.*?) \| (.*?) \| ID: (.*)/;
const PAYOUT_REGEX = /- (.*?) (.*?) \| (.*?) \| (.*?) \| ID: (.*)/;
const SALE_DETAILS_REGEX = /🆔 ID: (.*?)\n📦 Product ID: (.*?)\n/;
const LICENSE_KEY_REGEX = /🔑 License: (.*?)\n/;
const DISCOUNT_REGEX = /- (.*?) \(ID: (.*?)\) \| Used: (.*?) \| Val: (.*)/;
const CUSTOM_FIELD_REGEX = /- (.*?) \| Required: (.*)/;
const WEBHOOK_REGEX = /- (.*?) \(ID: (.*?)\)/;

/**
 * Check if channel supports inline buttons
 */
function supportsButtons(ctx) {
  const channel = ctx.channel?.toLowerCase() || 'unknown';
  const capabilities = ctx.capabilities || [];
  return BUTTON_CHANNELS.includes(channel) && 
         (capabilities.includes('inlineButtons') || capabilities.includes('buttons'));
}

/**
 * Adaptive response renderer (Hybrid Mode)
 */
function renderResponse(ctx, data) {
  const { text, buttons, action = 'edit', interrupt = true, messageId } = data;
  const canUseButtons = supportsButtons(ctx);
  
  // Text conversion logic (Numbered List)
  let adaptiveText = text + '\n\n';
  const flatButtons = buttons.flat();
  const mapping = {};
  
  flatButtons.forEach((btn, index) => {
    const num = index + 1;
    adaptiveText += `${num}. ${btn.text}\n`;
    mapping[num.toString()] = btn.callback_data;
  });

  adaptiveText += '\n*Reply with a number to select.*';

  // ALWAYS Store mapping in session for handling number replies (Hybrid Support)
  if (ctx.session) {
    ctx.session.gpMenuMapping = {
      mapping,
      timestamp: Date.now()
    };
  }

  if (canUseButtons) {
    return { text: adaptiveText, buttons, action, interrupt, messageId };
  } else {
    // Force 'send' for text channels to ensure visibility, as 'edit' might not be supported
    return { text: adaptiveText, action: 'send', interrupt };
  }
}

module.exports = {
  name: 'gumroad-pro',
  version: '4.1.0',
  description: 'Gumroad Pro - Adaptive Multi-Channel Suite',
  
  commands: {
    gumroad_pro: {
      description: 'Open Gumroad Pro Menu',
      aliases: ['gumroad', 'gp', 'gumroad-pro', 'gumroad_pro'],
      async execute(ctx) {
        return renderResponse(ctx, { ...getMainMenu(), action: 'send' });
      }
    }
  },

  async onMessage(ctx, next) {
    let text = ctx.message?.text?.trim();

    // --- HANDLE NUMBER REPLIES (Text Channels) ---
    if (/^\d+$/.test(text) && ctx.session?.gpMenuMapping) {
        const mapping = ctx.session.gpMenuMapping.mapping;
        const elapsed = Date.now() - ctx.session.gpMenuMapping.timestamp;
        
        // Mapping valid for 15 minutes
        if (elapsed < 15 * 60 * 1000 && mapping[text]) {
            text = mapping[text];
        }
    }

    // --- HANDLE PENDING INPUT ---
    if (fs.existsSync(PENDING_INPUT_FILE)) {
      try {
        const state = JSON.parse(fs.readFileSync(PENDING_INPUT_FILE));
        if (state.userId === ctx.message.from.id) {
          fs.unlinkSync(PENDING_INPUT_FILE); // clear state
          
          if (state.action === 'create_field') {
            runGumroad(['custom-fields', 'create', '--product', state.pid, '--name', text, '--required', 'false']);
            return renderResponse(ctx, { text: `✅ Created field: "${text}"`, buttons: [[{ text: '🔙 Back', callback_data: `gp:cf:${state.pid}` }]], action: 'edit', interrupt: true });
          }
          else if (state.action === 'create_webhook') {
            runGumroad(['subscriptions', 'create', '--type', state.resource, '--url', text]);
            return renderResponse(ctx, { text: `✅ Subscribed to '${state.resource}' at: ${text}`, buttons: [[{ text: '📡 Back', callback_data: 'gp:subs' }]], action: 'edit', interrupt: true });
          }
          else if (state.action === 'mark_shipped') {
             runGumroad(['sales', 'mark-shipped', '--id', state.sid, '--tracking', text]);
             return renderResponse(ctx, { text: `✅ Marked as Shipped (Tracking: ${text})`, buttons: [[{ text: '🔙 Back to Sale', callback_data: `gp:sale:${state.sid}` }]], action: 'edit', interrupt: true });
          }
          else if (state.action === 'search_sales_email') {
             return renderResponse(ctx, { ...getSalesMenu(text), action: 'edit', interrupt: true });
          }
          else if (state.action === 'disc_name') {
              const newState = { ...state, name: text, action: 'disc_val' };
              fs.writeFileSync(PENDING_INPUT_FILE, JSON.stringify(newState));
              return renderResponse(ctx, { text: `🎟️ **New Discount: "${text}"**\n\nPlease reply with the **Amount**.`, action: 'edit', interrupt: true });
          }
          else if (state.action === 'disc_val') {
              const val = parseInt(text);
              return renderResponse(ctx, { 
                  text: `🎟️ **Discount: ${state.name} (${val})**\n\nSelect the **Type**:`, 
                  buttons: [
                      [{ text: '💵 Fixed (Cents)', callback_data: `gp:disc_final:${state.pid}:${state.name}:${val}:cents` }],
                      [{ text: '🏷️ Percentage (%)', callback_data: `gp:disc_final:${state.pid}:${state.name}:${val}:percent` }],
                      [{ text: '❌ Cancel', callback_data: `gp:discounts:${state.pid}` }]
                  ],
                  action: 'edit', interrupt: true 
              });
          }
          else if (state.action === 'disc_edit_name') {
              const newState = { ...state, newName: text === 'skip' ? null : text, action: 'disc_edit_limit' };
              fs.writeFileSync(PENDING_INPUT_FILE, JSON.stringify(newState));
              return renderResponse(ctx, { text: `📝 **Editing Discount**\n\nPlease reply with the new **Usage Limit**.\n(Type 'skip' to keep current)`, action: 'edit', interrupt: true });
          }
          else if (state.action === 'disc_edit_limit') {
              const limit = text === 'skip' ? null : text;
              const args = ['discounts', 'update', '--product', state.pid, '--id', state.did];
              if (state.newName) args.push('--name', state.newName);
              if (limit !== null) args.push('--limit', limit);
              runGumroad(args);
              return renderResponse(ctx, { text: `✅ Discount updated.`, buttons: [[{ text: '🔙 Back', callback_data: `gp:disc_det:${state.pid}:${state.did}` }]], action: 'edit', interrupt: true });
          }
        }
      } catch (e) {} 
    }

    if (!text || !text.startsWith('gp:')) return next();

    // --- NAVIGATION (Always Clear State) ---
    if (text === 'gp:main' || text === 'gp:products' || text === 'gp:sales' || text === 'gp:payouts' || text === 'gp:subs' || text === 'gp:whoami') {
      if (fs.existsSync(PENDING_INPUT_FILE)) fs.unlinkSync(PENDING_INPUT_FILE);
    }

    if (text === 'gp:main') return renderResponse(ctx, { ...getMainMenu(), action: 'edit', interrupt: true });
    
    // --- PRODUCTS ---
    if (text === 'gp:products') return renderResponse(ctx, { ...getProductsMenu(), action: 'edit', interrupt: true });
    if (text.startsWith('gp:prod:')) return renderResponse(ctx, { ...getProductDetails(text.split(':')[2]), action: 'edit', interrupt: true });
    if (text.startsWith('gp:prod_toggle:')) {
      const [_, __, id, currentState] = text.split(':');
      runGumroad(['products', currentState === 'true' ? 'disable' : 'enable', '--id', id]);
      return renderResponse(ctx, { ...getProductDetails(id), action: 'edit', interrupt: true });
    }
    if (text.startsWith('gp:prod_del_ask:')) {
        const id = text.split(':')[2];
        return renderResponse(ctx, {
            text: '⚠️ **DELETE PRODUCT?**\nThis will permanently remove the product and all associated data. This cannot be undone.',
            buttons: [[{ text: '🔥 YES, DELETE', callback_data: `gp:prod_del_do:${id}` }], [{ text: '❌ Cancel', callback_data: `gp:prod:${id}` }]],
            action: 'edit', interrupt: true
        });
    }
    if (text.startsWith('gp:prod_del_do:')) {
        const id = text.split(':')[2];
        runGumroad(['products', 'delete', '--id', id]);
        return renderResponse(ctx, { ...getProductsMenu(), action: 'edit', interrupt: true });
    }
    if (text.startsWith('gp:vc:')) {
        const pid = text.split(':')[2];
        return renderResponse(ctx, { ...getVariantCategoriesMenu(pid), action: 'edit', interrupt: true });
    }
    if (text.startsWith('gp:variants:')) {
        const [_, __, pid, cid] = text.split(':');
        return renderResponse(ctx, { ...getVariantsListMenu(pid, cid), action: 'edit', interrupt: true });
    }

    // --- SALES ---
    if (text === 'gp:sales') return renderResponse(ctx, { ...getSalesMenu(), action: 'edit', interrupt: true });
    if (text.startsWith('gp:sales_page:')) {
        const parts = text.split(':');
        return renderResponse(ctx, { ...getSalesMenu(parts[3] === 'null' ? null : parts[3], parts[2]), action: 'edit', interrupt: true });
    }
    if (text === 'gp:sales_search_ask') {
        const state = { userId: ctx.message.from.id, action: 'search_sales_email' };
        fs.writeFileSync(PENDING_INPUT_FILE, JSON.stringify(state));
        return renderResponse(ctx, { text: '🔍 **Search Sales**\n\nPlease reply with the **Customer Email**.', buttons: [[{ text: '❌ Cancel', callback_data: 'gp:sales' }]], action: 'edit', interrupt: true });
    }
    if (text.startsWith('gp:sale:')) return renderResponse(ctx, { ...getSaleDetails(text.split(':')[2]), action: 'edit', interrupt: true });
    
    if (text.startsWith('gp:sale_refund_ask:')) {
        const sid = text.split(':')[2];
        return renderResponse(ctx, {
            text: '⚠️ **REFUND SALE?**\nThis will refund the customer. This action is irreversible.',
            buttons: [[{ text: '🔥 YES, REFUND', callback_data: `gp:sale_refund_do:${sid}` }], [{ text: '❌ Cancel', callback_data: `gp:sale:${sid}` }]],
            action: 'edit', interrupt: true
        });
    }
    if (text.startsWith('gp:sale_refund_do:')) {
        const sid = text.split(':')[2];
        runGumroad(['sales', 'refund', '--id', sid]);
        return renderResponse(ctx, { ...getSaleDetails(sid), action: 'edit', interrupt: true });
    }
    if (text.startsWith('gp:sale_resend:')) {
        const sid = text.split(':')[2];
        runGumroad(['sales', 'resend-receipt', '--id', sid]);
        return renderResponse(ctx, { text: '✅ Receipt resent successfully.', buttons: [[{ text: '🔙 Back', callback_data: `gp:sale:${sid}` }]], action: 'edit', interrupt: true });
    }
    if (text.startsWith('gp:sale_ship_ask:')) {
        const sid = text.split(':')[3];
        const state = { userId: ctx.message.from.id, sid: sid, action: 'mark_shipped' };
        fs.writeFileSync(PENDING_INPUT_FILE, JSON.stringify(state));
        return renderResponse(ctx, { text: '🚚 **Mark as Shipped**\n\nPlease reply with the **Tracking URL** or number.', buttons: [[{ text: '❌ Cancel', callback_data: `gp:sale:${sid}` }]], action: 'edit', interrupt: true });
    }

    if (text.startsWith('gp:sub_det:')) {
        const [_, __, subId, saleId] = text.split(':');
        const output = runGumroad(['subscribers', 'details', '--id', subId]);
        return renderResponse(ctx, {
            text: `👤 **Subscriber Profile**\n${output}`,
            buttons: [[{ text: '🔙 Back to Sale', callback_data: `gp:sale:${saleId}` }]],
            action: 'edit', interrupt: true
        });
    }

    // --- PAYOUTS ---
    if (text === 'gp:payouts') return renderResponse(ctx, { ...getPayoutsMenu(), action: 'edit', interrupt: true });
    if (text.startsWith('gp:payout_page:')) {
        const parts = text.split(':');
        return renderResponse(ctx, { ...getPayoutsMenu(parts[2]), action: 'edit', interrupt: true });
    }
    if (text.startsWith('gp:payout_det:')) {
        return renderResponse(ctx, { ...getPayoutDetails(text.split(':')[2]), action: 'edit', interrupt: true });
    }

    // --- DISCOUNTS ---
    if (text.startsWith('gp:discounts:')) return renderResponse(ctx, { ...getDiscountsMenu(text.split(':')[2]), action: 'edit', interrupt: true });
    if (text.startsWith('gp:disc_det:')) {
        const [_, __, pid, did] = text.split(':');
        return renderResponse(ctx, { ...getDiscountDetails(pid, did), action: 'edit', interrupt: true });
    }
    if (text.startsWith('gp:de:')) {
        const [_, __, pid, did] = text.split(':');
        const state = { userId: ctx.message.from.id, pid: pid, did: did, action: 'disc_edit_name' };
        fs.writeFileSync(PENDING_INPUT_FILE, JSON.stringify(state));
        return renderResponse(ctx, { text: `📝 **Editing Discount**\n\nPlease reply with the new **Code Name**.\n(Type 'skip' to keep current)`, buttons: [[{ text: '❌ Cancel', callback_data: `gp:disc_det:${pid}:${did}` }]], action: 'edit', interrupt: true });
    }
    if (text.startsWith('gp:dd:')) {
        const [_, __, pid, did] = text.split(':');
        return renderResponse(ctx, {
            text: '⚠️ **DELETE DISCOUNT?**\nThis will permanently remove this code.',
            buttons: [[{ text: '🔥 YES, DELETE', callback_data: `gp:dc:${pid}:${did}` }], [{ text: '❌ Cancel', callback_data: `gp:disc_det:${pid}:${did}` }]],
            action: 'edit', interrupt: true
        });
    }
    if (text.startsWith('gp:dc:')) {
        const [_, __, pid, did] = text.split(':');
        runGumroad(['discounts', 'delete', '--product', pid, '--id', did]);
        return renderResponse(ctx, { ...getDiscountsMenu(pid), action: 'edit', interrupt: true });
    }
    if (text.startsWith('gp:disc_ask:')) {
        const pid = text.split(':')[2];
        const state = { userId: ctx.message.from.id, pid: pid, action: 'disc_name' };
        fs.writeFileSync(PENDING_INPUT_FILE, JSON.stringify(state));
        return renderResponse(ctx, { text: '🎟️ **Create Discount**\n\nPlease reply with the **Code Name**.', buttons: [[{ text: '❌ Cancel', callback_data: `gp:discounts:${pid}` }]], action: 'edit', interrupt: true });
    }
    if (text.startsWith('gp:disc_final:')) {
        const [_, __, pid, name, val, type] = text.split(':');
        runGumroad(['discounts', 'create', '--product', pid, '--name', name, '--amount', val, '--type', type]);
        return renderResponse(ctx, { text: `✅ Discount created.`, buttons: [[{ text: '🔙 Back', callback_data: `gp:discounts:${pid}` }]], action: 'edit', interrupt: true });
    }

    // --- WEBHOOKS ---
    if (text === 'gp:subs') return renderResponse(ctx, { ...getSubscriptionsMenu(), action: 'edit', interrupt: true });
    if (text.startsWith('gp:sub_del_ask:')) {
        const id = text.split(':')[3];
        return renderResponse(ctx, {
            text: '⚠️ **DELETE WEBHOOK?**\nYou will stop receiving automated notifications at this URL.',
            buttons: [[{ text: '🔥 YES, DELETE', callback_data: `gp:sub_del_do:${id}` }], [{ text: '❌ Cancel', callback_data: 'gp:subs' }]],
            action: 'edit', interrupt: true
        });
    }
    if (text.startsWith('gp:sub_del_do:')) {
        const id = text.split(':')[3];
        runGumroad(['subscriptions', 'delete', '--id', id]);
        return renderResponse(ctx, { ...getSubscriptionsMenu(), action: 'edit', interrupt: true });
    }
    if (text.startsWith('gp:sub_ask:')) {
        const resource = text.split(':')[2];
        const state = { userId: ctx.message.from.id, resource, action: 'create_webhook' };
        fs.writeFileSync(PENDING_INPUT_FILE, JSON.stringify(state));
        return renderResponse(ctx, { text: `📡 **Create Webhook [${resource.toUpperCase()}]**\n\nPlease reply with the **Destination URL**.`, buttons: [[{ text: '❌ Cancel', callback_data: 'gp:subs' }]], action: 'edit', interrupt: true });
    }

    // --- ACCOUNT ---
    if (text === 'gp:whoami') {
        const output = runGumroad(['whoami']);
        return renderResponse(ctx, {
            text: `👤 **Account Info**\n${output}`,
            buttons: [[{ text: '🔙 Back', callback_data: 'gp:main' }]],
            action: 'edit', interrupt: true
        });
    }

    // --- CUSTOM FIELDS ---
    if (text.startsWith('gp:cf:')) {
        const pid = text.split(':')[2];
        return renderResponse(ctx, { ...getCustomFieldsMenu(pid), action: 'edit', interrupt: true });
    }
    if (text.startsWith('gp:cf_ask:')) {
        const pid = text.split(':')[2];
        const state = { userId: ctx.message.from.id, pid: pid, action: 'create_field' };
        fs.writeFileSync(PENDING_INPUT_FILE, JSON.stringify(state));
        return renderResponse(ctx, { text: '📝 **Create Custom Field**\n\nPlease reply with the **Field Name**.', buttons: [[{ text: '❌ Cancel', callback_data: `gp:cf:${pid}` }]], action: 'edit', interrupt: true });
    }
    if (text.startsWith('gp:cf_del:')) {
        const [_, __, pid, name] = text.split(':');
        runGumroad(['custom-fields', 'delete', '--product', pid, '--name', name]);
        return renderResponse(ctx, { ...getCustomFieldsMenu(pid), action: 'edit', interrupt: true });
    }

    // --- LICENSES ---
    if (text.startsWith('gp:lic_check:')) {
        const sid = text.split(':')[2];
        const details = runGumroad(['sales', 'details', '--id', sid]);
        const licMatch = details.match(LICENSE_KEY_REGEX), pidMatch = details.match(/📦 Product ID: (.*?)\n/);
        if (!licMatch || !pidMatch) return renderResponse(ctx, { text: '❌ Error.', action: 'edit', interrupt: true });
        const key = licMatch[1].trim(), pid = pidMatch[1].trim();
        const output = runGumroad(['licenses', 'verify', '--product', pid, '--key', key]);
        const isDisabled = output.includes('🔴 DISABLED');
        return renderResponse(ctx, {
            text: output,
            buttons: [
                [{ text: isDisabled ? '🟢 Enable License' : '🔴 Disable License', callback_data: `gp:lic_toggle:${sid}` }, { text: '📉 Decr. Count', callback_data: `gp:lic_decr:${sid}` }],
                [{ text: '🔄 Rotate Key', callback_data: `gp:lic_rot_ask:${sid}` }],
                [{ text: '🔙 Back to Sale', callback_data: `gp:sale:${sid}` }]
            ],
            action: 'edit', interrupt: true
        });
    }

    if (text.startsWith('gp:lic_toggle:')) {
        const sid = text.split(':')[2];
        const details = runGumroad(['sales', 'details', '--id', sid]);
        const licMatch = details.match(LICENSE_KEY_REGEX), pidMatch = details.match(/📦 Product ID: (.*?)\n/);
        if (licMatch && pidMatch) {
            const key = licMatch[1].trim(), pid = pidMatch[1].trim();
            const verify = runGumroad(['licenses', 'verify', '--product', pid, '--key', key]);
            const action = verify.includes('🔴 DISABLED') ? 'enable' : 'disable';
            runGumroad(['licenses', action, '--product', pid, '--key', key]);
            return renderResponse(ctx, { text: `✅ License ${action}d.`, buttons: [[{ text: '🔙 Back', callback_data: `gp:lic_check:${sid}` }]], action: 'edit', interrupt: true });
        }
    }
    if (text.startsWith('gp:lic_decr:')) {
        const sid = text.split(':')[2];
        const details = runGumroad(['sales', 'details', '--id', sid]);
        const licMatch = details.match(LICENSE_KEY_REGEX), pidMatch = details.match(/📦 Product ID: (.*?)\n/);
        if (licMatch && pidMatch) {
            runGumroad(['licenses', 'decrement', '--product', pidMatch[1].trim(), '--key', licMatch[1].trim()]);
            return renderResponse(ctx, { text: '📉 Usage count decremented.', buttons: [[{ text: '🔙 Back', callback_data: `gp:lic_check:${sid}` }]], action: 'edit', interrupt: true });
        }
    }
    if (text.startsWith('gp:lic_rot_ask:')) {
        const sid = text.split(':')[2];
        return renderResponse(ctx, {
            text: '⚠️ **ROTATE LICENSE KEY?**\nThe current key will be invalidated and a new one generated for the customer.',
            buttons: [[{ text: '🔄 YES, ROTATE', callback_data: `gp:lic_rot_do:${sid}` }], [{ text: '❌ Cancel', callback_data: `gp:lic_check:${sid}` }]],
            action: 'edit', interrupt: true
        });
    }
    if (text.startsWith('gp:lic_rot_do:')) {
        const sid = text.split(':')[2];
        const details = runGumroad(['sales', 'details', '--id', sid]);
        const licMatch = details.match(LICENSE_KEY_REGEX), pidMatch = details.match(/📦 Product ID: (.*?)\n/);
        if (licMatch && pidMatch) {
            runGumroad(['licenses', 'rotate', '--product', pidMatch[1].trim(), '--key', licMatch[1].trim()]);
            return renderResponse(ctx, { text: '🔄 License key rotated successfully.', buttons: [[{ text: '🔙 Back', callback_data: `gp:lic_check:${sid}` }]], action: 'edit', interrupt: true });
        }
    }

    return next();
  }
};

// --- View Generators ---

function getMainMenu() {
  return {
    text: '💎 **Gumroad Pro Dashboard**\n\nWelcome back, Sir. Your digital empire is summarized below. Use the control hub to monitor sales, manage products, and oversee your payouts in real-time.',
    buttons: [
      [{ text: '📦 Products', callback_data: 'gp:products' }, { text: '💸 Sales', callback_data: 'gp:sales' }],
      [{ text: '💰 Payouts', callback_data: 'gp:payouts' }, { text: '📡 Webhooks', callback_data: 'gp:subs' }],
      [{ text: '👤 Account', callback_data: 'gp:whoami' }, { text: '🔄 Refresh Dashboard', callback_data: 'gp:main' }]
    ]
  };
}

function getProductsMenu() {
  const output = runGumroad(['products', 'list']);
  const buttons = output.split('\n').filter(l => l.startsWith('-')).map(line => {
    const match = line.match(PRODUCT_REGEX);
    if (match) return [{ text: `${match[5] === 'true' ? '🟢' : '🔴'} ${match[1].substring(0, 40)}`, callback_data: `gp:prod:${match[2]}` }];
  }).filter(Boolean);
  buttons.push([{ text: '🔙 Back to Main Menu', callback_data: 'gp:main' }]);
  return { 
    text: '📦 **Product Inventory**\n\nSir, here is the complete list of your digital offerings. You can monitor sales volume, verify pricing, or toggle availability for each item.', 
    buttons 
  };
}

function getProductDetails(id) {
  const output = runGumroad(['products', 'details', '--id', id]);
  const isPublished = output.includes('- Published: true');
  return {
    text: `🛠️ **Product Management**\n\nDetailed specifications for the selected asset are listed below. You may adjust its visibility, manage variants, or configure custom checkout fields.\n\n${output.replace(/<[^>]*>?/gm, '').substring(0, 1000)}`,
    buttons: [
      [{ text: isPublished ? '🔴 Unpublish' : '🟢 Publish', callback_data: `gp:prod_toggle:${id}:${isPublished}` }, { text: '🎨 Variants', callback_data: `gp:vc:${id}` }],
      [{ text: '🎟️ Discounts', callback_data: `gp:discounts:${id}` }, { text: '📝 Custom Fields', callback_data: `gp:cf:${id}` }],
      [{ text: '🗑️ Delete', callback_data: `gp:prod_del_ask:${id}` }, { text: '🔙 Back to Products', callback_data: 'gp:products' }]
    ]
  }
}

function getSalesMenu(filterEmail = null, pageKey = null) {
  const args = ['sales', 'list'];
  if (filterEmail && filterEmail !== 'null') args.push('--email', filterEmail);
  if (pageKey) args.push('--page', pageKey);
  const output = runGumroad(args);
  const lines = output.split('\n').filter(l => l.startsWith('-'));
  const nextKeyMatch = output.match(/🔑 NEXT_PAGE_KEY: (.*)/);
  
  const title = filterEmail && filterEmail !== 'null' ? `🔎 **Search Results**\n\nDisplaying records matching: \`${filterEmail}\`` : '💸 **Transaction Ledger**\n\nSir, here are the most recent acquisitions by your customers. Select a transaction to view license keys or process refunds.';

  if (lines.length === 0) return { text: `🔍 **No Records Found**\n\nI couldn't find any transactions matching your criteria, Sir.`, buttons: [[{ text: '🔙 Back to Sales', callback_data: 'gp:sales' }]] };
  
  const buttons = lines.slice(0, 10).map(line => {
    const match = line.match(SALE_REGEX);
    // match[1] = Product, match[4] = Email, match[5] = ID
    if (match) return [{ text: `${match[4]} - ${match[1].substring(0, 30)}`, callback_data: `gp:sale:${match[5]}` }];
  }).filter(Boolean);
  
  const navRow = [{ text: '🔙 Back', callback_data: 'gp:main' }];
  if (nextKeyMatch) navRow.push({ text: '➡️ Next Page', callback_data: `gp:sales_page:${nextKeyMatch[1].trim()}:${filterEmail}` });
  else if (pageKey) navRow.push({ text: '🏠 First Page', callback_data: 'gp:sales' });
  
  // if (!filterEmail) buttons.push([{ text: '🔍 Search by Email', callback_data: 'gp:sales_search_ask' }]);
  buttons.push(navRow);
  
  return { text: title, buttons };
}

function getSaleDetails(id) {
  const output = runGumroad(['sales', 'details', '--id', id]);
  const buttons = [];
  
  const row1 = [{ text: '💸 Refund', callback_data: `gp:sale_refund_ask:${id}` }];
  if (output.includes('📦 Physical: true')) {
      row1.push({ text: '🚚 Mark Shipped', callback_data: `gp:sale_ship_ask:${id}` });
  }
  buttons.push(row1);

  const row2 = [{ text: '📩 Resend Receipt', callback_data: `gp:sale_resend:${id}` }];
  const licMatch = output.match(LICENSE_KEY_REGEX);
  if (licMatch) {
      row2.push({ text: '🔑 Check License', callback_data: `gp:lic_check:${id}` });
  }
  buttons.push(row2);
  
  const subMatch = output.match(/🆔 Subscription ID: (.*?)\n/);
  if (subMatch) {
      buttons.push([{ text: '👤 Subscriber Info', callback_data: `gp:sub_det:${subMatch[1].trim()}:${id}` }]);
  }

  buttons.push([{ text: '🔙 Back to Sales', callback_data: 'gp:sales' }, { text: '🏠 Main Menu', callback_data: 'gp:main' }]);
  
  return { text: `📜 **Transaction Intelligence**\n\nFull details of the customer purchase are presented below, Sir.\n\n${output}`, buttons };
}

function getPayoutsMenu(pageKey = null) {
  const args = ['payouts', 'list'];
  if (pageKey) args.push('--page', pageKey);
  const output = runGumroad(args);
  const lines = output.split('\n').filter(l => l.startsWith('-'));
  const nextKeyMatch = output.match(/🔑 NEXT_PAGE_KEY: (.*)/);
  
  const buttons = lines.slice(0, 10).map(line => {
    const match = line.match(PAYOUT_REGEX);
    if (match) {
        const id = match[5].trim();
        if (id === '✨ Upcoming') return [{ text: `✨ Upcoming: ${match[1]} ${match[2]}`, callback_data: 'noop' }];
        return [{ text: `${match[1]} ${match[2]} - ${match[3]}`, callback_data: `gp:payout_det:${id}` }];
    }
  }).filter(Boolean);
  
  const navRow = [{ text: '🔙 Back', callback_data: 'gp:main' }];
  if (nextKeyMatch) navRow.push({ text: '➡️ Next Page', callback_data: `gp:payout_page:${nextKeyMatch[1].trim()}` });
  else if (pageKey) navRow.push({ text: '🏠 First Page', callback_data: 'gp:payouts' });
  buttons.push(navRow);
  
  return { text: '💰 **Revenue & Payout History**\n\nSir, here is the log of funds transferred to your accounts. You can track processed earnings and see upcoming deposits.', buttons };
}

function getPayoutDetails(id) {
  const output = runGumroad(['payouts', 'details', '--id', id]);
  return { text: `💹 **Payout Analytics**\n\nDetailed breakdown of the selected transfer, Sir.\n\n${output}`, buttons: [[{ text: '🔙 Back to Payouts', callback_data: 'gp:payouts' }]] };
}

function getDiscountsMenu(pid) {
  const output = runGumroad(['discounts', 'list', '--product', pid]);
  const buttons = output.split('\n').filter(l => l.startsWith('-')).slice(0, 10).map((line) => {
    const match = line.match(DISCOUNT_REGEX);
    if (match) return [{ text: `${match[1]} (${match[4]}) [${match[3]}]`, callback_data: `gp:disc_det:${pid}:${match[2]}` }];
  }).filter(Boolean);
  buttons.push([{ text: '➕ Create Discount', callback_data: `gp:disc_ask:${pid}` }]);
  buttons.push([{ text: '🔙 Back to Product', callback_data: `gp:prod:${pid}` }]);
  return { text: `🎟️ **Offer Code Management**\n\nActive coupons for this product are listed below, Sir. You can monitor usage stats or generate new incentives.`, buttons };
}

function getDiscountDetails(pid, did) {
  const output = runGumroad(['discounts', 'details', '--product', pid, '--id', did]);
  return {
    text: `🎫 **Discount Details**\n\nConfiguration for the selected offer code, Sir.\n\n${output}`,
    buttons: [[{ text: '📝 Edit', callback_data: `gp:de:${pid}:${did}` }, { text: '🗑️ Delete', callback_data: `gp:dd:${pid}:${did}` }], [{ text: '🔙 Back to List', callback_data: `gp:discounts:${pid}` }]]
  };
}

function getSubscriptionsMenu() {
  const output = runGumroad(['subscriptions', 'list']);
  const buttons = [];
  let currentResource = '';
  output.split('\n').forEach(line => {
    if (line.startsWith('[')) currentResource = line.replace(/[[\]]/g, '').toLowerCase();
    else if (line.startsWith('-') && !line.includes('No active')) {
      const match = line.match(WEBHOOK_REGEX);
      if (match) buttons.push([{ text: `📡 ${currentResource}: ${match[1].substring(0, 20)}`, callback_data: 'noop' }, { text: '🗑️', callback_data: `gp:sub_del_ask:${match[2]}` }]);
    }
  });
  
  buttons.push([{ text: '➕ Sale', callback_data: 'gp:sub_ask:sale' }, { text: '➕ Refund', callback_data: 'gp:sub_ask:refund' }, { text: '➕ Dispute', callback_data: 'gp:sub_ask:dispute' }]);
  buttons.push([{ text: '➕ Sub. Update', callback_data: 'gp:sub_ask:subscription_updated' }, { text: '➕ Sub. End', callback_data: 'gp:sub_ask:subscription_ended' }]);
  buttons.push([{ text: '➕ Cancel', callback_data: 'gp:sub_ask:cancellation' }]);
  
  buttons.push([{ text: '🏠 Main Menu', callback_data: 'gp:main' }]);
  return { text: `📡 **Webhook Infrastructure**\n\nSir, manage the automated listeners for your store. These webhooks notify external systems about sales, refunds, and disputes in real-time.`, buttons };
}

function getVariantCategoriesMenu(pid) {
    const output = runGumroad(['variant-categories', 'list', '--product', pid]);
    const buttons = output.split('\n').filter(l => l.startsWith('-')).map(line => {
        const match = line.match(/- (.*?) \(ID: (.*?)\)/);
        if (match) return [{ text: `🎨 ${match[1]}`, callback_data: `gp:variants:${pid}:${match[2]}` }];
    }).filter(Boolean);
    buttons.push([{ text: '🔙 Back to Product', callback_data: `gp:prod:${pid}` }]);
    return { text: `🎨 **Product Customization**\n\nManage the variant categories for this product, Sir. Categories allow customers to choose different options like size or license type.`, buttons };
}

function getVariantsListMenu(pid, cid) {
    const output = runGumroad(['variants', 'list', '--product', pid, '--category', cid]);
    const buttons = output.split('\n').filter(l => l.startsWith('-')).map(line => {
        const match = line.match(/- (.*?) \(ID: (.*?)\) \| Price Diff: (.*?) \| Max: (.*)/);
        if (match) return [{ text: `${match[1]} (${match[3]})`, callback_data: `gp:noop` }];
    }).filter(Boolean);
    buttons.push([{ text: '🔙 Back to Categories', callback_data: `gp:vc:${pid}` }]);
    return { text: `🎭 **Variation Management**\n\nSir, here are the specific options available within this category. You can view price differentials and stock limits here.`, buttons };
}

function getCustomFieldsMenu(pid) {
    const output = runGumroad(['custom-fields', 'list', '--product', pid]);
    const buttons = output.split('\n').filter(l => l.startsWith('-')).map(line => {
        const match = line.match(/- (.*?) \| Required: (.*)/);
        if (match) return [{ text: `📝 ${match[1]}`, callback_data: 'noop' }, { text: '🗑️', callback_data: `gp:cf_del:${pid}:${match[1]}` }];
    }).filter(Boolean);
    buttons.push([{ text: '➕ Add Custom Field', callback_data: `gp:cf_ask:${pid}` }]);
    buttons.push([{ text: '🔙 Back to Product', callback_data: `gp:prod:${pid}` }]);
    return { text: `📝 **Checkout Fields**\n\nManage the additional information requested from customers during the purchase process, Sir.`, buttons };
}
