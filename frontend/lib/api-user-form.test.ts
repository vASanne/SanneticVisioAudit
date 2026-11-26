import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { fileURLToPath } from "node:url";

import { buildUserCreateRequest, formFields, validateUserForm } from "./api-user-form.ts";

const page = readFileSync(fileURLToPath(new URL("../app/users/page.tsx", import.meta.url)), "utf8");

const base = {
  apiUser: false,
  name: "Ada",
  email: "ada@example.com",
  password: "longenough",
  isAdmin: false,
  clientIds: ["client-1"],
  scopes: ["audits:create", "audits:read"],
  expiresOn: "",
};

test("the API user switch hides the password and forces a non-admin key", () => {
  assert.equal(formFields(false).loginFields, true);
  assert.equal(formFields(false).clientSelection, "multiple");
  assert.equal(formFields(true).loginFields, false);
  assert.equal(formFields(true).showEmail, false);
  assert.equal(formFields(true).showAdmin, false);
  assert.equal(formFields(true).showScopes, true);
  assert.equal(formFields(true).clientSelection, "single");

  const body = buildUserCreateRequest({ ...base, apiUser: true, password: "should-not-send", isAdmin: true });
  assert.equal(body.is_api_user, true);
  assert.equal(body.is_admin, false);
  assert.equal("password" in body, false);
  assert.equal("email" in body, false);
  assert.deepEqual(body.client_ids, ["client-1"]);
  assert.deepEqual(body.scopes, ["audits:create", "audits:read"]);
});

test("a login user still sends a password and is not an API user", () => {
  const body = buildUserCreateRequest(base);
  assert.equal(body.is_api_user, false);
  assert.equal(body.password, "longenough");
  assert.equal(body.email, "ada@example.com");
  assert.equal("scopes" in body, false);
  assert.equal(validateUserForm({ ...base, password: "short" }), "Passwort muss mindestens 8 Zeichen haben.");
  assert.equal(validateUserForm({ ...base, apiUser: true, clientIds: [] }), "Ein API-Nutzer braucht genau einen Mandanten.");
});

test("the user page wires the switch, the one-time secret, and does not store it", () => {
  assert.match(page, /role="switch"/);
  assert.match(page, /API-Nutzer/);
  assert.match(page, /buildUserCreateRequest/);
  assert.match(page, /nur dieses eine Mal/);
  assert.match(page, /revokeApiKey/);
  assert.match(page, /rotateApiKey/);
  assert.doesNotMatch(page, /localStorage|sessionStorage/);
});
