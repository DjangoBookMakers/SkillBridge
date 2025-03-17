from django import forms
from .models import ProjectSubmission


class ProjectSubmissionForm(forms.ModelForm):
    """중간/기말고사 프로젝트 제출 폼"""

    class Meta:
        model = ProjectSubmission
        fields = ["project_file"]
        widgets = {
            "project_file": forms.FileInput(
                attrs={
                    "accept": ".zip,.rar,.7z,.pdf",
                }
            ),
        }
        labels = {"project_file": "프로젝트 파일"}
        help_texts = {
            "project_file": "프로젝트 파일을 압축(ZIP, RAR, 7Z)하거나 PDF 형식으로 제출해주세요."
        }

    def clean_project_file(self):
        """파일 유효성 검사"""
        file = self.cleaned_data.get("project_file", False)
        if file:
            # 파일 크기 제한 (10MB)
            if file.size > 10 * 1024 * 1024:
                raise forms.ValidationError("파일 크기는 10MB를 초과할 수 없습니다.")

            # 파일 확장자 확인
            ext = file.name.split(".")[-1].lower()
            if ext not in ["zip", "rar", "7z", "pdf"]:
                raise forms.ValidationError(
                    "ZIP, RAR, 7Z, PDF 형식의 파일만 허용됩니다."
                )

        return file


class MissionAnswerForm(forms.Form):
    """미션(쪽지시험) 답안 제출 폼"""

    def __init__(self, *args, questions=None, **kwargs):
        super().__init__(*args, **kwargs)

        if questions:
            for question in questions:
                field_name = f"question_{question.id}"
                choices = [
                    (1, question.option1),
                    (2, question.option2),
                    (3, question.option3),
                    (4, question.option4),
                    (5, question.option5),
                ]
                self.fields[field_name] = forms.ChoiceField(
                    choices=choices,
                    widget=forms.RadioSelect(),
                    label=question.question_text,
                    required=True,
                )

    def get_answers(self):
        """사용자 답안을 딕셔너리 형태로 반환"""
        answers = {}
        for name, value in self.cleaned_data.items():
            if name.startswith("question_"):
                question_id = name.replace("question_", "")
                answers[question_id] = value
        return answers
