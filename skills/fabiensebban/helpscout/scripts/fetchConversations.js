const fetch = require('node-fetch');
const { getToken } = require('./getToken');

/**
 * Fetch conversations from a specific inbox with optional filters
 * @param {number} inboxId - The mailbox ID to fetch conversations from
 * @param {Object} options - Optional query parameters
 * @param {string} options.status - Filter by status: active, pending, closed, spam, or all (default: active)
 * @param {number} options.folderId - Filter by folder ID
 * @param {number} options.assignedTo - Filter by user ID
 * @param {number} options.customerId - Filter by customer ID
 * @param {number} options.number - Filter by conversation number
 * @param {string} options.modifiedSince - ISO8601 date to filter conversations modified after this date
 * @param {string} options.sortField - Sort field: createdAt, mailboxId, modifiedAt, number, score, status, subject (default: createdAt)
 * @param {string} options.sortOrder - Sort order: asc or desc (default: desc)
 * @param {string} options.tag - Filter by tag name
 * @param {string} options.query - Advanced search query (fieldId:value format)
 * @param {string} options.embed - Comma-separated list of resources to embed: threads
 * @param {number} options.page - Page number (default: 1)
 * @returns {Promise<Object>} - The conversations data with pagination info
 */
async function fetchConversations(inboxId, options = {}) {
  const token = await getToken();
  
  // Build query string from options
  const params = new URLSearchParams();
  params.append('mailbox', inboxId);
  
  // Add all optional parameters if they exist
  if (options.status) params.append('status', options.status);
  if (options.folderId) params.append('folderId', options.folderId);
  if (options.assignedTo) params.append('assignedTo', options.assignedTo);
  if (options.customerId) params.append('customerId', options.customerId);
  if (options.number) params.append('number', options.number);
  if (options.modifiedSince) params.append('modifiedSince', options.modifiedSince);
  if (options.sortField) params.append('sortField', options.sortField);
  if (options.sortOrder) params.append('sortOrder', options.sortOrder);
  if (options.tag) params.append('tag', options.tag);
  if (options.query) params.append('query', options.query);
  if (options.embed) params.append('embed', options.embed);
  if (options.page) params.append('page', options.page);

  const url = `https://api.helpscout.net/v2/conversations?${params.toString()}`;
  
  const response = await fetch(url, {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch conversations: ${response.status} ${response.statusText}`);
  }

  const conversations = await response.json();
  return conversations;
}

module.exports = { fetchConversations };
