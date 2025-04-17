from django.db import models
from django.contrib.auth.models import User
import random


# Course & Difficulty Models


class Course(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()

    def __str__(self):
        return self.name


class DifficultyLevel(models.Model):
    DIFFICULTY_CHOICES = [
        (1, 'Beginner'),
        (2, 'Intermediate'),
        (3, 'Advanced'),
    ]

    level = models.IntegerField(choices=DIFFICULTY_CHOICES)

    def __str__(self):
        return dict(self.DIFFICULTY_CHOICES).get(self.level, "Unknown")

    
# Quiz Model

class Quiz(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    difficulty_level = models.ForeignKey(DifficultyLevel, on_delete=models.CASCADE)
    question_number = models.PositiveIntegerField()
    question = models.TextField()
    option_1 = models.CharField(max_length=255)
    option_2 = models.CharField(max_length=255)
    option_3 = models.CharField(max_length=255)
    option_4 = models.CharField(max_length=255)
    correct_answer = models.PositiveIntegerField()  # 1, 2, 3, or 4
    answer = models.CharField(max_length=255, default="Default Answer")

    def __str__(self):
        return f"Q{self.question_number}: {self.question}"

    def clean(self):
        if self.correct_answer not in [1, 2, 3, 4]:
            raise ValueError("Correct answer must be 1, 2, 3, or 4")


# Student & Answer Models
from decimal import Decimal

class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    father_name = models.CharField(max_length=255)
    has_completed_quiz = models.BooleanField(default=False)
    score = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    enrolled_course = models.ForeignKey(Course, null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return self.user.username

    def update_score(self):
        total_attempted = StudentAnswer.objects.filter(student=self).count()
        correct_answers = StudentAnswer.objects.filter(student=self, is_correct=True).count()

        self.score = (correct_answers / total_attempted) * 100 if total_attempted > 0 else 0
        self.save()


class StudentAnswer(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    selected_option = models.PositiveIntegerField()
    is_correct = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        self.is_correct = self.selected_option == self.quiz.correct_answer
        super().save(*args, **kwargs)
        self.student.update_score()

    def __str__(self):
        return f"{self.student.user.username} - Q{self.quiz.question_number}"
# Certificate Model


from .models import Student, Course
from django.db import models
from django.utils import timezone
from django.core.files.base import ContentFile
from django.core.mail import EmailMessage
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.colors import black, gray, navy
from reportlab.pdfgen import canvas
from io import BytesIO
from datetime import datetime
import random

from .models import Student, Course  # Adjust if needed

def generate_certificate_number():
    return str(random.randint(10000000, 99999999))

class Certificate(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    certificate_pdf = models.FileField(upload_to='certificates/', blank=True, null=True)
    certificate_number = models.CharField(max_length=10, unique=True, blank=False)
    issued_on = models.DateTimeField(default=timezone.now)
    

    def save(self, *args, **kwargs):
        # Get percentage from kwargs or use student's score
        percentage = kwargs.pop('percentage', None)
        if percentage is None:
            self.student.refresh_from_db()
            percentage = self.student.score

        # Generate unique certificate number
        if not self.certificate_number:
            while True:
                new_cert_number = generate_certificate_number()
                if not Certificate.objects.filter(certificate_number=new_cert_number).exists():
                    self.certificate_number = new_cert_number
                    break

        # Generate PDF
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
        p.drawCentredString(width / 2, height - 230, self.student.name)

        p.setFont("Helvetica", 20)
        p.setFillColor(gray)
        p.drawCentredString(width / 2, height - 280, "For successfully completing the quiz competition in")

        p.setFont("Helvetica-Bold", 26)
        p.setFillColor(black)
        p.drawCentredString(width / 2, height - 320, self.course.name)

     
        score = percentage 
        
        p.setFont("Helvetica", 18)
        p.drawCentredString(width / 2, height - 360, f"Achieved a total score of {score:.2f}%")

        p.drawCentredString(width / 2, height - 420, "Presented by SkillEdge Academy")

        p.setFont("Helvetica", 14)
        p.drawString(50, 80, f"Certificate Number: {self.certificate_number}")
        p.drawString(width - 250, 80, f"Date: {datetime.now().strftime('%Y-%m-%d')}")

        p.showPage()
        p.save()
        buffer.seek(0)

        # Save file
        safe_name = f"certificate_{self.student.name.replace(' ', '_')}_{self.course.name.replace(' ', '_')}_{self.certificate_number}.pdf"
        self.certificate_pdf.save(safe_name, ContentFile(buffer.getvalue()), save=False)

        # Save to DB
        super().save(*args, **kwargs)

        # Send email with the certificate
        self.send_certificate_email(buffer, safe_name)

    def send_certificate_email(self, pdf_buffer, file_name):
        student_email = self.student.user.email
        email_subject = "🎓 Your Course Certificate - SkillEdge Academy"
        email_body = (
            f"Hi {self.student.name},\n\n"
            f"Congratulations on successfully completing the quiz for {self.course.name}!\n"
            f"Please find your certificate attached.\n\n"
            f"Regards,\nSkillEdge Academy Team"
        )

        email = EmailMessage(subject=email_subject, body=email_body, to=[student_email])
        email.attach(file_name, pdf_buffer.getvalue(), 'application/pdf')

        try:
            email.send()
            print(f"Certificate email sent to {student_email}")
        except Exception as e:
            print(f"Failed to send certificate email to {student_email}: {e}")
