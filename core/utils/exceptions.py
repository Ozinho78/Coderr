from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status


def exception_handler_status500(exc, context):
    """Calls DRF-Default-Handler and returns a custom response for exceptions"""
    response = exception_handler(exc, context)

    if response is None:
        error_message = {"error": "Interner Serverfehler"}
        return Response(error_message, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return response