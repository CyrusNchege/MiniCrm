from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Lead, Contact, Note, Reminder

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']
        read_only_fields = ['id', 'username', 'email', 'first_name', 'last_name']

class MinimalLeadSerializer(serializers.ModelSerializer):
    """Slimmed-down serializer for nested lead fields"""
    class Meta:
        model = Lead
        fields = ['id', 'name']
        read_only_fields = ['id', 'name']

class ContactSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)
    lead = MinimalLeadSerializer(read_only=True)
    lead_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Contact
        fields = ['id', 'lead', 'lead_id', 'name', 'email', 'phone', 'created_by', 'created_at']
        read_only_fields = ['id', 'created_at', 'created_by', 'lead']
        extra_kwargs = {'lead_id': {'write_only': True}}

class NoteSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)
    lead = MinimalLeadSerializer(read_only=True)
    lead_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Note
        fields = ['id', 'lead', 'lead_id', 'content', 'created_by', 'created_at']
        read_only_fields = ['id', 'created_at', 'created_by', 'lead']
        extra_kwargs = {'lead_id': {'write_only': True}}

class ReminderSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)
    lead = MinimalLeadSerializer(read_only=True)
    lead_id = serializers.IntegerField(write_only=True)
    lead_name = serializers.CharField(source='lead.name', read_only=True)

    class Meta:
        model = Reminder
        fields = ['id', 'lead', 'lead_id', 'lead_name', 'message', 'status', 'remind_at', 'created_by', 'created_at']
        read_only_fields = ['id', 'created_at', 'created_by', 'lead', 'lead_name']
        extra_kwargs = {'lead_id': {'write_only': True}}

class LeadSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)
    contacts = ContactSerializer(many=True, read_only=True)
    notes = NoteSerializer(many=True, read_only=True)
    reminders = ReminderSerializer(many=True, read_only=True)

    class Meta:
        model = Lead
        fields = ['id', 'name', 'email', 'company', 'status', 'phone', 'created_by', 'created_at', 'updated_at', 'contacts', 'notes', 'reminders']
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by', 'contacts', 'notes', 'reminders']

class LeadListSerializer(serializers.ModelSerializer):
    """Optimized serializer for list view"""
    created_by = UserSerializer(read_only=True)

    class Meta:
        model = Lead
        fields = ['id', 'name', 'email', 'company', 'status', 'phone', 'created_by', 'created_at', 'updated_at']