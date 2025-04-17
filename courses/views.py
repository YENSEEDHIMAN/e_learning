from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from django.core.files.base import ContentFile
from django.core.mail import EmailMessage
from django.utils.timezone import now
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt, csrf_protect

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.colors import black, gray, navy

from io import BytesIO
import random

from .models import Course, DifficultyLevel, Quiz, Student, Certificate, StudentAnswer
from .serializers import (
    CourseSerializer, DifficultyLevelSerializer, QuizSerializer, 
    StudentSerializer, LeaderboardStudentSerializer
)
from .forms import LoginForm

# --------- Student Registration ----------
class RegisterStudentView(generics.CreateAPIView):
    queryset = Student.objects.all()
    serializer_class = StudentSerializer
    permission_classes = [AllowAny]

# --------- Course Enrollment ----------
class SelectCourseView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, *args, **kwargs):
        student = request.user.student
        course_id = request.data.get('course_id')

        if not course_id:
            return Response({"error": "Course ID is required"}, status=400)

        try:
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            return Response({"error": "Invalid course ID"}, status=400)

        student.enrolled_course = course
        student.save()

        return Response({
            "message": f"You have successfully enrolled in {course.name}",
            "selected_course": course.name
        })

# --------- Student Profile ----------
class StudentProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        student = request.user.student
        latest_answers = StudentAnswer.objects.filter(student=student).order_by('-id')[:15]

        total = latest_answers.count()
        correct = sum(1 for answer in latest_answers if answer.is_correct)
        percentage = (correct / total * 100) if total > 0 else 0

        return Response({
            "id": student.id,
            "name": student.name,
            "email": student.user.email,
            "selected_course": student.enrolled_course.name if student.enrolled_course else "No course selected",
            "total_questions": total,
            "correct_answers": correct,
            "score": f"{correct}/{total}",
            "percentage": f"{percentage:.2f}%"
        })

# --------- Course List ----------
class CourseListView(generics.ListAPIView):
    serializer_class = CourseSerializer

    def get_queryset(self):
        if Course.objects.count() == 0:
            Course.objects.bulk_create([
                Course(name="Python", description="Learn Python programming"),
                Course(name="C", description="Learn C programming"),
                Course(name="Java", description="Learn Java programming"),
                Course(name="PHP", description="Learn PHP programming"),
            ])
        return Course.objects.all()

# --------- Difficulty Level List ----------
class DifficultyLevelView(generics.ListAPIView):
    serializer_class = DifficultyLevelSerializer

    def get_queryset(self):
        if DifficultyLevel.objects.count() == 0:
            DifficultyLevel.objects.bulk_create([
                DifficultyLevel(level="Beginner"),
                DifficultyLevel(level="Intermediate"),
                DifficultyLevel(level="Advanced"),
            ])
        return DifficultyLevel.objects.all()

# --------- Quiz Fetch ----------
class QuizView(generics.ListAPIView):
    serializer_class = QuizSerializer

    def get_queryset(self):
        course_id = self.kwargs.get('course_id')
        level_id = self.kwargs.get('difficulty_level_id')

        if not course_id or not level_id:
            return Quiz.objects.none()

        if not DifficultyLevel.objects.filter(id=level_id).exists():
            return Quiz.objects.none()

        # Get all questions
        all_questions = Quiz.objects.filter(course_id=course_id, difficulty_level_id=level_id)

        # Shuffle the questions randomly using Python's random.shuffle
        all_questions_list = list(all_questions)  # Convert to list to shuffle
        random.shuffle(all_questions_list)

        # Slice the first 15 random questions (do not sort them)
        random_questions = all_questions_list[:15]

        return random_questions
    
# --------- Create Quiz ----------

