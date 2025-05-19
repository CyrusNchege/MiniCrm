from django.urls import path
from .views import DashboardAPIView, LeadAPIView, ContactAPIView, NoteAPIView, RegisterView, ReminderAPIView

from knox import views as knox_views
from .views import LoginView
from django.views.decorators.csrf import csrf_exempt

urlpatterns = [
    # Auth
    path('login/', csrf_exempt(LoginView.as_view()), name='knox_login'),
    path('logout/', knox_views.LogoutView.as_view(), name='knox_logout'),
    path('logoutall/', knox_views.LogoutAllView.as_view(), name='knox_logoutall'),
    path('register/', csrf_exempt(RegisterView.as_view()), name='knox_register'),

    # Dashboard
    path('dashboard/', DashboardAPIView.as_view(), name='dashboard'),

    # API
    path('leads/', LeadAPIView.as_view()),
    path('leads/<int:pk>/', LeadAPIView.as_view()),
    path('contacts/', ContactAPIView.as_view()),
    path('contacts/<int:pk>/', ContactAPIView.as_view()),
    path('notes/', NoteAPIView.as_view()),
    path('notes/<int:pk>/', NoteAPIView.as_view()),
    path('reminders/', ReminderAPIView.as_view()),
    path('reminders/<int:pk>/', ReminderAPIView.as_view()),
]