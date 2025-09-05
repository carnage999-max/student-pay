import factory
from accounts.models import Department

class DepartmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Department
    email = factory.Faker('email')
    dept_name = factory.Faker('company')
    password = factory.PostGenerationMethodCall('set_password', 'Testpass123')
    
