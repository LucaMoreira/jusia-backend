from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.core.mail import send_mail
from django.shortcuts import redirect
from rest_framework import status
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
import stripe

from .decorators import check_auth, group_required
from .models import CustomUser
from .serializers import UserSerializer
from .utils import (
    create_password_token,
    get_auth,
    user_exists,
)

# Create your views here.
TOKEN_EXPIRE = 86400
HEADERS      = {
    "Access-Control-Allow-Origin": settings.FRONTEND_URL,
    "Access-Control-Allow-Methods": "POST, PUT, PATCH, GET, DELETE, OPTIONS",
    "Access-Control-Allow-Headers": "Origin, X-Api-Key, X-Requested-With, Content-Type, Accept, Authorization, X-Refresh-Token"
    }
SUCCESS      = status.HTTP_200_OK
ERROR        = status.HTTP_400_BAD_REQUEST

stripe.api_key = settings.STRIPE_PRIVATE_KEY


#* --- USER CRUD --- *#
@api_view(["POST"])
@permission_classes([AllowAny])
def create_user(request):
    print("Request data:", request.data)
    serializer = UserSerializer(data=request.data)
    
    if serializer.is_valid():
        print("Serializer is valid, calling save()...")
        user = serializer.save()
        print(f"User returned from serializer.save(): {user}")
        
        if user is None:
            print("ERROR: serializer.save() returned None!")
            return Response({
                'error': 'User creation failed',
                'message': 'Serializer returned None'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        user.is_active = True
        user.save()
        
        password = request.data.get('password')
        print(f"Password: {password}")

        # Try to authenticate the user
        authenticated_user = authenticate(email=user.email, password=password)
        print(f"Authentication result: {authenticated_user}")
        
        if authenticated_user is not None:
            refresh = RefreshToken.for_user(authenticated_user)
            return Response({ 
                'user': serializer.data, 
                'access': str(refresh.access_token), 
                'refresh': str(refresh)
            }, status=status.HTTP_201_CREATED)
        else:
            print("Authentication failed")
            return Response({
                'error': 'Authentication failed',
                'message': 'User created but authentication failed'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    print("Serializer errors:", serializer.errors)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_user(request):
    user = request.user
    serializer = UserSerializer(user)
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_users(request):
    """Listar todos os usuários - apenas para superusers"""
    if not request.user.is_superuser:
        return Response({'error': 'Acesso negado. Apenas superusers podem listar usuários.'}, 
                       status=status.HTTP_403_FORBIDDEN)
    
    users = CustomUser.objects.all().order_by('-date_joined')
    serializer = UserSerializer(users, many=True)
    return Response(serializer.data)


@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def update_user(request, user_id):
    """Atualizar usuário - apenas para superusers"""
    if not request.user.is_superuser:
        return Response({'error': 'Acesso negado. Apenas superusers podem atualizar usuários.'}, 
                       status=status.HTTP_403_FORBIDDEN)
    
    try:
        user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        return Response({'error': 'Usuário não encontrado.'}, status=status.HTTP_404_NOT_FOUND)
    
    serializer = UserSerializer(user, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_user_admin(request, user_id):
    """Deletar usuário - apenas para superusers"""
    if not request.user.is_superuser:
        return Response({'error': 'Acesso negado. Apenas superusers podem deletar usuários.'}, 
                       status=status.HTTP_403_FORBIDDEN)
    
    try:
        user = CustomUser.objects.get(id=user_id)
        # Não permitir deletar a si mesmo
        if user.id == request.user.id:
            return Response({'error': 'Você não pode deletar sua própria conta.'}, 
                           status=status.HTTP_400_BAD_REQUEST)
        user.delete()
        return Response({'message': 'Usuário deletado com sucesso.'}, status=status.HTTP_200_OK)
    except CustomUser.DoesNotExist:
        return Response({'error': 'Usuário não encontrado.'}, status=status.HTTP_404_NOT_FOUND)


@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def update_profile(request):
    """Atualizar perfil do usuário autenticado"""
    user = request.user
    serializer = UserSerializer(user, data=request.data, partial=True)
    
    if serializer.is_valid():
        # Remove campos que não devem ser atualizados pelo usuário
        validated_data = serializer.validated_data
        validated_data.pop('is_staff', None)
        validated_data.pop('is_superuser', None)
        validated_data.pop('is_active', None)
        validated_data.pop('password', None)  # Use update_password para senha
        
        for attr, value in validated_data.items():
            setattr(user, attr, value)
        
        user.save()
        
        return Response({
            'message': 'Perfil atualizado com sucesso',
            'user': UserSerializer(user).data
        }, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def update_email(request):
    user = request.user
    new_email = request.data.get("email")

    if not new_email:
        return Response(
            {"error": "Email é obrigatório."},
            status=status.HTTP_400_BAD_REQUEST
        )

    user.email = new_email
    user.save()

    return Response(
        {"email": user.email},
        status=status.HTTP_200_OK
    )


@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def update_password(request):
    user = request.user
    old_password = request.data.get("old_password")
    new_password = request.data.get("new_password")

    # valida se ambos foram enviados
    if not old_password or not new_password:
        return Response(
            {"error": "É necessário informar old_password e new_password."},
            status=status.HTTP_400_BAD_REQUEST
        )

    # confere se a senha antiga está correta
    if not user.check_password(old_password):
        return Response(
            {"error": "Senha atual incorreta."},
            status=status.HTTP_400_BAD_REQUEST
        )

    # atualiza a senha
    user.set_password(new_password)
    user.save()

    return Response(
        {"message": "Senha atualizada com sucesso."},
        status=status.HTTP_200_OK
    )


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_user(request):
    user = request.user
    user.delete()
    return Response({"detail": "Conta excluída com sucesso."}, status=status.HTTP_204_NO_CONTENT)


#* --- AUTH --- *#
@api_view(['POST'])
@permission_classes([AllowAny])
def login_user(request):
    email = request.data.get('email')
    password = request.data.get('password')
    
    try:
        user = CustomUser.objects.get(email=email)
        if user.check_password(password):
            refresh = RefreshToken.for_user(user)
            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh)
            })
        else:
            return Response({'detail': 'Credenciais inválidas'}, status=status.HTTP_401_UNAUTHORIZED)
    except CustomUser.DoesNotExist:
        return Response({'detail': 'Credenciais inválidas'}, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_user(request):
    try:
        print(f"Logout request data: {request.data}")
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response({"detail": "Token de refresh não fornecido."}, status=status.HTTP_400_BAD_REQUEST)
        
        token = RefreshToken(refresh_token)
        token.blacklist()
        print("Token blacklisted successfully")
        return Response({"detail": "Logout realizado com sucesso."}, status=status.HTTP_205_RESET_CONTENT)
    except Exception as e:
        print(f"Logout error: {e}")
        return Response({"detail": f"Erro ao realizar logout: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def check_auth(request):
    try:
        print(f"check_auth called with headers: {request.headers}")
        print(f"check_auth called with data: {request.data}")
        auth , msg = get_auth(request)
        print(f"get_auth returned: {auth}, {msg}")
        if auth['auth'] == 'Visitor':
            return Response(auth, status=status.HTTP_401_UNAUTHORIZED, headers=HEADERS)
        return Response(auth, status=SUCCESS, headers=HEADERS)
    except Exception as e:
        print(f"Exception in check_auth: {e}")
        return Response({'auth': 'Visitor'}, status=status.HTTP_401_UNAUTHORIZED, headers=HEADERS)


@api_view(["POST"])
@permission_classes([AllowAny])
def refresh_token(request):
    view = TokenRefreshView.as_view()
    return view(request._request)


@api_view(["POST"])
def forgot_password(request):
    try:
        email = request.data['email']
        if user_exists(email):
            user  = CustomUser.objects.get(email=email)
            token = create_password_token(user.username)
            
            send_mail(
                'Recuperação de senha - Cloud Pharma',
                f'Entre no link abaixo {settings.FRONTEND_URL}/recoverpassword/{token}',
                settings.EMAIL_HOST_USER,
                [email],
                fail_silently=False,
            )
        
        return Response(status=SUCCESS, headers=HEADERS)

    except Exception as e:
        return Response(status=ERROR, headers=HEADERS)


@api_view(['POST'])
def validadte_password_token(request):
    token = request.data['token']
    
    try:
        #PasswordToken.objects.get(id=token)
        is_expired         = token_expire_handler(token)
        if is_expired:
            return Response(status=ERROR, headers=HEADERS)
        
        return Response(status=SUCCESS, headers=HEADERS)

    except Exception as e:
        return Response(status=ERROR, headers=HEADERS)


#* --- SUBSCRIPTIONS --- *#
@api_view(['POST'])
def create_subscription(request):
    data = request.data
    try:
        checkout_session = stripe.checkout.Session.create(
            line_items = [
                {
                'price' : data['price_id'],
                'quantity' : 1
                }
            ],
            mode = 'subscription', 
            success_url = settings.FRONTEND_URL + '/success/{CHECKOUT_SESSION_ID}',
            cancel_url  = settings.FRONTEND_URL + '/failure'       
        )
        return redirect(checkout_session.url , code=303)
    except Exception as message:
        return Response(message, status=ERROR, headers=HEADERS)


@api_view(['POST'])
def delete_subscription(request):
    username   = request.data['user']
    token      = request.data['token']

    auth , msg = get_auth(request, username, token)
    
    if auth['auth'] == 'Client':
        user = CustomUser.objects.get(username=username)
        stripe.Subscription.cancel(user.sub_id)
        user.sub_id = ''
        user.status = True
        user.save()
        return Response(status=SUCCESS, headers=HEADERS)
    else:
        return Response(status=ERROR, headers=HEADERS)


@api_view(['POST'])
def validate_stripe_payment(request):
    try:
        session_id = request.data['id']
        session    = stripe.checkout.Session.retrieve(session_id)
        sub_id     = session['subscription']
        username   = request.data['user']
        token      = request.data['token']
        
        auth, msg = get_auth(request, username, token)
        
        if auth['auth'] != 'User':
            return Response(status=ERROR, headers=HEADERS)
        
        newuser        = CustomUser.objects.get(username=username)
        newuser.sub_id = sub_id
        newuser.status = True
        newuser.save()

        return Response(data={'message': 'Success'}, status=status.HTTP_200_OK, headers=HEADERS)

    except:
        return Response(data={'message': 'Error'}, status=ERROR, headers=HEADERS)


#* --- MESSAGING --- *#
@api_view(['POST'])
def contact(request):
    try:
        name    = request.data['name']
        email   = request.data['email']
        subject = request.data['subject']
        message = request.data['message']
        
        send_mail(
                subject        = subject,
                message        = f'Mensagem de {name}({email}): \n{message}',
                from_email     = settings.EMAIL_HOST_USER,
                recipient_list = [settings.EMAIL_HOST_USER],
                fail_silently  = False,
            )
        
        return Response(status=SUCCESS, headers=HEADERS)

    except Exception as e:
        return Response(status=ERROR, headers=HEADERS)


#* --- DECORATOR TEST --- *#
@api_view(['POST'])
@group_required(['Active Users (Cloudpharma)'])
def test_decorator(request):
    return Response(status=SUCCESS, headers=HEADERS)