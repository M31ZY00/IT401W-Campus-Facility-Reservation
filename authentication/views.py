from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.views import LoginView
from django.shortcuts import render, redirect
from django.urls import reverse

TEMPLATE = 'authentication/authentication.html'
HOME_TEMPLATE = 'authentication/authentication.html'   # change if you put home.html elsewhere


def home(request):
    """Landing page shown after login (and to visitors who aren't signed in)."""
    return render(request, HOME_TEMPLATE)


def register(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = UserCreationForm(request.POST)

        if form.is_valid():
            user = form.save(commit=False)

            # Registration can only ever create a basic user.
            user.is_staff = False
            user.is_superuser = False
            user.is_active = True

            user.save()

            messages.success(request, 'Account created. You can sign in now.')
            return redirect('login')

    else:
        form = UserCreationForm()

    return render(request, TEMPLATE, {
        'form': AuthenticationForm(request),
        'register_form': form,
        'active_tab': 'register',
    })



class HomeLoginView(LoginView):
    template_name = 'authentication/authentication.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        next_url = self.get_redirect_url()
        if next_url:
            return next_url

        return reverse('home')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['register_form'] = UserCreationForm()
        context['active_tab'] = 'login'
        return context
