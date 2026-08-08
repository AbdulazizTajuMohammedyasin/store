from djoser.serializers import UserCreatePasswordRetypeSerializer as Base


class UserCreateSerializer(Base):
    class Meta(Base.Meta):
        fields = ['id',
            'email',
            'username',
            'password',
            'first_name',
            'last_name']