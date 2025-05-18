from celery import shared_task
from django.core.mail import send_mail
from .models import Reminder
from django.conf import settings

@shared_task
def send_reminder_email(reminder_id):
    try:
        reminder = Reminder.objects.get(id=reminder_id)
        if reminder.status == 'PENDING':
            subject = f"Reminder: {reminder.message}"
            message = f"Reminder for lead {reminder.lead.name}: {reminder.message}\nScheduled for: {reminder.remind_at}"
            from_email = settings.DEFAULT_FROM_EMAIL
            recipient_list = [reminder.created_by.email]
            send_mail(subject, message, from_email, recipient_list)
            reminder.status = 'COMPLETED'
            reminder.save()
    except Reminder.DoesNotExist:
        pass

@shared_task
def send_notification(emails, title, body):
    subject = title
    message = body
    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = emails
    send_mail(subject, message, from_email, recipient_list)