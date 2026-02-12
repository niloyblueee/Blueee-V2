function getSessionContext(session) {
  return {
    name: session.userName || null,
    agency: session.userAgency || null
  };
}

function ensureHistory(session) {
  if (!Array.isArray(session.history)) {
    session.history = [];
  }
  return session.history;
}

function addHistory(session, role, text, maxItems = 12) {
  if (!text) {
    return;
  }
  const history = ensureHistory(session);
  history.push({ role, text, ts: Date.now() });
  if (history.length > maxItems) {
    history.splice(0, history.length - maxItems);
  }
}

function getRecentHistory(session, limit = 6) {
  const history = ensureHistory(session);
  return history.slice(-limit);
}

module.exports = {
  getSessionContext,
  ensureHistory,
  addHistory,
  getRecentHistory
};
