import logging
import json
import hashlib
from agents.basic_agent import BasicAgent
from utils.azure_file_storage import AzureFileStorageManager
from datetime import datetime
import re

class APIConnectorAgent(BasicAgent):
    def __init__(self):
        self.name = 'APIConnector'
        self.metadata = {
            "name": self.name,
            "description": "Connects to REST APIs, GraphQL endpoints, and web services with automatic authentication handling and response transformation",
            "parameters": {
                "type": "object",
                "properties": {
                    "endpoint": {
                        "type": "string",
                        "description": "API endpoint URL"
                    },
                    "method": {
                        "type": "string",
                        "description": "HTTP method: GET, POST, PUT, DELETE, PATCH",
                        "enum": ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]
                    },
                    "headers": {
                        "type": "object",
                        "description": "Request headers including authentication"
                    },
                    "body": {
                        "type": "object",
                        "description": "Request body for POST/PUT/PATCH requests"
                    },
                    "params": {
                        "type": "object",
                        "description": "Query parameters"
                    },
                    "auth_type": {
                        "type": "string",
                        "description": "Authentication type: bearer, basic, api_key, oauth2",
                        "enum": ["none", "bearer", "basic", "api_key", "oauth2"]
                    },
                    "auth_credentials": {
                        "type": "object",
                        "description": "Authentication credentials based on auth_type"
                    },
                    "transform": {
                        "type": "string",
                        "description": "Response transformation pattern"
                    },
                    "cache_result": {
                        "type": "boolean",
                        "description": "Whether to cache the API response"
                    },
                    "learn_pattern": {
                        "type": "boolean",
                        "description": "Whether to learn from this API pattern"
                    },
                    "retry_count": {
                        "type": "integer",
                        "description": "Number of retries on failure"
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Request timeout in seconds"
                    }
                },
                "required": ["endpoint", "method"]
            }
        }
        self.storage_manager = AzureFileStorageManager()
        self.api_patterns = self._load_api_patterns()
        self.auth_configs = self._load_auth_configs()
        super().__init__(name=self.name, metadata=self.metadata)

    def _load_api_patterns(self):
        """Load learned API patterns."""
        try:
            patterns = self.storage_manager.read_json_from_path(
                "api_patterns",
                "patterns.json"
            )
            return patterns if patterns else {}
        except Exception:
            return {}

    def _save_api_patterns(self):
        """Save learned API patterns."""
        try:
            self.storage_manager.write_json_to_path(
                self.api_patterns,
                "api_patterns",
                "patterns.json"
            )
        except Exception as e:
            logging.error(f"Error saving API patterns: {str(e)}")

    def _load_auth_configs(self):
        """Load saved authentication configurations."""
        try:
            configs = self.storage_manager.read_json_from_path(
                "api_patterns",
                "auth_configs.json"
            )
            return configs if configs else {}
        except Exception:
            return {}

    def _save_auth_configs(self):
        """Save authentication configurations."""
        try:
            self.storage_manager.write_json_to_path(
                self.auth_configs,
                "api_patterns",
                "auth_configs.json"
            )
        except Exception as e:
            logging.error(f"Error saving auth configs: {str(e)}")

    def perform(self, **kwargs):
        """Execute API requests with learning and transformation capabilities."""
        endpoint = kwargs.get('endpoint', '')
        method = kwargs.get('method', 'GET').upper()
        headers = kwargs.get('headers', {})
        body = kwargs.get('body', None)
        params = kwargs.get('params', {})
        auth_type = kwargs.get('auth_type', 'none')
        auth_credentials = kwargs.get('auth_credentials', {})
        transform = kwargs.get('transform', None)
        cache_result = kwargs.get('cache_result', True)
        learn_pattern = kwargs.get('learn_pattern', True)
        retry_count = kwargs.get('retry_count', 3)
        timeout = kwargs.get('timeout', 30)
        
        if not endpoint:
            return json.dumps({
                'status': 'error',
                'error': 'Endpoint URL is required'
            })
        
        try:
            # Check cache first if enabled
            if cache_result and method == 'GET':
                cache_key = f"{endpoint}_{method}_{json.dumps(params, sort_keys=True)}"
                cached_data = self.storage_manager.get_cached_data(cache_key)
                if cached_data:
                    logging.info(f"Returning cached API response")
                    return json.dumps({
                        'status': 'success',
                        'source': 'cache',
                        'data': cached_data
                    })
            
            # Apply authentication
            headers = self._apply_authentication(headers, auth_type, auth_credentials, endpoint)
            
            # Check for learned patterns
            if learn_pattern:
                suggested_params = self._suggest_parameters(endpoint, method)
                if suggested_params:
                    params = {**suggested_params, **params}
            
            # Simulate API call (in production, use requests library)
            result = self._make_api_call(
                endpoint, method, headers, body, params, timeout, retry_count
            )
            
            # Transform response if pattern provided
            if transform and result.get('status') == 'success':
                result['data'] = self._transform_response(result['data'], transform)
            
            # Learn from successful calls
            if learn_pattern and result.get('status') == 'success':
                self._learn_api_pattern(endpoint, method, params, result)
            
            # Cache successful GET responses
            if cache_result and method == 'GET' and result.get('status') == 'success':
                cache_key = f"{endpoint}_{method}_{json.dumps(params, sort_keys=True)}"
                self.storage_manager.cache_data(cache_key, result.get('data'))
            
            # Store successful auth config for reuse
            if auth_type != 'none' and result.get('status') == 'success':
                self._store_auth_config(endpoint, auth_type, auth_credentials)
            
            return json.dumps(result)
            
        except Exception as e:
            logging.error(f"Error in API connector: {str(e)}")
            return json.dumps({
                'status': 'error',
                'error': str(e)
            })

    def _apply_authentication(self, headers, auth_type, credentials, endpoint):
        """Apply authentication to request headers."""
        if auth_type == 'none':
            return headers
        
        # Check for stored auth config
        domain = self._extract_domain(endpoint)
        if domain in self.auth_configs and not credentials:
            stored_auth = self.auth_configs[domain]
            auth_type = stored_auth['type']
            credentials = stored_auth['credentials']
        
        if auth_type == 'bearer':
            token = credentials.get('token', '')
            headers['Authorization'] = f'Bearer {token}'
        
        elif auth_type == 'basic':
            import base64
            username = credentials.get('username', '')
            password = credentials.get('password', '')
            auth_string = base64.b64encode(f'{username}:{password}'.encode()).decode()
            headers['Authorization'] = f'Basic {auth_string}'
        
        elif auth_type == 'api_key':
            key_name = credentials.get('key_name', 'X-API-Key')
            key_value = credentials.get('key_value', '')
            headers[key_name] = key_value
        
        elif auth_type == 'oauth2':
            # Simplified OAuth2 - in production, handle token refresh
            access_token = credentials.get('access_token', '')
            headers['Authorization'] = f'Bearer {access_token}'
        
        return headers

    def _extract_domain(self, endpoint):
        """Extract domain from endpoint URL."""
        import re
        match = re.match(r'https?://([^/]+)', endpoint)
        return match.group(1) if match else endpoint

    def _make_api_call(self, endpoint, method, headers, body, params, timeout, retry_count):
        """Make the actual API call (simulated for demonstration)."""
        # In production, use the requests library:
        # import requests
        # response = requests.request(method, endpoint, headers=headers, json=body, params=params, timeout=timeout)
        
        # For demonstration, return simulated data based on endpoint patterns
        if 'users' in endpoint.lower():
            sample_data = [
                {'id': 1, 'name': 'Alice', 'email': 'alice@example.com'},
                {'id': 2, 'name': 'Bob', 'email': 'bob@example.com'}
            ]
        elif 'products' in endpoint.lower():
            sample_data = [
                {'id': 101, 'name': 'Product A', 'price': 99.99},
                {'id': 102, 'name': 'Product B', 'price': 149.99}
            ]
        elif 'graphql' in endpoint.lower():
            sample_data = {
                'data': {
                    'result': 'GraphQL response data'
                }
            }
        else:
            sample_data = {
                'message': f'Successfully called {method} {endpoint}',
                'timestamp': datetime.now().isoformat()
            }
        
        return {
            'status': 'success',
            'method': method,
            'endpoint': endpoint,
            'data': sample_data,
            'response_time': 0.234  # Simulated response time
        }

    def _transform_response(self, data, transform_pattern):
        """Transform API response based on pattern."""
        if not transform_pattern:
            return data
        
        try:
            # Simple JSONPath-like transformation
            if transform_pattern.startswith('$.'):
                path_parts = transform_pattern[2:].split('.')
                result = data
                for part in path_parts:
                    if '[' in part and ']' in part:
                        # Array access
                        field = part[:part.index('[')]
                        index = int(part[part.index('[')+1:part.index(']')])
                        result = result[field][index]
                    else:
                        result = result[part]
                return result
            
            # Custom transformations
            elif transform_pattern == 'flatten':
                return self._flatten_json(data)
            
            elif transform_pattern == 'extract_ids':
                return self._extract_ids(data)
            
            else:
                return data
                
        except Exception as e:
            logging.warning(f"Transform failed: {str(e)}, returning original data")
            return data

    def _flatten_json(self, data, parent_key='', sep='_'):
        """Flatten nested JSON structure."""
        items = []
        
        if isinstance(data, dict):
            for k, v in data.items():
                new_key = f"{parent_key}{sep}{k}" if parent_key else k
                if isinstance(v, dict):
                    items.extend(self._flatten_json(v, new_key, sep=sep).items())
                elif isinstance(v, list):
                    for i, item in enumerate(v):
                        items.extend(self._flatten_json(item, f"{new_key}_{i}", sep=sep).items())
                else:
                    items.append((new_key, v))
        elif isinstance(data, list):
            for i, item in enumerate(data):
                items.extend(self._flatten_json(item, f"{parent_key}_{i}", sep=sep).items())
        else:
            items.append((parent_key, data))
        
        return dict(items)

    def _extract_ids(self, data):
        """Extract all ID fields from response."""
        ids = []
        
        def extract(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if 'id' in key.lower():
                        ids.append({key: value})
                    elif isinstance(value, (dict, list)):
                        extract(value)
            elif isinstance(obj, list):
                for item in obj:
                    extract(item)
        
        extract(data)
        return ids

    def _learn_api_pattern(self, endpoint, method, params, result):
        """Learn from successful API patterns."""
        try:
            # Create pattern ID
            pattern_id = hashlib.md5(f"{endpoint}_{method}".encode()).hexdigest()[:12]
            
            if pattern_id not in self.api_patterns:
                self.api_patterns[pattern_id] = {
                    'endpoint': endpoint,
                    'method': method,
                    'successful_params': [],
                    'response_schema': None,
                    'avg_response_time': 0,
                    'success_count': 0,
                    'learned_at': datetime.now().isoformat()
                }
            
            # Update pattern
            pattern = self.api_patterns[pattern_id]
            pattern['success_count'] += 1
            
            # Store successful parameters
            if params:
                pattern['successful_params'].append({
                    'params': params,
                    'timestamp': datetime.now().isoformat()
                })
                # Keep only last 10 examples
                if len(pattern['successful_params']) > 10:
                    pattern['successful_params'] = pattern['successful_params'][-10:]
            
            # Update response time average
            if 'response_time' in result:
                current_avg = pattern['avg_response_time']
                count = pattern['success_count']
                new_avg = ((current_avg * (count - 1)) + result['response_time']) / count
                pattern['avg_response_time'] = new_avg
            
            # Learn response schema
            if result.get('data'):
                pattern['response_schema'] = self._extract_schema(result['data'])
            
            self._save_api_patterns()
            
        except Exception as e:
            logging.error(f"Error learning API pattern: {str(e)}")

    def _extract_schema(self, data):
        """Extract schema from response data."""
        if isinstance(data, dict):
            schema = {'type': 'object', 'properties': {}}
            for key, value in data.items():
                schema['properties'][key] = self._extract_schema(value)
            return schema
        elif isinstance(data, list):
            if data:
                return {'type': 'array', 'items': self._extract_schema(data[0])}
            return {'type': 'array'}
        elif isinstance(data, bool):
            return {'type': 'boolean'}
        elif isinstance(data, int):
            return {'type': 'integer'}
        elif isinstance(data, float):
            return {'type': 'number'}
        elif isinstance(data, str):
            return {'type': 'string'}
        else:
            return {'type': 'null'}

    def _suggest_parameters(self, endpoint, method):
        """Suggest parameters based on learned patterns."""
        pattern_id = hashlib.md5(f"{endpoint}_{method}".encode()).hexdigest()[:12]
        
        if pattern_id in self.api_patterns:
            pattern = self.api_patterns[pattern_id]
            if pattern['successful_params']:
                # Return the most recent successful parameters
                return pattern['successful_params'][-1]['params']
        
        return None

    def _store_auth_config(self, endpoint, auth_type, credentials):
        """Store successful authentication configuration."""
        domain = self._extract_domain(endpoint)
        
        # Don't store sensitive credentials in plain text in production
        # This is for demonstration only
        self.auth_configs[domain] = {
            'type': auth_type,
            'credentials': credentials,
            'last_used': datetime.now().isoformat()
        }
        
        self._save_auth_configs()

    def discover_endpoints(self, base_url):
        """Discover available endpoints from API documentation."""
        common_endpoints = [
            '/api',
            '/api/v1',
            '/api/v2', 
            '/swagger.json',
            '/openapi.json',
            '/.well-known/openapi',
            '/api-docs'
        ]
        
        discovered = []
        
        for endpoint in common_endpoints:
            full_url = base_url.rstrip('/') + endpoint
            # In production, make actual HEAD/GET requests
            # For now, simulate discovery
            discovered.append({
                'url': full_url,
                'status': 'potential',
                'checked': False
            })
        
        return discovered
