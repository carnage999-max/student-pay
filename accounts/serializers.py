from rest_framework.serializers import ModelSerializer, Serializer, EmailField, CharField, ImageField
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
    logo = ImageField(write_only=True, allow_empty_file=True, required=False)
    president_signature = ImageField(write_only=True, allow_empty_file=True, required=False)
    secretary_signature = ImageField(write_only=True, allow_empty_file=True, required=False)
    class Meta:
        model = Department
        fields = ['id', 'email', 'dept_name', 'account_number', 'bank_name', 'logo', 'logo_url', 'president_signature_url', 'president_signature', 'secretary_signature_url', 'secretary_signature']
        read_only_fields = ['id', 'email', 'logo_url', 'president_signature_url', 'secretary_signature_url']