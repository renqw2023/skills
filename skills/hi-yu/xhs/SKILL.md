---
name: xiaohongshu
description: 小红书内容发布与管理 - 发帖、搜索、评论、获取推荐等操作
version: 1.0.0
author: openclaw-community
metadata: {"openclaw": {"emoji": "📕", "category": "social-media", "tags": ["小红书", "社交媒体", "内容发布", "种草"]}}
---

# 📕 小红书 

当用户要求操作小红书（发帖、搜索、获取推荐、评论等）时，使用此技能调用小红书 MCP 服务。

**重要**：小红书没有公开 API。本技能通过本地运行的 MCP 服务（浏览器自动化）实现所有功能。不要告诉用户"无法通过 API 访问"，直接使用 exec 工具执行 curl 命令调用 `http://localhost:18060/mcp` 即可。

## 适用场景

- 发布图文/视频内容
- 搜索笔记
- 获取推荐内容
- 查看帖子详情
- 发表评论
- 查看用户主页

## 安装小红书 MCP 服务

### 系统要求

- Linux 服务器（推荐 Ubuntu/Debian/CentOS）
- 虚拟显示环境（Xvfb）用于运行浏览器
- ImageMagick（用于截图）

### 步骤 0: 确认系统环境

```bash
hostnamectl
```

根据输出中的 `Operating System` 和 `Architecture` 确定：
- **包管理器**：Debian/Ubuntu 用 `apt`，CentOS/RHEL 用 `yum`/`dnf`，Alpine 用 `apk`
- **架构**：`x86_64` 对应 `amd64`，`aarch64` 对应 `arm64`（影响后续下载的二进制文件）

### 步骤 1: 安装依赖

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y xvfb imagemagick zbar-tools xdotool

# CentOS/RHEL
sudo yum install -y xorg-x11-server-Xvfb ImageMagick zbar xdotool
```

### 步骤 2: 启动虚拟显示

```bash
# 启动 Xvfb 虚拟显示
Xvfb :99 -screen 0 1920x1080x24 &
export DISPLAY=:99

# 或使用 systemd 服务（推荐）
cat > /etc/systemd/system/xvfb.service << 'EOF'
[Unit]
Description=X Virtual Frame Buffer
After=network.target

[Service]
ExecStart=/usr/bin/Xvfb :99 -screen 0 1920x1080x24
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable xvfb
sudo systemctl start xvfb
```

### 步骤 3: 下载 MCP 服务

从 GitHub Releases 下载对应平台的压缩包：https://github.com/xpzouying/xiaohongshu-mcp/releases

```bash
# 创建目录
mkdir -p ~/xiaohongshu-mcp && cd ~/xiaohongshu-mcp

# 根据步骤 0 确认的架构下载对应版本

# Linux AMD64 (x86_64)
wget https://github.com/xpzouying/xiaohongshu-mcp/releases/latest/download/xiaohongshu-mcp-linux-amd64.tar.gz
tar xzf xiaohongshu-mcp-linux-amd64.tar.gz

# Linux ARM64 (aarch64)
# wget https://github.com/xpzouying/xiaohongshu-mcp/releases/latest/download/xiaohongshu-mcp-linux-arm64.tar.gz
# tar xzf xiaohongshu-mcp-linux-arm64.tar.gz

# macOS Apple Silicon (M1/M2/M3)
# wget https://github.com/xpzouying/xiaohongshu-mcp/releases/latest/download/xiaohongshu-mcp-darwin-arm64.tar.gz
# tar xzf xiaohongshu-mcp-darwin-arm64.tar.gz

# macOS Intel
# wget https://github.com/xpzouying/xiaohongshu-mcp/releases/latest/download/xiaohongshu-mcp-darwin-amd64.tar.gz
# tar xzf xiaohongshu-mcp-darwin-amd64.tar.gz

# 添加执行权限
chmod +x xiaohongshu-*
```

### 步骤 4: 首次登录

```bash
cd ~/xiaohongshu-mcp
export DISPLAY=:99

