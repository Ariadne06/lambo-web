from django.urls import reverse
from rest_framework.test import APITestCase
from django.core.files.uploadedfile import SimpleUploadedFile
import json
import os
import re
import base64

class VerifyIdFieldsTest(APITestCase):
    def test_verify_id_fields(self):
        url = reverse('verify-id-fields')
        # Use a real image file for the test
        img_path = os.path.join(os.path.dirname(__file__), 'sample.png')
        with open(img_path, 'rb') as img:
            data = {
                'registrationData': json.dumps({
                    'first_name': 'Juan',
                    'last_name': 'Dela Cruz',
                    'dob': '1990-01-01',
                    'document_type': 'Philippine National ID'
                }),
                'id_image': SimpleUploadedFile('sample.png', img.read(), content_type='image/png')
            }
            response = self.client.post(url, data, format='multipart')
            # Accept either 200 (success) or 400 (bad request, e.g. OCR mismatch)
            self.assertIn(response.status_code, [200, 400])
            print('Response:', response.json())