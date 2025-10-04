from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from unittest.mock import patch, MagicMock
import json

from .models import ChatSession, ChatMessage, ChatContext
from processes.models import ProcessData, ProcessParty, ProcessMovement

User = get_user_model()


class ChatModelTests(TestCase):
    """Testes para os modelos do chat"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        
        self.process = ProcessData.objects.create(
            process_number='12345678901234567890',
            court_name='Tribunal de Teste',
            case_class='Ação de Cobrança',
            subject='Teste de assunto',
            status='Ativo'
        )
    
    def test_chat_session_creation(self):
        """Testa criação de sessão de chat"""
        session = ChatSession.objects.create(
            user=self.user,
            title='Teste de Chat',
            process=self.process
        )
        
        self.assertEqual(session.user, self.user)
        self.assertEqual(session.title, 'Teste de Chat')
        self.assertEqual(session.process, self.process)
        self.assertTrue(session.is_active)
    
    def test_chat_message_creation(self):
        """Testa criação de mensagem de chat"""
        session = ChatSession.objects.create(
            user=self.user,
            title='Teste de Chat'
        )
        
        message = ChatMessage.objects.create(
            session=session,
            message_type='user',
            content='Olá, como posso ajudar?'
        )
        
        self.assertEqual(message.session, session)
        self.assertEqual(message.message_type, 'user')
        self.assertEqual(message.content, 'Olá, como posso ajudar?')
    
    def test_chat_context_creation(self):
        """Testa criação de contexto de chat"""
        session = ChatSession.objects.create(
            user=self.user,
            title='Teste de Chat',
            process=self.process
        )
        
        context = ChatContext.objects.create(
            session=session,
            process_summary='Resumo do processo',
            legal_analysis='Análise jurídica',
            key_points=['Ponto 1', 'Ponto 2']
        )
        
        self.assertEqual(context.session, session)
        self.assertEqual(context.process_summary, 'Resumo do processo')
        self.assertEqual(len(context.key_points), 2)


@override_settings(GEMINI_API_KEY='test-key')
class ChatAPITests(APITestCase):
    """Testes para as APIs do chat"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        
        self.process = ProcessData.objects.create(
            process_number='12345678901234567890',
            court_name='Tribunal de Teste',
            case_class='Ação de Cobrança',
            subject='Teste de assunto',
            status='Ativo'
        )
        
        # Criar token JWT
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
    
    def test_get_chat_sessions(self):
        """Testa listagem de sessões de chat"""
        # Criar algumas sessões
        ChatSession.objects.create(
            user=self.user,
            title='Sessão 1'
        )
        ChatSession.objects.create(
            user=self.user,
            title='Sessão 2',
            process=self.process
        )
        
        response = self.client.get('/chat/sessions/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(len(response.data['data']), 2)
    
    def test_create_chat_session(self):
        """Testa criação de nova sessão de chat"""
        data = {
            'title': 'Nova Sessão',
            'process': self.process.id
        }
        
        response = self.client.post('/chat/sessions/create/', data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['title'], 'Nova Sessão')
        self.assertEqual(response.data['data']['process']['id'], self.process.id)
    
    def test_create_chat_session_without_process(self):
        """Testa criação de sessão sem processo"""
        data = {
            'title': 'Sessão Geral'
        }
        
        response = self.client.post('/chat/sessions/create/', data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['title'], 'Sessão Geral')
        self.assertIsNone(response.data['data']['process'])
    
    def test_get_chat_session_detail(self):
        """Testa obtenção de detalhes de sessão"""
        session = ChatSession.objects.create(
            user=self.user,
            title='Sessão de Teste'
        )
        
        # Criar algumas mensagens
        ChatMessage.objects.create(
            session=session,
            message_type='user',
            content='Mensagem do usuário'
        )
        ChatMessage.objects.create(
            session=session,
            message_type='assistant',
            content='Resposta da IA'
        )
        
        response = self.client.get(f'/chat/sessions/{session.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(len(response.data['data']['messages']), 2)
    
    @patch('chat.views.GeminiService')
    def test_send_message(self, mock_gemini_service):
        """Testa envio de mensagem"""
        # Configurar mock do Gemini
        mock_service = MagicMock()
        mock_service.generate_response.return_value = {
            'content': 'Resposta da IA',
            'tokens_used': 100,
            'model_used': 'gemini-1.5-flash',
            'success': True
        }
        mock_gemini_service.return_value = mock_service
        
        session = ChatSession.objects.create(
            user=self.user,
            title='Sessão de Teste'
        )
        
        data = {
            'message': 'Olá, como posso ajudar?'
        }
        
        response = self.client.post(f'/chat/sessions/{session.id}/send/', data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['message'], 'Resposta da IA')
        
        # Verificar se a mensagem foi salva
        self.assertEqual(session.messages.count(), 2)  # 1 do usuário + 1 da IA
    
    def test_send_message_empty(self):
        """Testa envio de mensagem vazia"""
        session = ChatSession.objects.create(
            user=self.user,
            title='Sessão de Teste'
        )
        
        data = {
            'message': ''
        }
        
        response = self.client.post(f'/chat/sessions/{session.id}/send/', data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
    
    def test_delete_chat_session(self):
        """Testa exclusão de sessão de chat"""
        session = ChatSession.objects.create(
            user=self.user,
            title='Sessão para Excluir'
        )
        
        response = self.client.delete(f'/chat/sessions/{session.id}/delete/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Verificar se a sessão foi marcada como inativa
        session.refresh_from_db()
        self.assertFalse(session.is_active)
    
    def test_unauthorized_access(self):
        """Testa acesso não autorizado"""
        self.client.credentials()  # Remover autenticação
        
        response = self.client.get('/chat/sessions/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_access_other_user_session(self):
        """Testa acesso a sessão de outro usuário"""
        other_user = User.objects.create_user(
            email='other@example.com',
            password='testpass123'
        )
        
        other_session = ChatSession.objects.create(
            user=other_user,
            title='Sessão de Outro Usuário'
        )
        
        response = self.client.get(f'/chat/sessions/{other_session.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class ProcessAnalysisTests(APITestCase):
    """Testes para análise de processos"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        
        self.process = ProcessData.objects.create(
            process_number='12345678901234567890',
            court_name='Tribunal de Teste',
            case_class='Ação de Cobrança',
            subject='Teste de assunto',
            status='Ativo',
            value=1000.00
        )
        
        # Criar partes do processo
        ProcessParty.objects.create(
            process=self.process,
            name='João Silva',
            party_type='autor',
            document='12345678901'
        )
        
        ProcessParty.objects.create(
            process=self.process,
            name='Maria Santos',
            party_type='reu',
            document='98765432109'
        )
        
        # Criar movimentações
        from django.utils import timezone
        ProcessMovement.objects.create(
            process=self.process,
            date=timezone.now().date(),
            description='Distribuição',
            movement_type='Distribuição'
        )
        
        # Criar token JWT
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
    
    @patch('chat.views.GeminiService')
    def test_analyze_process(self, mock_gemini_service):
        """Testa análise de processo com IA"""
        # Configurar mock do Gemini
        mock_service = MagicMock()
        mock_service.analyze_process.return_value = {
            'analysis': 'Análise jurídica detalhada do processo',
            'success': True
        }
        mock_gemini_service.return_value = mock_service
        
        response = self.client.post(f'/chat/analyze/process/{self.process.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('Análise jurídica', response.data['analysis'])
    
    def test_analyze_nonexistent_process(self):
        """Testa análise de processo inexistente"""
        response = self.client.post('/chat/analyze/process/99999/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)