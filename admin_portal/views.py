from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse, HttpResponseForbidden
from django.db import models

from courses.models import Course, Subject, Lecture, MissionQuestion
from accounts.models import InstructorProfile

# 관리자 확인 함수
def is_admin(user):
    return user.is_authenticated and user.is_admin

# 관리자 대시보드
@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    """관리자 대시보드 화면"""
    # 요약 정보 수집
    courses_count = Course.objects.count()
    subjects_count = Subject.objects.count()
    lectures_count = Lecture.objects.count()
    
    # 최근 생성된 과정 (최대 5개)
    recent_courses = Course.objects.all().order_by('-created_at')[:5]
    
    context = {
        'courses_count': courses_count,
        'subjects_count': subjects_count,
        'lectures_count': lectures_count,
        'recent_courses': recent_courses,
    }
    
    return render(request, 'admin_portal/dashboard.html', context)

# 과정 관리 뷰
@login_required
@user_passes_test(is_admin)
def course_list(request):
    """과정 목록 관리 화면"""
    courses_list = Course.objects.all().order_by('-created_at')
    
    # 페이지네이션 (한 페이지에 10개씩 표시)
    paginator = Paginator(courses_list, 10)
    page = request.GET.get('page')
    
    try:
        courses = paginator.page(page)
    except PageNotAnInteger:
        courses = paginator.page(1)
    except EmptyPage:
        courses = paginator.page(paginator.num_pages)
    
    context = {
        'courses': courses,
    }
    
    return render(request, 'admin_portal/courses/list.html', context)

@login_required
@user_passes_test(is_admin)
def course_detail(request, course_id):
    """과정 상세 화면"""
    course = get_object_or_404(Course, id=course_id)
    subjects = Subject.objects.filter(course=course).order_by('order_index')
    
    context = {
        'course': course,
        'subjects': subjects,
    }
    
    return render(request, 'admin_portal/courses/detail.html', context)

@login_required
@user_passes_test(is_admin)
def course_create(request):
    """과정 생성 화면"""
    instructors = InstructorProfile.objects.all()
    
    if request.method == 'POST':
        # 과정 생성 로직
        title = request.POST.get('title')
        description = request.POST.get('description')
        short_description = request.POST.get('short_description')
        difficulty_level = request.POST.get('difficulty_level')
        target_audience = request.POST.get('target_audience')
        estimated_time = request.POST.get('estimated_time')
        credit = request.POST.get('credit')
        price = request.POST.get('price')
        instructor_id = request.POST.get('instructor')
        
        # 유효성 검사
        if not all([title, description, difficulty_level, estimated_time, credit, price, instructor_id]):
            messages.error(request, '모든 필수 항목을 입력해주세요.')
            return render(request, 'admin_portal/courses/create.html', {
                'instructors': instructors
            })
        
        instructor = get_object_or_404(InstructorProfile, id=instructor_id)
        
        # 썸네일 이미지 처리
        thumbnail_image = request.FILES.get('thumbnail_image')
        
        # 과정 생성
        course = Course.objects.create(
            title=title,
            description=description,
            short_description=short_description,
            difficulty_level=difficulty_level,
            target_audience=target_audience,
            estimated_time=estimated_time,
            credit=credit,
            price=price,
            instructor=instructor
        )
        
        if thumbnail_image:
            course.thumbnail_image = thumbnail_image
            course.save()
        
        messages.success(request, f'"{title}" 과정이 성공적으로 생성되었습니다.')
        return redirect('admin_portal:course_list')
    
    return render(request, 'admin_portal/courses/create.html', {
        'instructors': instructors
    })

@login_required
@user_passes_test(is_admin)
def course_edit(request, course_id):
    """과정 수정 화면"""
    course = get_object_or_404(Course, id=course_id)
    instructors = InstructorProfile.objects.all()
    
    if request.method == 'POST':
        # 과정 수정 로직
        course.title = request.POST.get('title')
        course.description = request.POST.get('description')
        course.short_description = request.POST.get('short_description')
        course.difficulty_level = request.POST.get('difficulty_level')
        course.target_audience = request.POST.get('target_audience')
        course.estimated_time = request.POST.get('estimated_time')
        course.credit = request.POST.get('credit')
        course.price = request.POST.get('price')
        
        instructor_id = request.POST.get('instructor')
        course.instructor = get_object_or_404(InstructorProfile, id=instructor_id)
        
        # 썸네일 이미지 처리
        thumbnail_image = request.FILES.get('thumbnail_image')
        if thumbnail_image:
            course.thumbnail_image = thumbnail_image
        
        course.save()
        messages.success(request, f'"{course.title}" 과정이 성공적으로 수정되었습니다.')
        return redirect('admin_portal:course_list')
    
    return render(request, 'admin_portal/courses/edit.html', {
        'course': course,
        'instructors': instructors
    })

