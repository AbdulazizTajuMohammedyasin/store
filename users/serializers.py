from djoser.serializers import UserCreatePasswordRetypeSerializer as Base
from djoser.serializers import UserSerializer as BaseUserSerializer
from rest_framework import serializers

class UserCreateSerializer(Base):
    class Meta(Base.Meta):
        fields = ['id',
            'email',
            'username',
            'password',
            'first_name',
            'last_name']
        
    def validate_email(self, value):
        if self.Meta.model.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                "A user with this email already exists."
            )

        return value

class UserSerializer(BaseUserSerializer):
    class Meta(BaseUserSerializer.Meta):
        fields = BaseUserSerializer.Meta.fields + ('is_staff',)