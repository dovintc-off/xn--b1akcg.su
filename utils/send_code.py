# send_code.py created by DOV1NTC powered by XWARED TEAM(C)
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_code(sender_email, sender_password, recipient_email, code):
    formatted_code = ' '.join(str(code))
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin: 0; padding: 0; background-color: #f4f4f4; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
        
        <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%" style="background-color: #f4f4f4; padding: 20px 0;">
            <tr>
                <td align="center">
                    <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="600" style="background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); overflow: hidden; max-width: 100%;">
                        
                        <tr>
                            <td style="padding: 40px 30px; text-align: center;">
                                
                                <h1 style="margin: 0 0 20px 0; font-size: 24px; color: #333333; font-weight: 600;">
                                    Код подтверждения
                                </h1>
                                
                                <p style="margin: 0 0 30px 0; font-size: 16px; color: #555555; line-height: 1.5;">
                                    Вы запросили код для входа в аккаунт на сайте <strong>квиз.su</strong>.<br>
                                    Используйте код ниже:
                                </p>
                                
                                <div style="background-color: #f0f4f8; border: 1px dashed #cbd5e0; border-radius: 8px; padding: 20px; margin-bottom: 30px;">
                                    <span style="font-size: 32px; letter-spacing: 8px; font-weight: bold; color: #2d3748;">
                                        {formatted_code}
                                    </span>
                                </div>
                                
                                <p style="margin: 0 0 10px 0; font-size: 14px; color: #718096;">
                                    Код действителен в течение <span style="color: #e53e3e; font-weight: 600;">10 минут</span>.
                                </p>
                                
                                <p style="margin: 0; font-size: 14px; color: #a0aec0;">
                                    Если вы не запрашивали вход, просто проигнорируйте это письмо.
                                </p>
                                
                            </td>
                        </tr>
                        
                        <tr>
                            <td style="background-color: #f8fafc; padding: 20px; text-align: center; border-top: 1px solid #edf2f7;">
                                <p style="margin: 0 0 5px 0; font-size: 12px; color: #a0aec0;">
                                    © 2024-2026 Xwaret Team. Все права защищены.
                                </p>
                                <p style="margin: 0; font-size: 12px; color: #cbd5e0;">
                                    Это автоматическое сообщение, пожалуйста, не отвечайте на него.
                                </p>
                            </td>
                        </tr>
                        
                    </table>
                </td>
            </tr>
        </table>
        
    </body>
    </html>
    """

    msg = MIMEMultipart('alternative')
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = "Код подтверждения для квиз.su"
    
    part = MIMEText(html_content, 'html', 'utf-8')
    msg.attach(part)
    
    try:
        smtp_server = 'smtp.gmail.com'
        smtp_port = 465
        
        server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipient_email, msg.as_string())
        server.quit()
        print(f"[SMTP] Код успешно отправлен на {recipient_email}")
    except Exception as e:
        print(f"[SMTP ERROR] Ошибка отправки письма: {e}")