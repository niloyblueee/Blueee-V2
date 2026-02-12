const http = require("http");
const path = require("path");
const express = require("express");
const cors = require("cors");
const session = require("express-session");
const dotenv = require("dotenv");

dotenv.config({ path: path.join(__dirname, "..", "..", ".env") });

const { voiceIntelligence } = require("./middleware/voiceIntelligence");
const apiRouter = require("./routes/api");

if (process.env.GEMINI_API_KEY || process.env.gemini_api_key) {
  console.log("[gemini] API key detected.");
} else {
  console.warn("[gemini] GEMINI_API_KEY is not set.");
}

const app = express();
const server = http.createServer(app);

app.use(cors({
  origin: process.env.CORS_ORIGIN || "http://localhost:5173",
  credentials: true
}));
app.use(express.json({ limit: "10mb" }));
app.use(session({
  name: "blueee.sid",
  secret: process.env.SESSION_SECRET || "dev-session-secret",
  resave: false,
  saveUninitialized: false,
  cookie: {
    httpOnly: true,
    sameSite: "lax",
    secure: false,
    maxAge: 1000 * 60 * 60 * 12
  }
}));

app.get("/health", (req, res) => {
  res.json({ ok: true, service: "blueee-v2-gateway" });
});

app.use("/api", voiceIntelligence, apiRouter);


const port = Number(process.env.PORT || 3001);
server.listen(port, () => {
  console.log(`Blueee V2 Gateway listening on :${port}`);
});
