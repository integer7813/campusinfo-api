from slowapi import Limiter
from slowapi.util import get_remote_address

# IP 주소를 기준으로 제한을 거는 리미터 객체를 생성합니다.
# limiter = Limiter(key_func=get_remote_address)

# 리미터를 해제합니다. - 테스트 목적.
limiter = Limiter(key_func=get_remote_address, enabled=False)