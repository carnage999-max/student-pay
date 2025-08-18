from django.contrib import admin
from .models import Department


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ["email", "dept_name"]
    list_filter = ["dept_name"]
    search_fields = ["dept_name"]
