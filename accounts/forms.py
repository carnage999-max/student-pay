from django import forms
from .models import Department
from .utils import get_banks, get_specific_bank_code


class DepartmentAdminForm(forms.ModelForm):
    bank_name = forms.ChoiceField(choices=[])

    class Meta:
        model = Department
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Fetch supported banks dynamically
        banks = get_banks()
        self.fields["bank_name"].choices = [(b["name"], b["name"]) for b in banks]

    def clean(self):
        cleaned_data = super().clean()
        bank_name = cleaned_data.get("bank_name")
        account_number = cleaned_data.get("account_number")

        if bank_name and account_number:
            bank_code = get_specific_bank_code(bank_name)
            cleaned_data["bank_code"] = bank_code
        return cleaned_data
