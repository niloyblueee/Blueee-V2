function isPatternTime(date) {
  const hours = String(date.getHours()).padStart(2, "0");
  const minutes = String(date.getMinutes()).padStart(2, "0");
  return hours[0] === hours[1] && minutes[0] === minutes[1];
}

function getPatternTimeWit(date = new Date()) {
  if (!isPatternTime(date)) {
    return null;
  }

  const options = [
    "Pattern time detected. The universe just winked.",
    "11:11 energy spotted. Make a wish, I already did.",
    "Perfect symmetry on the clock. That is a rare vibe.",
    "The time is a palindrome. I will take that as a yes.",
    "Blueee caught a pattern time. Lucky moment unlocked."
  ];

  return options[Math.floor(Math.random() * options.length)];
}

module.exports = { getPatternTimeWit };
