from django.conf import settings
from iamport import Iamport

from datetime import datetime
import uuid
import logging

logger = logging.getLogger("django")


class PortOneClient:
    """
    포트원(구 아임포트) 결제 서비스 연동 클라이언트

    결제 관련 API 호출을 담당하는 클래스입니다.
    """

    def __init__(self):
        # 환경 변수에서 API 키와 시크릿 가져오기
        self.api_key = settings.PORTONE_API_KEY
        self.api_secret = settings.PORTONE_API_SECRET

        # Iamport 객체 초기화
        self.iamport = Iamport(imp_key=self.api_key, imp_secret=self.api_secret)

    def generate_merchant_uid(self):
        """고유한 주문번호 생성

        주문번호는 'ORD-{날짜}-{UUID}' 형식의 고유 주문번호 형태로 생성됩니다.
        """
        return (
            f"ORD-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:12].upper()}"
        )

    def verify_payment(self, imp_uid, merchant_uid, amount):
        """
        포트원 결제 검증 메서드

        Parameters:
        - imp_uid: 포트원 결제 고유 ID
        - merchant_uid: 상품 ID
        - amount: 결제 예상 금액

        Returns:
        - (bool, dict/str): 성공 여부와 결제 정보 또는 오류 메시지
        """
        try:
            logger.info(
                f"Verifying payment: imp_uid={imp_uid}, merchant_uid={merchant_uid}, amount={amount}"
            )

            # 결제 정보 조회
            payment = self.iamport.find(imp_uid=imp_uid, merchant_uid=merchant_uid)

            # 결제 상태 및 금액 검증
            if payment["status"] == "paid" and payment["amount"] == amount:
                logger.info(f"Payment verification successful: {merchant_uid}")
                return True, payment
            else:
                logger.warning(
                    f"Payment verification failed - status or amount mismatch: {payment}"
                )
                return False, "포트원을 통해 검증한 결과, 결제한 내역이 맞지 않습니다."
        except (Iamport.ResponseError, Iamport.HttpError) as e:
            logger.error(f"Payment verification error: {str(e)}")
            return False, str(e)

    def cancel_payment(self, reason, imp_uid=None, merchant_uid=None):
        """
        포트원 결제 취소 메서드

        Parameters:
        - reason: 취소 사유
        - imp_uid: 포트원 결제 고유 ID (imp_uid나 merchant_uid 중 하나는 필수)
        - merchant_uid: 상품 ID

        Returns:
        - (bool, dict/str): 성공 여부와 취소 정보 또는 오류 메시지
        """
        try:
            if imp_uid:
                response = self.iamport.cancel(reason, imp_uid=imp_uid)
            elif merchant_uid:
                response = self.iamport.cancel(reason, merchant_uid=merchant_uid)
            else:
                return False, "imp_uid 또는 merchant_uid가 필요합니다."

            return True, response
        except (Iamport.ResponseError, Iamport.HttpError) as e:
            logger.error(str(e), exc_info=e)
            return False, str(e)

    def refund_payment(self, reason, imp_uid=None, merchant_uid=None, amount=None):
        """
        포트원 결제 환불 메서드 (부분 환불 지원)

        Parameters:
        - reason: 환불 사유
        - imp_uid: 포트원 결제 고유 ID
        - merchant_uid: 상품 ID
        - amount: 환불 금액 (부분 환불 시 필요)

        Returns:
        - (bool, dict/str): 성공 여부와 환불 정보 또는 오류 메시지
        """
        try:
            params = {"reason": reason}

            # 필수 파라미터 설정
            if imp_uid:
                params["imp_uid"] = imp_uid
            elif merchant_uid:
                params["merchant_uid"] = merchant_uid
            else:
                return False, "imp_uid 또는 merchant_uid가 필요합니다."

            # 부분 환불인 경우 금액 전달
            if amount:
                params["amount"] = amount

            response = self.iamport.cancel(**params)
            return True, response
        except (Iamport.ResponseError, Iamport.HttpError) as e:
            logger.error(str(e), exc_info=e)
            return False, str(e)


# 클라이언트 인스턴스 생성
payment_client = PortOneClient()
