from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path, re_path
from django.conf import settings
from django.views.static import serve
from core.forms import EmailCPFAuthenticationForm


urlpatterns = [
    path("admin/", admin.site.urls),
    path("login/", auth_views.LoginView.as_view(authentication_form=EmailCPFAuthenticationForm), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("recuperar-senha/", auth_views.PasswordResetView.as_view(), name="password_reset"),
    path("recuperar-senha/enviado/", auth_views.PasswordResetDoneView.as_view(), name="password_reset_done"),
    path("redefinir-senha/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path("redefinir-senha/concluido/", auth_views.PasswordResetCompleteView.as_view(), name="password_reset_complete"),
    path("", include("core.urls")),
]

urlpatterns += [
    re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
]
