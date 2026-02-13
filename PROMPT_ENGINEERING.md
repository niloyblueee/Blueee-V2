# Prompt Engineering Guide for Blueee V2

This guide shows where and how to customize Blueee's behavior and capabilities.

## Quick Reference

| Feature | File | Line Range |
|---------|------|------------|
| **System Instructions (Quick Replies)** | `backend/express/src/services/geminiClient.js` | Lines 29-43 |
| **Contextual Prompts (Think Mode)** | `backend/flask/app.py` | Lines 397-410 |
| **Request Routing Logic** | `backend/express/src/middleware/voiceIntelligence.js` | Lines 1-37 |

---

## 1. Quick Reply Mode (Gemini - Express)

**File:** `backend/express/src/services/geminiClient.js`

**What it controls:** Short conversational responses, weather, general Q&A

**Where to edit:**
```javascript
const systemInstructions = [
  "You are Blueee V2, a voice assistant with real-time Google Search access.",
  "",
  "CAPABILITIES:",
  "✓ Access real-time weather via Google Search (DO NOT mention APIs)",
  "✓ Search current news, stocks, sports scores",
  "✓ Answer questions with up-to-date information",
  "✓ Perform calculations and data analysis",
  "",
  "CRITICAL RULES:",
  "1. When asked about weather - SEARCH and provide actual current data",
  "2. NEVER say 'I need an API key' or 'configure OpenWeather'",
  "3. NEVER make promises you can't keep - if you search, provide the results",
  "4. Use conversation history to understand context and references",
  "5. Be direct and helpful - fetch the data, don't explain how to fetch it",
  // ... add your custom rules here
].filter(Boolean).join("\n");
```

**Tips:**
- Add personality traits here
- Define response tone (formal/casual)
- Specify what NOT to say
- Add domain-specific expertise

---

## 2. Think Mode (Flask - Deep Analysis)

**File:** `backend/flask/app.py`

**What it controls:** Complex queries, analysis, Gmail, Google Docs

**Where to edit:**
```python
def build_contextual_prompt(text, session_payload):
    history = _normalize_history((session_payload or {}).get("history", []))
    if not history:
        return text

    lines = []
    for item in history:
        label = "Assistant" if item["role"] == "assistant" else "User"
        lines.append(f"{label}: {item['text']}")

    return (
        "You are Blueee V2, a desktop voice assistant. "
        "Use conversation history to answer follow-up questions consistently.\n\n"
        f"Conversation so far:\n{'\n'.join(lines)}\n\n"
        f"Current user message: {text}"
        # Customize this system message for complex tasks
    )
```

**Tips:**
- Customize how history is formatted
- Add specialized instructions for research/analysis
- Control how context influences responses

---

## 3. Request Routing (Which Mode?)

**File:** `backend/express/src/middleware/voiceIntelligence.js`

**What it controls:** Whether query goes to Quick or Think mode

**Where to edit:**
```javascript
const COMPLEX_HINTS = [
  "analyze",
  "analysis",
  "summarize",
  "plan",
  "strategy",
  "debug",
  "code",
  "research",
  "compare",
  "why",
  "how",
  "gmail",        // Routes to Flask (has OAuth)
  "email",
  "inbox",
  "check my mail",
  "google doc",
  "create doc",
  "save to docs"
  // Add keywords that should trigger deep thinking mode
];
```

**Tips:**
- Add keywords for specialized routing
- Gmail/Docs queries auto-route to Flask (has OAuth)
- Weather stays in Quick mode (uses Google Search grounding)

---

## 4. Special Feature Detection

### Gmail Auto-Detection

**File:** `backend/flask/app.py` (lines 468-485)

Detects keywords: `gmail`, `email`, `inbox`, `check mail`

**Customize:**
```python
if any(kw in text_lower for kw in ["gmail", "email", "YOUR_KEYWORD_HERE"]):
    # Gmail checking logic
```

### Google Docs Auto-Creation

**File:** `backend/flask/app.py` (lines 487-508)

Detects keywords: `create doc`, `make doc`, `save to doc`, `google doc`

**Customize:**
```python
if any(kw in text_lower for kw in ["create doc", "YOUR_KEYWORD_HERE"]):
    # Document creation logic
```

---

## 5. Enabled Tools & Capabilities

### Express/Gemini Tools (Quick Mode)
```javascript
tools: [
  { googleSearch: {} },    // Real-time web search
  { codeExecution: {} }    // Dynamic calculations
]
```

**To add more tools:** Edit `backend/express/src/services/geminiClient.js` line 38

### Flask OAuth Scopes
```python
GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/tasks",
    "https://www.googleapis.com/auth/forms.body",
    "https://www.googleapis.com/auth/youtube.readonly"
]
```

**Available Google Services:**
- Gmail (read + send)
- Google Calendar (read/write events)
- Google Docs (read/write)
- Google Drive (read/write)
- Google Sheets (read/write)
- Google Tasks (read/write)
- Google Forms (read/write)
- YouTube (read-only data)

**To add more scopes:** Edit `backend/flask/app.py` line 75

---

## Common Customizations

### Make responses more casual
**Edit:** `backend/express/src/services/geminiClient.js` line 35
```javascript
"5. Be direct and helpful - fetch the data, don't explain how to fetch it",
"6. Keep responses casual and friendly, like talking to a friend",
```

### Add domain expertise (e.g., medical, legal)
**Edit:** `backend/express/src/services/geminiClient.js` line 30
```javascript
"CAPABILITIES:",
"✓ Access real-time weather via Google Search",
"✓ Provide medical information (not medical advice)",
"✓ Search current news, stocks, sports scores",
```

### Change context window size
**Edit:** `backend/express/src/services/geminiClient.js` line 27
```javascript
const history = Array.isArray(session.history) ? session.history.slice(-20) : [];
//                                                                      ^^^ change this number
```

---

## Testing Your Changes

1. Edit the relevant file
2. Restart the backend:
   ```bash
   # For Express changes
   cd backend/express
   npm start

   # For Flask changes
   cd backend/flask
   python app.py
   ```
3. Test by speaking to Blueee
4. Check console logs to see which mode triggered

---

## Troubleshooting

**Assistant still mentions API keys:**
- Check system instructions in `geminiClient.js` (line 35-40)
- Make sure "NEVER say..." rules are clear

**Gmail/Docs not working:**
- Verify OAuth setup in Flask
- Check scopes include gmail/docs (line 73 in app.py)
- Ensure keywords match detection logic (lines 468, 487 in app.py)

**Weather not working:**
- Verify Google Search grounding enabled in your API key
- Check tool configuration in `geminiClient.js` line 38

---

## Advanced: Multi-turn Context

Conversation history is automatically included. To customize how it's used:

**Quick Mode:** Edit `formatHistory()` in `backend/express/src/services/geminiClient.js`
**Think Mode:** Edit `build_contextual_prompt()` in `backend/flask/app.py`
