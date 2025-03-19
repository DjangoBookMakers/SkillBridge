from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path("signup/", views.SignupView.as_view(), name="signup"),
    path("profile/", views.ProfileView.as_view(), name="profile"),
    path("profile/edit/", views.ProfileEditView.as_view(), name="profile_edit"),
    path(
        "profile/change-password/",
        views.ChangePasswordView.as_view(),
        name="change_password",
    ),
    path("profile/delete/", views.DeleteAccountView.as_view(), name="delete_account"),
]
