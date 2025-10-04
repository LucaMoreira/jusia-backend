from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone
import logging

from .models import ProcessSearch, ProcessData, ProcessParty, ProcessMovement, UserProcessFavorite
from .serializers import (
    ProcessDataSerializer, ProcessSearchSerializer, ProcessSearchRequestSerializer,
    ProcessSearchByPartySerializer, ProcessSearchByCourtSerializer,
    UserProcessFavoriteSerializer, ProcessSearchResultSerializer
)
from accounts.services.datajud import datajud_service

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def search_process(request):
    """
    Busca um processo pelo número
    """
    serializer = ProcessSearchRequestSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    process_number = serializer.validated_data['process_number']
    user = request.user
    
    try:
        # Registrar a busca
        search_record = ProcessSearch.objects.create(
            user=user,
            process_number=process_number,
            success=False
        )
        
        # Buscar no DataJud
        api_result = datajud_service.search_process_by_number(process_number)
        
        # Processar e salvar os dados
        process_data = _process_api_result(api_result, process_number)
        
        # Marcar busca como sucesso
        search_record.success = True
        search_record.save()
        
        # Serializar resultado
        result_serializer = ProcessDataSerializer(
            process_data, 
            context={'request': request}
        )
        
        return Response({
            'success': True,
            'data': result_serializer.data,
            'message': 'Processo encontrado com sucesso'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Erro ao buscar processo {process_number}: {str(e)}")
        
        # Marcar busca como falha
        if 'search_record' in locals():
            search_record.success = False
            search_record.error_message = str(e)
            search_record.save()
        
        return Response({
            'success': False,
            'message': f'Erro ao buscar processo: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def search_by_party(request):
    """
    Busca processos por parte
    """
    serializer = ProcessSearchByPartySerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    party_name = serializer.validated_data['party_name']
    party_type = serializer.validated_data.get('party_type', '')
    
    try:
        # Buscar no DataJud
        api_result = datajud_service.search_by_party(party_name, party_type)
        
        # Processar resultados
        processes = []
        for process_data in api_result.get('processos', []):
            process = _process_api_result(process_data, process_data.get('numeroProcesso', ''))
            processes.append(process)
        
        # Serializar resultados
        result_serializer = ProcessDataSerializer(
            processes, 
            many=True,
            context={'request': request}
        )
        
        return Response({
            'success': True,
            'data': result_serializer.data,
            'count': len(processes),
            'message': f'Encontrados {len(processes)} processos'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Erro ao buscar processos da parte {party_name}: {str(e)}")
        return Response({
            'success': False,
            'message': f'Erro ao buscar processos: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def search_by_court(request):
    """
    Busca processos por tribunal
    """
    serializer = ProcessSearchByCourtSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    court_code = serializer.validated_data['court_code']
    limit = serializer.validated_data['limit']
    
    try:
        # Buscar no DataJud
        api_result = datajud_service.search_processes_by_court(court_code, limit)
        
        # Processar resultados
        processes = []
        for process_data in api_result.get('processos', []):
            process = _process_api_result(process_data, process_data.get('numeroProcesso', ''))
            processes.append(process)
        
        # Serializar resultados
        result_serializer = ProcessDataSerializer(
            processes, 
            many=True,
            context={'request': request}
        )
        
        return Response({
            'success': True,
            'data': result_serializer.data,
            'count': len(processes),
            'message': f'Encontrados {len(processes)} processos no tribunal {court_code}'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Erro ao buscar processos do tribunal {court_code}: {str(e)}")
        return Response({
            'success': False,
            'message': f'Erro ao buscar processos: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_process_details(request, process_id):
    """
    Obtém detalhes completos de um processo
    """
    try:
        process = get_object_or_404(ProcessData, id=process_id)
        
        # Atualizar dados se necessário
        if _should_update_process(process):
            api_result = datajud_service.get_process_details(process.process_id)
            _update_process_data(process, api_result)
        
        serializer = ProcessDataSerializer(process, context={'request': request})
        
        return Response({
            'success': True,
            'data': serializer.data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Erro ao obter detalhes do processo {process_id}: {str(e)}")
        return Response({
            'success': False,
            'message': f'Erro ao obter detalhes: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_searches(request):
    """
    Obtém histórico de buscas do usuário
    """
    searches = ProcessSearch.objects.filter(user=request.user).order_by('-search_date')[:50]
    serializer = ProcessSearchSerializer(searches, many=True)
    
    return Response({
        'success': True,
        'data': serializer.data
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_to_favorites(request, process_id):
    """
    Adiciona processo aos favoritos
    """
    try:
        process = get_object_or_404(ProcessData, id=process_id)
        
        favorite, created = UserProcessFavorite.objects.get_or_create(
            user=request.user,
            process=process
        )
        
        if created:
            message = 'Processo adicionado aos favoritos'
        else:
            message = 'Processo já estava nos favoritos'
        
        return Response({
            'success': True,
            'message': message,
            'is_favorite': True
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Erro ao adicionar processo {process_id} aos favoritos: {str(e)}")
        return Response({
            'success': False,
            'message': f'Erro ao adicionar aos favoritos: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def remove_from_favorites(request, process_id):
    """
    Remove processo dos favoritos
    """
    try:
        process = get_object_or_404(ProcessData, id=process_id)
        
        deleted = UserProcessFavorite.objects.filter(
            user=request.user,
            process=process
        ).delete()
        
        if deleted[0] > 0:
            message = 'Processo removido dos favoritos'
        else:
            message = 'Processo não estava nos favoritos'
        
        return Response({
            'success': True,
            'message': message,
            'is_favorite': False
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Erro ao remover processo {process_id} dos favoritos: {str(e)}")
        return Response({
            'success': False,
            'message': f'Erro ao remover dos favoritos: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_favorites(request):
    """
    Obtém processos favoritos do usuário
    """
    favorites = UserProcessFavorite.objects.filter(user=request.user).order_by('-created_at')
    serializer = UserProcessFavoriteSerializer(favorites, many=True)
    
    return Response({
        'success': True,
        'data': serializer.data
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_courts_list(request):
    """
    Obtém lista de tribunais disponíveis
    """
    try:
        courts = datajud_service.get_courts_list()
        
        return Response({
            'success': True,
            'data': courts
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Erro ao obter lista de tribunais: {str(e)}")
        return Response({
            'success': False,
            'message': f'Erro ao obter tribunais: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def _process_api_result(api_result, process_number):
    """
    Processa resultado da API e salva no banco de dados
    """
    with transaction.atomic():
        # Criar ou atualizar ProcessData
        process_data, created = ProcessData.objects.get_or_create(
            process_number=process_number,
            defaults={
                'process_id': api_result.get('id', ''),
                'court_code': api_result.get('tribunal', ''),
                'court_name': api_result.get('orgaoJulgador', {}).get('nome', ''),
                'case_class': api_result.get('classe', {}).get('nome', '') if isinstance(api_result.get('classe'), dict) else str(api_result.get('classe', '')),
                'subject': ', '.join([assunto.get('nome', '') for assunto in api_result.get('assuntos', []) if isinstance(assunto, dict)]),
                'value': api_result.get('valor_causa'),
                'distribution_date': _parse_date(api_result.get('dataAjuizamento')),
                'status': api_result.get('status', ''),
                'last_update': timezone.now(),
                'raw_data': api_result
            }
        )
        
        if not created:
            # Atualizar dados existentes
            _update_process_data(process_data, api_result)
        
        # Processar partes
        _process_parties(process_data, api_result.get('partes', []))
        
        # Processar movimentações
        _process_movements(process_data, api_result.get('movimentacoes', []))
        
        return process_data


def _update_process_data(process_data, api_result):
    """
    Atualiza dados de um processo existente
    """
    process_data.process_id = api_result.get('id', process_data.process_id)
    process_data.court_code = api_result.get('tribunal', process_data.court_code)
    process_data.court_name = api_result.get('nome_tribunal', process_data.court_name)
    process_data.case_class = api_result.get('classe', process_data.case_class)
    process_data.subject = api_result.get('assunto', process_data.subject)
    process_data.value = api_result.get('valor_causa', process_data.value)
    process_data.distribution_date = api_result.get('data_distribuicao', process_data.distribution_date)
    process_data.status = api_result.get('status', process_data.status)
    process_data.last_update = timezone.now()
    process_data.raw_data = api_result
    process_data.save()


def _process_parties(process_data, parties_data):
    """
    Processa e salva partes do processo
    """
    # Limpar partes existentes
    ProcessParty.objects.filter(process=process_data).delete()
    
    # Criar novas partes
    for party_data in parties_data:
        ProcessParty.objects.create(
            process=process_data,
            name=party_data.get('nome', ''),
            party_type=party_data.get('tipo', 'outros'),
            document=party_data.get('documento', ''),
            lawyer=party_data.get('advogado', '')
        )


def _process_movements(process_data, movements_data):
    """
    Processa e salva movimentações do processo
    """
    # Limpar movimentações existentes
    ProcessMovement.objects.filter(process=process_data).delete()
    
    # Criar novas movimentações
    for movement_data in movements_data:
        ProcessMovement.objects.create(
            process=process_data,
            date=movement_data.get('data'),
            description=movement_data.get('descricao', ''),
            movement_type=movement_data.get('tipo', '')
        )


def _should_update_process(process):
    """
    Verifica se o processo deve ser atualizado
    """
    if not process.last_update:
        return True
    
    # Atualizar se passou mais de 1 hora
    time_diff = timezone.now() - process.last_update
    return time_diff.total_seconds() > 3600


def _parse_date(date_string):
    """
    Converte string de data ISO 8601 para formato YYYY-MM-DD
    """
    if not date_string:
        return None
    
    try:
        from datetime import datetime
        # Parse ISO 8601 format
        dt = datetime.fromisoformat(date_string.replace('Z', '+00:00'))
        return dt.date()
    except (ValueError, AttributeError):
        return None
