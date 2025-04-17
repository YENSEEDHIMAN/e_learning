from django.urls import path
from .views import (
    RegisterStudentView,
    StudentProfileView,
    SelectCourseView,
    CourseListView,
    DifficultyLevelView,
    QuizView,
    SubmitAnswerView,
    SubmitQuizView,
    StudentScoreView,
    LeaderboardView,
    
   
)


urlpatterns = [
    # Student Registration & Profile
    path('register/', RegisterStudentView.as_view(), name='register-student'),
    path('student-profile/', StudentProfileView.as_view(), name='student-profile'),

    # Courses & Selection
    path('select-course/', SelectCourseView.as_view(), name='select-course'),
    path('courses/', CourseListView.as_view(), name='course-list'),
    path('difficulty-levels/', DifficultyLevelView.as_view(), name='difficulty-level-list'),

    # Quizzes
    path('quizzes/<int:course_id>/<int:difficulty_level_id>/', QuizView.as_view(), name='quiz-list'),
    path('quizzes/submit-answer/', SubmitAnswerView.as_view(), name='submit-answer'),
    path('submit-quiz/', SubmitQuizView.as_view(), name='submit-quiz'),
    path('quizzes/student-score/', StudentScoreView.as_view(), name='student-score'),

    # Leaderboard
    path('leaderboard/', LeaderboardView.as_view(), name='leaderboard'),

    
    
 
   
]
