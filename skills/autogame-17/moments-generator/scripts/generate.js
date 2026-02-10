const sharp = require('sharp');
const fs = require('fs');
const path = require('path');

// Constants
const WIDTH = 1080;
const PADDING = 40;
const AVATAR_SIZE = 130;
const NAME_SIZE = 42;
const CONTENT_SIZE = 38;
const TIME_SIZE = 32;
const COMMENT_SIZE = 36;
const IMG_GAP = 15;
const CONTENT_LEFT_MARGIN = PADDING + AVATAR_SIZE + 20;
const CONTENT_WIDTH = WIDTH - CONTENT_LEFT_MARGIN - PADDING;

// Theme Colors
const THEMES = {
  light: {
    bg: "white",
    name: "#576b95",
    text: "black",
    time: "#b0b0b0",
    footerBg: "#f7f7f7",
    footerLine: "#e0e0e0"
  },
  dark: {
    bg: "#111111",
    name: "#7d90a9",
    text: "#dddddd",
    time: "#666666",
    footerBg: "#202020",
    footerLine: "#333333"
  }
};

function wrapText(text, fontSize, maxWidth) {
  const lines = [];
  let currentLine = '';
  let currentWidth = 0;

  for (const char of text) {
    const charCode = char.charCodeAt(0);
    // CJK ranges + punctuation
    const isWide = (
      (charCode >= 0x3000 && charCode <= 0x303f) ||
      (charCode >= 0x2000 && charCode <= 0x206f) ||
      (charCode >= 0xff00 && charCode <= 0xffef) ||
      (charCode >= 0x4e00 && charCode <= 0x9faf)
    );
    // Better width estimation
    const charW = isWide ? fontSize : fontSize * 0.55;

    if (currentWidth + charW > maxWidth) {
      lines.push(currentLine);
      currentLine = char;
      currentWidth = charW;
    } else {
      currentLine += char;
      currentWidth += charW;
    }
  }
  if (currentLine) lines.push(currentLine);
  return lines;
}

function escape(str) {
  return (str || "").replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}

