# admin_portal/forms.py
from courses.models import Course, Subject, Lecture, MissionQuestion, VideoLecture
from django import forms

class CourseForm(forms.ModelForm):
    """과정 생성/수정 폼"""
    
    class Meta:
        model = Course
        fields = [
            'title', 'description', 'short_description', 'thumbnail_image', 
            'difficulty_level', 'target_audience', 'estimated_time', 'credit', 
            'price', 'instructor'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'short_description': forms.TextInput(attrs={'class': 'form-control'}),
            'thumbnail_image': forms.FileInput(attrs={'class': 'form-control'}),
            'difficulty_level': forms.Select(attrs={'class': 'form-control'}),
            'target_audience': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'estimated_time': forms.NumberInput(attrs={'class': 'form-control'}),
            'credit': forms.NumberInput(attrs={'class': 'form-control'}),
            'price': forms.NumberInput(attrs={'class': 'form-control'}),
            'instructor': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'title': '과정 제목',
            'description': '상세 설명',
            'short_description': '짧은 설명',
            'thumbnail_image': '썸네일 이미지',
            'difficulty_level': '난이도',
            'target_audience': '대상 수강생',
            'estimated_time': '예상 학습시간(시간)',
            'credit': '학점',
            'price': '가격(원)',
            'instructor': '강사'
        }
        help_texts = {
            'estimated_time': '과정 완료를 위한 총 예상 학습 시간(시간 단위)',
            'credit': '이 과정을 통해 얻을 수 있는 학점',
            'price': '한국 원화 기준 (소수점 없이 정수로 입력)'
        }

class SubjectForm(forms.ModelForm):
    """과목 생성/수정 폼"""
    
    class Meta:
        model = Subject
        fields = ['title', 'description', 'order_index', 'subject_type']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'order_index': forms.NumberInput(attrs={'class': 'form-control'}),
            'subject_type': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'title': '과목 제목',
            'description': '설명',
            'order_index': '순서',
            'subject_type': '과목 유형'
        }
        help_texts = {
            'order_index': '과목이 표시될 순서 (1부터 시작)',
            'subject_type': '일반: 강의로 구성, 중간고사/기말고사: 프로젝트 제출'
        }

class LectureForm(forms.ModelForm):
    """강의 생성/수정 폼 (기본)"""
    
    class Meta:
        model = Lecture
        fields = ['title', 'description', 'order_index']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'order_index': forms.NumberInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'title': '강의 제목',
            'description': '설명',
            'order_index': '순서'
        }
        help_texts = {
            'order_index': '강의가 표시될 순서 (1부터 시작)'
        }

class VideoLectureForm(LectureForm):
    """동영상 강의 생성/수정 폼"""
    
    class Meta(LectureForm.Meta):
        fields = LectureForm.Meta.fields + ['video_url', 'duration']
        widgets = {
            **LectureForm.Meta.widgets,
            'video_url': forms.FileInput(attrs={'class': 'form-control'}),
            'duration': forms.NumberInput(attrs={'class': 'form-control'}),
        }
        labels = {
            **LectureForm.Meta.labels,
            'video_url': '동영상 파일',
            'duration': '재생 시간(분)'
        }
        help_texts = {
            **LectureForm.Meta.help_texts,
            'video_url': 'MP4 파일 (.mp4)',
            'duration': '동영상 재생 시간(분)'
        }

class MissionQuestionForm(forms.ModelForm):
    """미션 문제 생성/수정 폼"""
    
    class Meta:
        model = MissionQuestion
        fields = [
            'question_text', 'option1', 'option2', 'option3', 'option4', 'option5',
            'correct_answer', 'order_index'
        ]
        widgets = {
            'question_text': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'option1': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'option2': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'option3': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'option4': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'option5': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'correct_answer': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 5}),
            'order_index': forms.NumberInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'question_text': '문제',
            'option1': '선택지 1',
            'option2': '선택지 2',
            'option3': '선택지 3',
            'option4': '선택지 4',
            'option5': '선택지 5',
            'correct_answer': '정답 번호',
            'order_index': '순서'
        }
        help_texts = {
            'correct_answer': '정답인 선택지 번호 (1~5)',
            'order_index': '문제가 표시될 순서'
        }