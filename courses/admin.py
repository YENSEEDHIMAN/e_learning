from django.contrib import admin
from .models import Course, DifficultyLevel, Quiz, Student, Certificate, StudentAnswer
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.contrib.admin import AdminSite



# Customize the Admin site header and title
admin.site.site_header = "Admin Login"
admin.site.site_title = "Admin Login"
admin.site.index_title = "Welcome to Admin Panel"

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'description')
    search_fields = ('name',)


@admin.register(DifficultyLevel)
class DifficultyLevelAdmin(admin.ModelAdmin):
    list_display = ('id', 'level',)
    search_fields = ('level',)


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ('id', 'question_number', 'question', 'course', 'difficulty_level', 'correct_answer')
    list_filter = ('course', 'difficulty_level')
    search_fields = ('question',)


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'name', 'father_name', 'enrolled_course', 'has_completed_quiz', 'score')
    list_filter = ('enrolled_course', 'has_completed_quiz')
    search_fields = ('user__username', 'name')
    ordering = ('-score',)  # Leaderboard: Highest score first


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ('id', 'student', 'course', 'certificate_number')
    search_fields = ('certificate_number', 'student__user__username')



