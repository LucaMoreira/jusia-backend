from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from .models import ChatSession, ChatMessage, ChatContext
from processes.models import ProcessData

User = get_user_model()


class SimpleChatTests(APITestCase):
    """Testes simples para o chat"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        
        # Criar token JWT
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
    
    def test_create_chat_session(self):
        """Testa criação de nova sessão de chat"""
        data = {
            'title': 'Nova Sessão'
        }
        
        response = self.client.post('/chat/sessions/create/', data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['title'], 'Nova Sessão')
    
    def test_get_chat_sessions(self):
        """Testa listagem de sessões de chat"""
        # Criar uma sessão
        ChatSession.objects.create(
            user=self.user,
            title='Sessão de Teste'
        )
        
        response = self.client.get('/chat/sessions/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(len(response.data['data']), 1)
    
    def test_unauthorized_access(self):
        """Testa acesso não autorizado"""
        self.client.credentials()  # Remover autenticação
        
        response = self.client.get('/chat/sessions/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class SimpleProcessTests(APITestCase):
    """Testes simples para processos"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        
        # Criar token JWT
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
    
    def test_get_courts_list(self):
        """Testa obtenção da lista de tribunais"""
        response = self.client.get('/processes/courts/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIsInstance(response.data['data'], list)
    
    def test_get_favorites_empty(self):
        """Testa obtenção de favoritos vazios"""
        response = self.client.get('/processes/favorites/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(len(response.data['data']), 0)
    
    def test_get_user_searches_empty(self):
        """Testa obtenção de buscas vazias"""
        response = self.client.get('/processes/searches/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(len(response.data['data']), 0)



