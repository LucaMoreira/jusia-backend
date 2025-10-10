# Gunicorn configuration for Google Cloud Run
bind = "0.0.0.0:8080"
workers = 1
threads = 8
timeout = 0
keepalive = 2
max_requests = 1000
max_requests_jitter = 100
preload_app = True
accesslog = "-"
errorlog = "-"
loglevel = "info"
