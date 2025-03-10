# accounts/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from allauth.socialaccount.models import SocialAccount
from django.core.files.base import ContentFile
from allauth.account.signals import user_logged_in
import requests
import os

@receiver(post_save, sender=SocialAccount)
def update_user_profile_on_connect(sender, instance, created, **kwargs):
    """소셜 계정이 처음 연결될 때 사용자 프로필 정보 업데이트"""
    if created:  # 새로 생성된 경우에만 실행
        save_social_profile_image(instance)

@receiver(user_logged_in)
def update_user_profile_on_login(sender, request, user, **kwargs):
    """사용자 로그인 시 소셜 계정 이미지 업데이트"""
    # 소셜 계정이 있는지 확인
    social_accounts = user.socialaccount_set.all()
    if social_accounts.exists():
        social_account = social_accounts.first()
        save_social_profile_image(social_account, force_update=True)

def save_social_profile_image(social_account, force_update=False):
    """소셜 계정 프로필 이미지 저장 함수"""
    user = social_account.user
    
    # 이미 프로필 이미지가 있고 강제 업데이트가 아니면 종료
    if user.profile_image and not force_update:
        return
        
    image_url = None
    file_name = None
    
    # 제공자에 따라 다른 처리
    if social_account.provider == 'google':
        if 'picture' in social_account.extra_data:
            image_url = social_account.extra_data['picture']
            file_name = f"profile_google_{user.id}.jpg"
                
    elif social_account.provider == 'kakao':
        if 'properties' in social_account.extra_data and 'profile_image' in social_account.extra_data['properties']:
            image_url = social_account.extra_data['properties']['profile_image']
            file_name = f"profile_kakao_{user.id}.jpg"
    
    if image_url and file_name:
        try:
            response = requests.get(image_url)
            if response.status_code == 200:
                # 기존 이미지가 있으면 삭제
                if user.profile_image and force_update:
                    if os.path.isfile(user.profile_image.path):
                        os.remove(user.profile_image.path)
                
                # 새 이미지 저장
                user.profile_image.save(file_name, ContentFile(response.content), save=True)
                print(f"프로필 이미지 {'업데이트' if force_update else '저장'} 완료: {user.username}")
            else:
                print(f"이미지 다운로드 실패: {response.status_code}")
        except Exception as e:
            print(f"프로필 이미지 저장 오류: {e}")