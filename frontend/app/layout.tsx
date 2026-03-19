import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI Consulting Agency",
  description: "Autonomous AI consulting — from brief to delivery in days, not months.",
};

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
            <div style={{ display: "flex", gap: "1rem", alignItems: "center" }}>
              <a href="/consult" className="btn btn-outline" style={{ padding: "0.5rem 1rem", fontSize: "0.875rem" }}>
                Start Consultation
              </a>
            </div>
          </div>
        </nav>
        <main>{children}</main>
      </body>
    </html>
  );
}
