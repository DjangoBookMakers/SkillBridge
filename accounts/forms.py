
from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User

class LoginForm(forms.Form):
    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500',
            'placeholder': '아이디'
            }),
        label='아이디'
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500',
            'placeholder': '비밀번호'
        }),
        label='비밀번호'
    )

class SignupForm(UserCreationForm):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': '이메일'}),
        required=True
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2', 'first_name', 
                  'last_name', 'profile_image', 'phone_number', 'birth_date', 'gender']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '아이디'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '이름'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '성'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '전화번호'}),
            'birth_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'gender': forms.Select(attrs={'class': 'form-control'}, choices=[('', '성별 선택'), ('남성', '남성'), ('여성', '여성')]),
            'profile_image': forms.FileInput(attrs={'class': 'form-control'}),
        }

class ProfileEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'profile_image', 'phone_number', 'birth_date', 'gender']
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md'}),
            'first_name': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md'}),
            'last_name': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md'}),
            'profile_image': forms.FileInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md'}),
            'phone_number': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md'}),
            'birth_date': forms.DateInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md', 'type': 'date'}),
            'gender': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md'}, choices=[('', '성별 선택'), ('남성', '남성'), ('여성', '여성')]),
        }        