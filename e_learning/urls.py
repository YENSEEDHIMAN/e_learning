# e_learning/urls.py

from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt import views as jwt_views
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from courses.views import ProtectedView, signup_view, login_view, dashboard_view, logout_view,courses_page, python_course,php_course,c_course,java_course,react_course,javascript_course, quizzes_intro,certificate_page,leaderboard_page ,start_quiz,quiz_links,submit_quiz,about_us,home,download_certificate,student_profile

from courses.views import chatbot_view
urlpatterns = [
    path('admin/', admin.site.urls),

    # JWT Authentication routes
    path('api/token/', jwt_views.TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', jwt_views.TokenRefreshView.as_view(), name='token_refresh'),

    # Include course API URLs
    path('api/', include('courses.urls')),

    # Protected route (for testing authenticated access)
    path('api/protected/', ProtectedView.as_view(), name='protected'),

    # User Authentication and Dashboard
    path('signup/', signup_view, name='signup'),
    path('login/', login_view, name='login'),
    path('dashboard/', dashboard_view, name='dashboard'),
    path('logout/', logout_view, name='logout'),

    # Courses page (HTML view)
    path('courses/', courses_page, name='courses_page'), 
    path('courses/python/', python_course, name='python_course'),
    path('courses/c/', c_course, name='c_course'),
    path('courses/java/', java_course, name='java_course'),
    path('courses/php/', php_course, name='php_course'),
    path('courses/javascript/', javascript_course, name='javascript_course'),
    path('courses/react/', react_course, name='react_course'),
    path('quizzes/', quizzes_intro, name='quizzes_intro'),
    path('certificate/', certificate_page, name='certificate_page'),
    path("leaderboard/", leaderboard_page, name="leaderboard-page"),
    path('quizzes/<str:course>/start/<str:level>/', start_quiz, name='start_quiz'),
    path('quizzes/', quiz_links, name='quiz_links'),
    path('quizzes/<str:course>/submit/<str:level>/', submit_quiz, name='quiz_submit'),
    path('about/', about_us, name='about_us'),
    path('', home, name='home'), 
    path('download-certificate/<int:course_id>/', download_certificate, name='download_certificate'),
    path('chatbot/', chatbot_view, name='chatbot'),
     path('profile/', student_profile, name='student_profile'),

      path('password-reset/', auth_views.PasswordResetView.as_view(template_name='password_reset.html'), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='password_reset_complete.html'), name='password_reset_complete'),
]

# Serving media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
