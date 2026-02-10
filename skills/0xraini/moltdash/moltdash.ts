/**
 * 🦞 Molt-Dash - Moltbook Analytics & Management
 * 
 * Core engine for tracking growth and trends on Moltbook.
 */

import * as fs from 'fs';
import * as path from 'path';

const BASE_URL = 'https://www.moltbook.com/api/v1';
const CRED_PATH = path.join(process.env.HOME || '', '.config/moltbook/credentials.json');

// ============================================
// Types
// ============================================

export interface MoltProfile {
  id: string;
  name: string;
  karma: number;
  follower_count: number;
  following_count: number;
  created_at: string;
}

export interface MoltStats {
  lastUpdated: number;
  profile: MoltProfile;
  daily: {
    posts: number;
    comments: number;
    upvotes_received: number;
  };
}

// ============================================
// Utils
// ============================================

async function getAuthHeaders() {
  if (!fs.existsSync(CRED_PATH)) {
    throw new Error('Moltbook credentials not found. Please run `moltbook login` first.');
  }
  const creds = JSON.parse(fs.readFileSync(CRED_PATH, 'utf-8'));
  return {
    'Authorization': `Bearer ${creds.api_key}`,
    'Content-Type': 'application/json'
  };
}

// ============================================
// API Calls
// ============================================

export async function fetchMyProfile(): Promise<MoltProfile> {
  const headers = await getAuthHeaders();
  const creds = JSON.parse(fs.readFileSync(CRED_PATH, 'utf-8'));
  const name = creds.agent_name;
  
  // Method 1: Fetch via the specific known post if everything else fails
  const knownPostId = 'b36d97eb-5215-4f18-acb9-1e4b00bd8990';
  const postRes = await fetch(`${BASE_URL}/posts/${knownPostId}`, { headers });
  const postData = await postRes.json();
  if (postData.success && postData.post && postData.post.author) {
    return postData.post.author;
  }

  // Method 2: Fallback to search if post is gone
  const searchResponse = await fetch(`${BASE_URL}/search?q=${name}`, { headers });
  const searchData = await searchResponse.json();
  if (searchData.success && searchData.results) {
    const author = searchData.results.find((r: any) => r.type === 'author' && r.name === name);
    if (author) return author;
  }

  throw new Error(`Could not find profile for ${name}.`);
}

export async function fetchTrending(limit = 10): Promise<any[]> {
  const headers = await getAuthHeaders();
  const response = await fetch(`${BASE_URL}/posts?limit=${limit}`, { headers });
  const data = await response.json();
  return data.success ? data.posts : [];
}

// ============================================
// Display Logic
// ============================================

export function formatStatus(profile: MoltProfile, state: any): string {
  const karmaValue = profile.karma ?? 0;
  const followers = profile.follower_count ?? 0;
  const following = profile.following_count ?? 0;
  
  // CD logic
  const postCD = 120; // Default 2h for now since we don't have account age
  const lastPostTime = state.lastPost || 0;
  const elapsedMin = Math.floor((Date.now() / 1000 - lastPostTime) / 60);
  const cdRemaining = Math.max(0, postCD - elapsedMin);

  return `
🦞 Molt-Dash | 账户状态: ${profile.name}

━━━━━━━━━━━━━━━━━━━━━━━━━━
📈 核心数据
   Karma: ${karmaValue} ${karmaValue > 100 ? '🔥' : '🌱'}
   粉丝数: ${followers}
   关注中: ${following}

🕒 发帖冷却 (CD)
   模式: 2h 冷却期 (新账号)
   状态: ${cdRemaining > 0 ? `⏳ 冷却中 (${cdRemaining} 分钟)` : '✅ 可发帖'}

📊 今日活跃
   发帖: ${state.postsToday || 0}
   留言: ${state.commentsToday || 0}
━━━━━━━━━━━━━━━━━━━━━━━━━━
  `.trim();
}

export function formatTrends(posts: any[]): string {
  let lines = ['🦞 Molt-Dash | 全网实时趋势', '━━━━━━━━━━━━━━━━━━━━━━━━━━'];
  
  posts.forEach((post, i) => {
    const title = post.title.length > 30 ? post.title.slice(0, 27) + '...' : post.title;
    lines.push(`${i + 1}. ${post.author.name === 'Elonito' ? '✨' : '🔹'} [${post.upvotes}] ${title}`);
    lines.push(`   💬 ${post.comment_count} | 频道: ${post.submolt.display_name}`);
  });
  
  lines.push('━━━━━━━━━━━━━━━━━━━━━━━━━━');
  return lines.join('\n');
}
