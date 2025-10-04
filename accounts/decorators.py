from django.utils.functional import wraps
from .utils import get_auth, is_user_in_groups, is_authenticated
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings


HEADERS      = {
    "Access-Control-Allow-Origin": settings.FRONTEND_URL,
    "Access-Control-Allow-Methods": "POST, PUT, PATCH, GET, DELETE, OPTIONS",
    "Access-Control-Allow-Headers": "Origin, X-Api-Key, X-Requested-With, Content-Type, Accept, Authorization"
    }
SUCCESS      = status.HTTP_200_OK
ERROR        = status.HTTP_400_BAD_REQUEST


def check_auth(required_auth:list):
    
    
    def decorator(view_function): 
        
        
        @wraps(view_function)
        def wrapper(request, *args, **kwargs):
            user       = request.data['user']
            token      = request.data['token']
            auth, msg  = get_auth(request, user, token)
            
            if auth['auth'] in required_auth:
                return view_function(request, *args, **kwargs)
            
            else:
                return Response(status=status.HTTP_401_UNAUTHORIZED, headers=HEADERS)
        
        
        return wrapper
    
    
    return decorator

def group_required(required_groups:list):
    
    
    def decorator(view_function): 
        
        
        @wraps(view_function)
        def wrapper(request, *args, **kwargs):
            try:
                username       = request.data['user']
                
                if is_authenticated(request) and is_user_in_groups(username, required_groups):
                    return view_function(request, *args, **kwargs)
                
                else:
                    return Response(status=status.HTTP_401_UNAUTHORIZED, headers=HEADERS)
                
            except Exception as e:
                print(e)
                return Response(status=status.HTTP_401_UNAUTHORIZED, headers=HEADERS)
        
        
        return wrapper
    
    
    return decorator