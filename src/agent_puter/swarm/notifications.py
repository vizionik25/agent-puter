"""
notifications.py — Email notification helpers.

Sends transactional emails at key project milestones:
  - Proposal ready   (after consultation complete)
  - Demo ready       (after demo URL is set)
  - Delivery complete (after final payment)

Configuration (all optional — notifications are silently skipped if unset):
    SMTP_HOST     — SMTP server hostname (e.g. smtp.gmail.com)
    SMTP_PORT     — SMTP port (default: 587)
    SMTP_USER     — SMTP login username / email address
    SMTP_PASS     — SMTP login password or app-specific password
    FROM_EMAIL    — Sender address (defaults to SMTP_USER)
    FRONTEND_URL  — Base URL for action links (default: http://localhost:3000)
"""
from __future__ import annotations

import os
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from .models import Project, ConsultSession


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _smtp_configured() -> bool:
    return bool(os.getenv("SMTP_HOST") and os.getenv("SMTP_USER") and os.getenv("SMTP_PASS"))


def _send(to: str, subject: str, body_html: str, body_text: str) -> None:
    """Send one email via SMTP. Logs and swallows all exceptions."""
    if not _smtp_configured():
        return

    host = os.environ["SMTP_HOST"]
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.environ["SMTP_USER"]
    password = os.environ["SMTP_PASS"]
    from_addr = os.getenv("FROM_EMAIL", user)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to
    msg.attach(MIMEText(body_text, "plain"))
    msg.attach(MIMEText(body_html, "html"))

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(host, port) as server:
            server.ehlo()
            server.starttls(context=context)
            server.login(user, password)
            server.sendmail(from_addr, [to], msg.as_string())
        print(f"[Notifications] Sent '{subject}' to {to}")
    except Exception as exc:
        print(f"[Notifications] Failed to send email to {to}: {exc}")


def _base_url() -> str:
    return os.getenv("FRONTEND_URL", "http://localhost:3000").rstrip("/")


# ---------------------------------------------------------------------------
# Public notification functions
# ---------------------------------------------------------------------------


def notify_proposal_ready(project: Project, session: ConsultSession) -> None:
    """Email the client that their proposal is ready for review.

    Sends an HTML email containing the project name, total price, deposit
    amount, estimated delivery days, and a link to the proposal page.  The
    email is silently skipped if SMTP is not configured.

    Args:
        project (Project): The project whose proposal has been generated.
            Must have ``total_price_usd`` set; ``proposal`` is used for
            deposit and ETA details if present.
        session (ConsultSession): The consultation session supplying the
            client's name and email address.
    """
    url = f"{_base_url()}/proposal/{project.id}"
    price = f"${project.total_price_usd:,.2f}"
    deposit = f"${project.proposal.deposit_amount_usd:,.2f}" if project.proposal else ""

    subject = f"Your proposal is ready — {project.name}"

    html = f"""
    <div style="font-family:sans-serif;max-width:600px;margin:auto">
      <h2 style="color:#7c3aed">Your Proposal Is Ready</h2>
      <p>Hi {session.client_name},</p>
      <p>Our team has reviewed your project and prepared a detailed proposal.</p>
      <ul>
        <li><strong>Project:</strong> {project.name}</li>
        <li><strong>Total price:</strong> {price}</li>
        <li><strong>Deposit to begin:</strong> {deposit} (20%)</li>
        <li><strong>Estimated delivery:</strong> {project.proposal.delivery_eta_days if project.proposal else "TBD"} days</li>
      </ul>
      <p>
        <a href="{url}" style="background:#7c3aed;color:#fff;padding:12px 24px;border-radius:6px;text-decoration:none;display:inline-block">
          Review Proposal →
        </a>
      </p>
      <p style="color:#6b7280;font-size:0.875rem">
        You will only be charged the 20% deposit to start. The remaining 80% is due after you approve the live demo.
      </p>
    </div>
    """
    text = (
        f"Hi {session.client_name},\n\n"
        f"Your proposal for '{project.name}' is ready.\n"
        f"Total price: {price} | Deposit: {deposit}\n\n"
        f"Review it here: {url}\n"
    )
    _send(session.client_email, subject, html, text)


def notify_demo_ready(project: Project, client_email: str, client_name: str) -> None:
    """Email the client that their live demo is ready to view.

    Sends an HTML email with a link to the demo review page.  The client is
    reminded that the remaining balance is due after approving the demo.
    The email is silently skipped if SMTP is not configured.

    Args:
        project (Project): The project that has been deployed to a demo
            environment.
        client_email (str): Recipient email address.
        client_name (str): Recipient's first or full name used in the
            greeting.
    """
    url = f"{_base_url()}/demo/{project.id}"
    subject = f"Your demo is live — {project.name}"

    html = f"""
    <div style="font-family:sans-serif;max-width:600px;margin:auto">
      <h2 style="color:#7c3aed">Your Demo Is Live</h2>
      <p>Hi {client_name},</p>
      <p>Great news! Your project is complete and a live demo is ready for your review.</p>
      <p>
        <a href="{url}" style="background:#7c3aed;color:#fff;padding:12px 24px;border-radius:6px;text-decoration:none;display:inline-block">
          View Demo →
        </a>
      </p>
      <p>Once you're happy with the demo, pay the remaining balance to receive full delivery.</p>
    </div>
    """
    text = (
        f"Hi {client_name},\n\n"
        f"Your demo for '{project.name}' is ready.\n\n"
        f"View it here: {url}\n"
    )
    _send(client_email, subject, html, text)


def notify_delivery_complete(project: Project, client_email: str, client_name: str) -> None:
    """Email the client confirming full delivery after final payment.

    Sends an HTML confirmation email with a link to the project status page.
    The email is silently skipped if SMTP is not configured.

    Args:
        project (Project): The fully delivered project.
        client_email (str): Recipient email address.
        client_name (str): Recipient's first or full name used in the
            greeting.
    """
    url = f"{_base_url()}/status/{project.id}"
    subject = f"Delivery confirmed — {project.name}"

    html = f"""
    <div style="font-family:sans-serif;max-width:600px;margin:auto">
      <h2 style="color:#7c3aed">Delivery Confirmed</h2>
      <p>Hi {client_name},</p>
      <p>Payment received. Your project <strong>{project.name}</strong> has been fully delivered.</p>
      <p>
        <a href="{url}" style="background:#7c3aed;color:#fff;padding:12px 24px;border-radius:6px;text-decoration:none;display:inline-block">
          View Project →
        </a>
      </p>
      <p>Thank you for choosing our AI consulting agency!</p>
    </div>
    """
    text = (
        f"Hi {client_name},\n\n"
        f"Your project '{project.name}' has been fully delivered.\n\n"
        f"View details: {url}\n"
    )
    _send(client_email, subject, html, text)
