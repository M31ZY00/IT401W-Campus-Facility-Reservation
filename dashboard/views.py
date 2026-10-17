from django.shortcuts import render
from authentication.decorators import basic_user_required


@basic_user_required
def home(request):

    return render(
        request,
        'dashboard/home.html'
    )