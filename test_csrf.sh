#!/bin/bash

# Script para testar configurações de CSRF
echo "🔒 Testando configurações de CSRF..."

# Verificar se estamos no diretório correto
if [ ! -f "manage.py" ]; then
    echo "❌ Execute este script dentro da pasta jusia-backend"
    exit 1
fi

# Verificar se o ambiente virtual está ativo
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Ambiente virtual não detectado. Ativando..."
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
        echo "✅ Ambiente virtual ativado"
    else
        echo "❌ Ambiente virtual não encontrado. Execute: python -m venv venv"
        exit 1
    fi
fi

# Testar configurações de CSRF
echo "🧪 Testando configurações de CSRF..."
python -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cloudpharma_backend.settings')

import django
django.setup()

from django.conf import settings

print('🔍 Configurações de CSRF:')
print(f'CSRF_TRUSTED_ORIGINS: {getattr(settings, \"CSRF_TRUSTED_ORIGINS\", \"Não configurado\")}')
print(f'CSRF_COOKIE_SECURE: {getattr(settings, \"CSRF_COOKIE_SECURE\", \"Não configurado\")}')
print(f'CSRF_COOKIE_HTTPONLY: {getattr(settings, \"CSRF_COOKIE_HTTPONLY\", \"Não configurado\")}')
print(f'CSRF_COOKIE_SAMESITE: {getattr(settings, \"CSRF_COOKIE_SAMESITE\", \"Não configurado\")}')

print('\\n🔍 Configurações de Sessão:')
print(f'SESSION_COOKIE_SECURE: {getattr(settings, \"SESSION_COOKIE_SECURE\", \"Não configurado\")}')
print(f'SESSION_COOKIE_HTTPONLY: {getattr(settings, \"SESSION_COOKIE_HTTPONLY\", \"Não configurado\")}')
print(f'SESSION_COOKIE_SAMESITE: {getattr(settings, \"SESSION_COOKIE_SAMESITE\", \"Não configurado\")}')

print('\\n🔍 Configurações de Segurança:')
print(f'SECURE_PROXY_SSL_HEADER: {getattr(settings, \"SECURE_PROXY_SSL_HEADER\", \"Não configurado\")}')
print(f'DEBUG: {getattr(settings, \"DEBUG\", \"Não configurado\")}')

print('\\n✅ Verificação de CSRF concluída!')
"

echo "📝 Para resolver problemas de CSRF:"
echo "1. Certifique-se de que DEBUG=False em produção"
echo "2. Adicione sua URL do Cloud Run ao CSRF_TRUSTED_ORIGINS"
echo "3. Configure ADDITIONAL_TRUSTED_ORIGINS se necessário"
echo "4. Verifique se os cookies estão sendo definidos corretamente"
