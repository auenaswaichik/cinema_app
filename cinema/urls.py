from django.urls import path
from . import views

app_name = 'cinema'

urlpatterns = [
    # Home page
    path('', views.home, name='home'),

    # Movie-related URLs
    path('movies/', views.MovieListView.as_view(), name='movie_list'),
    path('movies/<int:pk>/', views.MovieDetailView.as_view(), name='movie_detail'),

    # Session-related URLs
    path('sessions/', views.SessionListView.as_view(), name='session_list'),
    path('sessions/<int:session_id>/buy/', views.buy_ticket, name='buy_ticket'),

    # Ticket-related URLs
    path('tickets/', views.TicketListView.as_view(), name='ticket_list'),

    # Booking-related URLs
    path('bookings/', views.booking_list, name='booking_list'),
    path('bookings/<int:booking_id>/cancel/', views.cancel_booking, name='cancel_booking'),

    # Review-related URLs
    path('movies/<int:movie_id>/review/', views.ReviewCreateView.as_view(), name='create_review'),

    # News-related URLs
    path('news/', views.NewsListView.as_view(), name='news_list'),
    path('news/<int:pk>/', views.NewsDetailView.as_view(), name='news_detail'),

    # FAQ-related URLs
    path('faq/', views.FAQListView.as_view(), name='faq_list'),

    # Company information URLs
    path('about/', views.CompanyInfoView.as_view(), name='company_info'),
    path('vacancies/', views.VacancyListView.as_view(), name='vacancy_list'),
    path('vacancies/<int:pk>/', views.VacancyDetailView.as_view(), name='vacancy_detail'),

    # Contact-related URLs
    path('contacts/', views.ContactView.as_view(), name='contacts'),
    path('privacy-policy/', views.PrivacyPolicyView.as_view(), name='privacy_policy'),

    # Authentication URLs
    path('register/', views.RegisterView.as_view(), name='register'),
    path('logout/', views.logout_view, name='logout'),

    # Admin dashboard URLs
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('dashboard/statistics/', views.admin_statistics, name='admin_statistics'),
] 