class CreateQuizView(generics.CreateAPIView):
    serializer_class = QuizSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data
        required_fields = ["course", "difficulty_level", "question", "answer"]
        if not all(field in data for field in required_fields):
            return Response({"error": "All fields are required"}, status=400)

        try:
            course = Course.objects.get(id=data["course"])
            difficulty_level = DifficultyLevel.objects.get(id=data["difficulty_level"])
        except (Course.DoesNotExist, DifficultyLevel.DoesNotExist):
            return Response({"error": "Invalid Course or Difficulty Level ID"}, status=400)

        # Fetch a random quiz question if no question is provided in data
        if "question" not in data or "answer" not in data:
            random_quiz = Quiz.objects.filter(course=course, difficulty_level=difficulty_level).order_by("?").first()
            if random_quiz:
                data["question"] = random_quiz.question
                data["answer"] = random_quiz.answer

        # Create the new quiz
        quiz = Quiz.objects.create(
            course=course,
            difficulty_level=difficulty_level,
            question=data["question"],
            answer=data["answer"]
        )
        return Response(QuizSerializer(quiz).data, status=201)

# --------- Submit Answers ----------
class SubmitAnswerView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        student = request.user.student
        course_id = request.data.get("course_id")
        answers = request.data.get("answers", [])[:15]

        if not isinstance(answers, list):
            return Response({"error": "Answers must be a list."}, status=400)

        correct = 0
        for ans in answers:
            quiz_id = ans.get("quiz")
            selected = ans.get("selected_option")

            try:
                quiz = Quiz.objects.get(id=quiz_id, course_id=course_id)
                is_correct = str(quiz.correct_answer).strip().lower() == str(selected).strip().lower()
                if is_correct:
                    correct += 1

                StudentAnswer.objects.create(
                    student=student,
                    quiz=quiz,
                    selected_option=selected,
                    is_correct=is_correct
                )
            except Quiz.DoesNotExist:
                return Response({"error": f"Quiz ID {quiz_id} not found in this course."}, status=400)

        percentage = (correct / len(answers)) * 100 if answers else 0
        student.has_completed_quiz = True
        student.score = percentage
        student.save()

        return Response({
            "total_questions_attempted": len(answers),
            "correct_answers": correct,
            "score": f"{correct}/{len(answers)}",
            "percentage": f"{percentage:.2f}%"
        })

# --------- Student Score ----------
class StudentScoreView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        student = request.user.student
        answers = StudentAnswer.objects.filter(student=student).order_by('-id')[:15]
        total = answers.count()
        correct = sum(1 for a in answers if a.is_correct)
        score = (correct / total) * 100 if total > 0 else 0
        return Response({
            "student_name": student.name,
            "total_questions_attempted": total,
            "correct_answers": correct,
            "score": round(score, 2)
        })

# --------- Certificate Generation ----------
def generate_certificate_number():
    return ''.join(random.choices("0123456789", k=8))

