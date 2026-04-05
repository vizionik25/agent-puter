import type { Metadata } from "next";
import "./globals.css";
import UserMenu from "@/components/UserMenu";

export const metadata: Metadata = {
  title: "AI Consulting Agency",
  description: "Autonomous AI consulting — from brief to delivery in days, not months.",
};

/**
 * Root application layout that wraps every page with the Inter font, a top nav bar
 * (logo, Consult link, Pricing link, and UserMenu), and a main content area.
 *
 * @param {React.ReactNode} children - Page content rendered inside the main element.
 * @returns {JSX.Element} The full HTML document shell with persistent navigation.
 */
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>
        <nav className="nav">
          <div className="container nav-inner">
            <a href="/" className="nav-logo">⚡ SwarmAI</a>
            <div style={{ display: "flex", gap: ".75rem", alignItems: "center" }}>
              <a href="/consult" style={{ fontSize: ".85rem", color: "var(--muted)", textDecoration: "none" }}>
                Consult
              </a>
              <a href="/#pricing" style={{ fontSize: ".85rem", color: "var(--muted)", textDecoration: "none" }}>
                Pricing
              </a>
              <UserMenu />
            </div>
          </div>
        </nav>
        <main>{children}</main>
      </body>
    </html>
  );
}
