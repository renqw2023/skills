#!/usr/bin/env node

/**
 * Vanna Fuxi SQL 问答调用脚本
 *
 * 用法：
 *   node ask.js "我想查伏羲上的张博文准驾等级"
 *
 * 说明：
 *   - 会向 https://vanna-ai-sql-api-ontest.inner.chj.cloud/ask 发送 POST 请求
 *   - 请求体遵循 QuestionRequest 模型
 *   - 在控制台输出完整 JSON 响应，供 OpenClaw 代理进一步解析和转述
 */

const https = require("https");

const API_URL = "https://vanna-ai-sql-api-ontest.inner.chj.cloud/ask";

function buildRequestBody(question) {
  return JSON.stringify({
    question,
    visualize: false,
    allow_llm_to_see_data: true,
    model: null,
  });
}

function postJson(url, body) {
  return new Promise((resolve, reject) => {
    const urlObj = new URL(url);

    const options = {
      method: "POST",
      hostname: urlObj.hostname,
      path: urlObj.pathname + urlObj.search,
      port: urlObj.port || 443,
      headers: {
        "Content-Type": "application/json",
        "Content-Length": Buffer.byteLength(body),
      },
    };

    const req = https.request(options, (res) => {
      let data = "";

      res.on("data", (chunk) => {
        data += chunk;
      });

      res.on("end", () => {
        try {
          const parsed = JSON.parse(data);
          resolve({ statusCode: res.statusCode, body: parsed });
        } catch (e) {
          // 如果不是合法 JSON，也原样返回文本
          resolve({ statusCode: res.statusCode, body: data });
        }
      });
    });

    req.on("error", (err) => {
      reject(err);
    });

    req.write(body);
    req.end();
  });
}

async function main() {
  const question = process.argv[2];

  if (!question) {
    console.error("用法: node ask.js \"我想查伏羲上的张博文准驾等级\"");
    process.exit(1);
  }

  const body = buildRequestBody(question);

  try {
    const result = await postJson(API_URL, body);
    const output = {
      success: result.statusCode >= 200 && result.statusCode < 300,
      statusCode: result.statusCode,
      question,
      response: result.body,
    };
    console.log(JSON.stringify(output, null, 2));
  } catch (err) {
    const errorOutput = {
      success: false,
      question,
      error: err.message || String(err),
    };
    console.error(JSON.stringify(errorOutput, null, 2));
    process.exit(1);
  }
}

main();

