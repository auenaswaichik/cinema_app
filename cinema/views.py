from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.db.models import Avg, Count, Sum, Q
from django.utils import timezone
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import logout
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.db.models.functions import TruncDate, TruncMonth
from django.http import JsonResponse
from .models import (
    Movie, Session, Ticket, Review, News, FAQ,
    CompanyInfo, Vacancy, PromoCode, User, Booking
)
from .forms import CustomUserCreationForm
from datetime import timedelta

def home(request):
    """
    Home page view that displays latest news and upcoming movies.
    Returns a context with the latest news and upcoming movies for the next 5 days.
    """
    # Get the latest published news
    latest_news = News.objects.filter(is_published=True).order_by('-created_at')[:1]
    # Get upcoming movies for the next 5 days
    upcoming_movies = Movie.objects.filter(release_date__gte=timezone.now()).order_by('release_date')[:5]
    
    context = {
        'latest_news': latest_news,
        'upcoming_movies': upcoming_movies,
    }
    return render(request, 'cinema/home.html', context)

class MovieListView(ListView):
    """
    View for displaying a list of all movies with optional genre filtering.
    Supports pagination and genre filtering through URL parameters.
    """
    model = Movie
    template_name = 'cinema/movie_list.html'
    context_object_name = 'movies'
    paginate_by = 12  # Number of movies per page

    def get_queryset(self):
        """
        Returns a filtered queryset of movies based on genre parameter.
        If no genre is specified, returns all movies ordered by release date.
        """
        queryset = Movie.objects.all()
        genre = self.request.GET.get('genre')
        if genre:
            queryset = queryset.filter(genres__name=genre)
        return queryset.order_by('-release_date')

class MovieDetailView(DetailView):
    """
    View for displaying detailed information about a specific movie.
    Includes movie details, active sessions, and reviews.
    """
    model = Movie
    template_name = 'cinema/movie_detail.html'
    context_object_name = 'movie'

    def get_context_data(self, **kwargs):
        """
        Adds additional context data including active sessions and reviews.
        """
        context = super().get_context_data(**kwargs)
        # Get active sessions for the movie
        context['sessions'] = Session.objects.filter(
            movie=self.object,
            start_time__gte=timezone.now(),
            is_active=True
        ).order_by('start_time')
        # Get all reviews for the movie
        context['reviews'] = Review.objects.filter(movie=self.object).order_by('-created_at')
        return context

class SessionListView(ListView):
    """
    View for displaying a list of all active movie sessions.
    Shows only future sessions that are marked as active.
    """
    model = Session
    template_name = 'cinema/session_list.html'
    context_object_name = 'sessions'
    paginate_by = 20  # Number of sessions per page

    def get_queryset(self):
        """
        Returns a queryset of active future sessions.
        """
        return Session.objects.filter(
            start_time__gte=timezone.now(),
            is_active=True
        ).order_by('start_time')

class TicketListView(LoginRequiredMixin, ListView):
    """
    View for displaying a user's purchased tickets.
    Requires user authentication.
    """
    model = Ticket
    template_name = 'cinema/ticket_list.html'
    context_object_name = 'tickets'

    def get_queryset(self):
        """
        Returns a queryset of tickets for the current user.
        """
        return Ticket.objects.filter(user=self.request.user).order_by('-purchase_date')

@login_required
def buy_ticket(request, session_id):
    """
    View for purchasing or booking tickets for a specific session.
    Handles both direct purchases and temporary bookings.
    
    Args:
        request: HTTP request object
        session_id: ID of the session to buy/book tickets for
    """
    # Get the session or return 404
    session = get_object_or_404(Session, id=session_id)
    
    # Check if the session hasn't started yet
    if session.start_time <= timezone.now():
        messages.error(request, 'This session has already started or ended.')
        return redirect('cinema:movie_detail', pk=session.movie.id)
    
    # Get list of taken seats (both tickets and active bookings)
    taken_seats = set(Ticket.objects.filter(session=session).values_list('seat_number', flat=True))
    active_bookings = Booking.objects.filter(
        session=session,
        is_active=True,
        expiry_date__gt=timezone.now()
    )
    booked_seats = set(active_bookings.values_list('seat_number', flat=True))
    taken_seats.update(booked_seats)
    
    # Create list of available seats
    available_seats = [seat for seat in range(1, session.total_seats + 1) if seat not in taken_seats]
    
    if request.method == 'POST':
        action = request.POST.get('action')
        seat_number = request.POST.get('seat_number')
        
        if seat_number:
            try:
                seat_number = int(seat_number)
                if seat_number in taken_seats:
                    messages.error(request, 'This seat is already taken.')
                elif seat_number < 1 or seat_number > session.total_seats:
                    messages.error(request, 'Invalid seat number.')
                else:
                    if action == 'book':
                        # Create a booking with 15-minute expiry
                        booking = Booking.objects.create(
                            session=session,
                            user=request.user,
                            seat_number=seat_number,
                            price=session.price,
                            expiry_date=timezone.now() + timezone.timedelta(minutes=15)
                        )
                        messages.success(request, 'Seat successfully booked for 15 minutes!')
                        return redirect('cinema:booking_list')
                    elif action == 'buy':
                        # Create a ticket
                        ticket = Ticket.objects.create(
                            session=session,
                            user=request.user,
                            seat_number=seat_number,
                            price=session.price
                        )
                        messages.success(request, 'Ticket successfully purchased!')
                        return redirect('cinema:ticket_list')
            except ValueError:
                messages.error(request, 'Invalid seat number format.')
    
    context = {
        'session': session,
        'available_seats': available_seats,
    }
    return render(request, 'cinema/buy_ticket.html', context)

