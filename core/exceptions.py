# core/exceptions.py
from rest_framework.views import exception_handler

def custom_exception_handler(exc, context):
    # 1) DRF 기본 핸들러 호출
    response = exception_handler(exc, context)
    if response is None or not isinstance(response.data, dict):
        return response

    # 2) response.data 딕셔너리의 모든 값을 모아서, 첫 번째 메시지만 뽑아냄
    messages = []
    for val in response.data.values():
        if isinstance(val, list):
            messages += val
        else:
            messages.append(val)
    # 3) 첫 번째 메시지로만 재구성
    first = messages[0] if messages else str(exc)
    response.data = {"error": first}
    return response
