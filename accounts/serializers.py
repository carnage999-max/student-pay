from rest_framework.serializers import ModelSerializer, Serializer, EmailField, CharField
from .models import Department


class RegisterDepartmentSerializer(ModelSerializer):
    class Meta:
        model = Department
        fields = ['email', 'password', 'dept_name']
        extra_kwargs = {'password':{'write_only': True}}
    
    def create(self, validated_data):
        password = validated_data.pop('password')
        user = Department.objects.create(email=validated_data['email'], dept_name=validated_data['dept_name'])
        user.set_password(password)
        user.save()
        return user
        
class LoginSerializer(Serializer):
    email = EmailField()
    password = CharField(write_only=True)
    
class DepartmentSerializer(ModelSerializer):
    class Meta:
        model = Department
        fields = ['email', 'dept_name', 'account_number', 'bank_name']
        read_only_fields = ['email']