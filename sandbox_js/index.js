function generateId() {
  // Use native crypto.randomUUID if available (Node >=14, modern browsers)
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }

  // Fallback: generate a UUID v4 using Node's crypto module
  const cryptoModule = require('crypto');
  const bytes = cryptoModule.randomBytes(16);
  // Set version to 4 => xxxx4xxx
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  // Set variant to RFC4122 => xx8xxx, 9, a, or b => 10xx
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  const hex = [...bytes].map(b => b.toString(16).padStart(2, '0')).join('');
  return `${hex.substr(0, 8)}-${hex.substr(8, 4)}-${hex.substr(12, 4)}-${hex.substr(16, 4)}-${hex.substr(20, 12)}`;
}

module.exports = { generateId };
