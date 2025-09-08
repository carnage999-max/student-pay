import os
import requests
from django.contrib import admin, messages
from django.urls import reverse, path
from django.utils.html import format_html
from decouple import config

from accounts.utils import get_specific_bank_code, resolve_account_number
from .models import Department
from .forms import DepartmentAdminForm
from pay.utils import send_approval_email
from utils.supabase_util import supabase


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    form = DepartmentAdminForm
    list_display = [
        "dept_id",
        "dept_name",
        "email",
        "is_verified",
        "created_at",
        "updated_at",
        "actions_column",
    ]
    list_filter = ["dept_name", "is_verified"]
    search_fields = ["dept_name"]
    exclude = (
        "bank_code",
        "is_verified",
        "user_permissions",
        "groups",
        "is_staff",
        "username",
        "is_active",
    )
    readonly_fields = [
        "is_superuser",
        "logo_url",
        "secretary_signature_url",
        "president_signature_url",
        "account_name",
        "sub_account_code",
        "created_at",
        "updated_at",
    ]

    def actions_column(self, obj):
        if obj.is_verified:
            delete_url = reverse("admin:accounts_department_delete", args=[obj.pk])
            return format_html(
                '<a class="btn btn-danger btn-sm" href="{}">Delete</a>',
                delete_url,
            )
        else:
            approve_url = reverse("admin:approve_department", args=[obj.pk])
            reject_url = reverse("admin:reject_department", args=[obj.pk])

            return format_html(
                '<a class="btn btn-success btn-sm" href="{}">Approve</a> '
                '<a class="btn btn-warning btn-sm" href="{}">Reject</a>',
                approve_url,
                reject_url,
            )

    actions_column.short_description = "Actions"

    # === Custom admin URLs for per-row buttons ===
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<uuid:dept_id>/approve/",
                self.admin_site.admin_view(self.approve_department_view),
                name="approve_department",
            ),
            path(
                "<uuid:dept_id>/reject/",
                self.admin_site.admin_view(self.reject_department_view),
                name="reject_department",
            ),
        ]
        return custom_urls + urls

    # === Shared approval logic (single dept) ===
    def _approve_department(self, request, dept: Department):
        if dept.is_verified:
            return

        # === Step 1: Resolve account details ===
        bank_code = get_specific_bank_code(dept.bank_name)
        account_name = resolve_account_number(dept.account_number, bank_code)

        dept.bank_code = bank_code
        dept.account_name = account_name

        # === Step 2: Create Paystack subaccount ===
        url = "https://api.paystack.co/subaccount"
        headers = {
            "Authorization": f"Bearer {config('PAYSTACK_SECRET_KEY')}",
            "content_type": "application/json",
        }
        data = {
            "business_name": dept.dept_name,
            "settlement_bank": bank_code,
            "account_number": dept.account_number,
            "percentage_charge": 0,
        }
        response = requests.post(url=url, headers=headers, data=data)
        response.raise_for_status()

        sub_account_code = response.json()["data"]["subaccount_code"]
        dept.sub_account_code = sub_account_code

        # === Step 3: Upload files to Supabase ===
        if dept.logo:
            supabase.storage.from_("logo").upload(
                path=dept.logo.name,
                file=dept.logo.read(),
                file_options={"upsert": "true"},
            )
            dept.logo_url = supabase.storage.from_("logo").get_public_url(
                dept.logo.name
            )
            if dept.logo.path and os.path.exists(dept.logo.path):
                os.remove(dept.logo.path)

        if dept.president_signature:
            supabase.storage.from_("signatures").upload(
                path=dept.president_signature.name,
                file=dept.president_signature.read(),
                file_options={"upsert": "true"},
            )
            dept.president_signature_url = supabase.storage.from_(
                "signatures"
            ).get_public_url(dept.president_signature.name)

            if dept.president_signature.path and os.path.exists(
                dept.president_signature.path
            ):
                os.remove(dept.president_signature.path)

        if dept.secretary_signature:
            supabase.storage.from_("signatures").upload(
                path=dept.secretary_signature.name,
                file=dept.secretary_signature.read(),
                file_options={"upsert": "true"},
            )
            dept.secretary_signature_url = supabase.storage.from_(
                "signatures"
            ).get_public_url(dept.secretary_signature.name)

            if dept.secretary_signature.path and os.path.exists(
                dept.secretary_signature.path
            ):
                os.remove(dept.secretary_signature.path)

        # === Step 4: Mark verified ===
        dept.is_verified = True
        dept.save()

        email_context = {
            "dept_name": dept.dept_name,
            "approval_date": dept.updated_at,
            "account_id": dept.dept_id,
            "account_number": dept.account_number,
            "bank_name": dept.bank_name,
            "sub_account_code": dept.sub_account_code,
        }
        send_approval_email(dept.email, email_context)
        messages.success(
            request, f"✅ Department {dept.dept_name} approved successfully."
        )

    # === Per-row button views ===
    def approve_department_view(self, request, dept_id):
        try:
            dept = Department.objects.get(pk=dept_id)
            self._approve_department(request, dept)

        except Exception as e:
            messages.error(request, f"❌ Failed to approve department: {str(e)}")
        return self._redirect_back(request)

    def reject_department_view(self, request, dept_id):
        try:
            dept = Department.objects.get(pk=dept_id)
            dept.is_verified = False
            dept.save()
            messages.warning(request, f"❌ Department {dept.dept_name} rejected.")
        except Exception as e:
            messages.error(request, f"❌ Failed to reject department: {str(e)}")
        return self._redirect_back(request)

    def _redirect_back(self, request):
        from django.shortcuts import redirect

        return redirect(request.META.get("HTTP_REFERER", "admin:index"))

    # === Bulk actions ===
    def approve_departments(self, request, queryset):
        for dept in queryset:
            try:
                self._approve_department(request, dept)
                messages.success(
                    request, f"✅ Department {dept.dept_name} approved successfully."
                )
            except Exception as e:
                messages.error(
                    request, f"❌ Failed to approve {dept.dept_name}: {str(e)}"
                )

    approve_departments.short_description = "Approve selected departments"

    def reject_departments(self, request, queryset):
        updated = queryset.update(is_verified=False)
        messages.warning(request, f"❌ {updated} department(s) rejected.")

    reject_departments.short_description = "Reject selected departments"

    actions = [approve_departments, reject_departments]
