const { OAuth2Client } = require("google-auth-library");

const clientId = process.env.GOOGLE_CLIENT_ID;
const clientSecret = process.env.GOOGLE_CLIENT_SECRET;
const redirectUri = process.env.GOOGLE_REDIRECT_URI || "http://localhost:3001/api/oauth/google/callback";

const scopes = [
  "https://www.googleapis.com/auth/userinfo.email",
  "https://www.googleapis.com/auth/gmail.modify",
  "https://www.googleapis.com/auth/drive",
  "https://www.googleapis.com/auth/calendar"
];

function getClient() {
  if (!clientId || !clientSecret) {
    throw new Error("Missing GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET");
  }
  return new OAuth2Client(clientId, clientSecret, redirectUri);
}

function getOAuthUrl() {
  const client = getClient();
  return client.generateAuthUrl({
    access_type: "offline",
    scope: scopes,
    prompt: "consent"
  });
}

async function handleOAuthCallback(code) {
  if (!code) {
    throw new Error("Missing OAuth code");
  }
  const client = getClient();
  const { tokens } = await client.getToken(code);
  return tokens;
}

function getStoredTokens(session) {
  return session.googleTokens || null;
}

module.exports = {
  getOAuthUrl,
  handleOAuthCallback,
  getStoredTokens
};
