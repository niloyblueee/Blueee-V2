const { GoogleGenerativeAI } = require("@google/generative-ai");

const apiKey = process.env.GEMINI_API_KEY || process.env.gemini_api_key;
const modelName = process.env.GEMINI_MODEL || "gemini-2.5-flash";

function createClient(config = {}) {
  if (!apiKey) {
    throw new Error("Missing GEMINI_API_KEY");
  }
  const client = new GoogleGenerativeAI(apiKey);
  return client.getGenerativeModel({ 
    model: modelName,
    ...config
  });
}

function formatHistory(history) {
  if (!history.length) {
    return "";
  }
  const lines = history.map((item) => {
    const label = item.role === "assistant" ? "Assistant" : "User";
    return `${label}: ${item.text}`;
  });
  return `Conversation so far:\n${lines.join("\n")}`;
}

async function getQuickReply(payload, session) {
  const userName = session.userName || "";
  const agency = session.userAgency || "";
  const history = Array.isArray(session.history) ? session.history.slice(-20) : [];
  
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
    "",
    userName ? `User: ${userName}` : "",
    agency ? `Agency: ${agency}` : "",
  ].filter(Boolean).join("\n");
  
  const conversationContext = formatHistory(history);
  const userMessage = payload.text || "";

  // Enable Google Search and code execution
  const model = createClient({
    systemInstruction: systemInstructions,
    tools: [
      { googleSearch: {} },
      { codeExecution: {} }
    ]
  });

  const result = await model.generateContent([
    conversationContext ? conversationContext + "\n\n" : "",
    `User: ${userMessage}`
  ].join(""));
  
  const text = result?.response?.text?.() || "";
  return { text };
}

module.exports = { getQuickReply };
