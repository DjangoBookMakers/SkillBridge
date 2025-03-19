from django import forms
from django.contrib.auth.forms import (
    AuthenticationForm,
    UserCreationForm,
    PasswordChangeForm,
)
from .models import User


class LoginForm(AuthenticationForm):
    """로그인 폼

    사용자 로그인을 위한 커스텀 폼입니다.
    아이디와 비밀번호 필드의 스타일과 라벨을 한국어로 설정합니다.
    """

    username = forms.CharField(
        widget=forms.TextInput(attrs={"placeholder": "아이디"}),
        label="아이디",
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "비밀번호",
            }
        ),
        label="비밀번호",
    )


class SignupForm(UserCreationForm):
    """회원가입 폼

    새로운 사용자 계정 생성을 위한 커스텀 폼입니다.
    기본 사용자 생성 폼에 이메일과 추가 필드들을 포함합니다.
    """

    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={"class": "form-control", "placeholder": "이메일"}
        ),
        required=True,
    )

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "password1",
            "password2",
            "first_name",
            "last_name",
            "profile_image",
            "phone_number",
            "birth_date",
            "gender",
        ]
        widgets = {
            "username": forms.TextInput(attrs={"placeholder": "아이디"}),
            "first_name": forms.TextInput(attrs={"placeholder": "이름"}),
            "last_name": forms.TextInput(attrs={"placeholder": "성"}),
            "phone_number": forms.TextInput(attrs={"placeholder": "전화번호"}),
            "birth_date": forms.DateInput(attrs={"type": "date"}),
            "gender": forms.Select(
                choices=[("", "성별 선택"), ("남성", "남성"), ("여성", "여성")],
            ),
            "profile_image": forms.FileInput(),
        }


class ProfileEditForm(forms.ModelForm):
    """프로필 수정 폼

    사용자가 자신의 프로필 정보를 수정하기 위한 폼입니다.
    이메일, 이름, 프로필 이미지 등 개인 정보 필드를 포함합니다.
    """

    class Meta:
        model = User
        fields = [
            "email",
            "first_name",
            "last_name",
            "profile_image",
            "phone_number",
            "birth_date",
            "gender",
        ]
        widgets = {
            "email": forms.EmailInput(),
            "first_name": forms.TextInput(),
            "last_name": forms.TextInput(),
            "profile_image": forms.FileInput(),
            "phone_number": forms.TextInput(),
            "birth_date": forms.DateInput(attrs={"type": "date"}),
            "gender": forms.Select(
                choices=[("", "성별 선택"), ("남성", "남성"), ("여성", "여성")],
            ),
        }


class CustomPasswordChangeForm(PasswordChangeForm):
    """비밀번호 변경 폼

    사용자가 자신의 비밀번호를 변경하기 위한 커스텀 폼입니다.
    기본 PasswordChangeForm을 상속받아 커스터마이징합니다.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
