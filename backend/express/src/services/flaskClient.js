const axios = require("axios");

const FLASK_URL = process.env.FLASK_URL || "http://localhost:5000";

async function forwardToFlask(payload, session) {
  const response = await axios.post(`${FLASK_URL}/ai`, {
    ...payload,
    session: {
      name: session.userName || null,
      agency: session.userAgency || null,
      history: Array.isArray(session.history) ? session.history.slice(-20) : []
    }
  });
  return response.data;
}
module.exports = { forwardToFlask };
