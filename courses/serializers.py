from django.contrib.auth.models import User
from rest_framework import serializers
from .models import Student, Course, DifficultyLevel, Quiz, Certificate, StudentAnswer


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class StudentSerializer(serializers.ModelSerializer):
    name = serializers.CharField(max_length=255)
    email = serializers.EmailField(source='user.email', write_only=True)
    password = serializers.CharField(write_only=True, min_length=6)
    confirm_password = serializers.CharField(write_only=True, min_length=6)
    father_name = serializers.CharField(max_length=255)
    enrolled_course = serializers.PrimaryKeyRelatedField(
        queryset=Course.objects.all(), required=False
    )

    class Meta:
        model = Student
        fields = [
            'id', 'name', 'father_name', 'email',
            'password', 'confirm_password', 'enrolled_course'
        ]

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({"password": "Passwords do not match"})
        return data

    def create(self, validated_data):
        user_data = validated_data.pop('user')
        email = user_data['email']
        password = validated_data.pop('password')
        validated_data.pop('confirm_password')

        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError({"email": "This email is already registered."})

        user = User.objects.create_user(username=email, email=email, password=password)
        student = Student.objects.create(user=user, **validated_data)
        return student


class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ['id', 'name', 'description']

class DifficultyLevelSerializer(serializers.ModelSerializer):
    level_display = serializers.SerializerMethodField()

    class Meta:
        model = DifficultyLevel
        fields = ['id', 'level', 'level_display']

    def get_level_display(self, obj):
        return obj.get_level_display()

class QuizSerializer(serializers.ModelSerializer):
    class Meta:
        model = Quiz
        fields = [
            'course', 'difficulty_level', 'question_number',
            'question', 'option_1', 'option_2', 'option_3', 'option_4'
        ]


class StudentAnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentAnswer
        fields = ['quiz', 'selected_option']


class CertificateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Certificate
        fields = ['student', 'course', 'certificate_pdf']


class LeaderboardStudentSerializer(serializers.ModelSerializer):
   
    course = serializers.CharField(source='enrolled_course.name')
    class Meta:
        model = Student
        fields = ['name', 'course', 'score', 'has_completed_quiz']

from .models import StudentAnswer

class StudentAnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentAnswer
        fields = ['student', 'quiz', 'selected_option']