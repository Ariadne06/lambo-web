import os
import uuid
import mimetypes
from django.conf import settings
import tempfile

def upload_file_to_supabase(file, bucket_name='resident-documents', folder='id-documents'):
    """
    Upload file to Supabase Storage and return the file path
    """
    # Import here to avoid circular imports
    from supabase import create_client
    
    # Create Supabase client
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY')
    
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise Exception("Supabase configuration missing")
    
    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    
    try:
        # Detect MIME type and ensure it's an image
        content_type = file.content_type
        print(f"Original content type: {content_type}")
        
        # If content type is text/plain or not set, try to detect from filename
        if content_type == 'text/plain' or not content_type or not content_type.startswith('image/'):
            # Try to detect from filename
            mime_type, _ = mimetypes.guess_type(file.name)
            if mime_type and mime_type.startswith('image/'):
                content_type = mime_type
            else:
                # Default to JPEG if we can't detect
                content_type = 'image/jpeg'
        
        print(f"Using content type: {content_type}")
        
        # Generate unique filename with proper extension
        file_extension = os.path.splitext(file.name)[1]
        if not file_extension:
            # If no extension, add .jpg as default
            file_extension = '.jpg'
        
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = f"{folder}/{unique_filename}"
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            for chunk in file.chunks():
                temp_file.write(chunk)
            temp_file_path = temp_file.name
        
        try:
            # Upload to Supabase Storage with proper content type
            with open(temp_file_path, 'rb') as f:
                response = supabase.storage.from_(bucket_name).upload(
                    file_path, 
                    f,
                    file_options={
                        'content-type': content_type,
                        'cache-control': '3600'
                    }
                )
            
            # Clean up temp file
            os.unlink(temp_file_path)
            
            print(f"Upload response: {response}")
            
            # Check if upload was successful
            if hasattr(response, 'status_code') and response.status_code == 200:
                return file_path
            elif hasattr(response, 'error') and response.error:
                raise Exception(f"Upload failed: {response.error}")
            else:
                # If no error, assume success
                return file_path
                
        except Exception as e:
            # Clean up temp file on error
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
            raise e
            
    except Exception as e:
        raise Exception(f"Failed to upload file to Supabase: {str(e)}")