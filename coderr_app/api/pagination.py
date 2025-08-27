from rest_framework.pagination import PageNumberPagination  # Basis-Pagination-Klasse

class OfferPageNumberPagination(PageNumberPagination):
    # Standard-Seitengröße (Fallback, falls kein page_size-Query-Param kommt)
    page_size = 10  # sinnvoller Default; Frontend kann 'page_size' überschreiben

    # Query-Param, um Seitengröße zur Laufzeit zu setzen (vom Frontend steuerbar)
    page_size_query_param = 'page_size'  # wie in der Anforderung
    max_page_size = 100  # Sicherheitslimit gegen zu große Seiten