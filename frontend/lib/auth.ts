/**
 * lib/auth.ts — GitHub OAuth session helpers.
 *
 * The session cookie is httpOnly and managed by the backend.
 * The frontend only knows about the user via GET /api/auth/me.
 */

/** Authenticated user profile returned by GET /api/auth/me, sourced from GitHub OAuth data. */
export interface GitHubUser {
  github_id: string;
  login: string;
  name: string | null;
  email: string | null;
  avatar_url: string;
  tier: string;
  credits: number;
}

/**
 * Fetch the currently authenticated user.
 * Returns null when the session cookie is absent or expired.
 *
 * @returns {Promise<GitHubUser | null>} The authenticated user's profile, or null if unauthenticated.
 */
export async function getMe(): Promise<GitHubUser | null> {
  try {
    const res = await fetch("/api/auth/me", { credentials: "include" });
    if (res.status === 401) return null;
    if (!res.ok) return null;
    return (await res.json()) as GitHubUser;
  } catch {
    return null;
  }
}

/**
 * Redirect the browser to GitHub's OAuth consent screen.
 *
 * @returns {void}
 */
export function loginWithGitHub(): void {
  window.location.href = "/api/auth/github";
}

/**
 * Clear the session cookie and return to the home page.
 *
 * @returns {Promise<void>}
 */
export async function logout(): Promise<void> {
  await fetch("/api/auth/logout", { method: "POST", credentials: "include" });
  window.location.href = "/";
}
