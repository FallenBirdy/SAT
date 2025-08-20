from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('home.urls')),

    path('logout/', auth_views.LogoutView.as_view(next_page='/login/'), name='logout'),

    # Optional: if you want to customize the login path too
    path('login/', auth_views.LoginView.as_view(), name='login'),

    # Default auth routes at root: /login/, /logout/, /password_reset/, etc.
    path('', include('django.contrib.auth.urls'))
]
