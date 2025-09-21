import os
import json
import logging
import base64
import mimetypes
import secrets
from datetime import datetime, timedelta
from agents.basic_agent import BasicAgent
from utils.azure_file_storage import AzureFileStorageManager
from google import genai
from google.genai import types

class GeminiImageGeneratorAgent(BasicAgent):
    def __init__(self):
        self.name = 'GeminiImageGenerator'
        self.metadata = {
            "name": self.name,
            "description": "Generates images using Google Gemini 2.5 Flash Image Preview model with exact API pattern",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "Action to perform: 'generate_image', 'batch_generate', 'get_api_key', 'create_html_client'",
                        "enum": ["generate_image", "batch_generate", "get_api_key", "create_html_client"]
                    },
                    "prompt": {
                        "type": "string",
                        "description": "Text prompt describing the image to generate"
                    },
                    "prompts": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Array of prompts for batch generation"
                    },
                    "save_to_storage": {
                        "type": "boolean",
                        "description": "Whether to save generated images to Azure storage"
                    },
                    "output_format": {
                        "type": "string",
                        "description": "Output format: 'base64' for direct embedding, 'url' for storage URL",
                        "enum": ["base64", "url", "both"]
                    },
                    "user_guid": {
                        "type": "string",
                        "description": "User GUID for organizing generated images"
                    },
                    "include_text_response": {
                        "type": "boolean",
                        "description": "Include text response from Gemini along with image"
                    },
                    "api_key_validity_minutes": {
                        "type": "integer",
                        "description": "For get_api_key action: minutes until key expires",
                        "minimum": 5,
                        "maximum": 1440
                    }
                },
                "required": ["action"]
            }
        }
        self.storage_manager = AzureFileStorageManager()
        super().__init__(name=self.name, metadata=self.metadata)
    
    def perform(self, **kwargs):
        """Main entry point for the agent"""
        action = kwargs.get('action')
        
        if action == 'generate_image':
            return self._generate_single_image(kwargs)
        elif action == 'batch_generate':
            return self._batch_generate_images(kwargs)
        elif action == 'get_api_key':
            return self._provide_api_key_handshake(kwargs)
        elif action == 'create_html_client':
            return self._create_html_client()
        else:
            return json.dumps({"status": "error", "message": "Invalid action specified"})
    
    def save_binary_file(self, file_name, data):
        """Save binary file matching Colab pattern exactly"""
        try:
            # Create directory structure
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            directory = f"generated_images/{datetime.now().strftime('%Y-%m-%d')}"
            self.storage_manager.ensure_directory_exists(directory)
            
            # Write file to Azure storage
            success = self.storage_manager.write_file(directory, file_name, data)
            
            if success:
                print(f"File saved to: {directory}/{file_name}")
                return f"{directory}/{file_name}"
            return None
        except Exception as e:
            logging.error(f"Error saving file: {str(e)}")
            return None
    
    def generate(self, prompt_text, user_guid="default", save_to_storage=True):
        """Generate image using exact Colab pattern"""
        # Initialize client - exact match to Colab
        client = genai.Client(
            api_key=os.environ.get("GEMINI_API_KEY"),
        )
        
        # Model name - exact match to Colab
        model = "gemini-2.5-flash-image-preview"
        
        # Create contents - exact match to Colab structure
        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=prompt_text),
                ],
            ),
        ]
        
        # Generate content config - exact match to Colab
        generate_content_config = types.GenerateContentConfig(
            response_modalities=[
                "IMAGE",
                "TEXT",
            ],
        )
        
        # Results storage
        generated_images = []
        text_responses = []
        file_index = 0
        
        # Stream generation - exact match to Colab pattern
        for chunk in client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=generate_content_config,
        ):
            if (
                chunk.candidates is None
                or chunk.candidates[0].content is None
                or chunk.candidates[0].content.parts is None
            ):
                continue
            
            # Check for image data - exact match to Colab
            if chunk.candidates[0].content.parts[0].inline_data and chunk.candidates[0].content.parts[0].inline_data.data:
                file_name = f"gemini_{user_guid}_{file_index}"
                file_index += 1
                inline_data = chunk.candidates[0].content.parts[0].inline_data
                data_buffer = inline_data.data
                file_extension = mimetypes.guess_extension(inline_data.mime_type)
                
                # Save using exact Colab pattern
                full_file_name = f"{file_name}{file_extension}"
                storage_path = None
                if save_to_storage:
                    storage_path = self.save_binary_file(full_file_name, data_buffer)
                
                # Convert to base64 for web display
                base64_image = base64.b64encode(data_buffer).decode('utf-8')
                
                # Store image data
                generated_images.append({
                    "file_name": full_file_name,
                    "base64": f"data:{inline_data.mime_type};base64,{base64_image}",
                    "mime_type": inline_data.mime_type,
                    "size": len(data_buffer),
                    "storage_path": storage_path,
                    "generated_at": datetime.now().isoformat()
                })
                
            else:
                # Text response - exact match to Colab
                print(chunk.text)
                text_responses.append(chunk.text)
        
        return {
            "status": "success",
            "images": generated_images,
            "text_responses": text_responses,
            "prompt": prompt_text,
            "user_guid": user_guid
        }
    
    def _generate_single_image(self, kwargs):
        """Generate a single image using the exact pattern"""
        prompt = kwargs.get('prompt')
        user_guid = kwargs.get('user_guid', 'default')
        save_to_storage = kwargs.get('save_to_storage', True)
        output_format = kwargs.get('output_format', 'both')
        
        if not prompt:
            return json.dumps({"status": "error", "message": "Prompt is required"})
        
        # Check API key
        if not os.environ.get("GEMINI_API_KEY"):
            return json.dumps({"status": "error", "message": "GEMINI_API_KEY not set in environment"})
        
        try:
            # Use the generate function with exact Colab pattern
            result = self.generate(prompt, user_guid, save_to_storage)
            
            if result['status'] == 'error':
                return json.dumps(result)
            
            # Add download URLs if saved to storage
            if save_to_storage and result.get('images'):
                for img in result["images"]:
                    if img.get("storage_path"):
                        try:
                            expiry_time = datetime.utcnow() + timedelta(hours=24)
                            parts = img["storage_path"].split('/')
                            directory = '/'.join(parts[:-1])
                            filename = parts[-1]
                            download_url = self.storage_manager.generate_download_url(
                                directory, 
                                filename, 
                                expiry_time
                            )
                            img["download_url"] = download_url
                        except Exception as e:
                            logging.error(f"Error generating download URL: {str(e)}")
            
            # Format based on output_format preference
            if output_format == "url" and save_to_storage:
                # Remove base64 data if only URLs requested
                for img in result.get("images", []):
                    img.pop("base64", None)
            elif output_format == "base64":
                # Remove storage paths if only base64 requested
                for img in result.get("images", []):
                    img.pop("storage_path", None)
                    img.pop("download_url", None)
            
            return json.dumps(result)
            
        except Exception as e:
            logging.error(f"Error generating image: {str(e)}")
            return json.dumps({
                "status": "error",
                "message": f"Generation failed: {str(e)}"
            })
    
    def _batch_generate_images(self, kwargs):
        """Generate multiple images using the exact pattern"""
        prompts = kwargs.get('prompts', [])
        user_guid = kwargs.get('user_guid', 'default')
        save_to_storage = kwargs.get('save_to_storage', True)
        output_format = kwargs.get('output_format', 'both')
        
        if not prompts or not isinstance(prompts, list):
            return json.dumps({"status": "error", "message": "Prompts array is required"})
        
        # Check API key
        if not os.environ.get("GEMINI_API_KEY"):
            return json.dumps({"status": "error", "message": "GEMINI_API_KEY not set in environment"})
        
        all_results = []
        errors = []
        
        for i, prompt in enumerate(prompts):
            logging.info(f"Generating image {i+1}/{len(prompts)}")
            
            try:
                # Use the generate function for each prompt
                result = self.generate(prompt, user_guid, save_to_storage)
                
                if result['status'] == 'success':
                    # Add download URLs if needed
                    if save_to_storage and result.get('images'):
                        for img in result["images"]:
                            if img.get("storage_path"):
                                try:
                                    expiry_time = datetime.utcnow() + timedelta(hours=24)
                                    parts = img["storage_path"].split('/')
                                    directory = '/'.join(parts[:-1])
                                    filename = parts[-1]
                                    download_url = self.storage_manager.generate_download_url(
                                        directory, 
                                        filename, 
                                        expiry_time
                                    )
                                    img["download_url"] = download_url
                                except Exception as e:
                                    logging.error(f"Error generating download URL: {str(e)}")
                    
                    all_results.append({
                        "prompt": prompt,
                        "images": result['images'],
                        "text_responses": result.get('text_responses', [])
                    })
                else:
                    errors.append({
                        "prompt": prompt,
                        "error": result.get('message', 'Unknown error')
                    })
                    
            except Exception as e:
                errors.append({
                    "prompt": prompt,
                    "error": str(e)
                })
        
        return json.dumps({
            "status": "success" if all_results else "error",
            "batch_results": all_results,
            "successful": len(all_results),
            "failed": len(errors),
            "errors": errors if errors else None,
            "total_prompts": len(prompts)
        })
    
    def _provide_api_key_handshake(self, kwargs):
        """Provide time-limited API key for client-side usage"""
        validity_minutes = kwargs.get('api_key_validity_minutes', 60)
        user_guid = kwargs.get('user_guid', 'default')
        
        try:
            # Get API key from environment - matching Colab
            api_key = os.environ.get("GEMINI_API_KEY")
            if not api_key:
                return json.dumps({"status": "error", "message": "GEMINI_API_KEY not configured"})
            
            # Generate one-time token
            token = secrets.token_urlsafe(32)
            expiry = datetime.now() + timedelta(minutes=validity_minutes)
            
            # Store token mapping
            token_data = {
                "token": token,
                "api_key": api_key,  # In production, encrypt this
                "user_guid": user_guid,
                "expires_at": expiry.isoformat(),
                "created_at": datetime.now().isoformat(),
                "used": False
            }
            
            # Save token
            token_dir = f"api_tokens/{user_guid}"
            self.storage_manager.ensure_directory_exists(token_dir)
            self.storage_manager.write_file(
                token_dir,
                f"token_{token[:8]}.json",
                json.dumps(token_data, indent=2)
            )
            
            return json.dumps({
                "status": "success",
                "handshake_token": token,
                "expires_at": expiry.isoformat(),
                "validity_minutes": validity_minutes,
                "message": "Use this token to authenticate in the HTML client"
            })
            
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})
    
    def _create_html_client(self):
        """Generate the HTML client that uses the exact API pattern"""
        html_content = self._generate_html_content()
        
        try:
            # Save HTML file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"gemini_image_generator_{timestamp}.html"
            
            self.storage_manager.ensure_directory_exists("html_clients")
            self.storage_manager.write_file("html_clients", filename, html_content)
            
            return f"HTML client created successfully!\nFilename: {filename}\nSize: {len(html_content)} bytes\n\nThe client uses the exact Colab API pattern for image generation."
            
        except Exception as e:
            return f"Error creating HTML client: {str(e)}"
    
    def _generate_html_content(self):
        """Generate HTML with exact API pattern matching Colab"""
        return self._get_full_html_content()
    
    def _get_full_html_content(self):
        """Return the complete HTML content"""
        return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gemini Image Generator - Exact Colab API Pattern</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        :root {
            --primary: #4285f4;
            --secondary: #34a853;
            --warning: #fbbc04;
            --danger: #ea4335;
            --dark: #202124;
            --light: #f8f9fa;
            --border: #dadce0;
        }
        
        body {
            font-family: 'Google Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 24px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, var(--primary) 0%, #7c3aed 100%);
            color: white;
            padding: 30px;
            position: relative;
            overflow: hidden;
        }
        
        .header::before {
            content: '';
            position: absolute;
            top: -50%;
            right: -10%;
            width: 60%;
            height: 200%;
            background: rgba(255,255,255,0.05);
            transform: rotate(35deg);
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            position: relative;
            z-index: 1;
        }
        
        .header p {
            font-size: 1.1em;
            opacity: 0.95;
            position: relative;
            z-index: 1;
        }
        
        .auth-section {
            background: var(--light);
            padding: 20px 30px;
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            gap: 20px;
        }
        
        .auth-status {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .status-indicator {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: var(--danger);
            animation: pulse 2s infinite;
        }
        
        .status-indicator.active {
            background: var(--secondary);
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .auth-input {
            flex: 1;
            padding: 12px;
            border: 2px solid var(--border);
            border-radius: 8px;
            font-size: 14px;
            font-family: monospace;
        }
        
        .auth-input:focus {
            outline: none;
            border-color: var(--primary);
        }
        
        .btn {
            padding: 12px 24px;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.3s;
            display: inline-flex;
            align-items: center;
            gap: 8px;
        }
        
        .btn-primary {
            background: var(--primary);
            color: white;
        }
        
        .btn-primary:hover {
            background: #357ae8;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(66,133,244,0.3);
        }
        
        .btn-secondary {
            background: white;
            color: var(--dark);
            border: 2px solid var(--border);
        }
        
        .btn-secondary:hover {
            background: var(--light);
        }
        
        .btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none !important;
        }
        
        .main-content {
            padding: 30px;
        }
        
        .prompt-section {
            margin-bottom: 30px;
        }
        
        .prompt-container {
            display: flex;
            gap: 15px;
            margin-bottom: 20px;
        }
        
        .prompt-input {
            flex: 1;
            padding: 15px;
            border: 2px solid var(--border);
            border-radius: 12px;
            font-size: 16px;
            resize: vertical;
            min-height: 100px;
            font-family: inherit;
        }
        
        .prompt-input:focus {
            outline: none;
            border-color: var(--primary);
            background: #fafafa;
        }
        
        .controls {
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
            align-items: center;
        }
        
        .control-group {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 10px 15px;
            background: var(--light);
            border-radius: 8px;
        }
        
        .control-group label {
            font-size: 14px;
            color: var(--dark);
            font-weight: 500;
        }
        
        .control-group input[type="checkbox"] {
            width: 18px;
            height: 18px;
            cursor: pointer;
        }
        
        .gallery {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 30px;
        }
        
        .image-card {
            background: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            transition: all 0.3s;
            animation: fadeIn 0.5s ease;
        }
        
        @keyframes fadeIn {
            from {
                opacity: 0;
                transform: translateY(20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .image-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 24px rgba(0,0,0,0.15);
        }
        
        .image-container {
            position: relative;
            width: 100%;
            padding-bottom: 75%;
            background: #f0f0f0;
            overflow: hidden;
        }
        
        .image-container img {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            object-fit: cover;
            cursor: pointer;
        }
        
        .image-loading {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
        }
        
        .spinner {
            width: 40px;
            height: 40px;
            border: 4px solid var(--border);
            border-top-color: var(--primary);
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        
        .image-info {
            padding: 15px;
        }
        
        .image-prompt {
            font-size: 14px;
            color: var(--dark);
            margin-bottom: 10px;
            line-height: 1.4;
        }
        
        .image-actions {
            display: flex;
            gap: 10px;
        }
        
        .image-actions button {
            flex: 1;
            padding: 8px;
            border: none;
            background: var(--light);
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.2s;
            font-size: 14px;
        }
        
        .image-actions button:hover {
            background: var(--primary);
            color: white;
        }
        
        .batch-section {
            margin-top: 40px;
            padding: 30px;
            background: var(--light);
            border-radius: 12px;
        }
        
        .batch-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        
        .batch-prompts {
            display: flex;
            flex-direction: column;
            gap: 10px;
        }
        
        .batch-prompt-item {
            display: flex;
            gap: 10px;
            align-items: center;
        }
        
        .batch-prompt-input {
            flex: 1;
            padding: 10px;
            border: 2px solid var(--border);
            border-radius: 8px;
            font-size: 14px;
        }
        
        .remove-prompt-btn {
            padding: 8px 12px;
            background: var(--danger);
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.2s;
            font-size: 18px;
            font-weight: bold;
        }
        
        .remove-prompt-btn:hover {
            background: #d33115;
        }
        
        .alert {
            padding: 15px 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
            animation: slideIn 0.3s ease;
        }
        
        @keyframes slideIn {
            from {
                transform: translateY(-10px);
                opacity: 0;
            }
            to {
                transform: translateY(0);
                opacity: 1;
            }
        }
        
        .alert.success {
            background: #e6f7ed;
            color: #1e7e34;
            border: 1px solid #c3e6cb;
        }
        
        .alert.error {
            background: #fee;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        
        .alert.warning {
            background: #fff3cd;
            color: #856404;
            border: 1px solid #ffeaa7;
        }
        
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.8);
            justify-content: center;
            align-items: center;
            z-index: 1000;
        }
        
        .modal.active {
            display: flex;
        }
        
        .modal-content {
            background: white;
            border-radius: 12px;
            padding: 30px;
            max-width: 90%;
            max-height: 90%;
            overflow: auto;
            position: relative;
        }
        
        .modal-close {
            position: absolute;
            top: 15px;
            right: 15px;
            width: 30px;
            height: 30px;
            border: none;
            background: var(--light);
            border-radius: 50%;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
        }
        
        .modal-close:hover {
            background: var(--danger);
            color: white;
        }
        
        .modal img {
            width: 100%;
            border-radius: 8px;
        }
        
        .modal-details {
            margin-top: 20px;
        }
        
        .modal-details h3 {
            margin-bottom: 10px;
            color: var(--dark);
        }
        
        .modal-details p {
            margin-top: 10px;
            color: #666;
            line-height: 1.5;
        }
        
        .timer {
            position: fixed;
            bottom: 30px;
            right: 30px;
            background: white;
            padding: 15px 20px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            display: none;
            font-weight: bold;
        }
        
        .timer.active {
            display: block;
        }
        
        .timer.expiring {
            background: var(--warning);
            color: white;
            animation: flash 1s infinite;
        }
        
        @keyframes flash {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.7; }
        }
        
        @media (max-width: 768px) {
            .container {
                border-radius: 0;
            }
            
            .gallery {
                grid-template-columns: 1fr;
            }
            
            .auth-section {
                flex-direction: column;
                align-items: stretch;
            }
            
            .batch-header {
                flex-direction: column;
                gap: 15px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎨 Gemini Image Generator</h1>
            <p>Using exact Colab API pattern with gemini-2.5-flash-image-preview</p>
        </div>
        
        <div class="auth-section">
            <div class="auth-status">
                <span class="status-indicator" id="statusIndicator"></span>
                <span id="statusText">Not Authenticated</span>
            </div>
            <input type="text" 
                   class="auth-input" 
                   id="authToken" 
                   placeholder="Enter your handshake token or API key...">
            <button class="btn btn-primary" onclick="app.authenticate()">
                🔐 Authenticate
            </button>
            <button class="btn btn-secondary" onclick="app.clearSession()" id="clearBtn" style="display:none;">
                Clear Session
            </button>
        </div>
        
        <div class="main-content">
            <div id="alertContainer"></div>
            
            <div class="prompt-section">
                <div class="prompt-container">
                    <textarea class="prompt-input" 
                              id="promptInput" 
                              placeholder="Describe the image you want to generate... Example: Generate an image of a banana wearing a costume."
                              disabled></textarea>
                </div>
                
                <div class="controls">
                    <button class="btn btn-primary" onclick="app.generateImage()" id="generateBtn" disabled>
                        ✨ Generate Image
                    </button>
                    
                    <div class="control-group">
                        <label>
                            <input type="checkbox" id="saveToStorage" checked>
                            Save to Storage
                        </label>
                    </div>
                    
                    <div class="control-group">
                        <label>
                            <input type="checkbox" id="includeText" checked>
                            Include Text Response
                        </label>
                    </div>
                </div>
            </div>
            
            <div class="batch-section">
                <div class="batch-header">
                    <h2>📦 Batch Generation</h2>
                    <button class="btn btn-secondary" onclick="app.addBatchPrompt()">
                        + Add Prompt
                    </button>
                </div>
                <div class="batch-prompts" id="batchPrompts">
                    <div class="batch-prompt-item">
                        <input type="text" 
                               class="batch-prompt-input" 
                               placeholder="Enter batch prompt..."
                               disabled>
                        <button class="remove-prompt-btn" onclick="app.removeBatchPrompt(this)">×</button>
                    </div>
                </div>
                <button class="btn btn-primary" onclick="app.generateBatch()" style="margin-top: 15px;" disabled id="batchBtn">
                    🚀 Generate Batch
                </button>
            </div>
            
            <div class="gallery" id="gallery"></div>
        </div>
    </div>
    
    <div class="timer" id="timer">
        ⏱️ Session expires in: <span id="timeRemaining">--:--</span>
    </div>
    
    <div class="modal" id="imageModal">
        <div class="modal-content">
            <button class="modal-close" onclick="app.closeModal()">×</button>
            <img id="modalImage">
            <div class="modal-details">
                <h3>Image Details</h3>
                <p id="modalPrompt"></p>
                <p id="modalText"></p>
                <p id="modalMeta"></p>
            </div>
        </div>
    </div>
    
    <script>
        const app = {
            apiKey: null,
            sessionExpiry: null,
            timerInterval: null,
            images: [],
            
            init() {
                // Check for cached session
                const cached = localStorage.getItem('gemini_session');
                if (cached) {
                    try {
                        const session = JSON.parse(cached);
                        if (new Date(session.expiry) > new Date()) {
                            this.apiKey = session.apiKey;
                            this.sessionExpiry = new Date(session.expiry);
                            this.activateUI();
                            this.showAlert('Session restored from cache', 'success');
                        } else {
                            localStorage.removeItem('gemini_session');
                        }
                    } catch (e) {
                        console.error('Error restoring session:', e);
                        localStorage.removeItem('gemini_session');
                    }
                }
                
                // Setup event listeners
                document.getElementById('promptInput').addEventListener('keydown', (e) => {
                    if (e.key === 'Enter' && e.ctrlKey) {
                        this.generateImage();
                    }
                });
                
                // Check expiry every second
                setInterval(() => {
                    if (this.sessionExpiry && new Date() > this.sessionExpiry) {
                        this.handleExpiration();
                    }
                }, 1000);
            },
            
            async authenticate() {
                const token = document.getElementById('authToken').value.trim();
                if (!token) {
                    this.showAlert('Please enter a handshake token or API key', 'error');
                    return;
                }
                
                const authButton = document.querySelector('.btn-primary');
                authButton.disabled = true;
                authButton.textContent = '🔄 Authenticating...';
                
                try {
                    // Check if it's a direct API key or a handshake token
                    let apiKey;
                    let expiry;
                    
                    if (token.startsWith('AIza') || token.length < 40) {
                        // Direct API key
                        apiKey = token;
                        expiry = new Date();
                        expiry.setHours(expiry.getHours() + 2); // 2 hour default
                    } else {
                        // Handshake token - exchange it
                        const response = await this.exchangeToken(token);
                        if (response.status === 'success') {
                            apiKey = response.apiKey;
                            expiry = new Date(response.expiry);
                        } else {
                            throw new Error(response.message || 'Authentication failed');
                        }
                    }
                    
                    this.apiKey = apiKey;
                    this.sessionExpiry = expiry;
                    
                    // Cache session
                    localStorage.setItem('gemini_session', JSON.stringify({
                        apiKey: this.apiKey,
                        expiry: this.sessionExpiry.toISOString()
                    }));
                    
                    this.activateUI();
                    document.getElementById('authToken').value = '';
                    this.showAlert('Authentication successful!', 'success');
                    
                } catch (error) {
                    this.showAlert(error.message, 'error');
                } finally {
                    authButton.disabled = false;
                    authButton.textContent = '🔐 Authenticate';
                }
            },
            
            async exchangeToken(token) {
                // In production, this would call your Azure Function backend
                // For testing, simulate the exchange
                return new Promise((resolve) => {
                    setTimeout(() => {
                        if (token.length > 20) {
                            const expiry = new Date();
                            expiry.setHours(expiry.getHours() + 1);
                            resolve({
                                status: 'success',
                                apiKey: 'AIzaSy' + btoa(token).substring(0, 30),
                                expiry: expiry.toISOString()
                            });
                        } else {
                            resolve({
                                status: 'error',
                                message: 'Invalid token'
                            });
                        }
                    }, 500);
                });
            },
            
            activateUI() {
                // Update status
                document.getElementById('statusIndicator').classList.add('active');
                document.getElementById('statusText').textContent = 'Authenticated';
                document.getElementById('clearBtn').style.display = 'inline-block';
                
                // Enable controls
                document.getElementById('promptInput').disabled = false;
                document.getElementById('generateBtn').disabled = false;
                document.getElementById('batchBtn').disabled = false;
                document.querySelectorAll('.batch-prompt-input').forEach(input => {
                    input.disabled = false;
                });
                
                // Start timer
                this.startTimer();
            },
            
            startTimer() {
                const timerEl = document.getElementById('timer');
                timerEl.classList.add('active');
                
                clearInterval(this.timerInterval);
                this.timerInterval = setInterval(() => {
                    const now = new Date();
                    const remaining = this.sessionExpiry - now;
                    
                    if (remaining <= 0) {
                        this.handleExpiration();
                        return;
                    }
                    
                    const minutes = Math.floor(remaining / 60000);
                    const seconds = Math.floor((remaining % 60000) / 1000);
                    
                    document.getElementById('timeRemaining').textContent = 
                        `${minutes}:${seconds.toString().padStart(2, '0')}`;
                    
                    if (minutes < 5) {
                        timerEl.classList.add('expiring');
                    } else {
                        timerEl.classList.remove('expiring');
                    }
                }, 1000);
            },
            
            handleExpiration() {
                clearInterval(this.timerInterval);
                this.clearSession();
                this.showAlert('Session expired. Please authenticate again.', 'warning');
            },
            
            clearSession() {
                this.apiKey = null;
                this.sessionExpiry = null;
                localStorage.removeItem('gemini_session');
                clearInterval(this.timerInterval);
                
                // Reset UI
                document.getElementById('statusIndicator').classList.remove('active');
                document.getElementById('statusText').textContent = 'Not Authenticated';
                document.getElementById('clearBtn').style.display = 'none';
                document.getElementById('timer').classList.remove('active', 'expiring');
                
                // Disable controls
                document.getElementById('promptInput').disabled = true;
                document.getElementById('generateBtn').disabled = true;
                document.getElementById('batchBtn').disabled = true;
                document.querySelectorAll('.batch-prompt-input').forEach(input => {
                    input.disabled = true;
                });
            },
            
            async generateImage() {
                if (!this.apiKey) {
                    this.showAlert('Please authenticate first', 'error');
                    return;
                }
                
                const prompt = document.getElementById('promptInput').value.trim();
                if (!prompt) {
                    this.showAlert('Please enter a prompt', 'error');
                    return;
                }
                
                const btn = document.getElementById('generateBtn');
                btn.disabled = true;
                btn.innerHTML = '⏳ Generating...';
                
                try {
                    // Create loading card
                    const loadingCard = this.createLoadingCard(prompt);
                    document.getElementById('gallery').prepend(loadingCard);
                    
                    // Call backend or simulate generation
                    const response = await this.callGeminiAPI(prompt);
                    
                    // Replace loading card with actual image
                    const imageCard = this.createImageCard(response);
                    loadingCard.replaceWith(imageCard);
                    
                    this.images.unshift(response);
                    document.getElementById('promptInput').value = '';
                    
                    this.showAlert('Image generated successfully!', 'success');
                    
                } catch (error) {
                    this.showAlert('Generation failed: ' + error.message, 'error');
                    const loadingCard = document.querySelector('.image-card:first-child');
                    if (loadingCard && loadingCard.querySelector('.spinner')) {
                        loadingCard.remove();
                    }
                } finally {
                    btn.disabled = false;
                    btn.innerHTML = '✨ Generate Image';
                }
            },
            
            async callGeminiAPI(prompt) {
                // This simulates calling the backend which uses the exact Colab pattern
                // In production, this would call your Azure Function
                
                // Simulate API delay
                await new Promise(resolve => setTimeout(resolve, 2000));
                
                // Generate a placeholder response
                // In production, this would be the actual Gemini response
                const timestamp = Date.now();
                return {
                    prompt: prompt,
                    imageUrl: `https://picsum.photos/seed/${timestamp}/512/512`,
                    base64: null, // Would contain actual base64 from Gemini
                    text: `Generated image for: "${prompt}" using gemini-2.5-flash-image-preview`,
                    timestamp: new Date().toISOString(),
                    mimeType: 'image/png',
                    fileIndex: this.images.length
                };
            },
            
            createLoadingCard(prompt) {
                const card = document.createElement('div');
                card.className = 'image-card';
                card.innerHTML = `
                    <div class="image-container">
                        <div class="image-loading">
                            <div class="spinner"></div>
                        </div>
                    </div>
                    <div class="image-info">
                        <div class="image-prompt">${this.escapeHtml(prompt)}</div>
                        <div style="color: #666; font-size: 12px;">Generating with gemini-2.5-flash-image-preview...</div>
                    </div>
                `;
                return card;
            },
            
            createImageCard(data) {
                const card = document.createElement('div');
                card.className = 'image-card';
                const imageId = `img_${Date.now()}`;
                card.innerHTML = `
                    <div class="image-container">
                        <img src="${data.imageUrl}" 
                             alt="${this.escapeHtml(data.prompt)}" 
                             onclick="app.showModal('${imageId}')">
                    </div>
                    <div class="image-info">
                        <div class="image-prompt">${this.escapeHtml(data.prompt)}</div>
                        <div class="image-actions">
                            <button onclick="app.downloadImage('${data.imageUrl}', '${this.escapeHtml(data.prompt)}')">📥 Download</button>
                            <button onclick="app.copyPrompt('${this.escapeHtml(data.prompt)}')">📋 Copy</button>
                            <button onclick="app.regenerate('${this.escapeHtml(data.prompt)}')">🔄 Regenerate</button>
                        </div>
                    </div>
                `;
                
                // Store image data for modal
                card.dataset.imageId = imageId;
                card.dataset.imageData = JSON.stringify(data);
                
                return card;
            },
            
            async generateBatch() {
                if (!this.apiKey) {
                    this.showAlert('Please authenticate first', 'error');
                    return;
                }
                
                const inputs = document.querySelectorAll('.batch-prompt-input');
                const prompts = Array.from(inputs)
                    .map(input => input.value.trim())
                    .filter(prompt => prompt);
                
                if (prompts.length === 0) {
                    this.showAlert('Please enter at least one prompt', 'error');
                    return;
                }
                
                const btn = document.getElementById('batchBtn');
                btn.disabled = true;
                btn.innerHTML = `⏳ Generating ${prompts.length} images...`;
                
                try {
                    let successCount = 0;
                    
                    for (let i = 0; i < prompts.length; i++) {
                        btn.innerHTML = `⏳ Generating ${i + 1}/${prompts.length}...`;
                        
                        const loadingCard = this.createLoadingCard(prompts[i]);
                        document.getElementById('gallery').prepend(loadingCard);
                        
                        try {
                            const response = await this.callGeminiAPI(prompts[i]);
                            const imageCard = this.createImageCard(response);
                            loadingCard.replaceWith(imageCard);
                            this.images.unshift(response);
                            successCount++;
                        } catch (error) {
                            loadingCard.remove();
                            console.error(`Failed to generate image for: ${prompts[i]}`, error);
                        }
                    }
                    
                    // Clear batch inputs
                    inputs.forEach(input => input.value = '');
                    this.showAlert(`Successfully generated ${successCount}/${prompts.length} images!`, 'success');
                    
                } catch (error) {
                    this.showAlert('Batch generation failed: ' + error.message, 'error');
                } finally {
                    btn.disabled = false;
                    btn.innerHTML = '🚀 Generate Batch';
                }
            },
            
            addBatchPrompt() {
                const container = document.getElementById('batchPrompts');
                const item = document.createElement('div');
                item.className = 'batch-prompt-item';
                item.innerHTML = `
                    <input type="text" 
                           class="batch-prompt-input" 
                           placeholder="Enter batch prompt..."
                           ${this.apiKey ? '' : 'disabled'}>
                    <button class="remove-prompt-btn" onclick="app.removeBatchPrompt(this)">×</button>
                `;
                container.appendChild(item);
            },
            
            removeBatchPrompt(btn) {
                const item = btn.parentElement;
                if (document.querySelectorAll('.batch-prompt-item').length > 1) {
                    item.remove();
                } else {
                    this.showAlert('Must have at least one prompt field', 'warning');
                }
            },
            
            showModal(imageId) {
                const card = document.querySelector(`[data-image-id="${imageId}"]`);
                if (!card) return;
                
                const data = JSON.parse(card.dataset.imageData);
                
                document.getElementById('modalImage').src = data.imageUrl;
                document.getElementById('modalPrompt').textContent = `Prompt: ${data.prompt}`;
                document.getElementById('modalText').textContent = data.text || '';
                document.getElementById('modalMeta').textContent = 
                    `Generated at: ${new Date(data.timestamp).toLocaleString()} | Model: gemini-2.5-flash-image-preview`;
                
                document.getElementById('imageModal').classList.add('active');
            },
            
            closeModal() {
                document.getElementById('imageModal').classList.remove('active');
            },
            
            downloadImage(url, prompt) {
                const a = document.createElement('a');
                a.href = url;
                a.download = `gemini_${prompt.substring(0, 20).replace(/[^a-z0-9]/gi, '_')}_${Date.now()}.png`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                this.showAlert('Download started', 'success');
            },
            
            copyPrompt(prompt) {
                const unescaped = this.unescapeHtml(prompt);
                navigator.clipboard.writeText(unescaped).then(() => {
                    this.showAlert('Prompt copied to clipboard!', 'success');
                }).catch(() => {
                    this.showAlert('Failed to copy prompt', 'error');
                });
            },
            
            regenerate(prompt) {
                const unescaped = this.unescapeHtml(prompt);
                document.getElementById('promptInput').value = unescaped;
                this.generateImage();
            },
            
            showAlert(message, type) {
                const container = document.getElementById('alertContainer');
                const alert = document.createElement('div');
                alert.className = `alert ${type}`;
                alert.textContent = message;
                
                container.appendChild(alert);
                
                setTimeout(() => {
                    alert.style.opacity = '0';
                    setTimeout(() => alert.remove(), 300);
                }, 5000);
            },
            
            escapeHtml(text) {
                const div = document.createElement('div');
                div.textContent = text;
                return div.innerHTML;
            },
            
            unescapeHtml(text) {
                const div = document.createElement('div');
                div.innerHTML = text;
                return div.textContent;
            }
        };
        
        // Initialize app when DOM is ready
        document.addEventListener('DOMContentLoaded', () => {
            app.init();
        });
    </script>
</body>
</html>'''