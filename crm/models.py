from django.db import models
from django.contrib.auth.models import User

class Lead(models.Model):
    user = models.ForeignKey(User, related_name='Leads_user', on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=100)
    email = models.EmailField()
    company = models.CharField(max_length=100, null=True, blank=True)   
    status = models.CharField(max_length=100, null=True, blank=True)
    phone = models.CharField(max_length=15)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class Contact(models.Model):
    user = models.ForeignKey(User, related_name='User_Contact', on_delete=models.CASCADE, null=True, blank=True)
    lead = models.ForeignKey(Lead, related_name='Lead_Contact', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=15)

    def __str__(self):
        return self.name

class Note(models.Model):
    user = models.ForeignKey(User, related_name='User_Note', on_delete=models.CASCADE, null=True, blank=True)
    lead = models.ForeignKey(Lead, related_name='Lead_Note', on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Note for {self.lead.name}"

class Reminder(models.Model):
    user = models.ForeignKey(User, related_name='User_Remainder', on_delete=models.CASCADE, null=True, blank=True)
    lead = models.ForeignKey(Lead, related_name='Reminder_related_lead', on_delete=models.CASCADE)
    message = models.CharField(max_length=255)
    status = models.CharField(max_length=100, default='Pending')
    remind_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
