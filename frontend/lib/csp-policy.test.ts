import assert from "node:assert/strict";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

import { contentSecurityPolicy } from "./csp-policy.ts";

const root = fileURLToPath(new URL("..", import.meta.url));

test("production style policy has no unsafe-inline", () => {
  const policy = contentSecurityPolicy({
    isProd: true,
    nonce: "abc+def=",
    apiOrigin: "http://127.0.0.1:8000",
  });
  const style = directive(policy, "style-src");
  const styleAttr = directive(policy, "style-src-attr");
  assert.equal(style.includes("unsafe-inline"), false);
  assert.equal(styleAttr, "style-src-attr 'none'");
  assert.match(policy, /script-src 'self' 'nonce-abc\+def=' 'strict-dynamic'/);
  assert.match(policy, /connect-src 'self' http:\/\/127\.0\.0\.1:8000/);
});

test("a hostile API origin cannot break out of the policy", () => {
  const policy = contentSecurityPolicy({
    isProd: true,
    nonce: "abc",
    apiOrigin: "http://127.0.0.1:8000; script-src 'unsafe-inline'",
  });
  assert.equal(policy.includes("unsafe-inline"), false);
  assert.equal(directive(policy, "connect-src"), "connect-src 'self'");
});

test("the UI does not store tokens or use inline style attributes", () => {
  const files = walk(root).filter((path) => path.endsWith(".ts") || path.endsWith(".tsx"));
  assert.ok(files.length > 5);
  for (const path of files) {
    if (path.endsWith(".test.ts")) continue;
    const source = readFileSync(path, "utf8");
    assert.doesNotMatch(source, /localStorage\.setItem|sessionStorage\.setItem/, path);
    assert.doesNotMatch(source, /style=\{\{/, path);
  }
});

function directive(policy: string, name: string): string {
  const found = policy
    .split(";")
    .map((part) => part.trim())
    .find((part) => part.startsWith(`${name} `) || part === name);
  assert.ok(found, name);
  return found;
}

function walk(dir: string): string[] {
  const files: string[] = [];
  for (const name of readdirSync(dir)) {
    if (name === "node_modules" || name === ".next") continue;
    const path = join(dir, name);
    if (statSync(path).isDirectory()) files.push(...walk(path));
    else files.push(path);
  }
  return files;
}
