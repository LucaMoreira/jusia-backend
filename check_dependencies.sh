#!/bin/bash

# Script para verificar dependências do projeto
echo "🔍 Verificando dependências do Jusia Backend..."

# Verificar se estamos no diretório correto
if [ ! -f "requirements.txt" ]; then
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

# Instalar/atualizar dependências
echo "📦 Instalando dependências..."
pip install -r requirements.txt

# Verificar bibliotecas críticas
echo "🧪 Verificando bibliotecas críticas..."

python -c "
import django
print(f'✅ Django {django.get_version()}')

import rest_framework
print(f'✅ Django REST Framework {rest_framework.VERSION}')

import google.generativeai
print('✅ Google Generative AI')

import stripe
print('✅ Stripe')

import psycopg2
print('✅ PostgreSQL (psycopg2)')

import whitenoise
print('✅ WhiteNoise')

import gunicorn
print('✅ Gunicorn')

print('\\n🎉 Todas as dependências estão instaladas corretamente!')
"

# Testar configurações Django
echo "⚙️  Testando configurações Django..."
python manage.py check --deploy

# Verificar configurações críticas
echo "🔧 Verificando configurações críticas..."
python -c "
from django.conf import settings
import os

# Verificar configurações essenciais
configs = [
    'SECRET_KEY',
    'DATABASES',
    'STRIPE_PRIVATE_KEY',
    'EMAIL_HOST_USER',
    'FRONTEND_URL',
    'GEMINI_API_KEY',
    'DATAJUD_API_KEY',
    'DATAJUD_BASE_URL'
]

for config in configs:
    try:
        value = getattr(settings, config)
        if config == 'SECRET_KEY' and value == 'django-insecure-your-secret-key-here':
            print(f'⚠️  {config}: Valor padrão (configure em produção)')
        elif config == 'GEMINI_API_KEY' and not value:
            print(f'⚠️  {config}: Não configurado (opcional)')
        else:
            print(f'✅ {config}: Configurado')
    except AttributeError:
        print(f'❌ {config}: Não encontrado')

print('\\n🎉 Verificação de configurações concluída!')
"

echo "✅ Verificação concluída!"
