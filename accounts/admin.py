import os
from django.contrib import admin, messages
from decouple import config
import requests
from accounts.utils import get_specific_bank_code, resolve_account_number
from .models import Department
from .forms import DepartmentAdminForm
from utils.supabase_util import supabase


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    form = DepartmentAdminForm
    list_display = ["dept_name", "email", "is_verified", "created_at", "updated_at"]
    list_filter = ["dept_name"]
    search_fields = ["dept_name"]
    exclude = ("bank_code", "is_verified", 'user_permissions', 'groups', 'is_staff', 'username', 'is_active')
    readonly_fields = ['is_superuser', 'logo_url', 'secretary_signature_url', 'president_signature_url', 'account_name', 'sub_account_code', 'created_at', 'updated_at']
    

    actions = ["approve_department", "reject_department"]

    def approve_department(self, request, queryset):
        for dept in queryset:
            if dept.is_verified:
                continue

            try:
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
                    # cleanup local file
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
                    
                    if dept.president_signature.path and os.path.exists(dept.president_signature.path):
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
                    
                    if dept.secretary_signature.path and os.path.exists(dept.secretary_signature.path):
                        os.remove(dept.secretary_signature.path)

                # === Step 4: Mark verified ===
                dept.is_verified = True
                dept.save()

                messages.success(
                    request, f"✅ Department {dept.dept_name} approved successfully."
                )

            except Exception as e:
                messages.error(
                    request, f"❌ Failed to approve {dept.dept_name}: {str(e)}"
                )

    approve_department.short_description = "Approve selected departments"

    def reject_department(self, request, queryset):
        updated = queryset.update(is_verified=False)
        messages.warning(request, f"❌ {updated} department(s) rejected.")

    reject_department.short_description = "Reject selected departments"

    approve_department.short_description = "Approve selected departments"
