# The `CustomResultsSetPagination` class defines pagination parameters for views in a Django REST
# framework.
from rest_framework.pagination import PageNumberPagination


# The `CustomResultsSetPagination` class sets pagination parameters for views.
class CustomResultsSetPagination(PageNumberPagination):
    page_size = 5
    page_size_query_param = "page_size"
    max_page_size = 1000