class SubmitQuizView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        username = request.data.get("username")

        if not username:
            return Response({"error": "Username is required"}, status=400)

        try:
            student = User.objects.get(username=username).student
        except (User.DoesNotExist, AttributeError):
            return Response({"error": "Invalid student username"}, status=400)

        if not student.enrolled_course:
            return Response({"error": "Student is not enrolled in any course"}, status=400)

        answers = StudentAnswer.objects.filter(student=student).order_by('-id')[:10]
        total = answers.count()
        correct = sum(1 for a in answers if a.is_correct)
        percentage = (correct / total * 100) if total > 0 else 0
        
        student.score = percentage
        student.has_completed_quiz = True
        student.save()

        if percentage < 50:
            return Response({"error": f"Minimum 50% required. Your score: {percentage:.2f}%"}, status=400)

        course = student.enrolled_course
        certificate = Certificate.objects.filter(student=student, course=course).first()

        if not certificate:
            while True:
                cert_no = generate_certificate_number()
                if not Certificate.objects.filter(certificate_number=cert_no).exists():
                    break

            certificate = Certificate.objects.create(
                student=student,
                course=course,
                certificate_number=cert_no
            )

            buffer = BytesIO()
            p = canvas.Canvas(buffer, pagesize=landscape(A4))
            width, height = landscape(A4)
            margin = 40

            p.setStrokeColor(black)
            p.setLineWidth(5)
            p.rect(margin, margin, width - 2 * margin, height - 2 * margin)

            p.setFont("Times-BoldItalic", 40)
            p.drawCentredString(width / 2, height - 100, "Certificate of Achievement")

            p.setFont("Helvetica", 22)
            p.setFillColor(gray)
            p.drawCentredString(width / 2, height - 180, "This is proudly presented to")

            p.setFont("Helvetica-Bold", 32)
            p.setFillColor(navy)
            p.drawCentredString(width / 2, height - 230, f"{student.name}")

            p.setFont("Helvetica", 20)
            p.setFillColor(gray)
            p.drawCentredString(width / 2, height - 280, "For successfully completing the quiz competition in")

            p.setFont("Helvetica-Bold", 26)
            p.setFillColor(black)
            p.drawCentredString(width / 2, height - 320, f"{course.name}")

            p.setFont("Helvetica", 18)
            p.drawCentredString(width / 2, height - 360, f"Achieved a total score of {percentage:.2f}%")
            p.drawCentredString(width / 2, height - 420, "Presented by SkillEdge Academy")

            p.setFont("Helvetica", 14)
            p.drawString(50, 80, f"Certificate Number: {cert_no}")
            p.drawString(width - 250, 80, f"Date: {now().strftime('%Y-%m-%d')}")

            p.showPage()
            p.save()
            buffer.seek(0)

            filename = f'certificates/certificate_{student.id}_{course.id}.pdf'
            certificate.certificate_pdf.save(filename, ContentFile(buffer.getvalue()))
            certificate.save()

        if student.user.email:
            email = EmailMessage(
                subject="Your SkillEdge Certificate is Here!",
                body=(
                    f"Hi {student.name},\n\n"
                    f"Congratulations on completing the {course.name} quiz with {percentage:.2f}%.\n\n"
                    f"Attached is your certificate from SkillEdge Academy.\n\n"
                    f"Best,\nSkillEdge Team"
                ),
                to=[student.user.email]
            )

            with open(certificate.certificate_pdf.path, "rb") as pdf:
                email.attach(f"Certificate_{student.name.replace(' ', '_')}.pdf", pdf.read(), "application/pdf")

            try:
                email.send()
            except Exception as e:
                print(f"Email error: {e}")

        return Response({
            "message": "Certificate awarded and emailed.",
            "student_name": student.name,
            "course": course.name,
            "certificate_number": certificate.certificate_number,
            "student_score": f"{percentage:.2f}%",
            "certificate_url": certificate.certificate_pdf.url
        }, status=201)

# --------- Leaderboard ----------
class LeaderboardView(generics.ListAPIView):
    serializer_class = LeaderboardStudentSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        course_id = self.request.query_params.get('course_id')
        qs = Student.objects.filter(has_completed_quiz=True)
        return qs.filter(enrolled_course__id=course_id) if course_id else qs.order_by('-score')[:15]

from rest_framework.decorators import api_view, permission_classes

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def protected_view(request):
    return Response({'message': 'You are authenticated'})

class ProtectedView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"message": "This is protected data."})
    


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')  # Change to your actual dashboard URL name

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)

            if user is not None:
                login(request, user)
                return redirect('dashboard')  # Redirect to dashboard
            else:
                messages.error(request, 'Invalid username or password.')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = LoginForm()

    return render(request, 'login.html', {'form': form})


@login_required(login_url='login')
def dashboard_view(request):
    return render(request, 'dashboard.html')


def logout_view(request):
    logout(request)  # Logs out the user
    return redirect('login')  # Redirect to the login page

def csrf_failure(request, reason="CSRF cookie not set"):
    return render(request, 'csrf_error.html', {'reason': reason})



@csrf_protect

