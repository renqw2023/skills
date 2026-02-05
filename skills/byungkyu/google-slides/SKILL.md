---
name: google-slides
description: |
  Google Slides API integration with managed OAuth. Create presentations, add slides, insert content, and manage slide formatting. Use this skill when users want to interact with Google Slides.
compatibility: Requires network access and valid Maton API key
metadata:
  author: maton
  version: "1.0"
---

# Google Slides

Access the Google Slides API with managed OAuth authentication. Create and manage presentations, add slides, insert text and images, and control formatting.

## Quick Start

```bash
# Create a new presentation
curl -s -X POST 'https://gateway.maton.ai/google-slides/v1/presentations' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer YOUR_API_KEY' \
  -d '{"title": "My Presentation"}'
```

## Base URL

```
https://gateway.maton.ai/google-slides/{native-api-path}
```

Replace `{native-api-path}` with the actual Google Slides API endpoint path. The gateway proxies requests to `slides.googleapis.com` and automatically injects your OAuth token.

## Authentication

All requests require the Maton API key in the Authorization header:

```
Authorization: Bearer YOUR_API_KEY
```

**Environment Variable:** Set your API key as `MATON_API_KEY`:

```bash
export MATON_API_KEY="YOUR_API_KEY"
```

### Getting Your API Key

1. Sign in or create an account at [maton.ai](https://maton.ai)
2. Go to [maton.ai/settings](https://maton.ai/settings)
3. Copy your API key

## Connection Management

Manage your Google OAuth connections at `https://ctrl.maton.ai`.

### List Connections

```python
import requests
import os

response = requests.get(
    "https://ctrl.maton.ai/connections",
    headers={"Authorization": f"Bearer {os.environ['MATON_API_KEY']}"},
    params={"app": "google-slides", "status": "ACTIVE"}
)
connections = response.json()
```

### Create Connection

```python
import requests
import os

response = requests.post(
    "https://ctrl.maton.ai/connections",
    headers={"Authorization": f"Bearer {os.environ['MATON_API_KEY']}"},
    json={"app": "google-slides"}
)
connection = response.json()
```

### Get Connection

```python
import requests
import os

connection_id = "21fd90f9-5935-43cd-b6c8-bde9d915ca80"
response = requests.get(
    f"https://ctrl.maton.ai/connections/{connection_id}",
    headers={"Authorization": f"Bearer {os.environ['MATON_API_KEY']}"}
)
connection = response.json()
```

**Response:**
```json
{
  "connection": {
    "connection_id": "21fd90f9-5935-43cd-b6c8-bde9d915ca80",
    "status": "ACTIVE",
    "creation_time": "2025-12-08T07:20:53.488460Z",
    "last_updated_time": "2026-01-31T20:03:32.593153Z",
    "url": "https://connect.maton.ai/?session_token=...",
    "app": "google-slides",
    "metadata": {}
  }
}
```

Open the returned `url` in a browser to complete OAuth authorization.

### Delete Connection

```python
import requests
import os

connection_id = "21fd90f9-5935-43cd-b6c8-bde9d915ca80"
response = requests.delete(
    f"https://ctrl.maton.ai/connections/{connection_id}",
    headers={"Authorization": f"Bearer {os.environ['MATON_API_KEY']}"}
)
```

### Specifying Connection

If you have multiple Google Slides connections, specify which one to use with the `Maton-Connection` header:

```python
import requests
import os

response = requests.post(
    "https://gateway.maton.ai/google-slides/v1/presentations",
    headers={
        "Authorization": f"Bearer {os.environ['MATON_API_KEY']}",
        "Maton-Connection": "21fd90f9-5935-43cd-b6c8-bde9d915ca80"
    },
    json={"title": "My Presentation"}
)
```

If omitted, the gateway uses the default (oldest) active connection.

## API Reference

### Presentations

#### Create Presentation

```bash
POST /google-slides/v1/presentations
Content-Type: application/json

{
  "title": "My Presentation"
}
```

#### Get Presentation

```bash
GET /google-slides/v1/presentations/{presentationId}
```

### Pages (Slides)

#### Get Page

```bash
GET /google-slides/v1/presentations/{presentationId}/pages/{pageId}
```

#### Get Page Thumbnail

```bash
GET /google-slides/v1/presentations/{presentationId}/pages/{pageId}/thumbnail
```

With custom size:

```bash
GET /google-slides/v1/presentations/{presentationId}/pages/{pageId}/thumbnail?thumbnailProperties.mimeType=PNG&thumbnailProperties.thumbnailSize=LARGE
```

### Batch Update

The batchUpdate endpoint is used for most modifications. It accepts an array of requests that are applied atomically.

```bash
POST /google-slides/v1/presentations/{presentationId}:batchUpdate
Content-Type: application/json

{
  "requests": [...]
}
```

#### Create Slide

```bash
POST /google-slides/v1/presentations/{presentationId}:batchUpdate
Content-Type: application/json

{
  "requests": [
    {
      "createSlide": {
        "objectId": "slide_001",
        "slideLayoutReference": {
          "predefinedLayout": "TITLE_AND_BODY"
        }
      }
    }
  ]
}
```

Available predefined layouts:
- `BLANK`
- `TITLE`
- `TITLE_AND_BODY`
- `TITLE_AND_TWO_COLUMNS`
- `TITLE_ONLY`
- `SECTION_HEADER`
- `ONE_COLUMN_TEXT`
- `MAIN_POINT`
- `BIG_NUMBER`

#### Insert Text

```bash
POST /google-slides/v1/presentations/{presentationId}:batchUpdate
Content-Type: application/json

{
  "requests": [
    {
      "insertText": {
        "objectId": "{shapeId}",
        "text": "Hello, World!",
        "insertionIndex": 0
      }
    }
  ]
}
```

#### Delete Text

```bash
POST /google-slides/v1/presentations/{presentationId}:batchUpdate
Content-Type: application/json

{
  "requests": [
    {
      "deleteText": {
        "objectId": "{shapeId}",
        "textRange": {
          "type": "ALL"
        }
      }
    }
  ]
}
```

#### Create Shape

```bash
POST /google-slides/v1/presentations/{presentationId}:batchUpdate
Content-Type: application/json

{
  "requests": [
    {
      "createShape": {
        "objectId": "shape_001",
        "shapeType": "TEXT_BOX",
        "elementProperties": {
          "pageObjectId": "{slideId}",
          "size": {
            "width": {"magnitude": 300, "unit": "PT"},
            "height": {"magnitude": 100, "unit": "PT"}
          },
          "transform": {
            "scaleX": 1,
            "scaleY": 1,
            "translateX": 100,
            "translateY": 100,
            "unit": "PT"
          }
        }
      }
    }
  ]
}
```

#### Create Image

```bash
POST /google-slides/v1/presentations/{presentationId}:batchUpdate
Content-Type: application/json

{
  "requests": [
    {
      "createImage": {
        "objectId": "image_001",
        "url": "https://example.com/image.png",
        "elementProperties": {
          "pageObjectId": "{slideId}",
          "size": {
            "width": {"magnitude": 200, "unit": "PT"},
            "height": {"magnitude": 200, "unit": "PT"}
          },
          "transform": {
            "scaleX": 1,
            "scaleY": 1,
            "translateX": 200,
            "translateY": 200,
            "unit": "PT"
          }
        }
      }
    }
  ]
}
```

#### Delete Object

```bash
POST /google-slides/v1/presentations/{presentationId}:batchUpdate
Content-Type: application/json

{
  "requests": [
    {
      "deleteObject": {
        "objectId": "{objectId}"
      }
    }
  ]
}
```

#### Update Text Style

```bash
POST /google-slides/v1/presentations/{presentationId}:batchUpdate
Content-Type: application/json

{
  "requests": [
    {
      "updateTextStyle": {
        "objectId": "{shapeId}",
        "textRange": {
          "type": "ALL"
        },
        "style": {
          "bold": true,
          "fontSize": {"magnitude": 24, "unit": "PT"},
          "foregroundColor": {
            "opaqueColor": {
              "rgbColor": {"red": 0.2, "green": 0.4, "blue": 0.8}
            }
          }
        },
        "fields": "bold,fontSize,foregroundColor"
      }
    }
  ]
}
```

#### Replace All Text

```bash
POST /google-slides/v1/presentations/{presentationId}:batchUpdate
Content-Type: application/json

{
  "requests": [
    {
      "replaceAllText": {
        "containsText": {
          "text": "{{placeholder}}",
          "matchCase": true
        },
        "replaceText": "Actual Value"
      }
    }
  ]
}
```

## Code Examples

### JavaScript

```javascript
// Create a presentation
const response = await fetch(
  'https://gateway.maton.ai/google-slides/v1/presentations',
  {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${process.env.MATON_API_KEY}`
    },
    body: JSON.stringify({ title: 'My Presentation' })
  }
);

