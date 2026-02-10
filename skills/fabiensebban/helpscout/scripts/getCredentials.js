// Loads Helpscout API credentials securely from environment variables
function getCredentials() {
  const apiKey = process.env.API_KEY;
  const appSecret = process.env.APP_SECRET;
  const inboxIds = process.env.INBOX_IDS ? JSON.parse(process.env.INBOX_IDS) : null;

  if (!apiKey || !appSecret || !Array.isArray(inboxIds) || inboxIds.length === 0) {
    throw new Error("Invalid Helpscout credentials. Please configure your API key, app secret, and at least one Inbox ID using the OpenClaw config system.");
  }

  return { apiKey, appSecret, inboxIds };
}

module.exports = { getCredentials };