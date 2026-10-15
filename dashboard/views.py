from django.shortcuts import render, redirect


def home(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('admin_dashboard')

    return render(request, 'dashboard/home.html')