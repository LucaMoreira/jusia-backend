import logging
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db import transaction

from .models import ChatSession, ChatMessage, ChatContext
from .serializers import (
    ChatSessionSerializer, 
    ChatSessionCreateSerializer,
    ChatMessageSerializer,
    ChatResponseSerializer,
    ChatContextSerializer
)
from .services import GeminiService
from processes.models import ProcessData

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_chat_sessions(request):
    """
    Lista todas as sessões de chat do usuário
    """
    try:
        sessions = ChatSession.objects.filter(user=request.user, is_active=True)
        serializer = ChatSessionSerializer(sessions, many=True)
        
        return Response({
            'success': True,
            'data': serializer.data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Erro ao listar sessões de chat: {str(e)}")
        return Response({
            'success': False,
            'message': 'Erro ao carregar sessões de chat'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_chat_session(request):
    """
    Cria uma nova sessão de chat
    """
    try:
        serializer = ChatSessionCreateSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            session = serializer.save()
            
            # Criar contexto se houver processo associado
            if session.process:
                ChatContext.objects.create(session=session)
            
            response_serializer = ChatSessionSerializer(session)
            
            return Response({
                'success': True,
                'data': response_serializer.data
            }, status=status.HTTP_201_CREATED)
        
        return Response({
            'success': False,
            'message': 'Dados inválidos',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
        
    except Exception as e:
        logger.error(f"Erro ao criar sessão de chat: {str(e)}")
        return Response({
            'success': False,
            'message': 'Erro ao criar sessão de chat'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_chat_session(request, session_id):
    """
    Obtém uma sessão de chat específica com mensagens
    """
    try:
        session = get_object_or_404(ChatSession, id=session_id, user=request.user)
        serializer = ChatSessionSerializer(session)
        
        return Response({
            'success': True,
            'data': serializer.data
        }, status=status.HTTP_200_OK)
        
    except ChatSession.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Sessão de chat não encontrada'
        }, status=status.HTTP_404_NOT_FOUND)
        
    except Exception as e:
        logger.error(f"Erro ao obter sessão de chat {session_id}: {str(e)}")
        return Response({
            'success': False,
            'message': 'Erro ao carregar sessão de chat'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_message(request, session_id):
    """
    Envia uma mensagem em uma sessão de chat
    """
    try:
        session = get_object_or_404(ChatSession, id=session_id, user=request.user)
        user_message = request.data.get('message', '').strip()
        
        if not user_message:
            return Response({
                'success': False,
                'message': 'Mensagem não pode estar vazia'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Salvar mensagem do usuário
        user_msg = ChatMessage.objects.create(
            session=session,
            message_type='user',
            content=user_message
        )
        
        # Obter histórico de mensagens
        chat_history = list(session.messages.values('message_type', 'content').order_by('created_at'))
        
        # Obter contexto do processo se disponível
        process_context = None
        if session.process:
            process_context = {
                'process_number': session.process.process_number,
                'court_name': session.process.court_name,
                'case_class': session.process.case_class,
                'subject': session.process.subject,
                'parties': list(session.process.parties.values('name', 'type', 'role')),
                'movements': list(session.process.movements.values('description', 'date', 'movement_type').order_by('-date')[:10])
            }
        
        # Gerar resposta da IA
        try:
            gemini_service = GeminiService()
            ai_response = gemini_service.generate_response(
                user_message=user_message,
                chat_history=chat_history,
                process_context=process_context
            )
            
            # Salvar resposta da IA
            ai_msg = ChatMessage.objects.create(
                session=session,
                message_type='assistant',
                content=ai_response['content'],
                metadata={
                    'tokens_used': ai_response.get('tokens_used', 0),
                    'model_used': ai_response.get('model_used', ''),
                    'success': ai_response.get('success', True)
                }
            )
            
            # Atualizar contexto se necessário
            if session.process and ai_response.get('success', True):
                _update_chat_context(session, ai_response['content'])
            
            # Gerar sugestões
            suggestions = gemini_service.generate_suggestions(user_message, process_context)
            
            return Response({
                'success': True,
                'message': ai_response['content'],
                'message_id': ai_msg.id,
                'suggestions': suggestions,
                'context_updated': bool(session.process)
            }, status=status.HTTP_200_OK)
            
        except Exception as ai_error:
            logger.error(f"Erro na IA: {str(ai_error)}")
            
            # Salvar mensagem de erro
            error_msg = ChatMessage.objects.create(
                session=session,
                message_type='assistant',
                content="Desculpe, ocorreu um erro ao processar sua mensagem. Tente novamente.",
                metadata={'error': str(ai_error), 'success': False}
            )
            
            return Response({
                'success': False,
                'message': 'Erro ao processar mensagem com IA',
                'message_id': error_msg.id
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    except Exception as e:
        logger.error(f"Erro ao enviar mensagem: {str(e)}")
        return Response({
            'success': False,
            'message': 'Erro ao enviar mensagem'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def analyze_process(request, process_id):
    """
    Analisa um processo específico com IA
    """
    try:
        process = get_object_or_404(ProcessData, id=process_id)
        
        # Verificar se o usuário tem acesso ao processo (se necessário)
        # Aqui você pode adicionar lógica de permissão específica
        
        process_data = {
            'process_number': process.process_number,
            'court_name': process.court_name,
            'case_class': process.case_class,
            'subject': process.subject,
            'status': process.status,
            'value': process.value,
            'distribution_date': process.distribution_date,
            'parties': list(process.parties.values('name', 'party_type', 'document')),
            'movements': list(process.movements.values('description', 'date', 'movement_type').order_by('-date'))
        }
        
        gemini_service = GeminiService()
        analysis = gemini_service.analyze_process(process_data)
        
        return Response({
            'success': analysis.get('success', True),
            'analysis': analysis.get('analysis', ''),
            'process_id': process_id
        }, status=status.HTTP_200_OK)
        
    except ProcessData.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Processo não encontrado'
        }, status=status.HTTP_404_NOT_FOUND)
        
    except Exception as e:
        logger.error(f"Erro ao analisar processo {process_id}: {str(e)}")
        return Response({
            'success': False,
            'message': 'Erro ao analisar processo'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_chat_session(request, session_id):
    """
    Deleta uma sessão de chat (soft delete)
    """
    try:
        session = get_object_or_404(ChatSession, id=session_id, user=request.user)
        session.is_active = False
        session.save()
        
        return Response({
            'success': True,
            'message': 'Sessão de chat excluída com sucesso'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Erro ao excluir sessão de chat {session_id}: {str(e)}")
        return Response({
            'success': False,
            'message': 'Erro ao excluir sessão de chat'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def _update_chat_context(session: ChatSession, ai_response: str):
    """
    Atualiza o contexto do chat com base na resposta da IA
    """
    try:
        context, created = ChatContext.objects.get_or_create(session=session)
        
        # Aqui você pode implementar lógica para extrair insights da resposta da IA
        # e atualizar o contexto do processo
        
        # Por enquanto, apenas atualizamos o timestamp
        context.save()
        
    except Exception as e:
        logger.error(f"Erro ao atualizar contexto do chat: {str(e)}")