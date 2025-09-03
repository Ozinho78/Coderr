"""Provides custom exception handling for project"""
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger(__name__)

def exception_handler_status500(exc, context):
    """Custom DRF exceptions handling and HTTP codes for predictable API responses"""
    response = exception_handler(exc, context)

    if response is None:
        logger.error('Unexpected error: %s', str(exc))
        return Response({'detail': 'Internal Server Error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return response