@login_required
def booking_list(request):
    """
    View for displaying user's active and expired bookings.
    Automatically deactivates expired bookings.
    """
    # Get active bookings
    active_bookings = Booking.objects.filter(
        user=request.user,
        is_active=True,
        expiry_date__gt=timezone.now()
    ).order_by('expiry_date')
    
    # Get and deactivate expired bookings
    expired_bookings = Booking.objects.filter(
        user=request.user,
        is_active=True,
        expiry_date__lte=timezone.now()
    )
    expired_bookings.update(is_active=False)
    
    context = {
        'active_bookings': active_bookings,
    }
    return render(request, 'cinema/booking_list.html', context)

@login_required
def cancel_booking(request, booking_id):
    """
    View for canceling a specific booking.
    Only allows cancellation of active bookings that haven't expired.
    """
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    if booking.is_active and booking.expiry_date > timezone.now():
        booking.is_active = False
        booking.save()
        messages.success(request, 'Booking successfully canceled.')
    else:
        messages.error(request, 'Cannot cancel this booking.')
    return redirect('cinema:booking_list')

class NewsListView(ListView):
    model = News
    template_name = 'cinema/news_list.html'
    context_object_name = 'news'
    paginate_by = 10

    def get_queryset(self):
        return News.objects.filter(is_published=True).order_by('-created_at')

class NewsDetailView(DetailView):
    model = News
    template_name = 'cinema/news_detail.html'
    context_object_name = 'news'

class FAQListView(ListView):
    model = FAQ
    template_name = 'cinema/faq_list.html'
    context_object_name = 'faqs'

class CompanyInfoView(DetailView):
    model = CompanyInfo
    template_name = 'cinema/company_info.html'
    context_object_name = 'company_info'

    def get_object(self):
        return CompanyInfo.objects.first()

class VacancyListView(ListView):
    model = Vacancy
    template_name = 'cinema/vacancy_list.html'
    context_object_name = 'vacancies'

    def get_queryset(self):
        return Vacancy.objects.filter(is_active=True).order_by('-created_at')

class ReviewCreateView(LoginRequiredMixin, CreateView):
    """
    View for creating movie reviews.
    Prevents staff users from creating reviews.
    """
    model = Review
    template_name = 'cinema/review_form.html'
    fields = ['rating', 'text']

    def form_valid(self, form):
        """
        Validates the form and prevents staff users from creating reviews.
        """
        if self.request.user.is_staff:
            messages.error(self.request, 'Staff members cannot create reviews.')
            return redirect('cinema:movie_detail', pk=self.kwargs['movie_id'])
        form.instance.user = self.request.user
        form.instance.movie_id = self.kwargs['movie_id']
        return super().form_valid(form)

    def get_success_url(self):
        """
        Returns the URL to redirect to after successful review creation.
        """
        return reverse_lazy('cinema:movie_detail', kwargs={'pk': self.kwargs['movie_id']})

def promo_codes(request):
    active_promos = PromoCode.objects.filter(
        is_active=True,
        start_date__lte=timezone.now(),
        end_date__gte=timezone.now()
    )
    expired_promos = PromoCode.objects.filter(
        end_date__lt=timezone.now()
    )
    context = {
        'active_promos': active_promos,
        'expired_promos': expired_promos,
    }
    return render(request, 'cinema/promo_codes.html', context)

def contacts(request):
    # Здесь можно добавить выборку сотрудников
    return render(request, 'cinema/contacts.html')