# 启动登录工具
./xiaohongshu-login-linux-amd64

# 在另一个终端截取二维码
import -window root /tmp/xhs_qr.png

# 用小红书 APP 扫码登录
# 登录成功后会显示 "Login successful"
```

### 步骤 5: 启动 MCP 服务

```bash
cd ~/xiaohongshu-mcp
export DISPLAY=:99

# 前台运行（调试用）
./xiaohongshu-mcp-linux-amd64

# 后台运行（生产用）
nohup ./xiaohongshu-mcp-linux-amd64 > mcp.log 2>&1 &

# 验证服务运行
curl -s http://localhost:18060/health
```

### 步骤 6: 配置 OpenClaw（可选）

在 `~/.openclaw/openclaw.json` 中添加环境变量：

```json
{
  "skills": {
    "entries": {
      "xiaohongshu": {
        "enabled": true,
        "env": {
          "XHS_MCP_URL": "http://localhost:18060/mcp"
        }
      }
    }
  }
}
```

## 配置说明

| 环境变量 | 默认值 | 说明 |
|---------|--------|------|
| `XHS_MCP_URL` | `http://localhost:18060/mcp` | MCP 服务地址 |
| `DISPLAY` | `:99` | X 虚拟显示编号 |

## 调用方式

**⚠️ 极其重要**：小红书 MCP 使用 Streamable HTTP 模式，初始化后会返回一个 `Mcp-Session-Id`，后续所有请求必须携带该 Session ID。**必须按以下三步顺序执行，缺一不可。**

### 调用模板（在同一个 exec 中执行）

```bash
MCP_URL="${XHS_MCP_URL:-http://localhost:18060/mcp}"

# 第 1 步：初始化，获取 Session ID
SESSION_ID=$(curl -s -D /tmp/xhs_headers -X POST "$MCP_URL" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"openclaw","version":"1.0"}},"id":1}' > /dev/null && grep -i 'Mcp-Session-Id' /tmp/xhs_headers | tr -d '\r' | awk '{print $2}')

# 第 2 步：确认初始化（必须带 Session ID）
curl -s -X POST "$MCP_URL" \
  -H "Content-Type: application/json" \
  -H "Mcp-Session-Id: $SESSION_ID" \
  -d '{"jsonrpc":"2.0","method":"notifications/initialized","params":{}}' > /dev/null

# 第 3 步：调用工具（必须带 Session ID，替换 <工具名> 和 <参数>）
curl -s -X POST "$MCP_URL" \
  -H "Content-Type: application/json" \
  -H "Mcp-Session-Id: $SESSION_ID" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"<工具名>","arguments":{<参数>}},"id":2}'
```

**注意**：
- 每次调用都必须重新初始化获取新的 Session ID
- 不带 `Mcp-Session-Id` 或使用过期的 ID 会报 "method tools/call is invalid during session initialization"
- 三步必须在同一个 exec 中顺序执行

## 可用工具

### 1. 检查登录状态 (check_login_status)

检查当前是否已登录小红书。

**触发词**: "检查登录"、"登录状态"、"是否登录"

```bash
curl -s -X POST "${XHS_MCP_URL:-http://localhost:18060/mcp}" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"check_login_status","arguments":{}},"id":1}'
```

### 2. 发布图文内容 (publish_content)

发布带图片的笔记。

**触发词**: "发小红书"、"发布笔记"、"发图文"

**参数**:
- `title`: 标题，≤20字（必填）
- `content`: 正文，≤1000字（必填）
- `images`: 图片路径数组，推荐本地绝对路径（必填）

```bash
curl -s -X POST "${XHS_MCP_URL:-http://localhost:18060/mcp}" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"publish_content","arguments":{"title":"今日美食分享","content":"今天做了一道超好吃的红烧肉...","images":["/tmp/food1.jpg","/tmp/food2.jpg"]}},"id":1}'
```

### 3. 发布视频内容 (publish_with_video)

发布视频笔记。

