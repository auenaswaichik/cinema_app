from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from .models import Review, PromoCode
import re

User = get_user_model()

class CustomUserCreationForm(UserCreationForm):
    """
    Custom user registration form extending Django's UserCreationForm.
    Adds additional fields for user profile information.
    """
    email = forms.EmailField(required=True)
    phone = forms.CharField(max_length=15, required=False)
    birth_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    address = forms.CharField(widget=forms.Textarea, required=False)

    class Meta:
        model = User
        fields = ('username', 'email', 'phone', 'birth_date', 'address', 'password1', 'password2')

    def clean_email(self):
        """
        Validates that the email is unique.
        """
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('This email is already registered.')
        return email

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        # Регулярное выражение для белорусского номера телефона
        pattern = r'^\+375(25|29|33|44)\d{7}$'
        
        if not re.match(pattern, phone):
            raise forms.ValidationError(
                'Пожалуйста, введите корректный номер телефона в формате +375XXXXXXXXX'
            )
        return phone

class ReviewForm(forms.ModelForm):
    """
    Form for creating and editing movie reviews.
    Includes rating and text review fields.
    """
    class Meta:
        model = Review
        fields = ['rating', 'text']
        widgets = {
            'rating': forms.NumberInput(attrs={'min': 1, 'max': 10}),
            'text': forms.Textarea(attrs={'rows': 4}),
        }

    def clean_rating(self):
        """
        Validates that the rating is between 1 and 10.
        """
        rating = self.cleaned_data.get('rating')
        if rating < 1 or rating > 10:
            raise forms.ValidationError('Rating must be between 1 and 10.')
        return rating

class PromoCodeForm(forms.ModelForm):
    """
    Form for creating and editing promotional codes.
    Includes code, discount percentage, and expiry date fields.
    """
    class Meta:
        model = PromoCode
        fields = ['code', 'discount_percent', 'expiry_date']
        widgets = {
            'expiry_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

    def clean_code(self):
        """
        Validates that the promo code is unique and properly formatted.
        """
        code = self.cleaned_data.get('code')
        if not code.isalnum():
            raise forms.ValidationError('Promo code must contain only letters and numbers.')
        if PromoCode.objects.filter(code=code).exists():
            raise forms.ValidationError('This promo code already exists.')
        return code

    def clean_discount_percent(self):
        """
        Validates that the discount percentage is between 0 and 100.
        """
        discount = self.cleaned_data.get('discount_percent')
        if discount < 0 or discount > 100:
            raise forms.ValidationError('Discount must be between 0 and 100 percent.')
        return discount 