const { GoogleGenerativeAI } = require("@google/generative-ai");

const apiKey = process.env.GEMINI_API_KEY || process.env.gemini_api_key;
const modelName = process.env.GEMINI_MODEL || "gemini-2.5-flash";

function createClient() {
  if (!apiKey) {
    throw new Error("Missing GEMINI_API_KEY");
  }
  const client = new GoogleGenerativeAI(apiKey);
  return client.getGenerativeModel({ model: modelName });
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
  const model = createClient();
  const userName = session.userName || "";
  const agency = session.userAgency || "";
  const history = Array.isArray(session.history) ? session.history.slice(-6) : [];
  const prompt = [
    "You are Blueee V2, a desktop voice assistant.",
    userName ? `User name: ${userName}.` : "",
    agency ? `User agency: ${agency}.` : "",
    formatHistory(history),
    `User said: ${payload.text || ""}`,
    "Respond quickly and conversationally."
  ].filter(Boolean).join(" ");

  const result = await model.generateContent(prompt);
  const text = result?.response?.text?.() || "";
  return { text };
}

module.exports = { getQuickReply };