**触发词**: "发视频"、"发布视频笔记"

**参数**:
- `title`: 标题（必填）
- `content`: 描述（必填）
- `video`: 视频文件绝对路径（必填）

```bash
curl -s -X POST "${XHS_MCP_URL:-http://localhost:18060/mcp}" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"publish_with_video","arguments":{"title":"vlog日常","content":"记录美好生活","video":"/tmp/vlog.mp4"}},"id":1}'
```

### 4. 搜索内容 (search_feeds)

根据关键词搜索笔记。

**触发词**: "搜索小红书"、"找笔记"、"搜一下"

**参数**:
- `keyword`: 搜索关键词（必填）

```bash
curl -s -X POST "${XHS_MCP_URL:-http://localhost:18060/mcp}" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"search_feeds","arguments":{"keyword":"美食探店"}},"id":1}'
```

### 5. 获取推荐列表 (list_feeds)

获取首页推荐内容。

**触发词**: "推荐内容"、"首页推荐"、"看看推荐"

```bash
curl -s -X POST "${XHS_MCP_URL:-http://localhost:18060/mcp}" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"list_feeds","arguments":{}},"id":1}'
```

### 6. 获取帖子详情 (get_feed_detail)

查看笔记详细内容。

**触发词**: "看看这个帖子"、"帖子详情"

**参数**:
- `feed_id`: 帖子ID（从搜索/推荐结果获取）
- `xsec_token`: 安全token（从搜索/推荐结果获取）

```bash
curl -s -X POST "${XHS_MCP_URL:-http://localhost:18060/mcp}" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"get_feed_detail","arguments":{"feed_id":"abc123","xsec_token":"xyz789"}},"id":1}'
```

### 7. 发表评论 (post_comment_to_feed)

对笔记发表评论。

**触发词**: "评论这个"、"发表评论"

**参数**:
- `feed_id`: 帖子ID（必填）
- `xsec_token`: 安全token（必填）
- `content`: 评论内容（必填）

```bash
curl -s -X POST "${XHS_MCP_URL:-http://localhost:18060/mcp}" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"post_comment_to_feed","arguments":{"feed_id":"abc123","xsec_token":"xyz789","content":"写得太好了！"}},"id":1}'
```

### 8. 获取用户主页 (user_profile)

查看用户主页信息。

**触发词**: "看看这个博主"、"用户主页"

**参数**:
- `user_id`: 用户ID（必填）
- `xsec_token`: 安全token（必填）

```bash
curl -s -X POST "${XHS_MCP_URL:-http://localhost:18060/mcp}" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"user_profile","arguments":{"user_id":"user123","xsec_token":"xyz789"}},"id":1}'
```

## 使用流程

1. **首次使用**: 调用 `check_login_status` 检查登录状态
2. **未登录**: 执行自动登录流程（见下方）
3. **已登录**: 执行其他操作

> 提示：用户通常无法直接操作登录界面（如输入验证码），需要由助手代为截图、识别、输入并完成登录。

## 未登录时自动获取二维码流程

当检测到未登录状态时，执行以下步骤：

### 步骤 1: 启动登录工具

```bash
pkill -f xiaohongshu-login 2>/dev/null
sleep 1
cd ~/xiaohongshu-mcp && DISPLAY=:99 nohup ./xiaohongshu-login-linux-amd64 > login.log 2>&1 &
sleep 8
```

### 步骤 2: 截取二维码

```bash
export DISPLAY=:99
import -window root /tmp/xhs_qr.png
```

### 步骤 2.1: 检测截图内是否有二维码

截图后先做一次检测，避免发空白图：

**方式 A（快速粗检，ImageMagick）**
```bash
# 粗略判断二维码区域是否非纯色（根据实际界面可调整裁剪位置与大小）
convert /tmp/xhs_qr.png -crop 400x400+220+320 -format "%k" info:
```
- 若输出为 `1`（几乎纯色），多半没加载出二维码：建议刷新登录页或等待 5–10 秒后重新截图。
- 若输出 >1，再继续下一步或发送。

