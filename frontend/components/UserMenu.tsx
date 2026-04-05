"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { getMe, loginWithGitHub, logout, type GitHubUser } from "@/lib/auth";

/**
 * Navigation component that renders a GitHub sign-in button when logged out,
 * or a user avatar dropdown menu with links to Dashboard, New Project, Billing, and Sign out when authenticated.
 *
 * @returns {JSX.Element} A sign-in button or an avatar dropdown menu.
 */
export default function UserMenu() {
  const [user, setUser] = useState<GitHubUser | null | undefined>(undefined);
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    getMe().then(setUser);
  }, []);

  // Close dropdown on outside click
  useEffect(() => {
    function handle(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handle);
    return () => document.removeEventListener("mousedown", handle);
  }, []);

  // Loading state — render nothing so nav doesn't shift
  if (user === undefined) return null;

  if (!user) {
    return (
      <button
        onClick={loginWithGitHub}
        className="btn btn-outline"
        style={{ padding: "0.5rem 1rem", fontSize: "0.875rem", display: "flex", alignItems: "center", gap: "0.4rem" }}
      >
        <GitHubIcon />
        Sign in with GitHub
      </button>
    );
  }

  return (
    <div ref={menuRef} style={{ position: "relative" }}>
      <button
        onClick={() => setOpen((o) => !o)}
        style={{
          background: "none",
          border: "1px solid var(--border)",
          borderRadius: "9999px",
          cursor: "pointer",
          padding: "2px",
          display: "flex",
          alignItems: "center",
          gap: "0.5rem",
          paddingRight: "0.75rem",
        }}
      >
        {user.avatar_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={user.avatar_url}
            alt={user.login}
            width={28}
            height={28}
            style={{ borderRadius: "50%" }}
          />
        ) : (
          <div style={{
            width: 28, height: 28, borderRadius: "50%",
            background: "var(--violet-g)", display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: "0.75rem", color: "#fff", fontWeight: 700,
          }}>
            {user.login[0].toUpperCase()}
          </div>
        )}
        <span style={{ fontSize: "0.875rem", color: "var(--text)" }}>{user.login}</span>
        <ChevronIcon open={open} />
      </button>

      {open && (
        <div
          style={{
            position: "absolute",
            right: 0,
            top: "calc(100% + 0.5rem)",
            minWidth: "180px",
            background: "var(--card-bg)",
            border: "1px solid var(--border)",
            borderRadius: "var(--radius)",
            boxShadow: "0 8px 24px rgba(0,0,0,0.4)",
            zIndex: 100,
            overflow: "hidden",
          }}
        >
          <div style={{ padding: "0.75rem 1rem", borderBottom: "1px solid var(--border)" }}>
            <div style={{ fontSize: "0.85rem", color: "var(--text)", fontWeight: 600 }}>{user.name || user.login}</div>
            <div style={{ fontSize: "0.75rem", color: "var(--muted)", marginTop: "0.15rem" }}>
              {user.tier.charAt(0).toUpperCase() + user.tier.slice(1)} plan
            </div>
          </div>
          <nav>
            <DropdownLink href="/dashboard" onClick={() => setOpen(false)}>Dashboard</DropdownLink>
            <DropdownLink href="/consult" onClick={() => setOpen(false)}>New Project</DropdownLink>
            <DropdownLink href="/billing" onClick={() => setOpen(false)}>Billing</DropdownLink>
            <button
              onClick={() => { setOpen(false); logout(); }}
              style={{
                display: "block", width: "100%", textAlign: "left",
                padding: "0.6rem 1rem", fontSize: "0.875rem",
                color: "#f87171", background: "none", border: "none",
                cursor: "pointer",
              }}
            >
              Sign out
            </button>
          </nav>
        </div>
      )}
    </div>
  );
}

function DropdownLink({ href, onClick, children }: { href: string; onClick: () => void; children: React.ReactNode }) {
  return (
    <Link
      href={href}
      onClick={onClick}
      style={{
        display: "block",
        padding: "0.6rem 1rem",
        fontSize: "0.875rem",
        color: "var(--text)",
        textDecoration: "none",
      }}
      onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(255,255,255,0.05)")}
      onMouseLeave={(e) => (e.currentTarget.style.background = "none")}
    >
      {children}
    </Link>
  );
}

function GitHubIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
      <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z" />
    </svg>
  );
}

function ChevronIcon({ open }: { open: boolean }) {
  return (
    <svg
      width="12" height="12" viewBox="0 0 12 12" fill="none"
      style={{ transform: open ? "rotate(180deg)" : "none", transition: "transform 0.2s" }}
    >
      <path d="M2 4l4 4 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
