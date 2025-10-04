from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from unittest.mock import patch, MagicMock
import json

from .models import ProcessData, ProcessParty, ProcessMovement, ProcessSearch, UserProcessFavorite
from .services.datajud import DataJudService

User = get_user_model()


class ProcessModelTests(TestCase):
    """Testes para os modelos de processos"""
    
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
    
    def test_process_data_creation(self):
        """Testa criação de dados de processo"""
        self.assertEqual(self.process.process_number, '12345678901234567890')
        self.assertEqual(self.process.court_name, 'Tribunal de Teste')
        self.assertEqual(self.process.case_class, 'Ação de Cobrança')
        self.assertEqual(self.process.value, 1000.00)
    
    def test_process_party_creation(self):
        """Testa criação de parte do processo"""
        party = ProcessParty.objects.create(
            process=self.process,
            name='João Silva',
            party_type='autor',
            document='12345678901'
        )
        
        self.assertEqual(party.process, self.process)
        self.assertEqual(party.name, 'João Silva')
        self.assertEqual(party.party_type, 'autor')
    
    def test_process_movement_creation(self):
        """Testa criação de movimentação do processo"""
        movement = ProcessMovement.objects.create(
            process=self.process,
            date='2024-01-15',
            description='Distribuição',
            movement_type='Distribuição'
        )
        
        self.assertEqual(movement.process, self.process)
        self.assertEqual(movement.description, 'Distribuição')
    
    def test_process_search_creation(self):
        """Testa criação de busca de processo"""
        search = ProcessSearch.objects.create(
            user=self.user,
            process_number='12345678901234567890',
            search_type='number',
            success=True
        )
        
        self.assertEqual(search.user, self.user)
        self.assertEqual(search.process_number, '12345678901234567890')
        self.assertTrue(search.success)
    
    def test_user_process_favorite_creation(self):
        """Testa criação de favorito de processo"""
        favorite = UserProcessFavorite.objects.create(
            user=self.user,
            process=self.process
        )
        
        self.assertEqual(favorite.user, self.user)
        self.assertEqual(favorite.process, self.process)


