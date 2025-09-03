"""Provides pagination methods for usage within whole project"""
from rest_framework.pagination import PageNumberPagination

class OfferPageNumberPagination(PageNumberPagination):
    """Paginate offers with a default of 10 per page and optional page-size query"""
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100
    

class ReviewPageNumberPagination(PageNumberPagination):
    """Paginate reviews with a default of 10 per page and optional page-size query"""
    page_size = 10                  
    page_size_query_param = 'page_size'
    max_page_size = 100                