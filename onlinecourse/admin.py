from django.contrib import admin
from .models import (
    Course, Lesson, Instructor, Learner,
    Question, Choice, Submission
)


class LessonInline(admin.StackedInline):
    model = Lesson
    extra = 5


class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 2


class QuestionInline(admin.StackedInline):
    model = Question
    extra = 1


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    inlines = [LessonInline, QuestionInline]
    list_display = ('name', 'pub_date', 'total_enrollment')
    list_filter = ['pub_date']
    search_fields = ['name', 'description']


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ['title', 'course', 'order']
    list_filter = ['course']


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['question_text', 'course', 'grade']
    list_filter = ['course']
    search_fields = ['question_text']
    inlines = [ChoiceInline]


@admin.register(Choice)
class ChoiceAdmin(admin.ModelAdmin):
    list_display = ['choice_text', 'question', 'is_correct']
    list_filter = ['is_correct', 'question__course']
    search_fields = ['choice_text']


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ['id', 'enrollment', 'score', 'total_points', 'submitted_at']
    list_filter = ['submitted_at']
    readonly_fields = ['score', 'total_points', 'submitted_at']


admin.site.register(Instructor)
admin.site.register(Learner)
