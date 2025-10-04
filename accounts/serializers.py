from rest_framework import serializers
from .models import CustomUser
from django.contrib.auth.models import Group, Permission

class PermissionSerializer(serializers.ModelSerializer):
    content_type = serializers.CharField(source='content_type.model', read_only=True)

    class Meta:
        model = Permission
        fields = ['id', 'name', 'codename', 'content_type']

class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ['id', 'name']

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)

    # Para leitura (GET)
    groups = GroupSerializer(many=True, read_only=True)
    user_permissions = PermissionSerializer(many=True, read_only=True)

    # Para escrita (POST/PUT)
    group_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Group.objects.all(), write_only=True, required=False
    )
    permission_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Permission.objects.all(), write_only=True, required=False
    )

    class Meta:
        model = CustomUser
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'password', 'is_active', 'is_staff', 'is_superuser', 'is_tester',
            'date_joined',  # adicionar data de cadastro
            'groups', 'user_permissions',  # leitura
            'group_ids', 'permission_ids'  # escrita
        ]
        read_only_fields = ['id', 'date_joined']

    def create(self, validated_data):
        print("Serializer create() called with data:", validated_data)
        try:
            password = validated_data.pop('password', None)
            groups = validated_data.pop('group_ids', [])
            permissions = validated_data.pop('permission_ids', [])

            print("Creating user with manager...")
            # Use the custom manager to create the user
            user = CustomUser.objects.create_user(
                email=validated_data.get('email'),
                password=password,
                username=validated_data.get('username'),
                first_name=validated_data.get('first_name', ''),
                last_name=validated_data.get('last_name', ''),
                is_active=validated_data.get('is_active', True),
                is_staff=validated_data.get('is_staff', False),
                is_superuser=validated_data.get('is_superuser', False),
                is_tester=validated_data.get('is_tester', False),
            )
            print("User created with manager:", user)

            user.groups.set(groups)
            user.user_permissions.set(permissions)
            print("Groups and permissions set")
            
            print("Returning user:", user)
            return user
        except Exception as e:
            print(f"Error in serializer create(): {e}")
            raise e

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        groups = validated_data.pop('group_ids', None)
        permissions = validated_data.pop('permission_ids', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if password:
            instance.set_password(password)

        instance.save()

        if groups is not None:
            instance.groups.set(groups)
        if permissions is not None:
            instance.user_permissions.set(permissions)

        return instance