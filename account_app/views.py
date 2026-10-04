from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate,logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import CustomUserCreationForm
from find_physio_app.models import PhysioProfile


# Create your views here.
def package_load(request):
    return render (request, 'package.html')


# Function-based view (simpler to start)
def signup_personal(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.user_type = 'personal'
            # Log the user in immediately after signup

            user.save()
            PhysioProfile.objects.get_or_create(physio=user)
            login(request, user)
            messages.success(request, f'Welcome {user.username}! Registration successful.')
            return redirect('login-personal')  # Change to your home URL name
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'accounts_app/signup-personal.html', {'form': form})


def signup_clinic(request):
    
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.user_type='clinic'
            user.save()  # <-- ADD THIS LINE
            PhysioProfile.objects.get_or_create(physio=user)
            # Log the user in immediately after signup
            login(request, user)
            messages.success(request, f'Welcome {user.username}! Registration successful.')
            return redirect('clinic-dashboard')  # Change to your home URL name
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CustomUserCreationForm()
    
    
    return render (request, 'accounts_app/signup-clinic.html', {'form': form})


def signup_enterprise(request):

    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.user_type = 'enterprise'
            user.save()
            PhysioProfile.objects.get_or_create(physio=user)
            login(request, user)
            messages.success(request, f'Welcome {user.username}! Registration successful.')
            return redirect('enterprise-dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CustomUserCreationForm()

    return render (request, 'accounts_app/signup-enterprise.html', {'form': form})



def login_signup_clinic(request):
    return render (request, 'login-signup/login-signup-clinic.html')

def login_signup_personal(request):
    return render (request, 'login-signup/login-signup-personal.html')

def login_signup_enterprise(request):
    return render (request, 'login-signup/login-signup-enterprise.html')


def login_view_clinic(request):
    if request.method == 'POST':
        username = request.POST.get('username')   # Use .get() to avoid KeyError
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)            
            # Redirect based on user_type
            if user.user_type == 'clinic':
                return redirect('clinic-dashboard')
            else:
                messages.error(request, 'Go to your package')
        else:
            messages.error(request, 'Invalid credentials')
    
    return render(request, 'accounts_app/login-clinic.html')


def login_view_personal(request):
    if request.method == 'POST':
        username = request.POST.get('username')   # Use .get() to avoid KeyError
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)            
            # Redirect based on user_type
            if user.user_type == 'personal':
                return redirect('personal-dashboard')
            else:
                messages.error(request, 'Go to your package')
        else:
            messages.error(request, 'Invalid credentials')
    
    return render(request, 'accounts_app/login-personal.html')


def login_view_enterprise(request):
    if request.method == 'POST':
        username = request.POST.get('username')   # Use .get() to avoid KeyError
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            # Redirect based on user_type
            if user.user_type == 'enterprise':
                return redirect('enterprise-dashboard')
            else:
                messages.error(request, 'Go to your package')
        else:
            messages.error(request, 'Invalid credentials')

    return render(request, 'accounts_app/login-enterprise.html')


def login_chooser(request):
    """The site's one global "Sign in" link (header nav on the homepage,
    Marketplace, Pharmacy, Lab Tests, Donate, Careers) used to go straight
    to login_view below, which only ever authenticates against this app's
    own User table (physio/clinic/enterprise). A patient -- a completely
    separate, session-based account (personal_account.AddPatient, see
    patient_app.patient_login) -- has no row there at all, so landing on
    that form and entering a real patient_code/password always failed with
    "Invalid credentials", however correct those details were.

    This page is the fork in the road instead: already logged in either
    way, skip straight past it; otherwise ask which kind of account this
    is before going to the login form that actually matches it."""
    if request.session.get('patient_id'):
        return redirect('patient-dashboard')
    if request.user.is_authenticated:
        if request.user.user_type == 'clinic':
            return redirect('clinic-dashboard')
        elif request.user.user_type == 'personal':
            return redirect('personal-dashboard')
        elif request.user.user_type == 'enterprise':
            return redirect('enterprise-dashboard')
        elif request.user.user_type == 'rider':
            return redirect('rider-dashboard')
    return render(request, 'login-chooser.html')


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            # Redirect based on user_type
            if user.user_type == 'clinic':
                return redirect('clinic-dashboard')
            elif user.user_type == 'personal':
                return redirect('personal-dashboard')
            elif user.user_type == 'enterprise':
                return redirect('enterprise-dashboard')
            elif user.user_type == 'rider':
                return redirect('rider-dashboard')
            else:
                messages.error(request, 'User type not recognized.')
        else:
            messages.error(request, 'Invalid credentials.')

    return render(request, 'accounts_app/login.html')


def logout_view_personal(request):
    logout(request)
    return redirect ('login-personal')

def logout_view_clinic(request):
    logout(request)
    return redirect ('login-clinic')

def logout_view_enterprise(request):
    logout(request)
    return redirect ('login-enterprise')

def password_reset_view(request):
    return render (request,'accounts_app/password_reset.html')

def patientlist_dashboard(request):
    return render (request, 'dashboards/patient-list.html')


def landing_page(request):
    return render (request, 'index.html')



