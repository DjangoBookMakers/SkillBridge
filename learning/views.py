from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import FileResponse
from django.shortcuts import render, redirect, get_object_or_404

from courses.models import Course, Subject, Lecture, MissionQuestion, QnAQuestion
from .forms import ProjectSubmissionForm
from .models import (
    Enrollment,
    LectureProgress,
    MissionAttempt,
    ProjectSubmission,
    Certificate,
)


# 학습 대시보드
@login_required
def dashboard(request):
    # 사용자의 수강 중인 과정 목록
    enrollments = Enrollment.objects.filter(user=request.user).order_by("-enrolled_at")

    # 진행 중인 과정과 완료된 과정 분리
    in_progress = [e for e in enrollments if e.status == "enrolled"]
    completed = [e for e in enrollments if e.status in ["completed", "certified"]]

    # 수료증 목록
    certificates = Certificate.objects.filter(user=request.user).order_by("-issued_at")

    context = {
        "in_progress": in_progress,
        "completed": completed,
        "certificates": certificates,
    }
    return render(request, "learning/dashboard.html", context)


# 이어서 학습하기
@login_required
def resume_course(request, course_id):
    # 과정 정보 가져오기
    course = get_object_or_404(Course, id=course_id)

    # 수강 신청 여부 확인
    enrollment = get_object_or_404(Enrollment, user=request.user, course=course)

    # 다음 학습 항목 가져오기
    item_type, item = enrollment.get_next_learning_item()

    # 항목 유형에 따라 적절한 URL로 리다이렉트
    if item_type == "video_lecture":
        return redirect("learning_video_lecture", lecture_id=item.id)
    elif item_type == "mission":
        return redirect("learning_mission", lecture_id=item.id)
    elif item_type == "project":
        return redirect("learning_submit_project", subject_id=item.id)
    else:  # 'completed'
        return redirect("course_detail", course_id=course.id)


# 현재 강의 다음의 학습 항목으로 이동
@login_required
def next_item(request, lecture_id):
    """현재 강의 다음에 이어지는 학습 항목으로 이동"""
    lecture = get_object_or_404(Lecture, id=lecture_id)

    # 다음 학습 항목 가져오기
    item_type, item = lecture.get_next_learning_item()

    # 항목 유형에 따라 적절한 URL로 리다이렉트
    if item_type == "video_lecture":
        return redirect("learning_video_lecture", lecture_id=item.id)
    elif item_type == "mission":
        return redirect("learning_mission", lecture_id=item.id)
    elif item_type == "project":
        return redirect("learning_submit_project", subject_id=item.id)
    else:  # 'completed'
        return redirect("course_detail", course_id=item.id)


# 동영상 강의 시청
@login_required
def video_lecture(request, lecture_id):
    lecture = get_object_or_404(Lecture, id=lecture_id, lecture_type="video")

    # 수강 신청 여부 확인
    enrollment = get_object_or_404(
        Enrollment, user=request.user, course=lecture.subject.course
    )

    # 강의 시청 기록 생성 또는 업데이트
    lecture_progress, created = LectureProgress.objects.get_or_create(
        user=request.user, lecture=lecture
    )

    # 시청 완료 처리 (강의에 접근하는 것만으로도 완료 처리)
    if not lecture_progress.is_completed:
        lecture_progress.mark_as_completed()

    # 이전/다음 강의 찾기
    subject_lectures = Lecture.objects.filter(subject=lecture.subject).order_by(
        "order_index"
    )

    current_index = next(
        (i for i, l in enumerate(subject_lectures) if l.id == lecture.id), None
    )

    prev_lecture = subject_lectures[current_index - 1] if current_index > 0 else None
    next_lecture = (
        subject_lectures[current_index + 1]
        if current_index < len(subject_lectures) - 1
        else None
    )

    # 해당 강의에 대한 질문 목록
    questions = QnAQuestion.objects.filter(lecture=lecture).order_by("-created_at")

    context = {
        "lecture": lecture,
        "subject": lecture.subject,
        "course": lecture.subject.course,
        "prev_lecture": prev_lecture,
        "next_lecture": next_lecture,
        "questions": questions,
        "enrollment": enrollment,
    }
    return render(request, "learning/video_lecture.html", context)


