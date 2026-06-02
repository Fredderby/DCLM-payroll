#!/usr/bin/env python3
"""
SMTP Test Tool - Tests SMTP connection and authentication
using the same aiosmtplib library the application uses.
"""
import asyncio
import sys


async def test_smtp():
    print("=" * 60)
    print("aiosmtplib SMTP Diagnostic Test")
    print("=" * 60)
    
    server = "smtp.gmail.com"
    port = 587
    username = "nationaladministration@dclmgh.org"
    password = "lxvgthhpsfxagrpc"
    
    print(f"\nConfiguration:")
    print(f"  Server:     {server}:{port}")
    print(f"  Username:   {username}")
    print(f"  Password:   {'*' * len(password)} ({len(password)} chars)")
    
    # Test 1: Basic connection
    print(f"\n[Test 1] Connecting to {server}:{port}...")
    try:
        smtp = aiosmtplib.SMTP(hostname=server, port=port, timeout=15)
        await smtp.connect()
        print(f"  CONNECTED")
    except Exception as e:
        print(f"  FAILED: {type(e).__name__}: {e}")
        return False
    
    # Test 2: EHLO
    print(f"\n[Test 2] EHLO...")
    try:
        code, msg = await smtp.ehlo()
        msg_str = msg.decode('utf-8', errors='replace') if isinstance(msg, bytes) else str(msg)
        print(f"  Response: {code} - {msg_str[:200]}")
    except Exception as e:
        print(f"  FAILED: {type(e).__name__}: {e}")
        return False
    
    # Test 3: STARTTLS
    print(f"\n[Test 3] STARTTLS...")
    try:
        # The key fix: use validate_certs=False for starttls
        resp = await smtp.starttls(validate_certs=False)
        print(f"  TLS CONNECTED")
    except Exception as e:
        print(f"  FAILED: {type(e).__name__}: {e}")
        # Check if already using TLS
        if "already using" in str(e).lower():
            print("  (Connection was already using TLS - this is OK)")
        else:
            return False
    
    # Test 4: Re-EHLO after TLS
    print(f"\n[Test 4] EHLO after TLS...")
    try:
        code, msg = await smtp.ehlo()
        print(f"  Response: {code}")
    except Exception as e:
        print(f"  FAILED: {type(e).__name__}: {e}")
        return False
    
    # Test 5: Login
    print(f"\n[Test 5] SMTP Login as {username}...")
    try:
        resp = await smtp.login(username, password)
        print(f"  LOGIN SUCCESSFUL!")
    except Exception as e:
        print(f"  FAILED: {type(e).__name__}: {e}")
        error_str = str(e)
        if "535" in error_str or "Authentication" in error_str:
            print(f"\n  DIAGNOSIS: The password is being REJECTED by Gmail.")
            print(f"  This is NOT the same as the previous TLS error.")
            print(f"  The password '{password}' is incorrect or has expired.")
        return False
    
    # Test 6: Send test email
    print(f"\n[Test 6] Sending test email to {username}...")
    from email.mime.text import MIMEText
    try:
        msg = MIMEText("This is a test from DCLM Payroll SMTP diagnostic.")
        msg["Subject"] = "SMTP Test - DCLM Payroll"
        msg["From"] = username
        msg["To"] = username
        
        await smtp.send_message(msg)
        print(f"  SENT - Check {username} inbox")
    except Exception as e:
        print(f"  FAILED: {type(e).__name__}: {e}")
        return False
    
    print(f"\n" + "=" * 60)
    print("ALL TESTS PASSED - SMTP is working correctly!")
    print("=" * 60)
    
    try:
        await smtp.quit()
    except:
        pass
    return True


if __name__ == "__main__":
    import aiosmtplib
    success = asyncio.run(test_smtp())
    sys.exit(0 if success else 1)
