/**
 * Content-Security-Policy for the dashboard.
 * Production styles are stylesheets only: no 'unsafe-inline'.
 * Scripts keep a per-request nonce and 'strict-dynamic'.
 * The dev server still needs inline styles for its error overlay.
 */

export function contentSecurityPolicy(input: { isProd: boolean; nonce: string; apiOrigin: string }): string {
  const nonce = /^[A-Za-z0-9+/=]+$/.test(input.nonce) ? input.nonce : "invalid";
  const api = originToken(input.apiOrigin);
  const scriptSrc = input.isProd ? `'self' 'nonce-${nonce}' 'strict-dynamic'` : `'self' 'unsafe-inline' 'unsafe-eval'`;
  const styleSrc = input.isProd ? "'self'" : "'self' 'unsafe-inline'";
  const connectSrc = input.isProd
    ? joinSources(["'self'", api])
    : joinSources(["'self'", api, "ws:", "wss:", "http://127.0.0.1:8000", "http://localhost:8000"]);
  const directives = [
    "default-src 'self'",
    `script-src ${scriptSrc}`,
    `style-src ${styleSrc}`,
  ];
  if (input.isProd) directives.push("style-src-attr 'none'");
  directives.push(
    "img-src 'self' data: https:",
    "font-src 'self' data:",
    `connect-src ${connectSrc}`,
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
  );
  return directives.join("; ");
}

function originToken(value: string): string {
  const trimmed = value.trim();
  if (!/^https?:\/\/[A-Za-z0-9._:-]+$/.test(trimmed)) return "";
  return trimmed;
}

function joinSources(sources: string[]): string {
  return sources.filter((item) => item.length > 0).join(" ");
}