# 미션(쪽지시험) 수행
@login_required
def mission(request, lecture_id):
    lecture = get_object_or_404(Lecture, id=lecture_id, lecture_type="mission")

    # 수강 신청 여부 확인
    enrollment = get_object_or_404(
        Enrollment, user=request.user, course=lecture.subject.course
    )

    # 이미 통과한 미션인지 확인
    passed_attempt = MissionAttempt.objects.filter(
        user=request.user, lecture=lecture, is_passed=True
    ).first()

    if passed_attempt:
        return redirect("learning_mission_result", attempt_id=passed_attempt.id)

    # 시도 중인 미션이 있는지 확인
    active_attempt = MissionAttempt.objects.filter(
        user=request.user, lecture=lecture, completed_at__isnull=True
    ).first()

    # 문제 목록 가져오기
    questions = MissionQuestion.objects.filter(lecture=lecture).order_by("order_index")

    if request.method == "POST":
        # POST 요청에서 사용자 답안 수집
        user_answers = {}
        for key, value in request.POST.items():
            if key.startswith("question_"):
                question_id = key.replace("question_", "")
                user_answers[question_id] = value

        # 기존 미션 시도가 있으면 업데이트, 없으면 새로 생성
        if active_attempt:
            attempt = active_attempt
            attempt.user_answers = user_answers
        else:
            attempt = MissionAttempt(
                user=request.user, lecture=lecture, user_answers=user_answers
            )

        # 저장 및 점수 계산
        attempt.save()
        attempt.calculate_score()

        # 결과 페이지로 리다이렉트
        return redirect("learning_mission_result", attempt_id=attempt.id)

    context = {
        "lecture": lecture,
        "subject": lecture.subject,
        "course": lecture.subject.course,
        "questions": questions,
        "enrollment": enrollment,
    }
    return render(request, "learning/mission.html", context)


# 미션 결과 확인
@login_required
def mission_result(request, attempt_id):
    attempt = get_object_or_404(MissionAttempt, id=attempt_id, user=request.user)
    lecture = attempt.lecture

    # 문제 정보 가져오기
    questions = MissionQuestion.objects.filter(lecture=lecture).order_by("order_index")

    # 문제별 사용자 답안 및 정답 매칭
    results = []
    for question in questions:
        user_answer = attempt.user_answers.get(str(question.id), None)
        is_correct = user_answer and int(user_answer) == question.correct_answer

        results.append(
            {
                "question": question,
                "user_answer": user_answer,
                "is_correct": is_correct,
            }
        )

    context = {
        "attempt": attempt,
        "lecture": lecture,
        "subject": lecture.subject,
        "course": lecture.subject.course,
        "results": results,
        "total_questions": len(questions),
        "correct_count": sum(1 for r in results if r["is_correct"]),
    }
    return render(request, "learning/mission_result.html", context)


# 프로젝트 제출 (중간/기말고사)
@login_required
def submit_project(request, subject_id):
    subject = get_object_or_404(Subject, id=subject_id)

    # 수강 신청 여부 확인
    enrollment = get_object_or_404(Enrollment, user=request.user, course=subject.course)

    # 중간/기말고사 과목인지 확인
    if subject.subject_type not in ["midterm", "final"]:
        messages.error(request, "유효하지 않은 접근입니다.")
        return redirect("course_detail", course_id=subject.course.id)

    # 이미 제출한 프로젝트가 있는지 확인
    existing_submission = (
        ProjectSubmission.objects.filter(user=request.user, subject=subject)
        .order_by("-submitted_at")
        .first()
    )

    if request.method == "POST":
        form = ProjectSubmissionForm(request.POST, request.FILES)
        if form.is_valid():
            submission = form.save(commit=False)
            submission.user = request.user
            submission.subject = subject
            submission.save()

            messages.success(request, "프로젝트가 성공적으로 제출되었습니다.")
            return redirect("learning_project_detail", submission_id=submission.id)
    else:
        form = ProjectSubmissionForm()

    context = {
        "subject": subject,
        "course": subject.course,
        "form": form,
        "existing_submission": existing_submission,
        "enrollment": enrollment,
    }
    return render(request, "learning/submit_project.html", context)


