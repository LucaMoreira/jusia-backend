# Jusia Backend

Backend Django para o sistema Jusia - plataforma de consulta jurídica com IA.

## 🚀 Tecnologias

- **Django 5.2.5** - Framework web Python
- **Django REST Framework** - API REST
- **PostgreSQL** - Banco de dados
- **JWT Authentication** - Autenticação
- **Stripe** - Pagamentos
- **Google Cloud Run** - Deploy e hospedagem

## 📁 Estrutura do Projeto

```
jusia-backend/
├── accounts/           # Sistema de usuários e autenticação
├── chat/              # Integração com IA (Gemini)
├── notifications/     # Sistema de notificações
├── processes/         # Consulta de processos jurídicos
├── subscriptions/     # Sistema de assinaturas
├── health/           # Health checks para Cloud Run
├── cloudpharma_backend/  # Configurações Django
├── Dockerfile         # Container para Cloud Run
├── cloudbuild.yaml    # Deploy automático
└── requirements.txt   # Dependências Python
```

## 🛠️ Instalação Local

### Pré-requisitos
- Python 3.11+
- PostgreSQL
- Git

### Setup

1. **Clone o repositório**
```bash
git clone <repository-url>
cd jusia-backend
```

2. **Crie um ambiente virtual**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate    # Windows
```

3. **Instale as dependências**
```bash
pip install -r requirements.txt
```

4. **Configure as variáveis de ambiente**
```bash
cp env.example .env
# Edite o arquivo .env com suas configurações
```

5. **Execute as migrações**
```bash
python manage.py migrate
```

6. **Crie um superusuário**
```bash
python manage.py createsuperuser
```

7. **Coletar arquivos estáticos**
```bash
python manage.py collectstatic
```

8. **Execute o servidor**
```bash
python manage.py runserver
```

9. **Teste o admin**
```bash
# Execute o script de teste
./test_static_files.sh
```

## 🌐 Deploy no Google Cloud Run

### Configuração Automática

1. **Conecte o repositório ao Cloud Build**
2. **Configure um trigger para deploy automático**
3. **O arquivo `cloudbuild.yaml` já está configurado**

### Deploy Manual

```bash
# Build da imagem
gcloud builds submit --tag gcr.io/PROJECT_ID/jusia-backend

# Deploy no Cloud Run
gcloud run deploy jusia-backend \
  --image gcr.io/PROJECT_ID/jusia-backend \
  --region southamerica-east1 \
  --platform managed \
  --allow-unauthenticated \
  --port 8080 \
  --memory 1Gi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 10 \
  --concurrency 80 \
  --timeout 300
```

### Variáveis de Ambiente (Cloud Run)

Configure estas variáveis no Cloud Run Console:

```bash
# Django
SECRET_KEY=your-secret-key
DEBUG=False
PORT=8080

# Database
DB_ENGINE=django.db.backends.postgresql
DB_NAME=your-database-name
DB_USER=your-database-user
DB_PASSWORD=your-database-password
DB_HOST=your-database-host
DB_PORT=5432

# CORS
FRONTEND_URL=https://your-frontend-domain.com
BACKEND_HOST=your-cloud-run-service-url.run.app

# Stripe
STRIPE_PRIVATE_KEY=sk_live_your_stripe_key

# Email
EMAIL_HOST_USER=your-email@example.com
EMAIL_HOST_PASSWORD=your-email-password
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True

# Google Gemini AI
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-1.5-flash

# DataJud API (CNJ)
DATAJUD_API_KEY=your-datajud-api-key
DATAJUD_BASE_URL=https://api-publica.datajud.cnj.jus.br

# Additional trusted origins for CSRF (comma-separated)
ADDITIONAL_TRUSTED_ORIGINS=https://your-custom-domain.com,https://another-domain.com
```

## 🔍 Health Checks

O sistema inclui endpoints de health check para monitoramento:

- **Liveness**: `GET /health/live/` - Verifica se a aplicação está rodando
- **Readiness**: `GET /health/ready/` - Verifica conectividade com banco e cache

## 📊 APIs Disponíveis

### Autenticação
- `POST /accounts/register/` - Registro de usuário
- `POST /accounts/login/` - Login
- `POST /accounts/logout/` - Logout
- `POST /accounts/refresh/` - Renovar token

### Processos
- `GET /processes/search/` - Buscar processos
- `POST /processes/favorite/` - Adicionar aos favoritos
- `GET /processes/favorites/` - Listar favoritos

### Chat IA
- `POST /chat/message/` - Enviar mensagem para IA

### Assinaturas
- `GET /subscriptions/plans/` - Listar planos
- `POST /subscriptions/subscribe/` - Criar assinatura
- `GET /subscriptions/status/` - Status da assinatura

## 🧪 Testes

```bash
# Executar todos os testes
python manage.py test

# Executar testes de uma app específica
python manage.py test accounts
```

## 📝 Logs

Em produção, os logs são enviados para o Google Cloud Logging. Para desenvolvimento local:

```bash
# Logs detalhados
python manage.py runserver --verbosity=2
```

## 🔧 Comandos Úteis

```bash
# Criar migrações
python manage.py makemigrations

# Aplicar migrações
python manage.py migrate

# Coletar arquivos estáticos
python manage.py collectstatic

# Shell interativo
python manage.py shell

# Criar superusuário
python manage.py createsuperuser

# Testar arquivos estáticos
./test_static_files.sh

# Verificar dependências
./check_dependencies.sh

# Testar configurações de CSRF
./test_csrf.sh
```

## 📁 Arquivos Estáticos

O sistema está configurado para servir arquivos estáticos corretamente:

- **Desenvolvimento**: Django serve automaticamente
- **Produção**: WhiteNoise serve os arquivos coletados
- **Admin**: CSS e JS do Django Admin funcionam perfeitamente

### Configurações:
- `STATIC_URL = 'static/'`
- `STATIC_ROOT = BASE_DIR / 'staticfiles'`
- `WhiteNoise` middleware configurado
- Arquivos coletados durante o build do Docker

## 🚨 Troubleshooting

### Problemas Comuns

1. **Erro de conexão com banco**
   - Verifique as variáveis de ambiente DB_*
   - Confirme se o banco está acessível

2. **Erro de CORS**
   - Verifique FRONTEND_URL nas variáveis de ambiente
   - Confirme se o frontend está na lista de origens permitidas

3. **Erro de autenticação**
   - Verifique SECRET_KEY
   - Confirme se os tokens JWT estão sendo enviados corretamente

4. **Admin sem CSS/JS**
   - Execute `python manage.py collectstatic`
   - Verifique se WhiteNoise está no middleware
   - Confirme se STATIC_ROOT está configurado

5. **Erro CSRF no Admin**
   - Verifique se CSRF_TRUSTED_ORIGINS está configurado
   - Adicione sua URL do Cloud Run às origens confiáveis
   - Confirme se DEBUG=False em produção

## 📞 Suporte

Para dúvidas ou problemas, consulte a documentação da API ou entre em contato com a equipe de desenvolvimento.
