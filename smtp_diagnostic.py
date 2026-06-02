#!/usr/bin/env python3
"""
SMTP Diagnostic Tool for DCLM Payroll
Tests SMTP connectivity, authentication, and produces detailed diagnostics.
"""
import smtplib
import ssl
import sys
import os
from datetime import datetime

def test_smtp_connection():
    print("=" * 70)
    print("SMTP DIAGNOSTIC TOOL - DCLM Payroll")
    print(f"Started: {datetime.now()}")
    print("=" * 70)
    
    # SMTP settings from .env
    server = "smtp.gmail.com"
    port = 587
    username = "nationaladministration@dclmgh.org"
    password = "lxvgthhpsfxagrpc"
    
    print(f"\nCONFIGURATION:")
    print(f"  SMTP Server: {server}")
    print(f"  SMTP Port:   {port}")
    print(f"  Username:    {username}")
    print(f"  Password:    {'*' * len(password)} ({len(password)} chars)")
    
    # Step 1: DNS resolution
    print(f"\n[STEP 1] DNS Resolution for {server}...")
    try:
        import socket
        ip = socket.gethostbyname(server)
        print(f"  PASS: {server} resolves to {ip}")
    except Exception as e:
        print(f"  FAIL: Could not resolve hostname: {e}")
        return False
    
    # Step 2: TCP connectivity
    print(f"\n[STEP 2] TCP Connection to {server}:{port}...")
    try:
        s = smtplib.SMTP(timeout=15)
        s.set_debuglevel(1)
        s.connect(server, port)
        print(f"  PASS: TCP connection established")
    except smtplib.SMTPConnectError as e:
        print(f"  FAIL: SMTP connection failed: {e}")
        return False
    except Exception as e:
        print(f"  FAIL: Connection error: {type(e).__name__}: {e}")
        return False
    
    # Step 3: EHLO
    print(f"\n[STEP 3] EHLO greeting...")
    try:
        code, msg = s.ehlo()
        print(f"  Server response: {code} {msg.decode('utf-8', errors='replace')}")
        if code == 250:
            print(f"  PASS: EHLO accepted")
        else:
            print(f"  FAIL: Unexpected response code {code}")
            s.quit()
            return False
    except Exception as e:
        print(f"  FAIL: EHLO error: {type(e).__name__}: {e}")
        s.quit()
        return False
    
    # Step 4: STARTTLS
    print(f"\n[STEP 4] STARTTLS handshake...")
    try:
        s.starttls(context=ssl.create_default_context())
        print(f"  PASS: TLS handshake successful")
    except smtplib.SMTPNotSupportedError as e:
        print(f"  FAIL: Server does not support STARTTLS: {e}")
        s.quit()
        return False
    except Exception as e:
        print(f"  FAIL: STARTTLS error: {type(e).__name__}: {e}")
        s.quit()
        return False
    
    # Step 5: Re-EHLO after STARTTLS
    print(f"\n[STEP 5] Re-EHLO after TLS...")
    try:
        code, msg = s.ehlo()
        if code == 250:
            print(f"  PASS: EHLO accepted after TLS")
        else:
            print(f"  FAIL: Unexpected response {code}")
            s.quit()
            return False
    except Exception as e:
        print(f"  FAIL: EHLO after TLS error: {type(e).__name__}: {e}")
        s.quit()
        return False
    
    # Step 6: AUTH LOGIN
    print(f"\n[STEP 6] SMTP AUTH LOGIN...")
    try:
        s.login(username, password)
        print(f"  PASS: Authentication successful!")
    except smtplib.SMTPAuthenticationError as e:
        print(f"  FAIL: Authentication rejected!")
        print(f"  Server said: {e.smtp_code} {e.smtp_error.decode('utf-8', errors='replace')}")
        print(f"")
        print(f"  DIAGNOSIS:")
        print(f"  - The App Password you provided is being REJECTED by Gmail.")
        print(f"  - This usually means one of:")
        print(f"    1. The App Password has expired (Gmail App Passwords expire)")
        print(f"    2. The App Password was revoked or regenerated")
        print(f"    3. 2-Factor Authentication (2FA) was disabled then re-enabled")
        print(f"    4. The password has a typo or extra space")
        print(f"    5. You need to visit https://myaccount.google.com/apppasswords to generate a new one")
        print(f"")
        print(f"  REMEDY:")
        print(f"  1. Go to https://myaccount.google.com/security")
        print(f"  2. Enable 2-Step Verification if not already enabled")
        print(f"  3. Go to https://myaccount.google.com/apppasswords")
        print(f"  4. Select 'Mail' and 'Windows Computer'")
        print(f"  5. Generate a new 16-character App Password")
        print(f"  6. Update SMTP_PASSWORD in your .env file with the new password (including spaces it generates)")
        s.quit()
        return False
    except Exception as e:
        print(f"  FAIL: Authentication error: {type(e).__name__}: {e}")
        s.quit()
        return False
    
    # Step 7: Send test email
    print(f"\n[STEP 7] Sending test email to sender address...")
    from email.mime.text import MIMEText
    try:
        msg = MIMEText("This is a diagnostic test email from DCLM Payroll system.")
        msg["Subject"] = "SMTP Diagnostic Test - DCLM Payroll"
        msg["From"] = username
        msg["To"] = username
        
        s.send_message(msg)
        print(f"  PASS: Test email sent successfully to {username}")
        print(f"  Check inbox for the test message.")
    except smtplib.SMTPRecipientsRefused as e:
        print(f"  FAIL: Recipient refused: {e}")
        s.quit()
        return False
    except Exception as e:
        print(f"  FAIL: Send error: {type(e).__name__}: {e}")
        s.quit()
        return False
    
    s.quit()
    
    print(f"\n" + "=" * 70)
    print("DIAGNOSTIC RESULT: ALL TESTS PASSED")
    print("=" * 70)
    print(f"\nThe SMTP configuration is correctly set up for Gmail.")
    print(f"If emails still fail from the application, the issue is in how")
    print(f"the application uses the aiosmtplib library, not the SMTP credentials.")
    print(f"\nPossible application bugs:")
    print(f"  1. aiosmtplib may call starttls() when already in TLS mode")
    print(f"  2. aiosmtplib may use wrong API (send_message vs sendmail)")
    print(f"  3. The async event loop may not be properly initialized")
    return True


if __name__ == "__main__":
    success = test_smtp_connection()
    sys.exit(0 if success else 1)
