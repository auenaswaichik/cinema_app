from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

class User(AbstractUser):
    """
    Custom user model extending Django's AbstractUser.
    Adds additional fields for user profile information.
    """
    phone = models.CharField(max_length=15, blank=True, null=True)
    birth_date = models.DateField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')

    def __str__(self):
        return self.username

class Genre(models.Model):
    """
    Model representing movie genres.
    Used to categorize movies.
    """
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Genre')
        verbose_name_plural = _('Genres')

    def __str__(self):
        return self.name

class Movie(models.Model):
    """
    Model representing movies in the cinema.
    Contains all information about a movie including title, description, ratings, etc.
    """
    title = models.CharField(max_length=200)
    country = models.CharField(max_length=100)
    genres = models.ManyToManyField(Genre, related_name='movies')
    duration = models.IntegerField(help_text='Duration in minutes')
    budget = models.DecimalField(max_digits=12, decimal_places=2)
    poster = models.ImageField(upload_to='movie_posters/')
    description = models.TextField()
    rating = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        validators=[MinValueValidator(0), MaxValueValidator(10)]
    )
    release_date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Movie')
        verbose_name_plural = _('Movies')

    def __str__(self):
        return self.title

class Hall(models.Model):
    """
    Model representing cinema halls.
    Contains information about hall capacity and features.
    """
    name = models.CharField(max_length=100)
    capacity = models.IntegerField()
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Hall')
        verbose_name_plural = _('Halls')

    def __str__(self):
        return self.name

class Session(models.Model):
    """
    Model representing movie sessions.
    Links movies with halls and contains session-specific information.
    """
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='sessions')
    hall = models.ForeignKey(Hall, on_delete=models.CASCADE, related_name='sessions')
    start_time = models.DateTimeField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Session')
        verbose_name_plural = _('Sessions')

    def __str__(self):
        return f"{self.movie.title} - {self.start_time}"

    @property
    def available_seats(self):
        """
        Calculates the number of available seats for the session.
        Takes into account both sold tickets and active bookings.
        """
        sold_tickets = self.tickets.count()
        active_bookings = self.bookings.filter(is_active=True, expiry_date__gt=timezone.now()).count()
        return self.hall.capacity - sold_tickets - active_bookings

class Ticket(models.Model):
    """
    Model representing purchased tickets.
    Links users with sessions and contains ticket-specific information.
    """
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='tickets')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tickets')
    seat_number = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    purchase_date = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Ticket')
        verbose_name_plural = _('Tickets')

    def __str__(self):
        return f"Ticket for {self.session.movie.title} - Seat {self.seat_number}"

class Booking(models.Model):
    """
    Model representing temporary seat bookings.
    Used for holding seats before purchase.
    """
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='bookings')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings')
    seat_number = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    booking_date = models.DateTimeField(auto_now_add=True)
    expiry_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Booking')
        verbose_name_plural = _('Bookings')

    def __str__(self):
        return f"Booking for {self.session.movie.title} - Seat {self.seat_number}"

    def set_expiry_date(self):
        """
        Sets the booking expiry date to 15 minutes from creation.
        """
        self.expiry_date = timezone.now() + timezone.timedelta(minutes=15)
        self.save()

    @property
    def is_expired(self):
        """
        Checks if the booking has expired.
        """
        return timezone.now() > self.expiry_date

class Review(models.Model):
    """
    Model representing user reviews for movies.
    Contains rating and text review.
    """
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(10)])
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Review')
        verbose_name_plural = _('Reviews')

    def __str__(self):
        return f"Review by {self.user.username} for {self.movie.title}"

class News(models.Model):
    """
    Model representing news articles.
    Used for displaying news on the website.
    """
    title = models.CharField(max_length=200)
    content = models.TextField()
    image = models.ImageField(upload_to='news_images/', blank=True, null=True)
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('News')
        verbose_name_plural = _('News')

    def __str__(self):
        return self.title

class FAQ(models.Model):
    """
    Model representing frequently asked questions.
    Used for the FAQ section of the website.
    """
    question = models.CharField(max_length=200)
    answer = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('FAQ')
        verbose_name_plural = _('FAQs')

    def __str__(self):
        return self.question

class CompanyInfo(models.Model):
    """
    Model representing company information.
    Used for displaying company details on the website.
    """
    title = models.CharField(max_length=200)
    content = models.TextField()
    image = models.ImageField(upload_to='company_images/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Company Info')
        verbose_name_plural = _('Company Info')

    def __str__(self):
        return self.title

class Vacancy(models.Model):
    """
    Model representing job vacancies.
    Used for displaying available positions.
    """
    title = models.CharField(max_length=200)
    description = models.TextField()
    requirements = models.TextField()
    salary = models.CharField(max_length=100, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Vacancy')
        verbose_name_plural = _('Vacancies')

    def __str__(self):
        return self.title

class PromoCode(models.Model):
    """
    Model representing promotional codes.
    Used for discounts and special offers.
    """
    code = models.CharField(max_length=50, unique=True)
    discount_percent = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(100)])
    is_active = models.BooleanField(default=True)
    expiry_date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Promo Code')
        verbose_name_plural = _('Promo Codes')

    def __str__(self):
        return self.code

    @property
    def is_expired(self):
        """
        Checks if the promo code has expired.
        """
        return timezone.now() > self.expiry_date
