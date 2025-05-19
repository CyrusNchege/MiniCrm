from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone
from django.conf import settings
from .models import Reminder
import logging

# Get an instance of a logger
logger = logging.getLogger(__name__)

@shared_task
def check_pending_reminders():
    """
    Celery task to check for pending reminders and send reminder emails.
    """
    try:
        # Get all pending reminders where remind_at time has passed
        pending_reminders = Reminder.objects.filter(
            status='Pending',
            remind_at__lte=timezone.now()
        ).select_related('lead')

        if not pending_reminders.exists():
            logger.info("No pending reminders found.")
            return

        for reminder in pending_reminders:
            if not reminder.lead.email:
                logger.warning(f"Skipping reminder for lead {reminder.lead.name} (ID: {reminder.lead.id}) as no email is provided.")
                continue

            # Email details
            subject = f"Mini CRM Reminder: Task for {reminder.lead.name}"
            
            # Plain-text body (for email clients that don't support HTML)
            plain_message = f"""
Dear {reminder.lead.name},

This is a reminder for your task:
{reminder.message}

Lead: {reminder.lead.name}
Due: {reminder.remind_at.strftime('%B %d, %Y %I:%M %p %Z')}

Please contact us at support@minicrm.com if you need assistance.

Best regards,
Mini CRM Team
"""

            # HTML body for styled email
            html_message = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f4f4f4;
            margin: 0;
            padding: 0;
        }}
        .container {{
            max-width: 600px;
            margin: 20px auto;
            background: #fff;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .header {{
            background: #007bff;
            color: #fff;
            padding: 10px 20px;
            text-align: center;
            border-radius: 8px 8px 0 0;
        }}
        .header h1 {{
            margin: 0;
            font-size: 24px;
        }}
        .content {{
            padding: 20px;
        }}
        .content h2 {{
            color: #007bff;
            font-size: 20px;
        }}
        .content p {{
            margin: 10px 0;
        }}
        .details {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            margin: 10px 0;
        }}
        .details p {{
            margin: 5px 0;
        }}
        .cta {{
            display: inline-block;
            padding: 10px 20px;
            background: #007bff;
            color: #fff;
            text-decoration: none;
            border-radius: 5px;
            margin-top: 15px;
        }}
        .footer {{
            text-align: center;
            color: #777;
            font-size: 12px;
            padding: 10px;
            border-top: 1px solid #eee;
        }}
        .footer a {{
            color: #007bff;
            text-decoration: none;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Mini CRM Reminder</h1>
        </div>
        <div class="content">
            <h2>Hello, {reminder.lead.name}</h2>
            <p>We’re reaching out to remind you about an important task in Mini CRM.</p>
            <div class="details">
                <p><strong>Task:</strong> {reminder.message}</p>
                <p><strong>Lead:</strong> {reminder.lead.name}</p>
                <p><strong>Due:</strong> {reminder.remind_at.strftime('%B %d, %Y %I:%M %p %Z')}</p>
            </div>
            <p>Please take a moment to review this task in your Mini CRM account. If you need assistance, our support team is here to help.</p>
            <a href="https://mini-crm-frontend.vercel.app" class="cta">View Task in Mini CRM</a>
        </div>
        <div class="footer">
            <p>Mini CRM Team | <a href="mailto:support@minicrm.com">support@minicrm.com</a></p>
            <p>© 2025 Mini CRM. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
"""

            logger.info(f"Sending reminder email to {reminder.lead.email} from {settings.EMAIL_HOST_USER}")

            try:
                # Use EmailMultiAlternatives for plain text and HTML
                email = EmailMultiAlternatives(
                    subject=subject,
                    body=plain_message,
                    from_email=settings.EMAIL_HOST_USER,
                    to=[reminder.lead.email],
                )
                # Attach HTML version
                email.attach_alternative(html_message, 'text/html')
                email.send(fail_silently=False)

                # Update reminder status
                reminder.status = 'Complete'
                reminder.save()

            except Exception as e:
                logger.error(f"Failed to send reminder email to {reminder.lead.email}: {str(e)}")

    except Exception as e:
        logger.critical(f"Critical error in check_pending_reminders task: {str(e)}")