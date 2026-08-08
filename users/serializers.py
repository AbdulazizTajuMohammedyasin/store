from djoser.serializers import UserCreatePasswordRetypeSerializer as Base
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