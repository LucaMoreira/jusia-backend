# Resolução de Problemas CSRF no Google Cloud Run

## 🚨 Problema: CSRF verification failed

**Erro típico:**
```
Forbidden (403)
CSRF verification failed. Request aborted.
Origin checking failed - https://your-service.run.app does not match any trusted origins.
```

## ✅ Soluções Implementadas

### 1. Configurações CSRF Adicionadas

O sistema agora inclui configurações automáticas para Cloud Run:

```python
# CSRF and Security settings for Cloud Run
CSRF_TRUSTED_ORIGINS = [
    'https://*.run.app',
    'https://*.googleusercontent.com',
    'https://jusia-backend-394670659856.southamerica-east1.run.app',
    FRONTEND_URL,
]

# Add additional trusted origins from environment
ADDITIONAL_TRUSTED_ORIGINS = env('ADDITIONAL_TRUSTED_ORIGINS', default='').split(',')
CSRF_TRUSTED_ORIGINS.extend([origin.strip() for origin in ADDITIONAL_TRUSTED_ORIGINS if origin.strip()])
```

### 2. Configurações de Cookies Seguros

```python
# Additional CSRF settings
CSRF_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'

# Session security for production
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
```

## 🔧 Como Resolver

### Para Desenvolvimento Local:
```bash
# Testar configurações
./test_csrf.sh
```

### Para Produção (Cloud Run):

1. **Configure DEBUG=False:**
```bash
# No Cloud Run Console ou via gcloud
gcloud run services update jusia-backend \
  --set-env-vars DEBUG=False
```

2. **Adicione URLs adicionais se necessário:**
```bash
# Se você tiver domínios customizados
gcloud run services update jusia-backend \
  --set-env-vars ADDITIONAL_TRUSTED_ORIGINS=https://your-domain.com,https://another-domain.com
```

3. **Verifique se a URL está nas origens confiáveis:**
```bash
# Execute o teste
./test_csrf.sh
```

## 🧪 Testando

### Script de Teste:
```bash
./test_csrf.sh
```

### Verificação Manual:
```python
from django.conf import settings
print("CSRF_TRUSTED_ORIGINS:", settings.CSRF_TRUSTED_ORIGINS)
print("DEBUG:", settings.DEBUG)
```

## 📋 Checklist de Verificação

- [ ] DEBUG=False em produção
- [ ] CSRF_TRUSTED_ORIGINS inclui sua URL do Cloud Run
- [ ] ADDITIONAL_TRUSTED_ORIGINS configurado se necessário
- [ ] Cookies seguros habilitados
- [ ] SECURE_PROXY_SSL_HEADER configurado

## 🚀 Deploy Atualizado

Após fazer as alterações, faça um novo deploy:

```bash
./scripts/deploy.sh PROJECT_ID jusia-backend
```

## 📞 Se o Problema Persistir

1. Verifique os logs do Cloud Run
2. Confirme se DEBUG=False
3. Teste com diferentes navegadores
4. Limpe cookies e cache do navegador
5. Verifique se a URL está exatamente correta
