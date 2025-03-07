from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .forms import LoginForm, SignupForm

def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            
            
            if user is not None:
                login(request, user)
                user.login_at = timezone.now()  
                user.save()
            
            if user.is_admin:
                return redirect('admin_dashboard')  # 관리자 대시보드(보류)
            elif user.is_instructor:
                return redirect('instructor_dashboard')  # 강사 대시보드(보류)
            else:
                return redirect('home')  # 사용자 -> 메인 화면
        else:
            messages.error(request, '아이디 또는 비밀번호가 올바르지 않습니다.')
    else:
        form = LoginForm()
    
    return render(request, 'accounts/login.html', {'form': form})

def logout_view(request):
    if request.user.is_authenticated:
        request.user.logout_at = timezone.now()
        request.user.save()
        logout(request)
    return redirect('home')

def signup_view(request):
    if request.method == 'POST':
        form = SignupForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('login')
    else:
        form = SignupForm()
    
    return render(request, 'accounts/signup.html', {'form': form})

@login_required
def student_dashboard(request):
    return render(request, '')