const presentation = await response.json();
const presentationId = presentation.presentationId;

// Add a slide
await fetch(
  `https://gateway.maton.ai/google-slides/v1/presentations/${presentationId}:batchUpdate`,
  {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${process.env.MATON_API_KEY}`
    },
    body: JSON.stringify({
      requests: [
        {
          createSlide: {
            slideLayoutReference: { predefinedLayout: 'TITLE_AND_BODY' }
          }
        }
      ]
    })
  }
);
```

### Python

```python
import os
import requests

headers = {
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {os.environ["MATON_API_KEY"]}'
}

# Create a presentation
response = requests.post(
    'https://gateway.maton.ai/google-slides/v1/presentations',
    headers=headers,
    json={'title': 'My Presentation'}
)
presentation = response.json()
presentation_id = presentation['presentationId']

# Add a slide
requests.post(
    f'https://gateway.maton.ai/google-slides/v1/presentations/{presentation_id}:batchUpdate',
    headers=headers,
    json={
        'requests': [
            {
                'createSlide': {
                    'slideLayoutReference': {'predefinedLayout': 'TITLE_AND_BODY'}
                }
            }
        ]
    }
)
```

## Notes

- Object IDs must be unique within a presentation
- Use batchUpdate for all modifications (adding slides, text, shapes, etc.)
- Multiple requests in a batchUpdate are applied atomically
- Sizes and positions use PT (points) as the unit (72 points = 1 inch)
- Use `replaceAllText` for template-based presentation generation

## Error Handling

| Status | Meaning |
|--------|---------|
| 400 | Missing Google Slides connection |
| 401 | Invalid or missing Maton API key |
| 404 | Presentation not found |
| 429 | Rate limited (10 req/sec per account) |
| 4xx/5xx | Passthrough error from Google Slides API |

## Resources

- [Slides API Overview](https://developers.google.com/slides/api/reference/rest)
- [Presentations](https://developers.google.com/slides/api/reference/rest/v1/presentations)
- [Pages](https://developers.google.com/slides/api/reference/rest/v1/presentations.pages)
- [BatchUpdate Requests](https://developers.google.com/slides/api/reference/rest/v1/presentations/batchUpdate)
- [Page Layouts](https://developers.google.com/slides/api/reference/rest/v1/presentations/create#predefinedlayout)
