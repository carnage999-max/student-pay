import factory
from accounts.models import Department
from faker import Faker

fake = Faker()

class DepartmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Department
    email = fake.email()
    dept_name = fake.administrative_unit()
    password = fake.password(length=10, special_chars=True, upper_case=True, digits=True)
    
