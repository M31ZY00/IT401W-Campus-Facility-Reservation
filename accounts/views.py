from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.views import LoginView
from django.core.exceptions import ValidationError
from django.shortcuts import render, redirect


class StudentAuthenticationForm(AuthenticationForm):

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)

        if user.is_staff or user.is_superuser:
            raise ValidationError(
                'Administrator accounts cannot log in through Student Login.',
                code='invalid_role'
            )


class AdminAuthenticationForm(AuthenticationForm):

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)

        if not user.is_staff:
            raise ValidationError(
                'Only administrator accounts can log in here.',
                code='invalid_role'
            )


def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)

        if form.is_valid():
            user = form.save(commit=False)

            user.is_staff = False
            user.is_superuser = False
            user.is_active = True

            user.save()

            return redirect('login')

    else:
        form = UserCreationForm()

    return render(
        request,
        'accounts/register.html',
        {
            'form': form
        }
    )


class StudentLoginView(LoginView):
    template_name = 'accounts/login.html'
    authentication_form = StudentAuthenticationForm

    def get_success_url(self):
        return '/'


class AdminLoginView(LoginView):
    template_name = 'accounts/admin_login.html'
    authentication_form = AdminAuthenticationForm

    def get_success_url(self):
        return '/manage/'