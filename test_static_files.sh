#!/bin/bash

# Script para testar arquivos estáticos do Django Admin
echo "🧪 Testando configuração de arquivos estáticos..."

# Verificar se estamos no diretório correto
if [ ! -f "manage.py" ]; then
    echo "❌ Execute este script dentro da pasta jusia-backend"
    exit 1
fi

# Coletar arquivos estáticos
echo "📦 Coletando arquivos estáticos..."
python manage.py collectstatic --noinput --clear

# Verificar se os arquivos foram coletados
if [ -d "staticfiles/admin" ]; then
    echo "✅ Arquivos estáticos do admin coletados com sucesso"
    echo "📁 Arquivos encontrados:"
    ls -la staticfiles/admin/css/ | head -5
    ls -la staticfiles/admin/js/ | head -5
else
    echo "❌ Erro: Arquivos estáticos do admin não foram coletados"
    exit 1
fi

# Testar servidor de desenvolvimento
echo "🚀 Iniciando servidor de teste..."
echo "📝 Acesse http://localhost:8000/admin/ para testar"
echo "⏹️  Pressione Ctrl+C para parar o servidor"
python manage.py runserver 8000