def signup_view(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        father_name = request.POST.get('father_name')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if password != confirm_password:
            messages.error(request, "Passwords do not match")
            return render(request, 'signup.html')

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email is already registered")
            return render(request, 'signup.html')

        try:
            user = User.objects.create_user(username=email, email=email, password=password)
            user.first_name = name
            user.save()

            student = Student.objects.create(
                user=user,
                name=name,
                father_name=father_name,
                has_completed_quiz=False,
                score=0.0
            )
            print("Student Created:", student) 

            messages.success(request, "Account created successfully. Please log in.")
            return redirect('login')

        except Exception as e:
            print("ERROR:", e)
            messages.error(request, str(e)) 
            return render(request, 'signup.html')

    return render(request, 'signup.html')


def user_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']

        # Authenticate user
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, "You have successfully logged in!")
            return redirect('dashboard')  
        else:
            messages.error(request, "Invalid login credentials. Please try again.")
            return render(request, 'login.html')

    # If the user was redirected to the login page after successful signup
    if 'account_created' in request.GET:
        messages.success(request, "Account created successfully. Please log in.")
    
    return render(request, 'login.html')


@login_required
def courses_page(request):
    courses = Course.objects.all()  
    return render(request, 'courses.html', {'courses': courses})

@login_required
def python_course(request):
    return render(request, 'python.html')

@login_required
def c_course(request):
    return render(request, 'c.html')

@login_required
def java_course(request):
    return render(request, 'java.html')

@login_required
def php_course(request):
    return render(request, 'php.html')

@login_required
def javascript_course(request):
    return render(request, 'javascript.html')

@login_required
def react_course(request):
    return render(request, 'react.html')

@login_required
def quizzes_intro(request):
    return render(request, 'quizzes.html') 

@login_required
def certificate_page(request):
    return render(request, 'certificate.html')

@login_required
def leaderboard_page(request):
    return render(request, "leaderboard.html")

def about_us(request):
    return render(request, 'about_us.html')


def home(request):
    return render(request, 'home.html')

@login_required
@csrf_exempt
def start_quiz(request, course, level):
    level_map = {'easy': 1, 'intermediate': 2, 'advanced': 3}
    level_value = level_map.get(level.lower())
    if level_value is None:
        return render(request, 'error.html', {'message': 'Invalid difficulty level'})

    course_obj = get_object_or_404(Course, name__iexact=course)
    level_obj = get_object_or_404(DifficultyLevel, level=level_value)

    # Retrieve all questions for the selected course and difficulty level
    questions = Quiz.objects.filter(course=course_obj, difficulty_level=level_obj).order_by('question_number')

    # Shuffle questions randomly
    questions = list(questions)
    random.shuffle(questions)

    # Limit the questions to 15
    questions = questions[:15]

    score = None
    total = len(questions)

    if request.method == 'POST':
        score = 0
        # Iterate over the selected 15 questions
        for q in questions:
            selected = request.POST.get(f'q{q.id}')
            if selected and int(selected) == q.correct_answer:
                score += 1

    context = {
        'course': course,
        'level': level,
        'questions': questions,
        'score': score,
        'total': total
    }

    return render(request, 'start_quiz.html', context)



def quiz_links(request):
    context = {
        'courses': ['python', 'c', 'java', 'js', 'react', 'php'],
        'levels': ['easy', 'intermediate', 'advanced'],
    }
    return render(request, 'quizzes/quiz_links.html', context)


from django.shortcuts import render, redirect, get_object_or_404
from .models import Course, DifficultyLevel, Quiz

from courses.models import Student, Course, DifficultyLevel, Quiz  # make sure models are imported
from django.contrib.auth.decorators import login_required


