import unittest
from unittest.mock import patch, MagicMock
from django.test import TestCase
from albedo.amocrm_integration import create_amocrm_lead
from django.conf import settings

class AmoCRMIntegrationTest(TestCase):
    @patch('requests.post')
    @patch('requests.get')
    def test_create_contact_in_lists(self, mock_get, mock_post):
        """Тест только добавления в Списки (Контакты)"""
        # 1. Мокаем поиск контакта (не найден)
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"_embedded": {"contacts": []}}
        
        # 2. Мокаем создание контакта
        mock_contact_resp = MagicMock()
        mock_contact_resp.status_code = 200
        mock_contact_resp.json.return_value = {"_embedded": {"contacts": [{"id": 111}]}}
        
        mock_post.return_value = mock_contact_resp
        
        # Вызываем функцию
        result = create_amocrm_lead("Test User", "test@example.com")
        
        # Проверяем результат
        self.assertTrue(result)
        self.assertEqual(mock_get.call_count, 1)
        self.assertEqual(mock_post.call_count, 1) # Только создание контакта
        print("\n[OK] Test: create_contact_in_lists")

    @patch('requests.patch')
    @patch('requests.get')
    def test_update_contact_in_lists(self, mock_get, mock_patch):
        """Тест обновления контакта в Списках"""
        # 1. Мокаем поиск контакта (найден)
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"_embedded": {"contacts": [{"id": 12345}]}}
        
        # 2. Мокаем патч контакта
        mock_patch.return_value.status_code = 200
        
        # Вызываем функцию
        result = create_amocrm_lead("Updated User", "existing@example.com")
        
        # Проверяем результат
        self.assertTrue(result)
        self.assertEqual(mock_get.call_count, 1)
        self.assertEqual(mock_patch.call_count, 1)
        print("[OK] Test: update_contact_in_lists")

    @patch('requests.get')
    def test_api_error_handling(self, mock_get):
        """Тест обработки ошибки API"""
        # Имитируем ошибку соединения или 401
        mock_get.side_effect = Exception("API Connection Error")
        
        result = create_amocrm_lead("Error User", "error@example.com")
        
        self.assertFalse(result)
        print("[OK] Test: api_error_handling")