class ProcessAPITests(APITestCase):
    """Testes para as APIs de processos"""
    
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
    
    @patch('processes.services.datajud.DataJudService')
    def test_search_process_by_number(self, mock_datajud_service):
        """Testa busca de processo por número"""
        # Configurar mock do DataJud
        mock_service = MagicMock()
        mock_service.search_process_by_number.return_value = {
            'success': True,
            'data': [{
                'process_number': '12345678901234567890',
                'court_name': 'Tribunal de Teste',
                'case_class': 'Ação de Cobrança',
                'subject': 'Teste de assunto',
                'status': 'Ativo',
                'value': 1000.00
            }]
        }
        mock_datajud_service.return_value = mock_service
        
        data = {
            'process_number': '12345678901234567890'
        }
        
        response = self.client.post('/processes/search/', data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(len(response.data['data']), 1)
        self.assertEqual(response.data['data'][0]['process_number'], '12345678901234567890')
    
    def test_search_process_invalid_number(self):
        """Testa busca com número de processo inválido"""
        data = {
            'process_number': '123'  # Número muito curto
        }
        
        response = self.client.post('/processes/search/', data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
    
    @patch('processes.services.datajud.DataJudService')
    def test_search_by_party(self, mock_datajud_service):
        """Testa busca por parte"""
        # Configurar mock do DataJud
        mock_service = MagicMock()
        mock_service.search_by_party.return_value = {
            'success': True,
            'data': [{
                'process_number': '12345678901234567890',
                'court_name': 'Tribunal de Teste',
                'case_class': 'Ação de Cobrança'
            }]
        }
        mock_datajud_service.return_value = mock_service
        
        data = {
            'party_name': 'João Silva',
            'limit': 10
        }
        
        response = self.client.post('/processes/search/by-party/', data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(len(response.data['data']), 1)
    
    @patch('processes.services.datajud.DataJudService')
    def test_search_by_court(self, mock_datajud_service):
        """Testa busca por tribunal"""
        # Configurar mock do DataJud
        mock_service = MagicMock()
        mock_service.search_processes_by_court.return_value = {
            'success': True,
            'data': [{
                'process_number': '12345678901234567890',
                'court_name': 'Tribunal de Teste',
                'case_class': 'Ação de Cobrança'
            }]
        }
        mock_datajud_service.return_value = mock_service
        
        data = {
            'court_code': 'tjsp',
            'limit': 10
        }
        
        response = self.client.post('/processes/search/by-court/', data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(len(response.data['data']), 1)
    
    def test_get_courts_list(self):
        """Testa obtenção da lista de tribunais"""
        response = self.client.get('/processes/courts/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIsInstance(response.data['data'], list)
        self.assertGreater(len(response.data['data']), 0)
    
    def test_get_user_searches(self):
        """Testa obtenção do histórico de buscas do usuário"""
        # Criar algumas buscas
        ProcessSearch.objects.create(
            user=self.user,
            process_number='12345678901234567890',
            search_type='number',
            success=True
        )
        ProcessSearch.objects.create(
            user=self.user,
            process_number='98765432109876543210',
            search_type='party',
            success=False,
            error_message='Processo não encontrado'
        )
        
        response = self.client.get('/processes/searches/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(len(response.data['data']), 2)
    
    def test_add_to_favorites(self):
        """Testa adição de processo aos favoritos"""
        process = ProcessData.objects.create(
            process_number='12345678901234567890',
            court_name='Tribunal de Teste',
            case_class='Ação de Cobrança'
        )
        
        response = self.client.post(f'/processes/favorites/{process.id}/add/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertTrue(response.data['is_favorite'])
        
        # Verificar se foi criado no banco
        self.assertTrue(UserProcessFavorite.objects.filter(
            user=self.user,
            process=process
        ).exists())
    
    def test_remove_from_favorites(self):
        """Testa remoção de processo dos favoritos"""
        process = ProcessData.objects.create(
            process_number='12345678901234567890',
            court_name='Tribunal de Teste',
            case_class='Ação de Cobrança'
        )
        
        # Adicionar aos favoritos primeiro
        UserProcessFavorite.objects.create(
            user=self.user,
            process=process
        )
        
        response = self.client.delete(f'/processes/favorites/{process.id}/remove/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertFalse(response.data['is_favorite'])
        
        # Verificar se foi removido do banco
        self.assertFalse(UserProcessFavorite.objects.filter(
            user=self.user,
            process=process
        ).exists())
    
    def test_get_favorites(self):
        """Testa obtenção de processos favoritos"""
        process1 = ProcessData.objects.create(
            process_number='12345678901234567890',
            court_name='Tribunal de Teste',
            case_class='Ação de Cobrança'
        )
        process2 = ProcessData.objects.create(
            process_number='98765432109876543210',
            court_name='Tribunal de Teste 2',
            case_class='Ação Trabalhista'
        )
        
        # Adicionar aos favoritos
        UserProcessFavorite.objects.create(user=self.user, process=process1)
        UserProcessFavorite.objects.create(user=self.user, process=process2)
        
        response = self.client.get('/processes/favorites/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(len(response.data['data']), 2)
    
    def test_get_process_details(self):
        """Testa obtenção de detalhes de processo"""
        process = ProcessData.objects.create(
            process_number='12345678901234567890',
            court_name='Tribunal de Teste',
            case_class='Ação de Cobrança',
            subject='Teste de assunto',
            status='Ativo',
            value=1000.00
        )
        
        # Criar partes
        ProcessParty.objects.create(
            process=process,
            name='João Silva',
            party_type='autor',
            document='12345678901'
        )
        
        # Criar movimentações
        ProcessMovement.objects.create(
            process=process,
            date='2024-01-15',
            description='Distribuição',
            movement_type='Distribuição'
        )
        
        response = self.client.get(f'/processes/details/{process.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['process_number'], '12345678901234567890')
        self.assertEqual(len(response.data['data']['parties']), 1)
        self.assertEqual(len(response.data['data']['movements']), 1)
    
    def test_unauthorized_access(self):
        """Testa acesso não autorizado"""
        self.client.credentials()  # Remover autenticação
        
        response = self.client.get('/processes/favorites/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