# 프로젝트 상세 보기
@login_required
def project_detail(request, submission_id):
    submission = get_object_or_404(ProjectSubmission, id=submission_id)

    # 권한 확인 (제출자 본인 또는 관리자)
    if submission.user != request.user and not request.user.is_admin:
        raise PermissionDenied

    context = {
        "submission": submission,
        "subject": submission.subject,
        "course": submission.subject.course,
    }
    return render(request, "learning/project_detail.html", context)


# 수료증 발급
@login_required
def issue_certificate(request, enrollment_id):
    enrollment = get_object_or_404(Enrollment, id=enrollment_id, user=request.user)

    # 이미 발급된 수료증이 있는지 확인
    existing_cert = Certificate.objects.filter(enrollment=enrollment).first()
    if existing_cert:
        messages.info(request, "이미 발급된 수료증이 있습니다.")
        return redirect("learning_view_certificate", certificate_id=existing_cert.id)

    # 수료 조건 확인
    if enrollment.status != "completed":
        if not enrollment.check_completion():
            messages.error(
                request, "모든 과정을 완료해야 수료증을 발급받을 수 있습니다."
            )
            return redirect("learning_dashboard")

    # 수료증 발급
    certificate = Certificate(user=request.user, enrollment=enrollment)

    # 고유 번호 생성
    certificate.generate_certificate_number()

    # PDF 생성 (실제 구현 필요)
    # certificate.generate_pdf()

    certificate.save()

    # 수강 상태 업데이트
    enrollment.status = "certified"
    enrollment.certificate_number = certificate.certificate_number
    enrollment.certificate_issued_at = certificate.issued_at
    enrollment.save(
        update_fields=["status", "certificate_number", "certificate_issued_at"]
    )

    messages.success(request, "수료증이 성공적으로 발급되었습니다.")
    return redirect("learning_view_certificate", certificate_id=certificate.id)


# 수료증 보기
@login_required
def view_certificate(request, certificate_id):
    certificate = get_object_or_404(Certificate, id=certificate_id)

    # 권한 확인 (본인의 수료증만 조회 가능)
    if certificate.user != request.user and not request.user.is_admin:
        raise PermissionDenied

    context = {
        "certificate": certificate,
        "course": certificate.enrollment.course,
    }
    return render(request, "learning/view_certificate.html", context)


# 수료증 PDF 다운로드
@login_required
def download_certificate(request, certificate_id):
    certificate = get_object_or_404(Certificate, id=certificate_id)

    # 권한 확인 (본인의 수료증만 다운로드 가능)
    if certificate.user != request.user and not request.user.is_admin:
        raise PermissionDenied

    # 수료증 PDF 파일이 없으면 생성
    if not certificate.pdf_file:
        certificate.generate_pdf()
        certificate.save()

    # PDF 파일 제공
    try:
        return FileResponse(
            open(certificate.pdf_file.path, "rb"),
            content_type="application/pdf",
            as_attachment=True,
            filename=f"수료증_{certificate.certificate_number}.pdf",
        )
    except Exception as e:
        messages.error(request, f"파일 다운로드 중 오류가 발생했습니다: {str(e)}")
        return redirect("learning_view_certificate", certificate_id=certificate.id)

@login_required
def dashboard_view(request):
    # 관리자가 접근할 경우 관리자 대시보드로 리디렉션
    if request.user.is_admin:
        return redirect('learning:admin_dashboard')
    
    # TODO: 사용자의 등록된 과정 및 진행 상황 가져오기
    # enrolled_courses = Enrollment.objects.filter(user=request.user)
    
    # 임시 데이터
    enrolled_courses = []
    
    context = {
        'enrolled_courses': enrolled_courses,
    }
    return render(request, 'learning/dashboard.html', context)

@login_required
def admin_dashboard_view(request):
    # 일반 사용자가 접근할 경우 일반 대시보드로 리디렉션
    if not request.user.is_admin:
        messages.error(request, '관리자 권한이 필요합니다.')
        return redirect('learning:dashboard')
    
    # TODO: 관리자 통계 및 관리 데이터 가져오기
    # all_courses = Course.objects.all()
    # all_users = User.objects.all()
    
    # 임시 데이터
    all_courses = []
    all_users = []
    
    context = {
        'all_courses': all_courses,
        'all_users': all_users,
    }
    return render(request, 'learning/admin_dashboard.html', context)

