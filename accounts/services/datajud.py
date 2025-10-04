import requests
import logging
import re
from typing import Dict, List, Optional, Any
from django.conf import settings
from django.core.cache import cache
import json

logger = logging.getLogger(__name__)

class DataJudService:
    """
    Serviço para integração com a API do DataJud (CNJ)
    Documentação: https://datajud-wiki.cnj.jus.br/api-publica/acesso
    """
    
    def __init__(self):
        self.api_key = settings.DATAJUD_API_KEY or 'cDZHYzlZa0JadVREZDJCendQbXY6SkJlTzNjLV9TRENyQk1RdnFKZGRQdw=='
        self.base_url = settings.DATAJUD_BASE_URL or 'https://api-publica.datajud.cnj.jus.br'
        self.headers = {
            'Authorization': f'APIKey {self.api_key}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    
    def _make_request(self, endpoint: str, data: Dict = None, method: str = 'POST') -> Dict[str, Any]:
        """
        Faz uma requisição para a API do DataJud
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            if method.upper() == 'POST':
                response = requests.post(
                    url,
                    headers=self.headers,
                    json=data or {},
                    timeout=30
                )
            else:
                response = requests.get(
                    url,
                    headers=self.headers,
                    params=data or {},
                    timeout=30
                )
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro na requisição para DataJud: {e}")
            
            # Distinguir entre diferentes tipos de erro
            if hasattr(e, 'response') and e.response is not None:
                status_code = e.response.status_code
                if status_code == 404:
                    raise Exception(f"API do DataJud não encontrada (404). Endpoint pode estar indisponível ou incorreto.")
                elif status_code == 401:
                    raise Exception(f"Erro de autenticação na API do DataJud (401). Verifique a API key.")
                elif status_code == 403:
                    raise Exception(f"Acesso negado na API do DataJud (403). Verifique as permissões.")
                elif status_code >= 500:
                    raise Exception(f"Erro interno do servidor DataJud ({status_code}). Tente novamente mais tarde.")
                else:
                    raise Exception(f"Erro HTTP {status_code} na API do DataJud: {str(e)}")
            else:
                raise Exception(f"Erro de conexão com a API do DataJud: {str(e)}")
    
    def search_process_by_number(self, process_number: str) -> Dict[str, Any]:
        """
        Busca um processo pelo número
        
        Args:
            process_number: Número do processo (ex: 0001234-56.2023.8.26.0001)
        
        Returns:
            Dict com os dados do processo
        """
        # Verificar cache primeiro
        cache_key = f"datajud_process_{process_number}"
        cached_result = cache.get(cache_key)
        if cached_result:
            logger.info(f"Processo {process_number} encontrado no cache")
            return cached_result
        
        try:
            # Primeiro, tenta no tribunal extraído do número
            tribunal_code = self._extract_tribunal_code(process_number)
            endpoint = f"/api_publica_{tribunal_code.lower()}/_search"
            
            data = {
                "query": {
                    "match": {
                        "numeroProcesso": process_number
                    }
                }
            }
            
            try:
                result = self._make_request(endpoint, data, 'POST')
                
                if result and isinstance(result, dict) and "hits" in result:
                    hits = result["hits"].get("hits", [])
                    if hits and "_source" in hits[0]:
                        process_data = hits[0]["_source"]
                        cache.set(cache_key, process_data, 3600)  # Cache por 1 hora
                        logger.info(f"Processo {process_number} encontrado no tribunal {tribunal_code.upper()}")
                        return process_data
            except Exception as e:
                logger.warning(f"Processo não encontrado no tribunal {tribunal_code.upper()}: {e}")
            
            # Se não encontrou no tribunal extraído, busca nos principais tribunais
            main_tribunals = ['tjsp', 'tjrj', 'tjmg', 'tjrs', 'tjpr', 'tjsc', 'tjba', 'tjce', 'tjpe', 'tjgo']
            
            for tribunal in main_tribunals:
                try:
                    endpoint = f"/api_publica_{tribunal}/_search"
                    result = self._make_request(endpoint, data, 'POST')
                    
                    if result and isinstance(result, dict) and "hits" in result:
                        hits = result["hits"].get("hits", [])
                        if hits and "_source" in hits[0]:
                            process_data = hits[0]["_source"]
                            cache.set(cache_key, process_data, 3600)  # Cache por 1 hora
                            logger.info(f"Processo {process_number} encontrado no tribunal {tribunal.upper()}")
                            return process_data
                except Exception as e:
                    logger.warning(f"Erro ao buscar no tribunal {tribunal.upper()}: {e}")
                    continue
            
            # Se não encontrou em nenhum tribunal
            raise Exception(f"Processo {process_number} não encontrado em nenhum tribunal consultado")
            
        except Exception as e:
            logger.error(f"Erro ao buscar processo {process_number}: {e}")
            raise Exception(f"Não foi possível consultar o processo {process_number}. Verifique se o número está correto e tente novamente.")
    
    def search_processes_by_court(self, court_code: str, limit: int = 100) -> Dict[str, Any]:
        """
        Busca processos por tribunal
        
        Args:
            court_code: Código do tribunal (ex: TJSP, STF, STJ)
            limit: Limite de resultados
        
        Returns:
            Dict com lista de processos
        """
        cache_key = f"datajud_court_{court_code}_{limit}"
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        try:
            # Converter código do tribunal para lowercase
            tribunal_endpoint = court_code.lower()
            
            data = {
                "size": limit,
                "query": {
                    "match_all": {}
                }
            }
            
            result = self._make_request(f'/api_publica_{tribunal_endpoint}/_search', data, 'POST')
            
            # Salvar no cache por 30 minutos
            cache.set(cache_key, result, 1800)
            
            return result
            
        except Exception as e:
            logger.error(f"Erro ao buscar processos do tribunal {court_code}: {e}")
            raise Exception(f"Não foi possível consultar processos do tribunal {court_code}. Verifique se o código do tribunal está correto e tente novamente.")
    
    def get_process_details(self, process_id: str) -> Dict[str, Any]:
        """
        Obtém detalhes completos de um processo
        
        Args:
            process_id: ID único do processo
        
        Returns:
            Dict com detalhes completos do processo
        """
        cache_key = f"datajud_details_{process_id}"
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        try:
            result = self._make_request(f'/processos/{process_id}')
            
            # Salvar no cache por 2 horas
            cache.set(cache_key, result, 7200)
            
            return result
            
        except Exception as e:
            logger.error(f"Erro ao obter detalhes do processo {process_id}: {e}")
            raise
    
    def search_by_party(self, party_name: str, party_type: str = None) -> Dict[str, Any]:
        """
        Busca processos por parte
        
        Args:
            party_name: Nome da parte
            party_type: Tipo da parte (autor, reu, etc.)
        
        Returns:
            Dict com lista de processos
        """
        try:
            # Buscar em tribunais principais
            tribunals = ['tjsp', 'tjrj', 'tjmg', 'tjrs', 'tjpr', 'tjsc', 'tjba']
            all_results = []
            api_errors = []
            
            for tribunal in tribunals:
                try:
                    endpoint = f"/api_publica_{tribunal}/_search"
                    # Query mais simples possível
                    data = {
                        "query": {
                            "match": {
                                "assuntos.nome": party_name
                            }
                        },
                        "size": 5
                    }
                    
                    result = self._make_request(endpoint, data, 'POST')
                    
                    # Se retornou resultados, adicionar à lista
                    if result and isinstance(result, dict):
                        if "hits" in result and "hits" in result["hits"]:
                            # Extrair dados dos hits do Elasticsearch
                            for hit in result["hits"]["hits"]:
                                if "_source" in hit:
                                    all_results.append(hit["_source"])
                        elif "processos" in result:
                            all_results.extend(result["processos"])
                        elif "data" in result:
                            all_results.extend(result["data"])
                        else:
                            all_results.append(result)
                            
                except Exception as e:
                    error_msg = str(e)
                    api_errors.append(f"Tribunal {tribunal.upper()}: {error_msg}")
                    logger.warning(f"Tribunal {tribunal} falhou para parte {party_name}: {e}")
                    continue
            
            # Se houve erros de API em todos os tribunais, retornar erro
            if not all_results and api_errors:
                error_summary = "; ".join(api_errors)
                raise Exception(f"Erro ao consultar tribunais para a parte '{party_name}': {error_summary}")
            
            # Se nenhum tribunal retornou resultados, mas não houve erros de API
            if not all_results:
                logger.info(f"Nenhum processo encontrado para a parte '{party_name}' nos tribunais consultados")
                return {"processos": []}
            
            return {"processos": all_results}
            
        except Exception as e:
            logger.error(f"Erro ao buscar processos da parte {party_name}: {e}")
            raise
    
    def get_courts_list(self) -> List[Dict[str, Any]]:
        """
        Obtém lista de tribunais disponíveis baseada na documentação oficial
        
        Returns:
            Lista de tribunais
        """
        cache_key = "datajud_courts_list"
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        # Lista fixa baseada na documentação oficial da API DataJud
        courts = [
            # Tribunais Superiores
            {"code": "tst", "name": "Tribunal Superior do Trabalho", "type": "superior"},
            {"code": "tse", "name": "Tribunal Superior Eleitoral", "type": "superior"},
            {"code": "stj", "name": "Superior Tribunal de Justiça", "type": "superior"},
            {"code": "stm", "name": "Superior Tribunal Militar", "type": "superior"},
            
            # Justiça Federal
            {"code": "trf1", "name": "Tribunal Regional Federal da 1ª Região", "type": "federal"},
            {"code": "trf2", "name": "Tribunal Regional Federal da 2ª Região", "type": "federal"},
            {"code": "trf3", "name": "Tribunal Regional Federal da 3ª Região", "type": "federal"},
            {"code": "trf4", "name": "Tribunal Regional Federal da 4ª Região", "type": "federal"},
            {"code": "trf5", "name": "Tribunal Regional Federal da 5ª Região", "type": "federal"},
            {"code": "trf6", "name": "Tribunal Regional Federal da 6ª Região", "type": "federal"},
            
            # Justiça Estadual (principais)
            {"code": "tjsp", "name": "Tribunal de Justiça de São Paulo", "type": "estadual"},
            {"code": "tjrj", "name": "Tribunal de Justiça do Rio de Janeiro", "type": "estadual"},
            {"code": "tjmg", "name": "Tribunal de Justiça de Minas Gerais", "type": "estadual"},
            {"code": "tjrs", "name": "Tribunal de Justiça do Rio Grande do Sul", "type": "estadual"},
            {"code": "tjpr", "name": "Tribunal de Justiça do Paraná", "type": "estadual"},
            {"code": "tjsc", "name": "Tribunal de Justiça de Santa Catarina", "type": "estadual"},
            {"code": "tjba", "name": "Tribunal de Justiça da Bahia", "type": "estadual"},
            {"code": "tjce", "name": "Tribunal de Justiça do Ceará", "type": "estadual"},
            {"code": "tjpe", "name": "Tribunal de Justiça de Pernambuco", "type": "estadual"},
            {"code": "tjgo", "name": "Tribunal de Justiça de Goiás", "type": "estadual"},
        ]
        
        # Salvar no cache por 24 horas
        cache.set(cache_key, courts, 86400)
        return courts
    
    def get_process_movements(self, process_id: str) -> List[Dict[str, Any]]:
        """
        Obtém movimentações de um processo
        
        Args:
            process_id: ID único do processo
        
        Returns:
            Lista de movimentações
        """
        try:
            result = self._make_request(f'/processos/{process_id}/movimentacoes')
            
            return result
            
        except Exception as e:
            logger.error(f"Erro ao obter movimentações do processo {process_id}: {e}")
            raise
    
    def get_process_parties(self, process_id: str) -> List[Dict[str, Any]]:
        """
        Obtém partes de um processo
        
        Args:
            process_id: ID único do processo
        
        Returns:
            Lista de partes
        """
        try:
            result = self._make_request(f'/processos/{process_id}/partes')
            
            return result
            
        except Exception as e:
            logger.error(f"Erro ao obter partes do processo {process_id}: {e}")
            raise
    
    def validate_process_number(self, process_number: str) -> bool:
        """
        Valida se o número do processo está no formato correto
        
        Args:
            process_number: Número do processo
        
        Returns:
            True se válido, False caso contrário
        """
        import re
        
        # Padrão: NNNNNNN-DD.AAAA.J.TR.OOOO
        pattern = r'^\d{7}-\d{2}\.\d{4}\.\d{1}\.\d{2}\.\d{4}$'
        
        return bool(re.match(pattern, process_number))
    
    def format_process_number(self, process_number: str) -> str:
        """
        Formata o número do processo para o padrão correto
        
        Args:
            process_number: Número do processo (com ou sem formatação)
        
        Returns:
            Número formatado
        """
        # Remove caracteres não numéricos
        numbers_only = re.sub(r'[^\d]', '', process_number)
        
        if len(numbers_only) != 20:
            raise ValueError("Número do processo deve ter 20 dígitos")
        
        # Formata: NNNNNNN-DD.AAAA.J.TR.OOOO
        formatted = f"{numbers_only[:7]}-{numbers_only[7:9]}.{numbers_only[9:13]}.{numbers_only[13:14]}.{numbers_only[14:16]}.{numbers_only[16:20]}"
        
        return formatted
    
    def _extract_tribunal_code(self, process_number: str) -> str:
        """
        Extrai o código do tribunal do número do processo
        
        Args:
            process_number: Número do processo formatado
        
        Returns:
            Código do tribunal (ex: TJSP, STF, etc.)
        """
        # Remove caracteres não numéricos
        numbers_only = re.sub(r'[^\d]', '', process_number)
        
        if len(numbers_only) != 20:
            return "tjsp"  # Default
        
        # Extrair código do tribunal (posições 14-16)
        tribunal_code = numbers_only[14:16]
        
        # Mapear códigos para nomes de tribunais (em lowercase para URLs)
        tribunal_mapping = {
            "01": "tjac", "02": "tjal", "03": "tjam", "04": "tjap",
            "05": "tjba", "06": "tjce", "07": "tjdft", "08": "tjes",
            "09": "tjgo", "10": "tjma", "11": "tjmt", "12": "tjms",
            "13": "tjmg", "14": "tjpa", "15": "tjpb", "16": "tjpe",
            "17": "tjpi", "18": "tjpr", "19": "tjrj", "20": "tjrn",
            "21": "tjro", "22": "tjrr", "23": "tjrs", "24": "tjsc",
            "25": "tjsp", "26": "tjse", "27": "tjto"
        }
        
        return tribunal_mapping.get(tribunal_code, "tjsp")


# Instância global do serviço
datajud_service = DataJudService()