@login_required
@user_passes_test(is_admin)
def course_delete(request, course_id):
    """과정 삭제 처리"""
    course = get_object_or_404(Course, id=course_id)
    
    if request.method == 'POST':
        title = course.title
        course.delete()
        messages.success(request, f'"{title}" 과정이 성공적으로 삭제되었습니다.')
        return redirect('admin_portal:course_list')
    
    return render(request, 'admin_portal/courses/delete.html', {
        'course': course
    })

# 과목 관리 뷰
@login_required
@user_passes_test(is_admin)
def subject_list(request, course_id):
    """과목 목록 관리 화면"""
    course = get_object_or_404(Course, id=course_id)
    subjects = Subject.objects.filter(course=course).order_by('order_index')
    
    context = {
        'course': course,
        'subjects': subjects,
    }
    
    return render(request, 'admin_portal/subjects/list.html', context)

@login_required
@user_passes_test(is_admin)
def subject_detail(request, course_id, subject_id):
    """과목 상세 화면"""
    course = get_object_or_404(Course, id=course_id)
    subject = get_object_or_404(Subject, id=subject_id, course=course)
    lectures = Lecture.objects.filter(subject=subject).order_by('order_index')
    
    context = {
        'course': course,
        'subject': subject,
        'lectures': lectures,
    }
    
    return render(request, 'admin_portal/subjects/detail.html', context)

@login_required
@user_passes_test(is_admin)
def subject_create(request, course_id):
    """과목 생성 화면"""
    course = get_object_or_404(Course, id=course_id)
    
    if request.method == 'POST':
        # 과목 생성 로직
        title = request.POST.get('title')
        description = request.POST.get('description')
        subject_type = request.POST.get('subject_type')
        
        # 새 과목의 순서 결정 (기존 과목들 중 가장 큰 순서 + 1)
        max_order = Subject.objects.filter(course=course).aggregate(models.Max('order_index')).get('order_index__max') or 0
        order_index = max_order + 1
        
        # 과목 생성
        subject = Subject.objects.create(
            course=course,
            title=title,
            description=description,
            subject_type=subject_type,
            order_index=order_index
        )
        
        messages.success(request, f'"{title}" 과목이 성공적으로 생성되었습니다.')
        return redirect('admin_portal:subject_list', course_id=course.id)
    
    return render(request, 'admin_portal/subjects/create.html', {
        'course': course
    })

@login_required
@user_passes_test(is_admin)
def subject_edit(request, course_id, subject_id):
    """과목 수정 화면"""
    course = get_object_or_404(Course, id=course_id)
    subject = get_object_or_404(Subject, id=subject_id, course=course)
    
    if request.method == 'POST':
        # 과목 수정 로직
        subject.title = request.POST.get('title')
        subject.description = request.POST.get('description')
        subject.subject_type = request.POST.get('subject_type')
        
        # 순서 변경이 요청된 경우
        new_order = request.POST.get('order_index')
        if new_order and int(new_order) != subject.order_index:
            # 다른 과목들의 순서 조정이 필요할 수 있음
            subject.order_index = int(new_order)
        
        subject.save()
        messages.success(request, f'"{subject.title}" 과목이 성공적으로 수정되었습니다.')
        return redirect('admin_portal:subject_list', course_id=course.id)
    
    return render(request, 'admin_portal/subjects/edit.html', {
        'course': course,
        'subject': subject
    })

@login_required
@user_passes_test(is_admin)
def subject_delete(request, course_id, subject_id):
    """과목 삭제 처리"""
    course = get_object_or_404(Course, id=course_id)
    subject = get_object_or_404(Subject, id=subject_id, course=course)
    
    if request.method == 'POST':
        title = subject.title
        subject.delete()
        
        # 남은 과목들의 순서 재조정
        remaining_subjects = Subject.objects.filter(course=course).order_by('order_index')
        for i, subj in enumerate(remaining_subjects, 1):
            if subj.order_index != i:
                subj.order_index = i
                subj.save()
        
        messages.success(request, f'"{title}" 과목이 성공적으로 삭제되었습니다.')
        return redirect('admin_portal:subject_list', course_id=course.id)
    
    return render(request, 'admin_portal/subjects/delete.html', {
        'course': course,
        'subject': subject
    })

# 강의 관리 뷰
@login_required
@user_passes_test(is_admin)
def lecture_list(request, course_id, subject_id):
    """강의 목록 관리 화면"""
    course = get_object_or_404(Course, id=course_id)
    subject = get_object_or_404(Subject, id=subject_id, course=course)
    lectures = Lecture.objects.filter(subject=subject).order_by('order_index')
    
    context = {
        'course': course,
        'subject': subject,
        'lectures': lectures,
    }
    
    return render(request, 'admin_portal/lectures/list.html', context)

