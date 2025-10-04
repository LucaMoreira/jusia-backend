from rest_framework import status
from rest_framework.test import APITestCase
from django.http import HttpResponse
from .models import CustomUser
from django.conf import settings
from django.test import TestCase
import json


USER     : str = 'Luca'
EMAIL    : str = 'luca@example.com'
PASSWORD : str = 'senha'


class ApiTests(APITestCase):
    """
    Ensure all api routes are working correctly.
    """
    
    
    def setUp(self) -> None:
        """
        Ensure we can create and login with a user.
        """
        
        register_url   : str   = '/accounts/create_user/'
        register_data  : dict  = {
            "username" : USER,
            "email"    : EMAIL,
            "password": PASSWORD,
        }
        register_response : HttpResponse = self.client.post(register_url, register_data, format='json')
        self.token        : str          = json.loads(register_response.content)['access']
        self.refresh : str = json.loads(register_response.content)['refresh']
        self.assertEqual(register_response.status_code, status.HTTP_201_CREATED, 'Register failed!')
        
        user          = CustomUser.objects.get(username=USER)
        user.is_staff = True
        user.save()
        
        login_url      : str  = '/accounts/login/'
        login_data     : dict = {
            "email"    : EMAIL, 
            'password' : PASSWORD,
        }
        login_response : HttpResponse = self.client.post(login_url, login_data, format='json')
        self.assertEqual(login_response.status_code, status.HTTP_200_OK, 'Login failed!')


    def test_get_user(self) -> None:
        """
        Ensure we can get a user.
        """
        get_url    : str  = '/accounts/get_user/'
        get_response : HttpResponse = self.client.get(get_url, format='json', HTTP_AUTHORIZATION=f'Bearer {self.token}')
        self.assertEqual(get_response.status_code, status.HTTP_200_OK, 'Get user failed!')


    def test_change_email(self) -> None:
        """
        Ensure we can change user email.
        """
        change_email_url  : str  = '/accounts/changeemail/'
        change_email_data : dict = {
            'email'       : 'lucamoreira@example.com'
        }
        change_email_response : HttpResponse = self.client.put(change_email_url, change_email_data, format='json', HTTP_AUTHORIZATION=f'Bearer {self.token}')
        self.assertEqual(change_email_response.status_code, status.HTTP_200_OK, 'Change user email failed!')


    def test_change_password(self) -> None:
        """
        Ensure we can change user password.
        """
        change_password_url  : str  = '/accounts/changepassword/'
        change_password_data : dict = {
            'new_password' : 'senha1234',
            'old_password' : PASSWORD
        }
        change_password_response : HttpResponse = self.client.put(change_password_url, change_password_data, format='json', HTTP_AUTHORIZATION=f'Bearer {self.token}')
        self.assertEqual(change_password_response.status_code, status.HTTP_200_OK, 'Change user password failed!')


    def test_logout_user(self) -> None:
        """
        Ensure we can logout a user.
        """
        logout_url  : str  = '/accounts/logout/'
        logout_data : dict = {
            'refresh' : self.refresh
        }
        logout_response : HttpResponse = self.client.post(logout_url, logout_data, format='json', HTTP_AUTHORIZATION=f'Bearer {self.token}')
        self.assertEqual(logout_response.status_code, status.HTTP_205_RESET_CONTENT, 'Logout failed!')


    def test_delete_user(self) -> None:
        """
        Ensure we can delete a user.
        """
        delete_url  : str  = '/accounts/delete_user/'
        delete_response : HttpResponse = self.client.delete(delete_url, {}, format='json', HTTP_AUTHORIZATION=f'Bearer {self.token}')
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT, 'Delete user failed!')


    def test_recover_password(self) -> None:
        """
        Ensure we can recover a password.
        """
        recover_password_url  : str  = '/accounts/recoverpassword/'
        recover_password_data : dict = {
            'email'           : 'lucamoreiraofficial@gmail.com'
        }
        recover_password_response : HttpResponse = self.client.post(recover_password_url, recover_password_data, format='json')
        self.assertEqual(recover_password_response.status_code, status.HTTP_200_OK, 'Recover user password failed!')


    def test_contact(self) -> None:
        """
        Ensure we can recieve contact from custumers.
        """
        contact_url   : str = '/accounts/contact/'
        contact_data  : dict = {
            'name'    : 'Luca',
            'email'   : 'lucamoreiraofficial@gmail.com',
            'subject' : 'Contact test',
            'message' : 'It worked!'
        }
        contact_response : HttpResponse = self.client.post(contact_url, contact_data, format='json')
        self.assertEqual(contact_response.status_code, status.HTTP_200_OK, 'Contact failed!')


    def test_check_auth(self) -> None:
        """
        Ensure we can get user auth.
        """
        check_auth_url  : str  = '/accounts/check_auth/'
        check_auth_data : dict = {
            'user'      : USER,
            'token'     : self.token
        }
        check_auth_response : HttpResponse = self.client.post(check_auth_url, check_auth_data, format='json')
        self.assertEqual(check_auth_response.status_code, status.HTTP_200_OK, 'Get user auth failed!')