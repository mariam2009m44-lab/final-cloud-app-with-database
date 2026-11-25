import logging

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import generic

from .models import Choice, Course, Enrollment, Question, Submission

logger = logging.getLogger(__name__)


def registration_request(request):
    context = {}
    if request.method == 'GET':
        return render(request, 'onlinecourse/user_registration_bootstrap.html', context)

    username = request.POST['username']
    password = request.POST['psw']
    first_name = request.POST['firstname']
    last_name = request.POST['lastname']

    if User.objects.filter(username=username).exists():
        context['message'] = "User already exists."
        return render(request, 'onlinecourse/user_registration_bootstrap.html', context)

    user = User.objects.create_user(
        username=username,
        first_name=first_name,
        last_name=last_name,
        password=password
    )
    login(request, user)
    return redirect("onlinecourse:index")


def login_request(request):
    context = {}
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['psw']
        user = authenticate(username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('onlinecourse:index')
        context['message'] = "Invalid username or password."
    return render(request, 'onlinecourse/user_login_bootstrap.html', context)


def logout_request(request):
    logout(request)
    return redirect('onlinecourse:index')


def check_if_enrolled(user, course):
    if not user.is_authenticated:
        return False
    return Enrollment.objects.filter(user=user, course=course).exists()


class CourseListView(generic.ListView):
    template_name = 'onlinecourse/course_list_bootstrap.html'
    context_object_name = 'course_list'

    def get_queryset(self):
        courses = Course.objects.order_by('-total_enrollment')[:10]
        for course in courses:
            course.is_enrolled = check_if_enrolled(self.request.user, course)
        return courses


class CourseDetailView(generic.DetailView):
    model = Course
    template_name = 'onlinecourse/course_detail_bootstrap.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_enrolled'] = check_if_enrolled(
            self.request.user, context['course']
        )
        return context


def enroll(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    if request.user.is_authenticated and not check_if_enrolled(request.user, course):
        Enrollment.objects.create(user=request.user, course=course, mode='honor')
        course.total_enrollment += 1
        course.save(update_fields=['total_enrollment'])
    return HttpResponseRedirect(
        reverse(viewname='onlinecourse:course_details', args=(course.id,))
    )


def extract_answers(request):
    """Read the selected choice IDs from the submitted assessment form."""
    submitted_answers = []
    for key, value in request.POST.items():
        if key.startswith('choice_'):
            try:
                submitted_answers.append(int(value))
            except (TypeError, ValueError):
                continue
    return list(set(submitted_answers))


@login_required
def submit(request, course_id):
    if request.method != 'POST':
        return redirect('onlinecourse:course_details', pk=course_id)

    course = get_object_or_404(Course, pk=course_id)
    enrollment = get_object_or_404(
        Enrollment, user=request.user, course=course
    )

    questions = Question.objects.filter(course=course).prefetch_related('choice_set')
    valid_choices = Choice.objects.filter(
        question__course=course, id__in=extract_answers(request)
    )

    submission = Submission.objects.create(enrollment=enrollment)
    submission.choices.set(valid_choices)

    selected_by_question = {}
    for choice in valid_choices:
        selected_by_question.setdefault(choice.question_id, set()).add(choice.id)

    total_points = 0
    score = 0
    for question in questions:
        total_points += question.grade
        if question.is_get_score(selected_by_question.get(question.id, set())):
            score += question.grade

    submission.score = score
    submission.total_points = total_points
    submission.save(update_fields=['score', 'total_points'])

    return redirect(
        'onlinecourse:show_exam_result',
        course_id=course.id,
        submission_id=submission.id
    )


@login_required
def show_exam_result(request, course_id, submission_id):
    course = get_object_or_404(Course, pk=course_id)
    submission = get_object_or_404(
        Submission,
        pk=submission_id,
        enrollment__course=course,
        enrollment__user=request.user
    )

    question_results = []
    questions = Question.objects.filter(course=course).prefetch_related('choice_set')
    selected_ids = set(submission.choices.values_list('id', flat=True))

    for question in questions:
        selected_for_question = selected_ids.intersection(
            question.choice_set.values_list('id', flat=True)
        )
        is_correct = question.is_get_score(selected_for_question)
        question_results.append({
            'question': question,
            'choices': question.choice_set.all(),
            'selected_ids': selected_for_question,
            'is_correct': is_correct,
            'points_earned': question.grade if is_correct else 0,
        })

    percentage = (
        (submission.score / submission.total_points) * 100
        if submission.total_points else 0
    )
    return render(request, 'onlinecourse/exam_result_bootstrap.html', {
        'course': course,
        'submission': submission,
        'question_results': question_results,
        'percentage': percentage,
    })
