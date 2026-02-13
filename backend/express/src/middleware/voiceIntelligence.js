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
  "gmail",
  "email",
  "inbox",
  "check my mail",
  "google doc",
  "create doc",
  "save to docs"
];

function voiceIntelligence(req, res, next) {
  const text = String(req.body?.text || "");
  const hint = String(req.body?.hint || "");
  const force = String(req.body?.route || "");

  if (force === "think" || force === "quick") {
    req.voiceRoute = force;
    return next();
  }

  const lower = `${text} ${hint}`.toLowerCase();
  
  // Route Gmail and Docs to Flask (has OAuth)
  if (/\b(gmail|email|inbox|check.*(mail|email)|google doc|create doc|save.*doc)\b/i.test(lower)) {
    req.voiceRoute = "think";
    return next();
  }
  
  const isComplex =
    lower.length > 140 ||
    COMPLEX_HINTS.some((word) => lower.includes(word)) ||
    Boolean(req.body?.systemTask);

  req.voiceRoute = isComplex ? "think" : "quick";
  next();
}

module.exports = { voiceIntelligence };