@login_required
def submit_quiz(request, course, level):
    if request.method == 'POST':
        level_map = {'easy': 1, 'intermediate': 2, 'advanced': 3}
        level_value = level_map.get(level.lower())
        if level_value is None:
            return render(request, 'error.html', {'message': 'Invalid difficulty level'})

        course_obj = get_object_or_404(Course, name__iexact=course)
        level_obj = get_object_or_404(DifficultyLevel, level=level_value)

        questions = Quiz.objects.filter(course=course_obj, difficulty_level=level_obj).order_by('question_number')
        total = questions.count()
        score = 0

        # Debugging: Print total and each question's ID and answer
        print(f"Total questions: {total}")
        
        for q in questions:
            selected = request.POST.get(f'q{q.id}')
            print(f"Question {q.id}: Selected = {selected}, Correct = {q.correct_answer}")
            
            if selected and int(selected) == q.correct_answer:
                score += 1
        
        # Debugging: Print score after all questions are processed
        print(f"Total Score: {score}")
        
        percentage = (score / total) * 100
        passing_score = total * 0.6
        passed = score >= passing_score

        student = get_object_or_404(Student, user=request.user)
        student.enrolled_course = course_obj
        student.has_completed_quiz = True
        student.score = percentage
        student.save()

        certificate = None
        if passed:
            # Delete existing certificates (optional)
            Certificate.objects.filter(student=student, course=course_obj).delete()
        
            # Create new one
            certificate = Certificate(student=student, course=course_obj)
            certificate.save()

        # Feedback based on score
        if score == total:
            feedback = "Outstanding! You aced the quiz."
        elif passed:
            feedback = "Well done! You have a solid understanding."
        else:
            feedback = "Keep going! More practice will lead to success."

        return render(request, 'quiz_result.html', {
            'score': score,
            'total': total,
            'percentage': percentage,
            'feedback_message': feedback,
            'course': course_obj,
            'level': level,
            'passed': passed,
            'certificate': certificate,
        })

from django.shortcuts import render, get_object_or_404
from .models import Course, Certificate, Student

def quiz_result(request, course, level, score, total_score):
    passing_score = total_score * 0.5  # Assuming 50% is the passing score
    feedback_message = ""
    show_download_link = False

    if score >= passing_score:
        feedback_message = "Congratulations! You passed the quiz."
        show_download_link = True
    else:
        feedback_message = "Sorry, you didn't pass this time. Try again!"

    # Fetch the certificate if the student has passed
    certificate = None
    if show_download_link:
        student = get_object_or_404(Student, user=request.user)
        certificate = Certificate.objects.filter(student=student, course__name=course).first()

    return render(request, 'quiz_result.html', {
        'course': course,
        'level': level,
        'score': score,
        'total_score': total_score,
        'feedback_message': feedback_message,
        'show_download_link': show_download_link,
        'certificate': certificate
    })
from django.http import FileResponse ,HttpResponse
from .models import Certificate
from django.contrib.auth.decorators import login_required

@login_required
def download_certificate(request, course_id):
    student = Student.objects.get(user=request.user)
    certificate = Certificate.objects.filter(student=student, course_id=course_id).first()
    
    if certificate and certificate.certificate_pdf:
        return FileResponse(certificate.certificate_pdf.open(), as_attachment=True)
    else:
        return HttpResponse("Certificate not found or not available yet.", status=404)




# import json
# from sentence_transformers import SentenceTransformer
# import faiss
# import numpy as np
# from llama_cpp import Llama
# from django.http import JsonResponse

# # Initialize the embedder and FAISS index
# embedder = SentenceTransformer('all-MiniLM-L6-v2')

# # Sample corpus (You can replace this with actual documents or database data)
# documents = [
#     "Python is a programming language.",
#     "Django is a high-level Python web framework.",
#     "Llama 2 is a language model by Meta AI."
# ]

# # Generate embeddings for the documents
# embeddings = embedder.encode(documents)

# # Build the FAISS index
# dimension = embeddings.shape[1]
# index = faiss.IndexFlatL2(dimension)
# index.add(np.array(embeddings))

# # Initialize the Llama model
# llm = Llama(model_path="./models/llama-2-7b.Q4_K_M.gguf")  # Adjust path as needed

# def retrieve_docs(query, k=2):
#     """Retrieve the top k most relevant documents for a given query."""
#     query_vec = embedder.encode([query])
#     D, I = index.search(np.array(query_vec), k)
#     return [documents[i] for i in I[0]]

# def generate_answer(query):
#     """Generate an answer based on the query using the Llama model."""
#     # Construct a simple and clean prompt without unnecessary repetition
#     prompt = f"Question: {query}\nAnswer:"
    
#     # Get the response from the Llama model
#     response = llm(prompt, max_tokens=100)
    
#     # Extract and clean the response to ensure it's just the answer
#     answer = response["choices"][0]["text"].strip()
    
#     # Return only the first valid sentence or response part
#     if answer:
#         return answer.split("\n")[0]  # Avoid multiple question-answer repeats
    
