from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from .models import UserProfile


User = get_user_model()


class RegistrationForm(UserCreationForm):

    first_name = forms.CharField(
        max_length=150,
        required=True
    )

    last_name = forms.CharField(
        max_length=150,
        required=True
    )

    email = forms.EmailField(
        required=True
    )

    phone_number = forms.CharField(
        max_length=30,
        required=False
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = (
            'username',
            'first_name',
            'last_name',
            'email',
        )

    def clean_email(self):

        email = self.cleaned_data['email'].strip().lower()

        if User.objects.filter(
            email__iexact=email
        ).exists():

            raise forms.ValidationError(
                'This email address is already registered.'
            )

        return email

    def save(self, commit=True):

        user = super().save(commit=False)

        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data['email']

        # Public registration can create basic users only.
        user.is_staff = False
        user.is_superuser = False
        user.is_active = True

        if commit:

            user.save()

            UserProfile.objects.update_or_create(
                user=user,
                defaults={
                    'phone_number':
                    self.cleaned_data.get('phone_number', '')
                }
            )

        return user


class ProfileForm(forms.ModelForm):

    phone_number = forms.CharField(
        max_length=30,
        required=False
    )

    class Meta:
        model = User

        fields = [
            'first_name',
            'last_name',
            'email'
        ]

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        if self.instance.pk:

            profile = UserProfile.objects.filter(
                user=self.instance
            ).first()

            if profile:
                self.fields['phone_number'].initial = (
                    profile.phone_number
                )

    def clean_email(self):

        email = self.cleaned_data['email'].strip().lower()

        if User.objects.filter(
            email__iexact=email
        ).exclude(
            pk=self.instance.pk
        ).exists():

            raise forms.ValidationError(
                'This email address is already registered.'
            )

        return email

    def save(self, commit=True):

        user = super().save(commit=commit)

        if commit:

            UserProfile.objects.update_or_create(
                user=user,
                defaults={
                    'phone_number':
                    self.cleaned_data.get('phone_number', '')
                }
            )

        return user
