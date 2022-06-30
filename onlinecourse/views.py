from secrets import choice
from django.shortcuts import render
from django.http import HttpResponseRedirect
# <HINT> Import any new Models here
from .models import Course, Enrollment, Question, Choice, Submission
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.views import generic
from django.contrib.auth import login, logout, authenticate
import logging
# Get an instance of a logger
logger = logging.getLogger(__name__)
# Create your views here.


def registration_request(request):
    context = {}
    if request.method == 'GET':
        return render(request, 'onlinecourse/user_registration_bootstrap.html', context)
    elif request.method == 'POST':
        # Check if user exists
        username = request.POST['username']
        password = request.POST['psw']
        first_name = request.POST['firstname']
        last_name = request.POST['lastname']
        user_exist = False
        try:
            User.objects.get(username=username)
            user_exist = True
        except:
            logger.error("New user")
        if not user_exist:
            user = User.objects.create_user(username=username, first_name=first_name, last_name=last_name,
                                            password=password)
            login(request, user)
            return redirect("onlinecourse:index")
        else:
            context['message'] = "User already exists."
            return render(request, 'onlinecourse/user_registration_bootstrap.html', context)


def login_request(request):
    context = {}
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['psw']
        user = authenticate(username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('onlinecourse:index')
        else:
            context['message'] = "Invalid username or password."
            return render(request, 'onlinecourse/user_login_bootstrap.html', context)
    else:
        return render(request, 'onlinecourse/user_login_bootstrap.html', context)


def logout_request(request):
    logout(request)
    return redirect('onlinecourse:index')


def check_if_enrolled(user, course):
    is_enrolled = False
    if user.id is not None:
        # Check if user enrolled
        num_results = Enrollment.objects.filter(user=user, course=course).count()
        if num_results > 0:
            is_enrolled = True
    return is_enrolled


# CourseListView
class CourseListView(generic.ListView):
    template_name = 'onlinecourse/course_list_bootstrap.html'
    context_object_name = 'course_list'

    def get_queryset(self):
        user = self.request.user
        courses = Course.objects.order_by('-total_enrollment')[:10]
        for course in courses:
            if user.is_authenticated:
                course.is_enrolled = check_if_enrolled(user, course)
        return courses


class CourseDetailView(generic.DetailView):
    model = Course
    template_name = 'onlinecourse/course_detail_bootstrap.html'


def enroll(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    user = request.user

    is_enrolled = check_if_enrolled(user, course)
    if not is_enrolled and user.is_authenticated:
        # Create an enrollment
        Enrollment.objects.create(user=user, course=course, mode='honor')
        course.total_enrollment += 1
        course.save()

    return HttpResponseRedirect(reverse(viewname='onlinecourse:course_details', args=(course.id,)))


'''
version one: Create a submit view to create an exam submission record for a course enrollment

'''
def submit(request, course_id):
    # Get user and course object, then get the associated enrollment object created when the user enrolled the course
    user = request.user
    course = get_object_or_404(Course, pk=course_id)
    associated_enrollment = Enrollment.objects.get(user=user, course=course)
    
    # Create a submission object referring to the enrollment
    submission = Submission.objects.create(enrollment=associated_enrollment)

    # Collect the selected choices from exam form
    # Add each selected choice object to the submission object
    if request.method == "POST":
        selected_choices = extract_answers(request)
        for selected_choice in selected_choices:
            submission.choices.add(selected_choice)
            submission.save()

    # Redirect to show_exam_result with the submission id
    return HttpResponseRedirect(reverse(viewname='onlinecourse:show_exam_result', args=(course_id, submission.id)))


# <HINT> A example method to collect the selected choices from the exam form from the request object
def extract_answers(request):
   submitted_anwsers = []
   for key in request.POST:
       if key.startswith('choice'):
           value = request.POST[key]
           choice_id = int(value)
           submitted_anwsers.append(choice_id)
   return submitted_anwsers


'''
version one: Create an exam result view to check if learner passed exam and show their question results and result for each question,
'''
def show_exam_result(request, course_id, submission_id):
    context = {}
    exam_result = 0
    # Get course and submission based on their ids
    course = get_object_or_404(Course, pk=course_id)
    submission = get_object_or_404(Submission, pk=submission_id)

    # Get the selected choice ids from the submission record
    selected_choice_ids = Submission.objects.filter(id=submission.id).values_list('choices',flat=True)

    correct_choices_ids = Choice.objects.filter(is_correct=True).values_list('id', flat=True)

    print('selected_choice_ids [show_exam_result]: ', selected_choice_ids)
    print('correct_choices_ids [show_exam_result]: ', correct_choices_ids)

    choices = submission.choices.all()
    print('choices [show_exam_result]: ', choices)

    '''
    version a [better version. cleaner version.]:
    # For each selected choice, check if it is a correct answer or not
    # Calculate the total score
    total_score = 0
    for choice in choices:
        if choice.is_correct:
            total_score += int(choice.question.grade)
    
    '''
   
    '''
    version b:
    '''
    # For each selected choice, check if it is a correct answer or not
    # Calculate the total score
    actual_total_score = 0
    possible_total_score = 0
    for selected_choice in selected_choice_ids:

        question_id = Choice.objects.filter(id=selected_choice).values_list('question', flat=True)[0]

        associated_question = Question.objects.all().filter(id=question_id).values_list('grade', flat=True)
        associated_question_grade = associated_question[0]
        
        if selected_choice in correct_choices_ids:
            print('selected_choice in correct_choices_ids [show_exam_result]: Yup')
            actual_total_score += associated_question_grade
        else:
            print('selected_choice in correct_choices_ids [show_exam_result]: Nope')

        possible_total_score += associated_question_grade

    exam_result = int((actual_total_score / possible_total_score) * 100)
    print('exam_result:',exam_result) 
    
    # Add the course, selected_ids, and grade to context for rendering HTML page
    context['course'] = course
    context['selected_ids'] = selected_choice_ids
    context['grade'] = exam_result
    return render(request, 'onlinecourse/exam_result_bootstrap.html', context)