@login_required
@user_passes_test(is_admin)
def lecture_detail(request, course_id, subject_id, lecture_id):
    """강의 상세 화면"""
    course = get_object_or_404(Course, id=course_id)
    subject = get_object_or_404(Subject, id=subject_id, course=course)
    lecture = get_object_or_404(Lecture, id=lecture_id, subject=subject)
    
    # 미션 강의인 경우 문제 목록 가져오기
    questions = None
    if lecture.lecture_type == 'mission':
        questions = MissionQuestion.objects.filter(lecture=lecture).order_by('order_index')
    
    context = {
        'course': course,
        'subject': subject,
        'lecture': lecture,
        'questions': questions,
    }
    
    return render(request, 'admin_portal/lectures/detail.html', context)

@login_required
@user_passes_test(is_admin)
def lecture_create(request, course_id, subject_id):
    """강의 생성 화면"""
    course = get_object_or_404(Course, id=course_id)
    subject = get_object_or_404(Subject, id=subject_id, course=course)
    
    if request.method == 'POST':
        # 강의 생성 로직
        title = request.POST.get('title')
        description = request.POST.get('description')
        lecture_type = request.POST.get('lecture_type')
        duration = request.POST.get('duration') if lecture_type == 'video' else None
        
        # 새 강의의 순서 결정 (기존 강의들 중 가장 큰 순서 + 1)
        max_order = Lecture.objects.filter(subject=subject).aggregate(models.Max('order_index')).get('order_index__max') or 0
        order_index = max_order + 1
        
        # 강의 생성
        lecture = Lecture.objects.create(
            subject=subject,
            title=title,
            description=description,
            lecture_type=lecture_type,
            duration=duration,
            order_index=order_index
        )
        
        # 비디오 파일 처리
        if lecture_type == 'video':
            video_file = request.FILES.get('video_file')
            if video_file:
                lecture.video_url = video_file
                lecture.save()
        
        messages.success(request, f'"{title}" 강의가 성공적으로 생성되었습니다.')
        return redirect('admin_portal:lecture_list', course_id=course.id, subject_id=subject.id)
    
    return render(request, 'admin_portal/lectures/create.html', {
        'course': course,
        'subject': subject
    })

@login_required
@user_passes_test(is_admin)
def lecture_edit(request, course_id, subject_id, lecture_id):
    """강의 수정 화면"""
    course = get_object_or_404(Course, id=course_id)
    subject = get_object_or_404(Subject, id=subject_id, course=course)
    lecture = get_object_or_404(Lecture, id=lecture_id, subject=subject)
    
    if request.method == 'POST':
        # 강의 수정 로직
        lecture.title = request.POST.get('title')
        lecture.description = request.POST.get('description')
        
        # 강의 유형은 변경 불가능하게 할 수도 있음 (데이터 일관성을 위해)
        # lecture.lecture_type = request.POST.get('lecture_type')
        
        if lecture.lecture_type == 'video':
            lecture.duration = request.POST.get('duration')
            
            # 비디오 파일 처리
            video_file = request.FILES.get('video_file')
            if video_file:
                lecture.video_url = video_file
        
        # 순서 변경이 요청된 경우
        new_order = request.POST.get('order_index')
        if new_order and int(new_order) != lecture.order_index:
            lecture.order_index = int(new_order)
        
        lecture.save()
        messages.success(request, f'"{lecture.title}" 강의가 성공적으로 수정되었습니다.')
        return redirect('admin_portal:lecture_list', course_id=course.id, subject_id=subject.id)
    
    return render(request, 'admin_portal/lectures/edit.html', {
        'course': course,
        'subject': subject,
        'lecture': lecture
    })

@login_required
@user_passes_test(is_admin)
def lecture_delete(request, course_id, subject_id, lecture_id):
    """강의 삭제 처리"""
    course = get_object_or_404(Course, id=course_id)
    subject = get_object_or_404(Subject, id=subject_id, course=course)
    lecture = get_object_or_404(Lecture, id=lecture_id, subject=subject)
    
    if request.method == 'POST':
        title = lecture.title
        lecture.delete()
        
        # 남은 강의들의 순서 재조정
        remaining_lectures = Lecture.objects.filter(subject=subject).order_by('order_index')
        for i, lect in enumerate(remaining_lectures, 1):
            if lect.order_index != i:
                lect.order_index = i
                lect.save()
        
        messages.success(request, f'"{title}" 강의가 성공적으로 삭제되었습니다.')
        return redirect('admin_portal:lecture_list', course_id=course.id, subject_id=subject.id)
    
    return render(request, 'admin_portal/lectures/delete.html', {
        'course': course,
        'subject': subject,
        'lecture': lecture
    })

