from django.shortcuts import get_object_or_404
from django.utils.timezone import now
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from .models import Lead, Contact, Note, Reminder
from .serializers import LeadSerializer, ContactSerializer, NoteSerializer, RegisterSerializer, ReminderSerializer
from knox.models import AuthToken
from django.contrib.auth import login
from rest_framework.authtoken.serializers import AuthTokenSerializer
from knox.views import LoginView as KnoxLoginView
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone

class LoginView(KnoxLoginView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request, format=None):
        try:
            print("POST: login ", request.data)
            serializer = AuthTokenSerializer(data=request.data)
            if serializer.is_valid():
                user = serializer.validated_data['user']
                login(request, user)
                
                # Get the token and expiry from Knox
                token_instance, token = AuthToken.objects.create(user)
                
                return Response({
                    'message': 'Successfully logged in',
                    'data': {
                        'token': token,
                        'user': {
                            'id': user.id,
                            'username': user.username,
                            'email': user.email
                        }
                    }
                })
            
            return Response({
                'message': 'Invalid credentials',
                'errors': serializer.errors
            })
                
        except Exception:
            return Response({
                'message': 'An error occurred during login'
            })

class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, format=None):
        try:
            print("POST: register ", request.data)
            serializer = RegisterSerializer(data=request.data)
            if serializer.is_valid():
                user = serializer.save()
                _, token = AuthToken.objects.create(user)

                return Response({
                    'message': 'User registered successfully',
                    'data': {
                        'token': token,
                        'user': {
                            'id': user.id,
                            'username': user.username,
                            'email': user.email
                        }
                    }
                })

            return Response({
                'message': 'Registration failed',
                'errors': serializer.errors
            })

        except Exception:
            return Response({
                'message': 'An error occurred during registration'
            })

class DashboardAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            user = request.user

            total_leads = Lead.objects.filter(user=user).count()
            active_contacts = Contact.objects.filter(user=user).count()
            pending_reminders = Reminder.objects.filter(
                user=user, remind_at__gte=now()
            ).count()

            recent_notes = (
                Note.objects.filter(user=user)
                .select_related('lead')
                .order_by('-created_at')[:5]
            )
            recent_notes_count = recent_notes.count()

            recent_reminders = (
                Reminder.objects.filter(user=user)
                .select_related('lead')
                .order_by('-created_at')[:5]
            )

            recent_activities = [
                {
                    "id": note.id,
                    "description": f"Note added for lead: {note.lead.name}",
                    "timestamp": note.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                }
                for note in recent_notes
            ] + [
                {
                    "id": reminder.id,
                    "description": f"Reminder created for lead: {reminder.lead.name}",
                    "timestamp": reminder.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                }
                for reminder in recent_reminders
            ]

            recent_activities = sorted(
                recent_activities, key=lambda x: x["timestamp"], reverse=True
            )

            data = {
                "stats": {
                    "total_leads": total_leads,
                    "active_contacts": active_contacts,
                    "pending_reminders": pending_reminders,
                    "recent_notes": recent_notes_count,
                },
                "recent_activity": recent_activities,
            }

            return Response({
                "status": "success",
                "message": "Dashboard data retrieved successfully",
                "data": data
            })

        except Exception:
            return Response({
                "message": "An error occurred while retrieving dashboard data"
            })

class LeadAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk=None):
        print("User: ", request.user)
        if pk:
            lead = get_object_or_404(Lead, pk=pk, user=request.user) 
            serializer = LeadSerializer(lead)
        else:
            leads = Lead.objects.filter(user=request.user)
            serializer = LeadSerializer(leads, many=True)
        return Response({
            'message': 'Lead(s) retrieved successfully',
            'data': serializer.data
        })

    def post(self, request):
        serializer = LeadSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user) 
            return Response({
                'message': 'Lead created successfully',
                'data': serializer.data
            })
        return Response({
            'message': 'Lead creation failed',
            'errors': serializer.errors
        })

    def put(self, request, pk):
        lead = get_object_or_404(Lead, pk=pk, user=request.user)
        serializer = LeadSerializer(lead, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Lead updated successfully',
                'data': serializer.data
            })
        return Response({
            'message': 'Lead update failed',
            'errors': serializer.errors
        })

    def delete(self, request, pk):
        lead = get_object_or_404(Lead, pk=pk, user=request.user)
        lead.delete()
        return Response({
            'message': 'Lead deleted successfully'
        })
    
class ContactAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk=None):
        if pk:
            contact = get_object_or_404(Contact, pk=pk, user=request.user)
            serializer = ContactSerializer(contact)
        else:
            contacts = Contact.objects.filter(user=request.user)
            serializer = ContactSerializer(contacts, many=True)
        return Response({
            'message': 'Contact(s) retrieved successfully',
            'data': serializer.data
        })

    def post(self, request):
        serializer = ContactSerializer(data=request.data, context={'user': request.user})
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Contact created successfully',
                'data': serializer.data
            })
        return Response({
            'message': 'Contact creation failed',
            'errors': serializer.errors
        })

    def put(self, request, pk):
        contact = get_object_or_404(Contact, pk=pk, user=request.user)
        serializer = ContactSerializer(contact, data=request.data, context={'user': request.user})
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Contact updated successfully',
                'data': serializer.data
            })
        return Response({
            'message': 'Contact update failed',
            'errors': serializer.errors
        })

    def delete(self, request, pk):
        contact = get_object_or_404(Contact, pk=pk, user=request.user)
        contact.delete()
        return Response({
            'message': 'Contact deleted successfully'
        })

class NoteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk=None):
        if pk:
            note = get_object_or_404(Note, pk=pk, user=request.user)
            serializer = NoteSerializer(note)
        else:
            notes = Note.objects.filter(user=request.user).select_related('lead')
            serializer = NoteSerializer(notes, many=True)
        return Response({
            'message': 'Note(s) retrieved successfully',
            'data': serializer.data
        })

    def post(self, request):
        serializer = NoteSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user) 
            return Response({
                'message': 'Note created successfully',
                'data': serializer.data
            })
        return Response({
            'message': 'Note creation failed',
            'errors': serializer.errors
        })

    def put(self, request, pk):
        note = get_object_or_404(Note, pk=pk, user=request.user)
        serializer = NoteSerializer(note, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Note updated successfully',
                'data': serializer.data
            })
        return Response({
            'message': 'Note update failed',
            'errors': serializer.errors
        })

    def delete(self, request, pk):
        note = get_object_or_404(Note, pk=pk, user=request.user)
        note.delete()
        return Response({
            'message': 'Note deleted successfully'
        })

class ReminderAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk=None):
        if pk:
            reminder = get_object_or_404(Reminder, pk=pk, user=request.user) 
            serializer = ReminderSerializer(reminder)
        else:
            reminders = Reminder.objects.filter(user=request.user).select_related('lead') 
            serializer = ReminderSerializer(reminders, many=True)
        return Response({
            'message': 'Reminder(s) retrieved successfully',
            'data': serializer.data
        })

    def post(self, request):
        if 'remind_at' not in request.data:
            request.data['remind_at'] = timezone.now()

        serializer = ReminderSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)  
            return Response({
                'message': 'Reminder created successfully',
                'data': serializer.data
            })

        return Response({
            'message': 'Reminder creation failed',
            'errors': serializer.errors
        })

    def put(self, request, pk):
        reminder = get_object_or_404(Reminder, pk=pk, user=request.user)
        serializer = ReminderSerializer(reminder, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Reminder updated successfully',
                'data': serializer.data
            })
        return Response({
            'message': 'Reminder update failed',
            'errors': serializer.errors
        })

    def delete(self, request, pk):
        reminder = get_object_or_404(Reminder, pk=pk, user=request.user)
        reminder.delete()
        return Response({
            'message': 'Reminder deleted successfully'
        })