async function main() {
  const args = process.argv.slice(2);
  if (args.length < 2) {
    console.error("Usage: node generate.js <config.json> <output.png>");
    process.exit(1);
  }

  const configPath = args[0];
  const outputPath = args[1];

  let config;
  try {
    config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
  } catch (e) {
    console.error("Failed to read config:", e.message);
    process.exit(1);
  }

  const themeKey = config.theme === 'dark' ? 'dark' : 'light';
  const colors = THEMES[themeKey];

  // Measurements
  const nameLines = [config.name || "Unknown"];
  const contentLines = wrapText(config.content || "", CONTENT_SIZE, CONTENT_WIDTH);
  
  // Image Grid Layout
  const imgCount = (config.images || []).length;
  let imageSize = 0;
  let imagesHeight = 0;
  let singleImage = false;

  if (imgCount === 1) {
    singleImage = true;
    imageSize = WIDTH * 0.5; // Single image max width
    imagesHeight = imageSize; // Assume square for placeholder layout
  } else if (imgCount > 0) {
    imageSize = (CONTENT_WIDTH - 2 * IMG_GAP) / 3;
    const rows = Math.ceil(imgCount / 3);
    imagesHeight = rows * imageSize + (rows - 1) * IMG_GAP;
  }

  // Footer (Likes/Comments)
  const likes = config.likes || [];
  let likesHeight = 0;
  let likesLines = [];
  if (likes.length > 0) {
    const likesText = "♡ " + likes.join(", ");
    likesLines = wrapText(likesText, COMMENT_SIZE, CONTENT_WIDTH - 20); // padding inside footer
    likesHeight = likesLines.length * (COMMENT_SIZE * 1.4) + 20; // + padding
  }

  const comments = config.comments || [];
  let commentsHeight = 0;
  let commentItems = [];
  if (comments.length > 0) {
    comments.forEach(c => {
      const fullText = `${c.name}: ${c.text}`;
      const lines = wrapText(fullText, COMMENT_SIZE, CONTENT_WIDTH - 20);
      commentItems.push({ name: c.name, lines: lines });
      commentsHeight += lines.length * (COMMENT_SIZE * 1.4);
    });
    commentsHeight += 10; // extra padding
  }

  let totalFooterHeight = likesHeight + commentsHeight;
  if (totalFooterHeight > 0) totalFooterHeight += 20; // Top/bottom padding for grey box

  // Total Height Calculation
  let currentY = PADDING;
  const avatarY = currentY;
  const nameY = currentY + 10;
  const contentY = nameY + NAME_SIZE * 1.5;
  const imagesY = contentY + contentLines.length * (CONTENT_SIZE * 1.4) + 15;
  const timeY = imagesY + (imgCount > 0 ? imagesHeight + 20 : 0);
  const footerY = timeY + TIME_SIZE + 20;
  
  const TOTAL_HEIGHT = footerY + totalFooterHeight + PADDING;

  // 1. Generate SVG Template
  let svg = `<svg width="${WIDTH}" height="${TOTAL_HEIGHT}" xmlns="http://www.w3.org/2000/svg">`;
  
  // Background
  svg += `<rect x="0" y="0" width="${WIDTH}" height="${TOTAL_HEIGHT}" fill="${colors.bg}"/>`;

  // Name
  svg += `<text x="${CONTENT_LEFT_MARGIN}" y="${nameY + NAME_SIZE}" font-family="Noto Sans SC" font-size="${NAME_SIZE}" fill="${colors.name}" font-weight="bold">${escape(config.name)}</text>`;

  // Content
  contentLines.forEach((line, i) => {
    svg += `<text x="${CONTENT_LEFT_MARGIN}" y="${contentY + (i+1) * CONTENT_SIZE * 1.4}" font-family="Noto Sans SC" font-size="${CONTENT_SIZE}" fill="${colors.text}">${escape(line)}</text>`;
  });

  // Time
  svg += `<text x="${CONTENT_LEFT_MARGIN}" y="${timeY + TIME_SIZE}" font-family="Noto Sans SC" font-size="${TIME_SIZE}" fill="${colors.time}">Just now</text>`;

  // Footer BG
  if (likesHeight + commentsHeight > 0) {
    svg += `<rect x="${CONTENT_LEFT_MARGIN}" y="${footerY}" width="${CONTENT_WIDTH}" height="${totalFooterHeight}" fill="${colors.footerBg}" rx="8" ry="8"/>`;
  }

  // Likes
  let currentFooterY = footerY + 10;
  if (likesLines.length > 0) {
    likesLines.forEach((line, i) => {
      svg += `<text x="${CONTENT_LEFT_MARGIN + 10}" y="${currentFooterY + (i+1) * COMMENT_SIZE * 1.4}" font-family="Noto Sans SC" font-size="${COMMENT_SIZE}" fill="${colors.name}">${escape(line)}</text>`;
    });
    currentFooterY += likesHeight;
    
    // Line separator if comments exist
    if (commentsHeight > 0) {
      svg += `<line x1="${CONTENT_LEFT_MARGIN}" y1="${currentFooterY}" x2="${CONTENT_WIDTH + CONTENT_LEFT_MARGIN}" y2="${currentFooterY}" stroke="${colors.footerLine}" stroke-width="1"/>`;
      currentFooterY += 10;
    }
  }

  // Comments
  commentItems.forEach(item => {
    item.lines.forEach((line, i) => {
      const y = currentFooterY + (i+1) * (COMMENT_SIZE * 1.4);
      
      svg += `<text x="${CONTENT_LEFT_MARGIN + 10}" y="${y}" font-family="Noto Sans SC" font-size="${COMMENT_SIZE}" fill="${colors.text}">`;
      
      if (i === 0 && line.startsWith(item.name)) {
        const namePart = item.name;
        const restPart = line.substring(item.name.length);
        svg += `<tspan fill="${colors.name}" font-weight="bold">${escape(namePart)}</tspan><tspan>${escape(restPart)}</tspan>`;
      } else {
        svg += escape(line);
      }
      svg += `</text>`;
    });
    currentFooterY += item.lines.length * (COMMENT_SIZE * 1.4);
  });

  svg += `</svg>`;

  // 3. Render and Composite
  const base = sharp(Buffer.from(svg));
  const composites = [];

  // Avatar
  if (config.avatar && fs.existsSync(config.avatar)) {
    try {
        const avatarBuffer = await sharp(config.avatar)
        .resize(AVATAR_SIZE, AVATAR_SIZE)
        .toBuffer();
        composites.push({ input: avatarBuffer, top: PADDING, left: PADDING });
    } catch(e) {
        console.warn("Failed to load avatar:", e.message);
    }
  }

  // Grid Images
  if (imgCount > 0) {
    for (let i = 0; i < imgCount; i++) {
      const imgPath = config.images[i];
      if (fs.existsSync(imgPath)) {
        let w = imageSize, h = imageSize;
        let top, left;

        if (singleImage) {
          top = imagesY;
          left = CONTENT_LEFT_MARGIN;
        } else {
          const col = i % 3;
          const row = Math.floor(i / 3);
          left = CONTENT_LEFT_MARGIN + col * (imageSize + IMG_GAP);
          top = imagesY + row * (imageSize + IMG_GAP);
        }

        try {
          const imgBuffer = await sharp(imgPath)
            .resize({ width: Math.round(w), height: Math.round(h), fit: 'cover', position: 'center' })
            .toBuffer();
          composites.push({ input: imgBuffer, top: Math.round(top), left: Math.round(left) });
        } catch(e) {
          console.error("Failed to load image " + imgPath);
        }
      }
    }
  }

  await base
    .composite(composites)
    .toFile(outputPath);
  
  console.log(outputPath);
}

main();