# 미션 문제 관리 뷰
@login_required
@user_passes_test(is_admin)
def question_list(request, course_id, subject_id, lecture_id):
    """미션 문제 관리 화면"""
    course = get_object_or_404(Course, id=course_id)
    subject = get_object_or_404(Subject, id=subject_id, course=course)
    lecture = get_object_or_404(Lecture, id=lecture_id, subject=subject, lecture_type='mission')
    
    questions = MissionQuestion.objects.filter(lecture=lecture).order_by('order_index')
    
    context = {
        'course': course,
        'subject': subject,
        'lecture': lecture,
        'questions': questions,
    }
    
    return render(request, 'admin_portal/questions/list.html', context)

@login_required
@user_passes_test(is_admin)
def question_create(request, course_id, subject_id, lecture_id):
    """미션 문제 생성 화면"""
    course = get_object_or_404(Course, id=course_id)
    subject = get_object_or_404(Subject, id=subject_id, course=course)
    lecture = get_object_or_404(Lecture, id=lecture_id, subject=subject, lecture_type='mission')
    
    if request.method == 'POST':
        # 문제 생성 로직
        question_text = request.POST.get('question_text')
        option1 = request.POST.get('option1')
        option2 = request.POST.get('option2')
        option3 = request.POST.get('option3')
        option4 = request.POST.get('option4')
        option5 = request.POST.get('option5')
        correct_answer = request.POST.get('correct_answer')
        
        # 새 문제의 순서 결정 (기존 문제들 중 가장 큰 순서 + 1)
        max_order = MissionQuestion.objects.filter(lecture=lecture).aggregate(models.Max('order_index')).get('order_index__max') or 0
        order_index = max_order + 1
        
        # 문제 생성
        question = MissionQuestion.objects.create(
            lecture=lecture,
            question_text=question_text,
            option1=option1,
            option2=option2,
            option3=option3,
            option4=option4,
            option5=option5,
            correct_answer=correct_answer,
            order_index=order_index
        )
        
        messages.success(request, '문제가 성공적으로 생성되었습니다.')
        return redirect('admin_portal:question_list', course_id=course.id, subject_id=subject.id, lecture_id=lecture.id)
    
    return render(request, 'admin_portal/questions/create.html', {
        'course': course,
        'subject': subject,
        'lecture': lecture
    })

@login_required
@user_passes_test(is_admin)
def question_edit(request, course_id, subject_id, lecture_id, question_id):
    """미션 문제 수정 화면"""
    course = get_object_or_404(Course, id=course_id)
    subject = get_object_or_404(Subject, id=subject_id, course=course)
    lecture = get_object_or_404(Lecture, id=lecture_id, subject=subject, lecture_type='mission')
    question = get_object_or_404(MissionQuestion, id=question_id, lecture=lecture)
    
    if request.method == 'POST':
        # 문제 수정 로직
        question.question_text = request.POST.get('question_text')
        question.option1 = request.POST.get('option1')
        question.option2 = request.POST.get('option2')
        question.option3 = request.POST.get('option3')
        question.option4 = request.POST.get('option4')
        question.option5 = request.POST.get('option5')
        question.correct_answer = request.POST.get('correct_answer')
        
        # 순서 변경이 요청된 경우
        new_order = request.POST.get('order_index')
        if new_order and int(new_order) != question.order_index:
            question.order_index = int(new_order)
        
        question.save()
        messages.success(request, '문제가 성공적으로 수정되었습니다.')
        return redirect('admin_portal:question_list', course_id=course.id, subject_id=subject.id, lecture_id=lecture.id)
    
    return render(request, 'admin_portal/questions/edit.html', {
        'course': course,
        'subject': subject,
        'lecture': lecture,
        'question': question
    })

@login_required
@user_passes_test(is_admin)
def question_delete(request, course_id, subject_id, lecture_id, question_id):
    """미션 문제 삭제 처리"""
    course = get_object_or_404(Course, id=course_id)
    subject = get_object_or_404(Subject, id=subject_id, course=course)
    lecture = get_object_or_404(Lecture, id=lecture_id, subject=subject, lecture_type='mission')
    question = get_object_or_404(MissionQuestion, id=question_id, lecture=lecture)
    
    if request.method == 'POST':
        question.delete()
        
        # 남은 문제들의 순서 재조정
        remaining_questions = MissionQuestion.objects.filter(lecture=lecture).order_by('order_index')
        for i, q in enumerate(remaining_questions, 1):
            if q.order_index != i:
                q.order_index = i
                q.save()
        
        messages.success(request, '문제가 성공적으로 삭제되었습니다.')
        return redirect('admin_portal:question_list', course_id=course.id, subject_id=subject.id, lecture_id=lecture.id)
    
    return render(request, 'admin_portal/questions/delete.html', {
        'course': course,
        'subject': subject,
        'lecture': lecture,
        'question': question
    })