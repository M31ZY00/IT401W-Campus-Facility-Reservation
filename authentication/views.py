from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.views import LoginView
from django.shortcuts import render, redirect

TEMPLATE = 'authentication/authentication.html'


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
    """
    One page for sign in and registration, shared by both roles.
    Django's default AuthenticationForm already rejects deactivated
    accounts (is_active=False), so no custom form is needed.
    """
    template_name = TEMPLATE
    redirect_authenticated_user = True   # signed-in users skip this page

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['register_form'] = UserCreationForm()
        context['active_tab'] = 'login'
        return context

    def get_success_url(self):
        # Honor a safe ?next= value if present (Django validates the host).
        next_url = self.get_redirect_url()
        if next_url:
            return next_url

        user = self.request.user
        if user.is_staff or user.is_superuser:
            return '/manage/'
        return '/portal/'