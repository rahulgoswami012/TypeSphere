import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import threading
from flask import current_app

class EmailService:
    @staticmethod
    def _send_async_email(app, msg):
        with app.app_context():
            server_host = app.config.get('MAIL_SERVER', 'smtp.gmail.com')
            port = int(app.config.get('MAIL_PORT', 587))
            
            raw_username = app.config.get('MAIL_USERNAME') or ''
            raw_password = app.config.get('MAIL_PASSWORD') or ''
            
            username = str(raw_username).strip()
            password = str(raw_password).replace(' ', '').strip()

            if not username or not password or 'your_' in username.lower() or 'your_' in password.lower():
                print("\n" + "=" * 65)
                print("❌ EMAIL NOT SENT: Please set MAIL_USERNAME and MAIL_PASSWORD in config.py")
                print(f"   Intended Recipient: {msg['To']}")
                print("=" * 65 + "\n")
                return

            try:
                print(f"📡 Connecting to {server_host}:{port}...")
                server = smtplib.SMTP(server_host, port, timeout=20)
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(username, password)
                server.sendmail(username, [msg['To']], msg.as_string())
                server.quit()

                print("=" * 65)
                print(f"✅ SUCCESS: Email delivered to {msg['To']}")
                print("=" * 65 + "\n")

            except smtplib.SMTPAuthenticationError as auth_err:
                print("\n" + "!" * 65)
                print(f"❌ GMAIL AUTHENTICATION FAILED: {auth_err}")
                print("   Use a 16-letter App Password, not your normal password.")
                print("!" * 65 + "\n")
            except Exception as e:
                print(f"\n❌ SMTP ERROR: {e}\n")

    @staticmethod
    def send_verification_email(recipient_email, username, verification_url):
        app = current_app._get_current_object()
        sender_email = app.config.get('MAIL_USERNAME', 'noreply@typesphere.com')
        sender = f"TypeSphere <{sender_email}>"

        msg = MIMEMultipart('alternative')
        msg['Subject'] = "Action Required: Verify Your TypeSphere Account"
        msg['From'] = sender
        msg['To'] = recipient_email

        text_content = f"""Hello {username},

Welcome to TypeSphere!

Please verify your email address by clicking the link below:
{verification_url}

— The TypeSphere Team
"""
        html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #0e1117; color: #f0f6fc; margin: 0; padding: 20px; }}
    .email-card {{ max-width: 540px; margin: 0 auto; background-color: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 35px 30px; }}
    .brand-title {{ font-size: 24px; font-weight: 800; color: #58a6ff; text-align: center; margin-bottom: 25px; }}
    .content {{ font-size: 15px; line-height: 1.6; color: #c9d1d9; }}
    .btn-wrap {{ text-align: center; margin: 30px 0; }}
    .btn {{ background-color: #238636; color: #ffffff !important; padding: 14px 28px; border-radius: 6px; text-decoration: none; font-weight: 700; font-size: 16px; display: inline-block; }}
    .footer {{ border-top: 1px solid #30363d; margin-top: 25px; padding-top: 15px; font-size: 12px; color: #8b949e; text-align: center; }}
  </style>
</head>
<body>
  <div class="email-card">
    <div class="brand-title">⚡ TypeSphere</div>
    <div class="content">
      <p>Hello <strong>{username}</strong>,</p>
      <p>Welcome to TypeSphere! To activate your account and start tracking your Biometric Typing DNA, please confirm your email address:</p>
      
      <div class="btn-wrap">
        <a href="{verification_url}" class="btn" target="_blank">Verify Email Address</a>
      </div>

      <p style="font-size: 13px; color: #8b949e;">Or paste this link into your browser:</p>
      <p style="word-break: break-all; font-size: 12px; color: #58a6ff;"><a href="{verification_url}" style="color: #58a6ff;">{verification_url}</a></p>
    </div>
    <div class="footer">&copy; 2026 TypeSphere. All rights reserved.</div>
  </div>
</body>
</html>
"""
        msg.attach(MIMEText(text_content, 'plain'))
        msg.attach(MIMEText(html_content, 'html'))
        threading.Thread(target=EmailService._send_async_email, args=(app, msg)).start()

    @staticmethod
    def send_password_reset_email(recipient_email, username, reset_url):
        app = current_app._get_current_object()
        sender_email = app.config.get('MAIL_USERNAME', 'noreply@typesphere.com')
        sender = f"TypeSphere Security <{sender_email}>"

        msg = MIMEMultipart('alternative')
        msg['Subject'] = "Reset Your TypeSphere Password"
        msg['From'] = sender
        msg['To'] = recipient_email

        text_content = f"""Hello {username},

We received a request to reset your TypeSphere account password.

Click the link below to set a new password:
{reset_url}

This link will expire in 1 hour. If you did not request a password reset, you can safely ignore this email.

— The TypeSphere Security Team
"""
        html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #0e1117; color: #f0f6fc; margin: 0; padding: 20px; }}
    .email-card {{ max-width: 540px; margin: 0 auto; background-color: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 35px 30px; }}
    .brand-title {{ font-size: 24px; font-weight: 800; color: #58a6ff; text-align: center; margin-bottom: 25px; }}
    .content {{ font-size: 15px; line-height: 1.6; color: #c9d1d9; }}
    .btn-wrap {{ text-align: center; margin: 30px 0; }}
    .btn {{ background-color: #b05c2a; color: #ffffff !important; padding: 14px 28px; border-radius: 6px; text-decoration: none; font-weight: 700; font-size: 16px; display: inline-block; }}
    .footer {{ border-top: 1px solid #30363d; margin-top: 25px; padding-top: 15px; font-size: 12px; color: #8b949e; text-align: center; }}
  </style>
</head>
<body>
  <div class="email-card">
    <div class="brand-title">⚡ TypeSphere Security</div>
    <div class="content">
      <p>Hello <strong>{username}</strong>,</p>
      <p>We received a request to reset the password for your TypeSphere account. Click the button below to establish a new password:</p>
      
      <div class="btn-wrap">
        <a href="{reset_url}" class="btn" target="_blank">Reset Your Password</a>
      </div>

      <p style="font-size: 13px; color: #8b949e;">This secure link expires in <strong>1 hour</strong>. If you did not request this, you can safely ignore this email.</p>
      <p style="word-break: break-all; font-size: 12px; color: #58a6ff;"><a href="{reset_url}" style="color: #58a6ff;">{reset_url}</a></p>
    </div>
    <div class="footer">&copy; 2026 TypeSphere. All rights reserved.</div>
  </div>
</body>
</html>
"""
        msg.attach(MIMEText(text_content, 'plain'))
        msg.attach(MIMEText(html_content, 'html'))
        threading.Thread(target=EmailService._send_async_email, args=(app, msg)).start()