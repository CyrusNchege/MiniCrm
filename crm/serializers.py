from rest_framework import serializers
from .models import Lead, Contact, Note, Reminder
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password

class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'username', 'email', 'password']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        validated_data['password'] = make_password(validated_data['password'])
        return super().create(validated_data)

class LeadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lead
        fields = ['id', 'name', 'email', 'company', 'status', 'phone', 'created_at', 'updated_at', 'user']
        read_only_fields = ['user']  

class LeadRelatedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lead
        fields = ['id', 'name']

class ContactSerializer(serializers.ModelSerializer):
    lead = LeadRelatedSerializer(read_only=True) 
    lead_id = serializers.PrimaryKeyRelatedField(queryset=Lead.objects.all(), write_only=True, source='lead')

    class Meta:
        model = Contact
        fields = ['id', 'name', 'email', 'phone', 'lead', 'lead_id', 'user']
        read_only_fields = ['user'] 

    def create(self, validated_data):
        validated_data['user'] = self.context['user']
        return super().create(validated_data)

class NoteSerializer(serializers.ModelSerializer):
    lead = LeadRelatedSerializer(read_only=True) 
    lead_id = serializers.PrimaryKeyRelatedField(queryset=Lead.objects.all(), write_only=True, source='lead')

    class Meta:
        model = Note
        fields = ['id', 'content', 'created_at', 'lead', 'lead_id', 'user']
        read_only_fields = ['user'] 

class ReminderSerializer(serializers.ModelSerializer):
    lead = LeadRelatedSerializer(read_only=True) 
    lead_id = serializers.PrimaryKeyRelatedField(queryset=Lead.objects.all(), write_only=True, source='lead')

    class Meta:
        model = Reminder
        fields = ['id', 'message', 'remind_at', 'created_at', 'status', 'lead', 'lead_id', 'user']
        read_only_fields = ['user'] 