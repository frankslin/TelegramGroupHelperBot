"""CWD.PW image uploader module for the TelegramGroupHelperBot."""

import logging
import base64
import secrets
import aiohttp
from typing import Optional

from bot.config import CWD_PW_API_KEY

logger = logging.getLogger(__name__)


async def upload_base64_image_to_cwd(base64_data: str, api_key: str, model: str = None, prompt: str = None) -> Optional[str]:
    """Upload a base64 encoded image to cwd.pw.
    
    Args:
        base64_data: Base64 encoded image data with data URI prefix (e.g., "data:image/png;base64,...")
        api_key: API key for cwd.pw service
        model: The AI model used to generate the image
        prompt: The prompt used to generate the image
        
    Returns:
        The URL of the uploaded image, or None if upload failed.
    """
    try:
        # Extract MIME type and validate format
        if not base64_data.startswith('data:image/'):
            logger.error("Invalid base64 image format - missing data URI prefix")
            return None
            
        # Parse the data URI to extract MIME type and base64 data
        header, pure_base64 = base64_data.split(',', 1)
        mime_match = header.split(';')[0].replace('data:', '')
        
        if not mime_match.startswith('image/'):
            logger.error(f"Unsupported MIME type: {mime_match}")
            return None
            
        # Extract file extension from MIME type
        mime_parts = mime_match.split('/')
        if len(mime_parts) != 2:
            logger.error(f"Invalid MIME type format: {mime_match}")
            return None
            
        extension = mime_parts[1]
        # Normalize jpeg -> jpg
        if extension == 'jpeg':
            extension = 'jpg'
            
        # Validate supported formats
        if extension not in ['png', 'jpg', 'webp']:
            logger.error(f"Unsupported image format: {extension}")
            return None
        
        # Decode base64 to binary
        try:
            binary_data = base64.b64decode(pure_base64)
        except Exception as e:
            logger.error(f"Failed to decode base64 data: {e}")
            return None
        
        # Generate a random boundary for multipart form data
        boundary = '----WebKitFormBoundary' + secrets.token_hex(16)
        
        # Create multipart form data body
        body_parts = []
        
        # Image file part
        image_header = (
            f'--{boundary}\r\n'
            f'Content-Disposition: form-data; name="image"; filename="upload.{extension}"\r\n'
            f'Content-Type: {mime_match}\r\n'
            f'\r\n'
        ).encode('utf-8')
        
        # API key field
        api_key_field = (
            f'--{boundary}\r\n'
            f'Content-Disposition: form-data; name="api_key"\r\n'
            f'\r\n'
            f'{api_key}'
        ).encode('utf-8')
        
        # ai_generated field (always true)
        ai_generated_field = (
            f'--{boundary}\r\n'
            f'Content-Disposition: form-data; name="ai_generated"\r\n'
            f'\r\n'
            f'true'
        ).encode('utf-8')
        
        # model field
        model_field = (
            f'--{boundary}\r\n'
            f'Content-Disposition: form-data; name="model"\r\n'
            f'\r\n'
            f'{model or ""}'
        ).encode('utf-8')
        
        # prompt field
        prompt_field = (
            f'--{boundary}\r\n'
            f'Content-Disposition: form-data; name="prompt"\r\n'
            f'\r\n'
            f'{prompt or ""}'
        ).encode('utf-8')
        
        # Footer
        footer = f'--{boundary}--\r\n'.encode('utf-8')
        
        # Combine all parts
        body_parts = [
            image_header,
            binary_data,
            b'\r\n',
            api_key_field,
            b'\r\n',
            ai_generated_field,
            b'\r\n',
            model_field,
            b'\r\n',
            prompt_field,
            b'\r\n',
            footer
        ]
        body = b''.join(body_parts)
        
        # Set up headers
        headers = {
            'Content-Type': f'multipart/form-data; boundary={boundary}'
        }
        
        # Make the upload request
        async with aiohttp.ClientSession() as session:
            async with session.post(
                'https://cwd.pw/api/upload-image',
                headers=headers,
                data=body,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                
                if not response.ok:
                    error_text = await response.text()
                    logger.error(f"Upload failed with status {response.status}: {error_text}")
                    return None
                
                result = await response.json()
                
                if not result.get('success'):
                    logger.error(f"Upload error: {result}")
                    return None
                
                image_url = result.get('imageUrl')
                if image_url:
                    logger.info(f"Successfully uploaded image to cwd.pw: {image_url}")
                    return image_url
                else:
                    logger.error("Upload response missing imageUrl")
                    return None
                    
    except Exception as e:
        logger.error(f"Error uploading image to cwd.pw: {e}", exc_info=True)
        return None


async def upload_image_bytes_to_cwd(image_bytes: bytes, api_key: str, mime_type: str = "image/jpeg", model: str = None, prompt: str = None) -> Optional[str]:
    """Upload raw image bytes to cwd.pw.
    
    Args:
        image_bytes: Raw image data as bytes
        api_key: API key for cwd.pw service
        mime_type: MIME type of the image (default: image/jpeg)
        model: The AI model used to generate the image
        prompt: The prompt used to generate the image
        
    Returns:
        The URL of the uploaded image, or None if upload failed.
    """
    try:
        # Convert bytes to base64 data URI
        base64_encoded = base64.b64encode(image_bytes).decode('utf-8')
        base64_data = f"data:{mime_type};base64,{base64_encoded}"
        
        # Use the base64 upload function
        return await upload_base64_image_to_cwd(base64_data, api_key, model, prompt)
        
    except Exception as e:
        logger.error(f"Error converting image bytes to base64 for cwd.pw upload: {e}", exc_info=True)
        return None


async def upload_to_cwd_pw_paste(title: str, content: str, user_prompt: str = '', debug_info: str = '', raw_response: str = '') -> Optional[str]:
    """Upload AI generated content to cwd.pw pastebin service.
    
    Args:
        title: The title of the paste.
        content: The content to upload.
        user_prompt: Optional user prompt that generated this content.
        debug_info: Optional debug information.
        raw_response: Optional raw response from AI.
        
    Returns:
        The URL of the created paste, or None if creation failed.
    """
    try:
        logger.info(f'Uploading to cwd.pw pastebin, content length: {len(content)}')
        metadata = {
            'source': 'https://github.com/frankslin/TelegramGroupHelperBot',
        }
        
        payload = {
            'title': title,
            'content': content,
            'userPrompt': user_prompt,
            'debugInfo': debug_info,
            'rawResponse': raw_response,
            'metadata': metadata,
        }
        
        headers = {
            'X-API-Key': CWD_PW_API_KEY,
            'Content-Type': 'application/json',
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                'https://cwd.pw/api/paste',
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                
                if response.status in [301, 302]:
                    location = response.headers.get('Location')
                    if location:
                        logger.info(f'cwd.pw paste created: {location}')
                        return location
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to create cwd.pw paste: HTTP {response.status}, {error_text}")
                    return None
            
    except Exception as e:
        logger.error(f"Error uploading to cwd.pw pastebin: {e}", exc_info=True)
        return None