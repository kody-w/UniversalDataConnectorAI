import os
import json
import logging
import base64
import mimetypes
from datetime import datetime
from agents.basic_agent import BasicAgent
from utils.azure_file_storage import AzureFileStorageManager

# Import Google Gemini libraries
try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logging.warning("Google Gemini libraries not installed. GeminiImageGenerator agent will not function.")

class GeminiImageGeneratorAgent(BasicAgent):
    def __init__(self):
        self.name = "GeminiImageGenerator"
        self.metadata = {
            "name": self.name,
            "description": "Generates images using Google's Gemini AI model based on text prompts. Can create custom images for presentations, reports, or creative needs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "The text prompt describing the image you want to generate. Be specific and descriptive for best results."
                    },
                    "save_to_azure": {
                        "type": "boolean",
                        "description": "Whether to save the generated image to Azure storage. Default is true."
                    },
                    "file_prefix": {
                        "type": "string",
                        "description": "Prefix for the generated image filename. Default is 'gemini_image'."
                    },
                    "user_guid": {
                        "type": "string",
                        "description": "Optional user GUID to organize images by user."
                    }
                },
                "required": ["prompt"]
            }
        }
        self.storage_manager = AzureFileStorageManager()
        self.gemini_api_key = os.environ.get('GEMINI_API_KEY')
        super().__init__(name=self.name, metadata=self.metadata)

    def perform(self, **kwargs):
        """
        Generates an image using Google's Gemini AI model.
        
        Args:
            prompt (str): The text prompt for image generation
            save_to_azure (bool): Whether to save to Azure storage (default: True)
            file_prefix (str): Prefix for the filename (default: 'gemini_image')
            user_guid (str): Optional user GUID for file organization
            
        Returns:
            str: Status message with details about the generated image
        """
        # Check if Gemini libraries are available
        if not GEMINI_AVAILABLE:
            return "Error: Google Gemini libraries are not installed. Please install with: pip install google-genai"
        
        # Check for API key
        if not self.gemini_api_key:
            return "Error: GEMINI_API_KEY environment variable is not set. Please configure your Gemini API key."
        
        # Extract parameters
        prompt = kwargs.get('prompt', '')
        save_to_azure = kwargs.get('save_to_azure', True)
        file_prefix = kwargs.get('file_prefix', 'gemini_image')
        user_guid = kwargs.get('user_guid')
        
        if not prompt:
            return "Error: No prompt provided for image generation."
        
        try:
            # Initialize Gemini client
            client = genai.Client(api_key=self.gemini_api_key)
            model = "gemini-2.5-flash-image-preview"
            
            # Prepare the content request
            contents = [
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=prompt),
                    ],
                ),
            ]
            
            # Configure generation to include both image and text
            generate_content_config = types.GenerateContentConfig(
                response_modalities=[
                    "IMAGE",
                    "TEXT",
                ],
            )
            
            # Generate content
            generated_images = []
            generated_text = []
            
            for chunk in client.models.generate_content_stream(
                model=model,
                contents=contents,
                config=generate_content_config,
            ):
                if (chunk.candidates is None or 
                    chunk.candidates[0].content is None or 
                    chunk.candidates[0].content.parts is None):
                    continue
                
                # Check for image data
                if (chunk.candidates[0].content.parts[0].inline_data and 
                    chunk.candidates[0].content.parts[0].inline_data.data):
                    
                    inline_data = chunk.candidates[0].content.parts[0].inline_data
                    data_buffer = inline_data.data
                    mime_type = inline_data.mime_type
                    file_extension = mimetypes.guess_extension(mime_type) or '.png'
                    
                    # Generate filename with timestamp
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"{file_prefix}_{timestamp}{file_extension}"
                    
                    if save_to_azure:
                        # Determine directory structure
                        if user_guid:
                            directory = f"generated_images/{user_guid}"
                        else:
                            directory = "generated_images/shared"
                        
                        # Save to Azure storage
                        success = self.storage_manager.write_file(
                            directory_name=directory,
                            file_name=filename,
                            content=data_buffer
                        )
                        
                        if success:
                            # Generate a download URL (valid for 30 minutes)
                            from datetime import datetime, timedelta
                            expiry_time = datetime.utcnow() + timedelta(minutes=30)
                            
                            download_url = self.storage_manager.generate_download_url(
                                directory=directory,
                                filename=filename,
                                expiry_time=expiry_time
                            )
                            
                            if download_url:
                                generated_images.append({
                                    'filename': filename,
                                    'path': f"{directory}/{filename}",
                                    'url': download_url,
                                    'mime_type': mime_type
                                })
                            else:
                                generated_images.append({
                                    'filename': filename,
                                    'path': f"{directory}/{filename}",
                                    'mime_type': mime_type
                                })
                    else:
                        # Just track that we generated an image
                        generated_images.append({
                            'filename': filename,
                            'mime_type': mime_type,
                            'size': len(data_buffer)
                        })
                        
                # Check for text response
                elif hasattr(chunk, 'text') and chunk.text:
                    generated_text.append(chunk.text)
            
            # Prepare response
            if not generated_images:
                return f"No images were generated for the prompt: '{prompt}'. The model may have refused or failed to generate the requested image."
            
            # Format the response
            response_parts = []
            
            if len(generated_images) == 1:
                img = generated_images[0]
                if 'url' in img:
                    response_parts.append(f"Successfully generated an image from prompt: '{prompt}'")
                    response_parts.append(f"Image saved to Azure: {img['path']}")
                    response_parts.append(f"Download URL (valid for 30 minutes): {img['url']}")
                    response_parts.append(f"You can display this image using: ![Generated Image]({img['url']})")
                elif 'path' in img:
                    response_parts.append(f"Successfully generated an image from prompt: '{prompt}'")
                    response_parts.append(f"Image saved to Azure: {img['path']}")
                else:
                    response_parts.append(f"Successfully generated an image from prompt: '{prompt}'")
                    response_parts.append(f"Image size: {img['size']} bytes")
            else:
                response_parts.append(f"Successfully generated {len(generated_images)} images from prompt: '{prompt}'")
                for i, img in enumerate(generated_images, 1):
                    if 'url' in img:
                        response_parts.append(f"Image {i}: {img['path']}")
                        response_parts.append(f"  URL: {img['url']}")
            
            # Add any text response from the model
            if generated_text:
                text_response = ' '.join(generated_text).strip()
                if text_response:
                    response_parts.append(f"Model response: {text_response}")
            
            return '\n'.join(response_parts)
            
        except Exception as e:
            error_msg = str(e)
            logging.error(f"Error generating image with Gemini: {error_msg}")
            
            # Provide helpful error messages
            if "API key" in error_msg:
                return "Error: Invalid or missing Gemini API key. Please check your GEMINI_API_KEY configuration."
            elif "quota" in error_msg.lower() or "limit" in error_msg.lower():
                return "Error: API quota exceeded. Please check your Gemini API usage limits."
            elif "model" in error_msg.lower():
                return "Error: The specified Gemini model may not be available or may not support image generation."
            else:
                return f"Error generating image: {error_msg}"
    
    def list_generated_images(self, user_guid=None, limit=10):
        """
        Helper method to list recently generated images.
        
        Args:
            user_guid (str): Optional user GUID to filter images
            limit (int): Maximum number of images to return
            
        Returns:
            str: List of generated images with their details
        """
        try:
            if user_guid:
                directory = f"generated_images/{user_guid}"
            else:
                directory = "generated_images/shared"
            
            files = self.storage_manager.list_files(directory)
            
            if not files:
                return f"No generated images found in {directory}"
            
            # Sort by name (which includes timestamp) and get most recent
            file_list = sorted([f for f in files], key=lambda x: x.name, reverse=True)[:limit]
            
            results = []
            for file in file_list:
                results.append(f"• {file.name}")
            
            return f"Recent generated images in {directory}:\n" + "\n".join(results)
            
        except Exception as e:
            logging.error(f"Error listing generated images: {str(e)}")
            return f"Error listing generated images: {str(e)}"