def privacy_policy(request):
    return render(request, 'cinema/privacy_policy.html')

class ReviewListView(ListView):
    model = Review
    template_name = 'cinema/review_list.html'
    context_object_name = 'reviews'
    paginate_by = 10

    def get_queryset(self):
        return Review.objects.order_by('-created_at')

class RegisterView(CreateView):
    form_class = CustomUserCreationForm
    template_name = 'registration/register.html'
    success_url = reverse_lazy('login')

@require_http_methods(["GET", "POST"])
def custom_logout(request):
    if request.method == "POST":
        logout(request)
        return render(request, 'registration/logged_out.html')
    return render(request, 'registration/logout_confirm.html')

def is_admin(user):
    return user.is_staff

@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    """
    Admin dashboard view showing overall statistics and metrics.
    Only accessible to staff users.
    """
    # Overall statistics
    total_users = User.objects.count()
    total_movies = Movie.objects.count()
    total_tickets = Ticket.objects.count()
    total_revenue = Ticket.objects.aggregate(total=Sum('price'))['total'] or 0

    # Movie statistics
    top_movies = Movie.objects.annotate(
        ticket_count=Count('sessions__tickets'),
        revenue=Sum('sessions__tickets__price')
    ).order_by('-ticket_count')[:5]

    # Session statistics
    upcoming_sessions = Session.objects.filter(
        start_time__gte=timezone.now()
    ).order_by('start_time')[:5]

    # Sales statistics for the last 7 days
    daily_sales = Ticket.objects.filter(
        purchase_date__gte=timezone.now() - timezone.timedelta(days=7)
    ).annotate(
        date=TruncDate('purchase_date')
    ).values('date').annotate(
        total=Count('id'),
        revenue=Sum('price')
    ).order_by('date')

    # User activity statistics
    active_users = User.objects.annotate(
        ticket_count=Count('tickets')
    ).filter(ticket_count__gt=0).order_by('-ticket_count')[:5]

    # Hall statistics
    hall_stats = Session.objects.values('hall__name').annotate(
        session_count=Count('id'),
        ticket_count=Count('tickets'),
        revenue=Sum('tickets__price')
    ).order_by('-revenue')

    context = {
        'total_users': total_users,
        'total_movies': total_movies,
        'total_tickets': total_tickets,
        'total_revenue': total_revenue,
        'top_movies': top_movies,
        'upcoming_sessions': upcoming_sessions,
        'daily_sales': daily_sales,
        'active_users': active_users,
        'hall_stats': hall_stats,
    }
    return render(request, 'cinema/admin_dashboard.html', context)

