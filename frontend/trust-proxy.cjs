"use strict";

const http = require("http");

const FORWARDED = [
  "x-forwarded-for",
  "x-forwarded-host",
  "x-forwarded-proto",
  "x-forwarded-port",
  "x-forwarded-prefix",
  "forwarded",
  "x-real-ip",
];

function normalizeIp(value) {
  if (!value) return "";
  const ip = String(value).trim().toLowerCase();
  return ip.startsWith("::ffff:") ? ip.slice(7) : ip;
}

function ipv4ToInt(ip) {
  const parts = ip.split(".");
  if (parts.length !== 4) return null;
  let value = 0;
  for (const part of parts) {
    if (!/^\d{1,3}$/.test(part)) return null;
    const n = Number(part);
    if (n > 255) return null;
    value = (value * 256) + n;
  }
  return value >>> 0;
}

function ruleMatches(remote, rule) {
  const host = normalizeIp(remote);
  const expected = normalizeIp(rule);
  if (!host || !expected) return false;
  if (!expected.includes("/")) return host === expected;
  const [base, bitsRaw] = expected.split("/");
  const bits = Number(bitsRaw);
  const ip = ipv4ToInt(host);
  const network = ipv4ToInt(base);
  if (ip === null || network === null || !Number.isInteger(bits) || bits < 1 || bits > 32) return false;
  const mask = bits === 32 ? 0xffffffff : ((~0 << (32 - bits)) >>> 0);
  return (ip & mask) === (network & mask);
}

function parseAllowlist(raw) {
  const items = String(raw || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
  if (items.length === 0) {
    throw new Error("TRUSTED_PROXY_IPS is required");
  }
  for (const item of items) {
    if (item === "*" || item === "0.0.0.0/0" || item === "::/0" || /\s/.test(item)) {
      throw new Error("TRUSTED_PROXY_IPS must list specific proxy addresses");
    }
  }
  return items;
}

function peerIsTrusted(remoteAddress, allowlist) {
  return allowlist.some((rule) => ruleMatches(remoteAddress, rule));
}

function install(allowlist) {
  const original = http.Server.prototype.emit;
  http.Server.prototype.emit = function (event, req, ...rest) {
    if (event === "request" && req && req.headers && req.socket && !peerIsTrusted(req.socket.remoteAddress, allowlist)) {
      for (const name of FORWARDED) delete req.headers[name];
    }
    return original.call(this, event, req, ...rest);
  };
}

install(parseAllowlist(process.env.TRUSTED_PROXY_IPS));

module.exports = { parseAllowlist, peerIsTrusted };
