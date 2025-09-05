from rest_framework.views import exception_handler
from rest_framework.exceptions import PermissionDenied


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if isinstance(exc, PermissionDenied):
        response_data = {
            "error_message": exc.detail.get('verification_error', 'Permission Denied')
        }
    response.data = response_data
    return response
