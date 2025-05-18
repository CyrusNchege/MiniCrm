from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q
from django.utils import timezone
from datetime import datetime
from .models import Lead, Contact, Note, Reminder
from .serializers import LeadSerializer, LeadListSerializer, ContactSerializer, NoteSerializer, ReminderSerializer
from .tasks import send_reminder_email, send_notification
from django.core.paginator import Paginator
from django.core.exceptions import ValidationError

class LeadGenericAPIView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.query_params.get('action') == 'lead_details':
            return LeadSerializer
        return LeadListSerializer

    def get(self, request):
        user = request.user
        action = request.query_params.get("action")
        date = request.query_params.get("date") or datetime.now().date()
        start = request.query_params.get("start")
        end = request.query_params.get("end")
        page = request.query_params.get('page', 1)
        rows = request.query_params.get('rows', 25)
        status_filter = request.query_params.get('status')

        if isinstance(date, str):
            date = datetime.strptime(date, '%Y-%m-%d').date()

        if isinstance(start, str) and isinstance(end, str):
            start = datetime.strptime(start, '%Y-%m-%d')
            end = datetime.strptime(end, '%Y-%m-%d')

        query = Q(created_by=user)

        if start and end:
            query &= Q(created_at__gte=start) & Q(created_at__lte=end)
        elif date:
            query &= Q(created_at__date=date)

        if status_filter:
            query &= Q(status=status_filter)

        leads = Lead.objects.filter(query).select_related('created_by')

        if action == "lead_details":
            lead_id = request.query_params.get("lead_id")
            if not lead_id:
                return Response({
                    "message": "lead_id is required"
                }, status=status.HTTP_400_BAD_REQUEST)

            try:
                lead = leads.prefetch_related('contacts', 'notes', 'reminders').get(id=lead_id)
                return Response({
                    "message": "Lead details fetched successfully",
                    "data": LeadSerializer(lead).data
                })
            except Lead.DoesNotExist:
                return Response({
                    "message": "Lead not found"
                }, status=status.HTTP_404_NOT_FOUND)

        paginator = Paginator(leads, rows)
        try:
            current_page = paginator.page(page)
        except:
            return Response({
                "message": "Invalid page number"
            }, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "message": "Leads fetched successfully",
            "leads": LeadListSerializer(current_page.object_list, many=True).data,
            "pagination": {
                "currentPage": current_page.number,
                "total": paginator.count,
                "pageSize": rows
            },
            "last_page": paginator.num_pages,
        })

    def post(self, request):
        user = request.user
        form_data = request.data

        # Required field validation
        name = form_data.get('name')
        if not name:
            return Response({
                "message": "Name is required"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Check for existing lead with same email
        email = form_data.get('email')
        if email:
            existing_lead = Lead.objects.filter(
                Q(created_by=user) & Q(email__iexact=email)
            ).first()
            if existing_lead:
                return Response({
                    "message": "A lead with this email already exists"
                }, status=status.HTTP_400_BAD_REQUEST)

        # Use get_or_create to prevent duplicates
        lead, created = Lead.objects.get_or_create(
            created_by=user,
            name=name,
            email=email,
            defaults={
                'company': form_data.get('company', ''),
                'status': form_data.get('status', 'NEW'),
                'phone': form_data.get('phone', ''),
            }
        )

        if not created:
            return Response({
                "message": "Similar lead exists"
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            lead.full_clean()  # Trigger model validation for email uniqueness
        except ValidationError as e:
            lead.delete()  # Rollback if validation fails
            return Response({
                "message": "Invalid data",
                "errors": e.message_dict
            }, status=status.HTTP_400_BAD_REQUEST)

        lead.save()

        # Notification
        notification_title = "Lead Created"
        notification_message = f"Lead {lead.name} created successfully!"
        emails = [user.email]

        send_notification.delay(
            emails=emails,
            title=notification_title,
            body=notification_message,
        )

        return Response({
            "message": "Lead created successfully!",
            "data": LeadSerializer(lead).data
        }, status=status.HTTP_201_CREATED)

    def put(self, request):
        lead_id = request.data.get('id')
        try:
            lead = Lead.objects.get(id=lead_id, created_by=request.user)
            serializer = LeadSerializer(lead, data=request.data, partial=True)
            if serializer.is_valid():
                lead = serializer.save()
                try:
                    lead.full_clean()
                except ValidationError as e:
                    return Response({
                        "message": "Invalid data",
                        "errors": e.message_dict
                    }, status=status.HTTP_400_BAD_REQUEST)
                lead.save()
                return Response({
                    "message": "Lead updated successfully",
                    "data": serializer.data
                })
            return Response({
                "message": "Invalid data",
                "errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        except Lead.DoesNotExist:
            return Response({
                "message": "Lead not found"
            }, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request):
        lead_id = request.query_params.get('lead_id')
        try:
            lead = Lead.objects.get(id=lead_id, created_by=request.user)
            lead.delete()
            return Response({
                "message": "Lead deleted successfully"
            }, status=status.HTTP_204_NO_CONTENT)
        except Lead.DoesNotExist:
            return Response({
                "message": "Lead not found"
            }, status=status.HTTP_404_NOT_FOUND)

class ContactGenericAPIView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ContactSerializer

    def get(self, request):
        user = request.user
        lead_id = request.query_params.get("lead_id")
        page = request.query_params.get('page', 1)
        rows = request.query_params.get('rows', 25)

        query = Q(created_by=user)
        if lead_id:
            query &= Q(lead_id=lead_id)

        contacts = Contact.objects.filter(query).select_related('lead', 'created_by')

        paginator = Paginator(contacts, rows)
        try:
            current_page = paginator.page(page)
        except:
            return Response({
                "message": "Invalid page number"
            }, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "message": "Contacts fetched successfully",
            "contacts": ContactSerializer(current_page.object_list, many=True).data,
            "pagination": {
                "currentPage": current_page.number,
                "total": paginator.count,
                "pageSize": rows
            },
            "last_page": paginator.num_pages,
        })

    def post(self, request):
        user = request.user
        form_data = request.data

        # Required field validation
        name = form_data.get('name')
        lead_id = form_data.get('lead_id')
        if not name:
            return Response({
                "message": "Name is required"
            }, status=status.HTTP_400_BAD_REQUEST)
        if not lead_id:
            return Response({
                "message": "Lead ID is required"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Validate lead existence
        try:
            lead = Lead.objects.get(id=lead_id)
        except Lead.DoesNotExist:
            return Response({
                "message": "Lead not found"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Check for existing contact with same email
        email = form_data.get('email')
        if email:
            existing_contact = Contact.objects.filter(
                Q(created_by=user) & Q(email__iexact=email)
            ).first()
            if existing_contact:
                return Response({
                    "message": "A contact with this email already exists"
                }, status=status.HTTP_400_BAD_REQUEST)

        # Use get_or_create to prevent duplicates
        contact, created = Contact.objects.get_or_create(
            created_by=user,
            lead=lead,
            name=name,
            email=email,
            defaults={
                'phone': form_data.get('phone', ''),
            }
        )

        if not created:
            return Response({
                "message": "Similar contact exists"
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            contact.full_clean()
        except ValidationError as e:
            contact.delete()
            return Response({
                "message": "Invalid data",
                "errors": e.message_dict
            }, status=status.HTTP_400_BAD_REQUEST)

        contact.save()

        # Notification
        notification_title = "Contact Created"
        notification_message = f"Contact {contact.name} created successfully!"
        emails = [user.email]

        send_notification.delay(
            emails=emails,
            title=notification_title,
            body=notification_message,
        )

        return Response({
            "message": "Contact created successfully!",
            "data": ContactSerializer(contact).data
        }, status=status.HTTP_201_CREATED)

    def put(self, request):
        contact_id = request.data.get('id')
        try:
            contact = Contact.objects.get(id=contact_id, created_by=request.user)
            data = request.data.copy()
            lead_id = data.get('lead_id')
            if lead_id and not Lead.objects.filter(id=lead_id).exists():
                return Response({
                    "message": "Valid lead_id is required"
                }, status=status.HTTP_400_BAD_REQUEST)
            serializer = self.get_serializer(contact, data=data, partial=True)
            if serializer.is_valid():
                contact = serializer.save()
                try:
                    contact.full_clean()
                except ValidationError as e:
                    return Response({
                        "message": "Invalid data",
                        "errors": e.message_dict
                    }, status=status.HTTP_400_BAD_REQUEST)
                contact.save()
                return Response({
                    "message": "Contact updated successfully",
                    "data": serializer.data
                })
            return Response({
                "message": "Invalid data",
                "errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        except Contact.DoesNotExist:
            return Response({
                "message": "Contact not found"
            }, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request):
        contact_id = request.query_params.get('contact_id')
        try:
            contact = Contact.objects.get(id=contact_id, created_by=request.user)
            contact.delete()
            return Response({
                "message": "Contact deleted successfully"
            }, status=status.HTTP_204_NO_CONTENT)
        except Contact.DoesNotExist:
            return Response({
                "message": "Contact not found"
            }, status=status.HTTP_404_NOT_FOUND)

class NoteGenericAPIView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = NoteSerializer

    def get(self, request):
        user = request.user
        lead_id = request.query_params.get("lead_id")
        page = request.query_params.get('page', 1)
        rows = request.query_params.get('rows', 25)

        query = Q(created_by=user)
        if lead_id:
            query &= Q(lead_id=lead_id)

        notes = Note.objects.filter(query).select_related('lead', 'created_by')

        paginator = Paginator(notes, rows)
        try:
            current_page = paginator.page(page)
        except:
            return Response({
                "message": "Invalid page number"
            }, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "message": "Notes fetched successfully",
            "notes": NoteSerializer(current_page.object_list, many=True).data,
            "pagination": {
                "currentPage": current_page.number,
                "total": paginator.count,
                "pageSize": rows
            },
            "last_page": paginator.num_pages,
        })

    def post(self, request):
        user = request.user
        form_data = request.data

        # Required field validation
        content = form_data.get('content')
        lead_id = form_data.get('lead_id')
        if not content:
            return Response({
                "message": "Content is required"
            }, status=status.HTTP_400_BAD_REQUEST)
        if not lead_id:
            return Response({
                "message": "Lead ID is required"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Validate lead existence
        try:
            lead = Lead.objects.get(id=lead_id)
        except Lead.DoesNotExist:
            return Response({
                "message": "Lead not found"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Notes are unique per content and lead
        note, created = Note.objects.get_or_create(
            created_by=user,
            lead=lead,
            content=content,
        )

        if not created:
            return Response({
                "message": "Similar note exists"
            }, status=status.HTTP_400_BAD_REQUEST)

        note.save()

        # Notification
        notification_title = "Note Created"
        notification_message = f"Note for {lead.name} created successfully!"
        emails = [user.email]

        send_notification.delay(
            emails=emails,
            title=notification_title,
            body=notification_message,
        )

        return Response({
            "message": "Note created successfully!",
            "data": NoteSerializer(note).data
        }, status=status.HTTP_201_CREATED)

    def put(self, request):
        note_id = request.data.get('id')
        try:
            note = Note.objects.get(id=note_id, created_by=request.user)
            data = request.data.copy()
            lead_id = data.get('lead_id')
            if lead_id and not Lead.objects.filter(id=lead_id).exists():
                return Response({
                    "message": "Valid lead_id is required"
                }, status=status.HTTP_400_BAD_REQUEST)
            serializer = self.get_serializer(note, data=data, partial=True)
            if serializer.is_valid():
                note = serializer.save()
                note.save()
                return Response({
                    "message": "Note updated successfully",
                    "data": serializer.data
                })
            return Response({
                "message": "Invalid data",
                "errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        except Note.DoesNotExist:
            return Response({
                "message": "Note not found"
            }, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request):
        note_id = request.query_params.get('note_id')
        try:
            note = Note.objects.get(id=note_id, created_by=request.user)
            note.delete()
            return Response({
                "message": "Note deleted successfully"
            }, status=status.HTTP_204_NO_CONTENT)
        except Note.DoesNotExist:
            return Response({
                "message": "Note not found"
            }, status=status.HTTP_404_NOT_FOUND)

class ReminderGenericAPIView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ReminderSerializer

    def get(self, request):
        user = request.user
        lead_id = request.query_params.get("lead_id")
        status_filter = request.query_params.get("status")
        page = request.query_params.get('page', 1)
        rows = request.query_params.get('rows', 25)

        query = Q(created_by=user)
        if lead_id:
            query &= Q(lead_id=lead_id)
        if status_filter:
            query &= Q(status=status_filter)

        reminders = Reminder.objects.filter(query).select_related('lead', 'created_by')

        paginator = Paginator(reminders, rows)
        try:
            current_page = paginator.page(page)
        except:
            return Response({
                "message": "Invalid page number"
            }, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "message": "Reminders fetched successfully",
            "reminders": ReminderSerializer(current_page.object_list, many=True).data,
            "pagination": {
                "currentPage": current_page.number,
                "total": paginator.count,
                "pageSize": rows
            },
            "last_page": paginator.num_pages,
        })

    def post(self, request):
        user = request.user
        form_data = request.data

        # Required field validation
        message = form_data.get('message')
        lead_id = form_data.get('lead_id')
        remind_at = form_data.get('remind_at')
        status = form_data.get('status', 'PENDING')
        if not message:
            return Response({
                "message": "Message is required"
            }, status=status.HTTP_400_BAD_REQUEST)
        if not lead_id:
            return Response({
                "message": "Lead ID is required"
            }, status=status.HTTP_400_BAD_REQUEST)
        if not remind_at:
            return Response({
                "message": "Remind at is required"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Validate lead existence
        try:
            lead = Lead.objects.get(id=lead_id)
        except Lead.DoesNotExist:
            return Response({
                "message": "Lead not found"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Validate remind_at
        try:
            remind_at_dt = datetime.fromisoformat(remind_at.replace('Z', '+00:00'))
            if remind_at_dt <= timezone.now():
                return Response({
                    "message": "Reminder time must be in the future"
                }, status=status.HTTP_400_BAD_REQUEST)
        except ValueError:
            return Response({
                "message": "Invalid remind_at format"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Use get_or_create to prevent duplicates
        reminder, created = Reminder.objects.get_or_create(
            created_by=user,
            lead=lead,
            message=message,
            remind_at=remind_at,
            defaults={
                'status': status,
            }
        )

        if not created:
            return Response({
                "message": "Similar reminder exists"
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            reminder.full_clean()
        except ValidationError as e:
            reminder.delete()
            return Response({
                "message": "Invalid data",
                "errors": e.message_dict
            }, status=status.HTTP_400_BAD_REQUEST)

        reminder.save()

        # Schedule reminder email
        send_reminder_email.apply_async((reminder.id,), eta=remind_at_dt)

        # Notification
        notification_title = "Reminder Created"
        notification_message = f"Reminder for {lead.name} created successfully!"
        emails = [user.email]

        send_notification.delay(
            emails=emails,
            title=notification_title,
            body=notification_message,
        )

        return Response({
            "message": "Reminder created successfully!",
            "data": ReminderSerializer(reminder).data
        }, status=status.HTTP_201_CREATED)

    def put(self, request):
        reminder_id = request.data.get('id')
        try:
            reminder = Reminder.objects.get(id=reminder_id, created_by=request.user)
            data = request.data.copy()
            lead_id = data.get('lead_id')
            if lead_id and not Lead.objects.filter(id=lead_id).exists():
                return Response({
                    "message": "Valid lead_id is required"
                }, status=status.HTTP_400_BAD_REQUEST)
            serializer = self.get_serializer(reminder, data=data, partial=True)
            if serializer.is_valid():
                reminder = serializer.save()
                try:
                    reminder.full_clean()
                except ValidationError as e:
                    return Response({
                        "message": "Invalid data",
                        "errors": e.message_dict
                    }, status=status.HTTP_400_BAD_REQUEST)
                reminder.save()
                if 'remind_at' in request.data:
                    try:
                        remind_at_dt = datetime.fromisoformat(request.data['remind_at'].replace('Z', '+00:00'))
                        send_reminder_email.apply_async((reminder.id,), eta=remind_at_dt)
                    except ValueError:
                        pass  # Skip rescheduling if remind_at is invalid
                return Response({
                    "message": "Reminder updated successfully",
                    "data": serializer.data
                })
            return Response({
                "message": "Invalid data",
                "errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        except Reminder.DoesNotExist:
            return Response({
                "message": "Reminder not found"
            }, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request):
        reminder_id = request.query_params.get('reminder_id')
        try:
            reminder = Reminder.objects.get(id=reminder_id, created_by=request.user)
            reminder.delete()
            return Response({
                "message": "Reminder deleted successfully"
            }, status=status.HTTP_204_NO_CONTENT)
        except Reminder.DoesNotExist:
            return Response({
                "message": "Reminder not found"
            }, status=status.HTTP_404_NOT_FOUND)