const express = require("express");

const { forwardToFlask } = require("../services/flaskClient");
const { getQuickReply } = require("../services/geminiClient");
const {
  getOAuthUrl,
  handleOAuthCallback,
  getStoredTokens
} = require("../services/googleOAuth");
const { getPatternTimeWit } = require("../utils/patternTime");
const { addHistory, ensureHistory } = require("../services/sessionMemory");

const router = express.Router();

function normalizeIncomingHistory(history, maxItems = 24) {
  if (!Array.isArray(history)) {
    return [];
  }
  return history
    .map((item) => ({
      role: item?.role === "assistant" ? "assistant" : "user",
      text: String(item?.text || "").trim(),
      ts: Date.now()
    }))
    .filter((item) => item.text)
    .slice(-maxItems);
}

router.post("/voice", async (req, res) => {
  try {
    const userText = String(req.body?.text || "");
    const intent = String(req.body?.intent || "");

    ensureHistory(req.session);
    const incomingHistory = normalizeIncomingHistory(req.body?.history);
    if (incomingHistory.length) {
      req.session.history = incomingHistory;
    }

    const lastMessage = req.session.history[req.session.history.length - 1];
    if (userText && (!lastMessage || lastMessage.role !== "user" || lastMessage.text !== userText)) {
      addHistory(req.session, "user", userText);
    }

    if (intent === "clock" || /\b(time|clock|what\s+time)\b/i.test(userText)) {
      const wit = getPatternTimeWit();
      if (wit) {
        addHistory(req.session, "assistant", wit);
        return res.json({
          mode: "pattern-time",
          reply: wit
        });
      }
    }

    if (req.voiceRoute === "think") {
      const flaskResponse = await forwardToFlask(req.body, req.session);
      const assistantText = flaskResponse?.text || flaskResponse?.summary || "";
      addHistory(req.session, "assistant", String(assistantText));
      
      // Pass through video action from Flask
      const result = {
        mode: "thinking",
        source: "flask",
        response: flaskResponse
      };
      
      if (flaskResponse?.response?.action === "play_video" && flaskResponse?.response?.url) {
        result.response.action = "play_video";
        result.response.url = flaskResponse.response.url;
      }
      
      return res.json(result);
    }

    const quickReply = await getQuickReply(req.body, req.session);
    addHistory(req.session, "assistant", quickReply.text || "");
    res.json({
      mode: "quick",
      source: "gemini",
      response: quickReply
    });
  } catch (error) {
    res.status(500).json({
      error: "voice_failed",
      message: error.message
    });
  }
});

router.get("/session", (req, res) => {
  res.json({
    name: req.session.userName || null,
    agency: req.session.userAgency || null,
    history: Array.isArray(req.session.history) ? req.session.history : []
  });
});

router.post("/session", (req, res) => {
  const { name, agency } = req.body || {};
  if (name) {
    req.session.userName = String(name);
  }
  if (agency) {
    req.session.userAgency = String(agency);
  }
  res.json({
    ok: true,
    name: req.session.userName || null,
    agency: req.session.userAgency || null
  });
});

router.get("/oauth/google/url", (req, res) => {
  const authUrl = getOAuthUrl();
  res.json({ url: authUrl });
});

router.get("/oauth/google/callback", async (req, res) => {
  try {
    const { code } = req.query;
    const tokens = await handleOAuthCallback(String(code || ""));
    req.session.googleTokens = tokens;
    res.json({ ok: true });
  } catch (error) {
    res.status(500).json({
      error: "oauth_callback_failed",
      message: error.message
    });
  }
});

router.get("/oauth/google/tokens", (req, res) => {
  const tokens = getStoredTokens(req.session);
  res.json({ tokens });
});

module.exports = router;
