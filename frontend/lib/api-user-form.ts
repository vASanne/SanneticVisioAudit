/** Form rules for Nutzerverwaltung. An API user has no password and no browser login. */

export const API_SCOPES = ["audits:create", "audits:read"] as const;

export interface UserFormInput {
  apiUser: boolean;
  name: string;
  email: string;
  password: string;
  isAdmin: boolean;
  clientIds: string[];
  scopes: string[];
  expiresOn: string;
}

export interface UserCreateBody {
  name: string;
  email?: string;
  password?: string;
  is_admin: boolean;
  is_api_user: boolean;
  client_ids: string[];
  scopes?: string[];
  expires_at?: string;
}

export function formFields(apiUser: boolean): {
  showEmail: boolean;
  loginFields: boolean;
  showAdmin: boolean;
  showScopes: boolean;
  showExpiry: boolean;
  clientSelection: "single" | "multiple";
} {
  return {
    showEmail: !apiUser,
    loginFields: !apiUser,
    showAdmin: !apiUser,
    showScopes: apiUser,
    showExpiry: apiUser,
    clientSelection: apiUser ? "single" : "multiple",
  };
}

export function validateUserForm(input: UserFormInput): string | null {
  if (!input.name.trim()) return "Name fehlt.";
  if (input.apiUser) {
    if (input.clientIds.filter(Boolean).length !== 1) return "Ein API-Nutzer braucht genau einen Mandanten.";
    if (input.scopes.length === 0) return "Mindestens ein Scope ist erforderlich.";
    return null;
  }
  if (!input.email.trim()) return "E-Mail fehlt.";
  if (input.password.length < 8) return "Passwort muss mindestens 8 Zeichen haben.";
  return null;
}

export function buildUserCreateRequest(input: UserFormInput): UserCreateBody {
  if (input.apiUser) {
    const body: UserCreateBody = {
      name: input.name.trim(),
      is_admin: false,
      is_api_user: true,
      client_ids: input.clientIds.filter(Boolean).slice(0, 1),
      scopes: [...input.scopes],
    };
    if (input.expiresOn) body.expires_at = `${input.expiresOn}T23:59:59Z`;
    return body;
  }
  return {
    name: input.name.trim(),
    email: input.email.trim(),
    password: input.password,
    is_admin: input.isAdmin,
    is_api_user: false,
    client_ids: [...input.clientIds],
  };
}