@login_required
@user_passes_test(lambda u: u.is_staff)
def user_statistics(request):
    # Получаем параметры фильтрации
    start_date = request.GET.get('start_date', (timezone.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    end_date = request.GET.get('end_date', timezone.now().strftime('%Y-%m-%d'))
    sort_by = request.GET.get('sort_by', 'tickets')

    # Преобразуем строки в объекты datetime
    start_date = timezone.datetime.strptime(start_date, '%Y-%m-%d')
    end_date = timezone.datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)

    # Получаем всех пользователей с их статистикой
    users = User.objects.annotate(
        ticket_count=Count('ticket', filter=Q(ticket__purchase_date__range=[start_date, end_date])),
        total_spent=Sum('ticket__price', filter=Q(ticket__purchase_date__range=[start_date, end_date])),
        booking_count=Count('booking', filter=Q(booking__booking_date__range=[start_date, end_date])),
        review_count=Count('review', filter=Q(review__created_at__range=[start_date, end_date]))
    )

    # Сортируем пользователей
    if sort_by == 'tickets':
        users = users.order_by('-ticket_count')
    elif sort_by == 'spent':
        users = users.order_by('-total_spent')
    elif sort_by == 'bookings':
        users = users.order_by('-booking_count')
    elif sort_by == 'reviews':
        users = users.order_by('-review_count')

    # Рассчитываем общую статистику
    active_users_count = users.filter(last_login__range=[start_date, end_date]).count()
    new_users_count = users.filter(date_joined__range=[start_date, end_date]).count()
    
    # Рассчитываем среднюю активность
    total_actions = sum(user.ticket_count + user.booking_count + user.review_count for user in users)
    avg_activity = round(total_actions / users.count() if users.count() > 0 else 0, 1)
    
    # Рассчитываем конверсию (процент пользователей, совершивших хотя бы одно действие)
    active_users = users.filter(Q(ticket_count__gt=0) | Q(booking_count__gt=0) | Q(review_count__gt=0)).count()
    conversion_rate = round((active_users / users.count() * 100) if users.count() > 0 else 0, 1)

    # Добавляем процент активности для каждого пользователя
    max_actions = max((user.ticket_count + user.booking_count + user.review_count for user in users), default=1)
    for user in users:
        user_actions = user.ticket_count + user.booking_count + user.review_count
        user.activity_percentage = round((user_actions / max_actions * 100) if max_actions > 0 else 0, 1)

    context = {
        'users': users,
        'start_date': start_date,
        'end_date': end_date,
        'sort_by': sort_by,
        'active_users_count': active_users_count,
        'new_users_count': new_users_count,
        'avg_activity': avg_activity,
        'conversion_rate': conversion_rate,
    }

    return render(request, 'cinema/user_statistics.html', context)

@login_required
@user_passes_test(lambda u: u.is_staff)
def admin_statistics(request):
    """
    Detailed admin statistics view with filtering options.
    Only accessible to staff users.
    """
    # Get filter parameters
    start_date = request.GET.get('start_date', (timezone.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    end_date = request.GET.get('end_date', timezone.now().strftime('%Y-%m-%d'))
    stat_type = request.GET.get('stat_type', 'tickets')

    # Convert strings to datetime objects
    start_date = timezone.datetime.strptime(start_date, '%Y-%m-%d')
    end_date = timezone.datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)

    # Overall statistics
    total_tickets = Ticket.objects.filter(purchase_date__range=[start_date, end_date]).count()
    active_bookings = Booking.objects.filter(
        booking_date__range=[start_date, end_date],
        is_active=True,
        expiry_date__gt=timezone.now()
    ).count()
    total_revenue = Ticket.objects.filter(
        purchase_date__range=[start_date, end_date]
    ).aggregate(total=Sum('price'))['total'] or 0

    # Movie statistics
    movie_stats = Movie.objects.annotate(
        tickets_sold=Count('sessions__tickets', filter=Q(sessions__tickets__purchase_date__range=[start_date, end_date])),
        active_bookings=Count('sessions__bookings', filter=Q(
            sessions__bookings__booking_date__range=[start_date, end_date],
            sessions__bookings__is_active=True,
            sessions__bookings__expiry_date__gt=timezone.now()
        )),
        revenue=Sum('sessions__tickets__price', filter=Q(sessions__tickets__purchase_date__range=[start_date, end_date])),
        avg_rating=Avg('review__rating')
    ).order_by('-tickets_sold')

    # Session statistics
    session_stats = Session.objects.filter(
        start_time__range=[start_date, end_date]
    ).annotate(
        tickets_sold=Count('tickets'),
        active_bookings=Count('bookings', filter=Q(
            bookings__is_active=True,
            bookings__expiry_date__gt=timezone.now()
        ))
    ).select_related('movie', 'hall')

    # Calculate available seats and occupancy rate for each session
    for session in session_stats:
        occupied_seats = session.tickets_sold + session.active_bookings
        session.remaining_seats = session.total_seats - occupied_seats
        session.occupancy_rate = round((occupied_seats / session.total_seats * 100) if session.total_seats > 0 else 0)

    # User activity statistics
    user_activity = User.objects.annotate(
        tickets_bought=Count('tickets', filter=Q(tickets__purchase_date__range=[start_date, end_date])),
        active_bookings=Count('bookings', filter=Q(
            bookings__booking_date__range=[start_date, end_date],
            bookings__is_active=True,
            bookings__expiry_date__gt=timezone.now()
        )),
        total_spent=Sum('tickets__price', filter=Q(tickets__purchase_date__range=[start_date, end_date])),
        reviews_count=Count('review', filter=Q(review__created_at__range=[start_date, end_date]))
    ).filter(
        Q(tickets_bought__gt=0) | Q(active_bookings__gt=0) | Q(reviews_count__gt=0)
    ).order_by('-tickets_bought')

    # Calculate conversion rate
    total_users = User.objects.filter(date_joined__range=[start_date, end_date]).count()
    active_users = user_activity.count()
    conversion_rate = round((active_users / total_users * 100) if total_users > 0 else 0, 1)

    context = {
        'start_date': start_date,
        'end_date': end_date,
        'stat_type': stat_type,
        'total_tickets': total_tickets,
        'active_bookings': active_bookings,
        'total_revenue': total_revenue,
        'conversion_rate': conversion_rate,
        'movie_stats': movie_stats,
        'session_stats': session_stats,
        'user_activity': user_activity,
    }

    return render(request, 'cinema/admin_statistics.html', context)
