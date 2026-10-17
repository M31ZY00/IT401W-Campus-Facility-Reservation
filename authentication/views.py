from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.views import LoginView
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import render, redirect
from django.urls import reverse

from .forms import RegistrationForm, ProfileForm


TEMPLATE = 'authentication/authentication.html'


def register(request):

    if request.user.is_authenticated:

        if (
            request.user.is_staff
            or request.user.is_superuser
        ):
            return redirect('admin_dashboard')

        return redirect('home')

    if request.method == 'POST':

        form = RegistrationForm(request.POST)

        if form.is_valid():

            with transaction.atomic():
                form.save()

            messages.success(
                request,
                'Account created successfully. You can sign in now.'
            )

            return redirect('login')

    else:
        form = RegistrationForm()

    return render(
        request,
        TEMPLATE,
        {
            'form': AuthenticationForm(request),
            'register_form': form,
            'active_tab': 'register',
        }
    )


class HomeLoginView(LoginView):

    template_name = TEMPLATE
    redirect_authenticated_user = True

    def get_success_url(self):

        user = self.request.user

        if user.is_staff or user.is_superuser:
            return reverse('admin_dashboard')

        return reverse('home')

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        context['register_form'] = RegistrationForm()
        context['active_tab'] = 'login'

        return context


@login_required
def profile(request):

    # Only active basic users may access the profile.
    if (
        not request.user.is_active
        or request.user.is_staff
        or request.user.is_superuser
    ):
        raise PermissionDenied

    if request.method == 'POST':

        form = ProfileForm(
            request.POST,
            instance=request.user
        )

        if form.is_valid():

            with transaction.atomic():
                form.save()

            messages.success(
                request,
                'Your profile has been updated successfully.'
            )

            return redirect('profile')

    else:

        form = ProfileForm(
            instance=request.user
        )

    return render(
        request,
        'authentication/profile.html',
        {
            'form': form
        }
    )
