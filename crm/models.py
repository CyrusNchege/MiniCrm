from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.exceptions import ValidationError

class Lead(models.Model):
    STATUS_CHOICES = (
        ('NEW', 'New'),
        ('CONTACTED', 'Contacted'),
        ('QUALIFIED', 'Qualified'),
        ('LOST', 'Lost'),
    )
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True, blank=True, null=True)
    company = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='NEW')
    phone = models.CharField(max_length=20, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def clean(self):
        if self.email:
            self.email = self.email.lower()
            queryset = Lead.objects.filter(email__iexact=self.email)
            if self.pk:
                queryset = queryset.exclude(pk=self.pk)
            if queryset.exists():
                raise ValidationError({'email': 'Lead with this email already exists.'})

    class Meta:
        ordering = ['-created_at']

class Contact(models.Model):
    lead = models.ForeignKey(Lead, related_name='contacts', on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    def clean(self):
        if self.email:
            self.email = self.email.lower()
            queryset = Contact.objects.filter(email__iexact=self.email)
            if self.pk:
                queryset = queryset.exclude(pk=self.pk)
            if queryset.exists():
                raise ValidationError({'email': 'Contact with this email already exists.'})

    class Meta:
        ordering = ['-created_at']

class Note(models.Model):
    lead = models.ForeignKey(Lead, related_name='notes', on_delete=models.CASCADE)
    content = models.TextField()
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Note for {self.lead.name}"

    class Meta:
        ordering = ['-created_at']

class Reminder(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    )
    lead = models.ForeignKey(Lead, related_name='reminders', on_delete=models.CASCADE)
    message = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    remind_at = models.DateTimeField()
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Reminder for {self.lead.name}"

    def clean(self):
        if self.remind_at <= timezone.now():
            raise ValidationError({'remind_at': 'Reminder time must be in the future.'})

    class Meta:
        ordering = ['-created_at']