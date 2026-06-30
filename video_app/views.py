from django.shortcuts import render

# Create your views here.
def load_tutorial(request):
    return render (request, 'tutorial-page.html')