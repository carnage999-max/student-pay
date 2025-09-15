import os
import requests
from django.contrib import admin, messages
from django.urls import reverse, path
from django.utils.html import format_html
from decouple import config

from accounts.utils import get_specific_bank_code, resolve_account_number
from .models import Department
from .forms import DepartmentAdminForm
from pay.utils import send_approval_email, send_rejection_email
from utils.supabase_util import upload_to_supabase


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    form = DepartmentAdminForm
    list_display = [
        "id",
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
                "<uuid:id>/approve/",
                self.admin_site.admin_view(self.approve_department_view),
                name="approve_department",
            ),
            path(
                "<uuid:id>/reject/",
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
        try:
            bank_code = get_specific_bank_code(dept.bank_name)

            dept.bank_code = bank_code
        except requests.HTTPError as e:
            messages.warning(
                request,
                f"⚠️ Account verification failed for {dept.dept_name}: {str(e)}. "
                "Department approved but requires manual bank verification.",
            )

        # === Step 2: Create Paystack subaccount ===
        try:
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
            account_name = response.json()["data"]["account_name"]
            dept.account_name = account_name
            dept.sub_account_code = sub_account_code
        except requests.HTTPError as e:
            if response.status_code == 400:
                raise Exception(
                    f"Paystack subaccount creation failed for {dept.dept_name}: {response.json().get('message', 'Unknown error')}"
                )

        # === Step 3: Upload files to Supabase ===
        if dept.logo:
            dept.logo_url = upload_to_supabase("logo", dept.logo.name, dept.logo.read())
            if dept.logo.path and os.path.exists(dept.logo.path):
                os.remove(dept.logo.path)

        if dept.president_signature:
            dept.president_signature_url = upload_to_supabase(
                "signatures",
                dept.president_signature.name,
                dept.president_signature.read(),
            )
            if dept.president_signature.path and os.path.exists(
                dept.president_signature.path
            ):
                os.remove(dept.president_signature.path)

        if dept.secretary_signature:
            dept.secretary_signature_url = upload_to_supabase(
                "signatures",
                dept.secretary_signature.name,
                dept.secretary_signature.read(),
            )
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
            "dept_id": dept.id,
            "account_number": dept.account_number,
            "bank_name": dept.bank_name,
        }
        send_approval_email(dept.email, email_context)
        messages.success(
            request, f"✅ Department {dept.dept_name} approved successfully."
        )

    # === Per-row button views ===
    def approve_department_view(self, request, id):
        try:
            dept = Department.objects.get(pk=id)
            self._approve_department(request, dept)
            messages.success(
                request, f"✅ Department {dept.dept_name} approved successfully."
            )

        except Exception as e:
            messages.error(request, f"❌ Failed to approve department: {str(e)}")
        return self._redirect_back(request)

    def reject_department_view(self, request, id):
        try:
            dept = Department.objects.get(pk=id)
            dept.is_verified = False
            dept.save()

            email_context = {
                "dept_name": dept.dept_name,
                "review_date": dept.updated_at,
                "dept_id": dept.id,
            }
            send_rejection_email(dept.email, email_context)
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

    def save_model(self, request, obj, form, change):
        """
        Override save_model so that if a verified department updates its logo or signatures,
        we sync the new file(s) to Supabase and clean up the old ones.
        """
        if change and obj.is_verified:
            # track old versions
            old_obj = Department.objects.get(pk=obj.pk)

            file_fields = ["logo", "president_signature", "secretary_signature"]
            for field in file_fields:
                old_file = getattr(old_obj, field)
                new_file = getattr(obj, field)

                # Only process if a new file is uploaded
                if new_file and old_file != new_file:
                    # upload new file
                    supabase_url = upload_to_supabase(
                        "signatures" if field != "logo" else "logo",
                        new_file.name,
                        new_file.read(),
                    )
                    setattr(obj, f"{field}_url", supabase_url)

                    # delete old file from Supabase if it existed
                    # if old_file:
                    #     delete_from_supabase(old_file)

        super().save_model(request, obj, form, change)