#     return "Sorry, I couldn't find an answer."

# @csrf_exempt
# def chatbot_view(request):
#     if request.method == "POST":
#         try:
#             # Get the user's input from the request body
#             data = json.loads(request.body)
#             user_input = data.get('input', '')

#             if user_input:
#                 # Generate answer from Llama model based on the input query
#                 answer = generate_answer(user_input)
#                 return JsonResponse({"answer": answer})

#             else:
#                 return JsonResponse({"error": "No input provided"}, status=400)

#         except Exception as e:
#             return JsonResponse({"error": f"Error processing request: {str(e)}"}, status=500)
#     else:
#         return JsonResponse({"error": "Only POST requests are allowed"}, status=405)




import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def chatbot_view(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            user_input = data.get('input', '').lower()

            responses = {
                "welcome": {
                    "answer": "Welcome! How can I assist you today?",
                    "options": ["Ask about courses", "Ask about quizzes", "Ask about certificates", "Ask about leaderboard"]
                },
                "hello": {
                    "answer": "Hello! How can I assist you today?",
                    "options": ["Ask about courses", "Ask about quizzes", "Ask about certificates", "Ask about leaderboard"]
                },
                "ask about courses": {
                    "answer": "We offer 6 courses: Java, JavaScript, Python, React, C, and PHP — each with Beginner, Intermediate, and Hard levels.",
                    "options": ["View available courses", "Enroll in a course", "Get course recommendations"]
                },
                "courses": {
                    "answer": "You can browse and enroll in 6 courses: Java, JavaScript, Python, React, C, and PHP. Each course has Beginner, Intermediate, and Hard levels.",
                    "options": ["View available courses", "Enroll in a course", "Get course recommendations"]
                },
                "view available courses": {
                    "answer": "Here are the available courses:\n- Java\n- JavaScript\n- Python\n- React\n- C\n- PHP",
                    "options": ["Enroll in a course", "Ask about quizzes", "Ask about certificates"]
                },
                "enroll in a course": {
                    "answer": "To enroll, go to the 'Courses' section and click 'Enroll' on your preferred course.",
                    "options": ["Go to Courses", "See my enrolled courses", "Ask about quizzes"]
                },
                "get course recommendations": {
                    "answer": "Tell me your interest or experience level, and I’ll recommend a course!",
                    "options": ["Beginner", "Intermediate", "Advanced"]
                },
                "ask about quizzes": {
                    "answer": "Each course includes quizzes at Beginner, Intermediate, and Hard levels.",
                    "options": ["Take a quiz", "Check quiz results", "Retake a quiz"]
                },
                "quizzes": {
                    "answer": "You can access quizzes from the 'Quizzes' section based on your selected course and level.",
                    "options": ["Take a quiz", "Check quiz results", "Retake a quiz"]
                },
                "take a quiz": {
                    "answer": "To take a quiz, go to the quiz section, select your course and difficulty level, then start the quiz.",
                    "options": ["Ask about certificates", "Check quiz results", "Ask about leaderboard"]
                },
                "check quiz results": {
                    "answer": "Go to your dashboard and open the 'Profile' section to check your scores.",
                    "options": ["Take a quiz", "Retake a quiz", "Ask about certificates"]
                },
                "retake a quiz": {
                    "answer": "Go to the quiz section and select the course and level you want to retake.",
                    "options": ["Take a quiz", "Check quiz results", "Ask about courses"]
                },
                "ask about certificates": {
                    "answer": "Students scoring more than 50% in quizzes will receive a certificate via email.",
                    "options": ["View my certificates", "How do I earn a certificate?", "Share my certificate"]
                },
                "certificates": {
                    "answer": "Certificates are awarded to students who score more than 50% in any quiz. It will be sent to your registered email.",
                    "options": ["View my certificates", "How do I earn a certificate?", "Share my certificate"]
                },
                "view my certificates": {
                    "answer": "Go to the 'Profile' section on your dashboard and download your certificate there.",
                    "options": ["Share my certificate", "Ask about leaderboard", "Ask about quizzes"]
                },
                "how do i earn a certificate?": {
                    "answer": "You must score more than 50% in any quiz to earn a certificate.",
                    "options": ["Take a quiz", "Check quiz results", "View my certificates"]
                },
                "share my certificate": {
                    "answer": "You can share your certificate directly from your dashboard via social media or email.",
                    "options": ["Email my certificate", "Download certificate", "View my certificates"]
                },
                "email my certificate": {
                    "answer": "Your certificate has been sent to your registered email address.",
                    "options": ["View my certificates", "Share my certificate", "Ask about leaderboard"]
                },
                "ask about leaderboard": {
                    "answer": "The leaderboard displays the top 10 students based on quiz scores.",
                    "options": ["View leaderboard", "How is ranking calculated?", "Ask about courses"]
                },
                "leaderboard": {
                    "answer": "Visit the leaderboard section to see the top 10 students ranked by quiz performance.",
                    "options": ["View leaderboard", "Ask about quizzes", "Ask about certificates"]
                },
                "view leaderboard": {
                    "answer": "Top 10 students based on scores and completion times are shown on the leaderboard.",
                    "options": ["Ask about certificates", "Ask about quizzes", "Go back to home"]
                },
                "how is ranking calculated?": {
                    "answer": "Ranking is based on total quiz scores and how quickly students complete them.",
                    "options": ["View leaderboard", "Ask about courses", "Ask about certificates"]
                },
                "go back to home": {
                    "answer": "Sure! How can I help you today?",
                    "options": ["Ask about courses", "Ask about quizzes", "Ask about certificates", "Ask about leaderboard"]
                },
                "beginner": {
                    "answer": "Great! As a beginner, we recommend starting with Python or Java — both are beginner-friendly and widely used.",
                    "options": ["Enroll in Python", "Enroll in Java", "Ask about quizzes"]
                },
                "intermediate": {
                    "answer": "Nice! You can explore JavaScript or React to enhance your skills and start building real-world projects.",
                    "options": ["Enroll in JavaScript", "Enroll in React", "Ask about certificates"]
                },
                "advanced": {
                    "answer": "Awesome! Try challenging yourself with advanced courses like React or C to master programming concepts.",
                    "options": ["Enroll in React", "Enroll in C", "Ask about leaderboard"]
                },
                "enroll in python": {
                    "answer": "You’ve selected Python. Visit the 'Courses' section and click 'Enroll' to start learning!",
                    "options": ["Go to Courses", "Take a quiz", "Ask about certificates"]
                },
                "enroll in java": {
                    "answer": "You’ve selected Java. Visit the 'Courses' section and click 'Enroll' to start learning!",
                    "options": ["Go to Courses", "Take a quiz", "Ask about certificates"]
                },
                "enroll in javascript": {
                    "answer": "You’ve selected JavaScript. Visit the 'Courses' section and click 'Enroll' to start learning!",
                    "options": ["Go to Courses", "Take a quiz", "Ask about certificates"]
                },
                "enroll in react": {
                    "answer": "You’ve selected React. Visit the 'Courses' section and click 'Enroll' to start learning!",
                    "options": ["Go to Courses", "Take a quiz", "Ask about certificates"]
                },
                "enroll in c": {
                    "answer": "You’ve selected C. Visit the 'Courses' section and click 'Enroll' to start learning!",
                    "options": ["Go to Courses", "Take a quiz", "Ask about certificates"]
                }
            }

            default_response = {
                "answer": "Sorry, I didn't understand that. Please choose an option below.",
                "options": ["Ask about courses", "Ask about quizzes", "Ask about certificates", "Ask about leaderboard"]
            }

            result = responses.get(user_input, default_response)
            return JsonResponse(result)

        except Exception as e:
            return JsonResponse({"error": f"Error: {str(e)}"}, status=500)

    return JsonResponse({"error": "Only POST requests are allowed"}, status=405)



@login_required
def student_profile(request):
    student = Student.objects.get(user=request.user)
    certificate = Certificate.objects.filter(student=student, course=student.enrolled_course).first()

    return render(request, 'student_profile.html', {
        'student': student,
        'certificate': certificate
    })

