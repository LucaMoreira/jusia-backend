from rest_framework import serializers
from .models import (
    ProcessSearch, ProcessData, ProcessParty, 
    ProcessMovement, UserProcessFavorite, ProcessNotification
)


class ProcessPartySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcessParty
        fields = ['name', 'party_type', 'document', 'lawyer']


class ProcessMovementSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcessMovement
        fields = ['date', 'description', 'movement_type']


class ProcessDataSerializer(serializers.ModelSerializer):
    parties = ProcessPartySerializer(many=True, read_only=True)
    movements = ProcessMovementSerializer(many=True, read_only=True)
    is_favorite = serializers.SerializerMethodField()
    
    class Meta:
        model = ProcessData
        fields = [
            'id', 'process_number', 'process_id', 'court_code', 'court_name',
            'case_class', 'subject', 'value', 'distribution_date', 'status',
            'last_update', 'parties', 'movements', 'is_favorite', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_is_favorite(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return UserProcessFavorite.objects.filter(
                user=request.user, 
                process=obj
            ).exists()
        return False


class ProcessSearchSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcessSearch
        fields = ['process_number', 'search_date', 'success', 'error_message']
        read_only_fields = ['search_date']


class ProcessSearchRequestSerializer(serializers.Serializer):
    process_number = serializers.CharField(
        max_length=25,
        help_text="Número do processo no formato: NNNNNNN-DD.AAAA.J.TR.OOOO ou apenas 20 dígitos"
    )
    
    def validate_process_number(self, value):
        import re
        # Aceitar tanto formato com pontos e hífens quanto apenas dígitos
        if not re.match(r'^(\d{7}-\d{2}\.\d{4}\.\d{1}\.\d{2}\.\d{4}|\d{20})$', value):
            raise serializers.ValidationError(
                "Número do processo deve estar no formato: NNNNNNN-DD.AAAA.J.TR.OOOO ou apenas 20 dígitos"
            )
        return value


class ProcessSearchByPartySerializer(serializers.Serializer):
    party_name = serializers.CharField(max_length=500)
    party_type = serializers.ChoiceField(
        choices=ProcessParty.PARTY_TYPES,
        required=False,
        allow_blank=True
    )


class ProcessSearchByCourtSerializer(serializers.Serializer):
    court_code = serializers.CharField(max_length=10)
    limit = serializers.IntegerField(min_value=1, max_value=1000, default=100)


class UserProcessFavoriteSerializer(serializers.ModelSerializer):
    process = ProcessDataSerializer(read_only=True)
    
    class Meta:
        model = UserProcessFavorite
        fields = ['id', 'process', 'created_at']
        read_only_fields = ['id', 'created_at']


class ProcessNotificationSerializer(serializers.ModelSerializer):
    process = ProcessDataSerializer(read_only=True)
    
    class Meta:
        model = ProcessNotification
        fields = [
            'id', 'process', 'notification_type', 'title', 
            'message', 'is_read', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class ProcessSearchResultSerializer(serializers.Serializer):
    """
    Serializer para resultados de busca de processos
    """
    process_number = serializers.CharField()
    court_name = serializers.CharField()
    case_class = serializers.CharField()
    subject = serializers.CharField()
    status = serializers.CharField()
    value = serializers.DecimalField(max_digits=15, decimal_places=2, allow_null=True)
    distribution_date = serializers.DateField(allow_null=True)
    last_update = serializers.DateTimeField(allow_null=True)
    parties = ProcessPartySerializer(many=True)
    movements = ProcessMovementSerializer(many=True)
    is_favorite = serializers.BooleanField(default=False)