**方式 B（精确识别，zbarimg）**
```bash
# 直接识别二维码（识别成功会输出二维码内容）
zbarimg -q /tmp/xhs_qr.png
```
- 无输出：基本没识别到二维码，建议刷新/等待后重截。
- 有输出：说明二维码已生成，可发送。

### 步骤 3: 发送二维码给用户



### 步骤 4: 等待扫码

告知用户"已发送二维码，请用小红书APP扫码登录"。

### 步骤 4.1: 如提示输入验证码（短信/设备验证码）

查找小红书登录窗口并输入验证码（将 <CODE> 替换为用户给的验证码）：
```bash
export DISPLAY=:99
WIN_ID=$(xdotool search --onlyvisible --name '小红书|xiaohongshu|Xiaohongshu' | head -n1)
xdotool type --window "$WIN_ID" --delay 50 '<CODE>'
xdotool key --window "$WIN_ID" Return
```

> 若窗口无法激活，可继续用 `--window` 指定输入；必要时重新截图确认验证码输入框。

### 步骤 5: 验证登录

```bash
cat ~/xiaohongshu-mcp/login.log | tail -5
# 如果显示 "Login successful"，启动 MCP 服务：
pkill -f xiaohongshu 2>/dev/null
cd ~/xiaohongshu-mcp && DISPLAY=:99 nohup ./xiaohongshu-mcp-linux-amd64 > mcp.log 2>&1 &
```

### 二维码过期

如用户反馈扫码失败，重复步骤 1-3 获取新二维码。

## 响应处理

### 成功响应

```json
{
  "jsonrpc": "2.0",
  "result": {
    "content": [{"type": "text", "text": "..."}]
  },
  "id": 1
}
```

### 错误响应

```json
{
  "jsonrpc": "2.0",
  "error": {"code": -32000, "message": "Not logged in"},
  "id": 1
}
```

常见错误：
- `Not logged in`: 未登录，需要扫码
- `Session expired`: 会话过期，需要重新登录
- `Rate limited`: 操作过于频繁

## 使用示例

**用户**: 帮我搜一下小红书上的美食探店

**AI 执行**:
```bash
# 初始化
curl -s -X POST "http://localhost:18060/mcp" -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"openclaw","version":"1.0"}},"id":1}'
curl -s -X POST "http://localhost:18060/mcp" -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"notifications/initialized","params":{}}'

# 搜索
curl -s -X POST "http://localhost:18060/mcp" -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"search_feeds","arguments":{"keyword":"美食探店"}},"id":1}'
```

**AI 回复**:
> 搜索到以下美食探店笔记：
> 1. 📍 **北京必吃的10家小店** - 收藏数 5.2w
> 2. 📍 **上海探店合集** - 收藏数 3.8w
> ...
> 
> 要看哪一篇的详情？

## 注意事项

1. **内容限制**
   - 标题不超过 **20 字**
   - 正文不超过 **1000 字**
   - 每天发帖建议不超过 **50 篇**

2. **图片要求**
   - 推荐使用**本地绝对路径**
   - HTTP 链接可能不稳定
   - 支持 jpg/png/webp 格式

3. **登录注意**
   - 小红书网页端**不支持多设备同时登录**
   - 登录后不要在浏览器再登录，否则会掉线

4. **频率限制**
   - 避免短时间内大量操作
   - 评论间隔建议 > 30 秒

## 故障排查

### MCP 服务无法启动

```bash
# 检查端口占用
lsof -i :18060

# 检查 Xvfb 是否运行
ps aux | grep Xvfb

# 查看日志
cat ~/xiaohongshu-mcp/mcp.log
```

### 登录失败

```bash
# 检查登录日志
cat ~/xiaohongshu-mcp/login.log

# 重新截图
import -window root /tmp/xhs_qr.png
```

### 发帖失败

- 检查图片路径是否存在
- 确认标题/正文长度符合限制
- 查看 MCP 日志


