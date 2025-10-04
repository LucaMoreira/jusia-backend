import google.generativeai as genai
from django.conf import settings
import logging
import json
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class GeminiService:
    """
    Serviço para integração com a API do Google Gemini
    """
    
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.model_name = settings.GEMINI_MODEL
        
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY não configurada nas configurações do Django")
        
        # Configurar a API do Gemini
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(self.model_name)
    
    def generate_response(
        self, 
        user_message: str, 
        chat_history: List[Dict[str, str]] = None,
        process_context: Dict[str, Any] = None,
        system_prompt: str = None
    ) -> Dict[str, Any]:
        """
        Gera uma resposta da IA baseada na mensagem do usuário e contexto
        
        Args:
            user_message: Mensagem do usuário
            chat_history: Histórico de mensagens da conversa
            process_context: Contexto específico do processo (se houver)
            system_prompt: Prompt do sistema personalizado
        
        Returns:
            Dict com a resposta da IA e metadados
        """
        try:
            # Construir o prompt do sistema
            system_prompt = system_prompt or self._get_default_system_prompt()
            
            # Adicionar contexto do processo se disponível
            if process_context:
                system_prompt += self._build_process_context_prompt(process_context)
            
            # Construir histórico de conversa
            conversation_history = self._build_conversation_history(chat_history or [])
            
            # Construir prompt final
            full_prompt = f"{system_prompt}\n\n{conversation_history}\nUsuário: {user_message}\nAssistente:"
            
            # Gerar resposta
            response = self.model.generate_content(full_prompt)
            
            return {
                'content': response.text,
                'tokens_used': self._estimate_tokens(full_prompt + response.text),
                'model_used': self.model_name,
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Erro ao gerar resposta do Gemini: {str(e)}")
            return {
                'content': "Desculpe, ocorreu um erro ao processar sua solicitação. Tente novamente.",
                'tokens_used': 0,
                'model_used': self.model_name,
                'success': False,
                'error': str(e)
            }
    
    def analyze_process(self, process_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analisa um processo jurídico e fornece insights
        
        Args:
            process_data: Dados do processo
        
        Returns:
            Dict com análise do processo
        """
        try:
            process_prompt = self._build_process_analysis_prompt(process_data)
            response = self.model.generate_content(process_prompt)
            
            return {
                'analysis': response.text,
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Erro ao analisar processo: {str(e)}")
            return {
                'analysis': "Não foi possível analisar o processo no momento.",
                'success': False,
                'error': str(e)
            }
    
    def generate_suggestions(self, user_message: str, process_context: Dict[str, Any] = None) -> List[str]:
        """
        Gera sugestões de perguntas baseadas na mensagem do usuário
        
        Args:
            user_message: Mensagem do usuário
            process_context: Contexto do processo
        
        Returns:
            Lista de sugestões
        """
        try:
            suggestions_prompt = f"""
            Baseado na seguinte mensagem do usuário, gere 3 sugestões de perguntas relacionadas:
            
            Mensagem: {user_message}
            
            Contexto do processo: {json.dumps(process_context, ensure_ascii=False) if process_context else 'Nenhum'}
            
            Retorne apenas as sugestões, uma por linha, sem numeração.
            """
            
            response = self.model.generate_content(suggestions_prompt)
            suggestions = [s.strip() for s in response.text.split('\n') if s.strip()]
            
            return suggestions[:3]  # Limitar a 3 sugestões
            
        except Exception as e:
            logger.error(f"Erro ao gerar sugestões: {str(e)}")
            return []
    
    def _get_default_system_prompt(self) -> str:
        """Retorna o prompt padrão do sistema"""
        return """
        Você é uma assistente jurídica especializada em direito brasileiro. Sua função é:

        1. Responder perguntas sobre processos jurídicos
        2. Explicar conceitos legais de forma clara e acessível
        3. Fornecer orientações sobre procedimentos jurídicos
        4. Analisar dados de processos e fornecer insights
        5. Sugerir próximos passos em casos jurídicos

        IMPORTANTE:
        - Sempre esclareça que suas respostas são informativas e não substituem consulta jurídica profissional
        - Use linguagem clara e acessível
        - Baseie suas respostas na legislação brasileira
        - Se não souber algo, admita e sugira consultar um advogado
        - Mantenha um tom profissional mas amigável
        """
    
    def _build_process_context_prompt(self, process_context: Dict[str, Any]) -> str:
        """Constrói prompt com contexto do processo"""
        context_parts = []
        
        if process_context.get('process_number'):
            context_parts.append(f"Número do processo: {process_context['process_number']}")
        
        if process_context.get('court_name'):
            context_parts.append(f"Tribunal: {process_context['court_name']}")
        
        if process_context.get('case_class'):
            context_parts.append(f"Classe processual: {process_context['case_class']}")
        
        if process_context.get('subject'):
            context_parts.append(f"Assunto: {process_context['subject']}")
        
        if process_context.get('parties'):
            parties_text = ", ".join([f"{p.get('name', 'N/A')} ({p.get('role', 'N/A')})" for p in process_context['parties']])
            context_parts.append(f"Partes envolvidas: {parties_text}")
        
        if process_context.get('movements'):
            recent_movements = process_context['movements'][:5]  # Últimas 5 movimentações
            movements_text = "\n".join([f"- {m.get('description', 'N/A')} ({m.get('date', 'N/A')})" for m in recent_movements])
            context_parts.append(f"Últimas movimentações:\n{movements_text}")
        
        if context_parts:
            return f"\n\nCONTEXTO DO PROCESSO:\n" + "\n".join(context_parts)
        
        return ""
    
    def _build_conversation_history(self, chat_history: List[Dict[str, str]]) -> str:
        """Constrói histórico de conversa para o prompt"""
        if not chat_history:
            return ""
        
        history_text = ""
        for msg in chat_history[-10:]:  # Últimas 10 mensagens
            role = "Usuário" if msg.get('message_type') == 'user' else "Assistente"
            content = msg.get('content', '')
            history_text += f"{role}: {content}\n"
        
        return f"HISTÓRICO DA CONVERSA:\n{history_text}"
    
    def _build_process_analysis_prompt(self, process_data: Dict[str, Any]) -> str:
        """Constrói prompt para análise de processo"""
        return f"""
        Analise o seguinte processo jurídico e forneça insights relevantes:

        DADOS DO PROCESSO:
        {json.dumps(process_data, ensure_ascii=False, indent=2)}

        Forneça:
        1. Resumo do caso
        2. Pontos jurídicos relevantes
        3. Possíveis próximos passos
        4. Observações importantes
        5. Recomendações gerais

        Mantenha a análise objetiva e baseada nos dados fornecidos.
        """
    
    def _estimate_tokens(self, text: str) -> int:
        """Estima o número de tokens usados (aproximação)"""
        # Aproximação: 1 token ≈ 4 caracteres para português
        return len(text) // 4


