import logging
import json
from datetime import datetime, timedelta
import hashlib
from agents.basic_agent import BasicAgent
from utils.azure_file_storage import AzureFileStorageManager

class DataCacheAgent(BasicAgent):
    def __init__(self):
        self.name = "DataCache"
        self.metadata = {
            "name": self.name,
            "description": "Manages data caching, schema storage, transformation templates, and query patterns for optimal performance.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "The cache operation to perform",
                        "enum": ["cache", "get_cache", "store_schema", "get_schema", "store_transformation", "get_transformation", "store_query", "get_query", "clear_cache"]
                    },
                    "key": {
                        "type": "string",
                        "description": "Cache key for storing/retrieving data"
                    },
                    "data": {
                        "type": "object",
                        "description": "Data to cache"
                    },
                    "ttl": {
                        "type": "integer",
                        "description": "Time to live in seconds (default: 300)"
                    },
                    "source_id": {
                        "type": "string",
                        "description": "ID of the data source for schema operations"
                    },
                    "schema": {
                        "type": "object",
                        "description": "Schema data to store"
                    },
                    "transformation_id": {
                        "type": "string",
                        "description": "ID of the transformation"
                    },
                    "transformation": {
                        "type": "object",
                        "description": "Transformation data to store"
                    },
                    "template_id": {
                        "type": "string",
                        "description": "ID of the query template"
                    },
                    "template": {
                        "type": "object",
                        "description": "Query template to store"
                    },
                    "cache_pattern": {
                        "type": "string",
                        "description": "Pattern to match when clearing cache (for clear_cache action)"
                    }
                },
                "required": ["action"]
            }
        }
        self.storage_manager = AzureFileStorageManager()
        self.local_cache = {}
        self.cache_ttl = 300  # 5 minutes default TTL
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'stores': 0,
            'evictions': 0
        }
        self._initialize_cache_directories()
        super().__init__(name=self.name, metadata=self.metadata)
    
    def perform(self, **kwargs):
        action = kwargs.get('action')
        
        try:
            if action == 'cache':
                key = kwargs.get('key')
                data = kwargs.get('data')
                ttl = kwargs.get('ttl', self.cache_ttl)
                
                if not key or data is None:
                    return json.dumps({
                        "status": "error",
                        "message": "key and data are required for caching"
                    })
                
                cache_key = self.cache_data(key, data, ttl)
                return json.dumps({
                    "status": "success",
                    "action": "cache",
                    "cache_key": cache_key,
                    "ttl": ttl
                })
            
            elif action == 'get_cache':
                key = kwargs.get('key')
                if not key:
                    return json.dumps({
                        "status": "error",
                        "message": "key is required"
                    })
                
                cached_data = self.get_cached_data(key)
                if cached_data is not None:
                    self.cache_stats['hits'] += 1
                    return json.dumps({
                        "status": "success",
                        "action": "get_cache",
                        "data": cached_data,
                        "cache_hit": True
                    })
                else:
                    self.cache_stats['misses'] += 1
                    return json.dumps({
                        "status": "success",
                        "action": "get_cache",
                        "data": None,
                        "cache_hit": False
                    })
            
            elif action == 'store_schema':
                source_id = kwargs.get('source_id')
                schema = kwargs.get('schema')
                
                if not source_id or not schema:
                    return json.dumps({
                        "status": "error",
                        "message": "source_id and schema are required"
                    })
                
                success = self.storage_manager.store_schema(source_id, schema)
                return json.dumps({
                    "status": "success" if success else "error",
                    "action": "store_schema",
                    "source_id": source_id
                })
            
            elif action == 'get_schema':
                source_id = kwargs.get('source_id')
                if not source_id:
                    return json.dumps({
                        "status": "error",
                        "message": "source_id is required"
                    })
                
                schema = self.storage_manager.get_schema(source_id)
                if schema:
                    return json.dumps({
                        "status": "success",
                        "action": "get_schema",
                        "schema": schema
                    })
                else:
                    return json.dumps({
                        "status": "error",
                        "message": f"Schema not found for {source_id}"
                    })
            
            elif action == 'store_transformation':
                transformation_id = kwargs.get('transformation_id')
                transformation = kwargs.get('transformation')
                
                if not transformation_id or not transformation:
                    return json.dumps({
                        "status": "error",
                        "message": "transformation_id and transformation are required"
                    })
                
                success = self.storage_manager.store_transformation(transformation_id, transformation)
                return json.dumps({
                    "status": "success" if success else "error",
                    "action": "store_transformation",
                    "transformation_id": transformation_id
                })
            
            elif action == 'get_transformation':
                transformation_id = kwargs.get('transformation_id')
                if not transformation_id:
                    return json.dumps({
                        "status": "error",
                        "message": "transformation_id is required"
                    })
                
                transformation = self.storage_manager.get_transformation(transformation_id)
                if transformation:
                    return json.dumps({
                        "status": "success",
                        "action": "get_transformation",
                        "transformation": transformation
                    })
                else:
                    return json.dumps({
                        "status": "error",
                        "message": f"Transformation not found for {transformation_id}"
                    })
            
            elif action == 'store_query':
                template_id = kwargs.get('template_id')
                template = kwargs.get('template')
                
                if not template_id or not template:
                    return json.dumps({
                        "status": "error",
                        "message": "template_id and template are required"
                    })
                
                success = self.storage_manager.store_query_template(template_id, template)
                return json.dumps({
                    "status": "success" if success else "error",
                    "action": "store_query",
                    "template_id": template_id
                })
            
            elif action == 'get_query':
                template_id = kwargs.get('template_id')
                if not template_id:
                    return json.dumps({
                        "status": "error",
                        "message": "template_id is required"
                    })
                
                template = self.storage_manager.get_query_template(template_id)
                if template:
                    return json.dumps({
                        "status": "success",
                        "action": "get_query",
                        "template": template
                    })
                else:
                    return json.dumps({
                        "status": "error",
                        "message": f"Query template not found for {template_id}"
                    })
            
            elif action == 'clear_cache':
                cache_pattern = kwargs.get('cache_pattern', '')
                cleared_count = self.clear_cache(cache_pattern)
                return json.dumps({
                    "status": "success",
                    "action": "clear_cache",
                    "cleared_count": cleared_count,
                    "cache_stats": self.cache_stats
                })
            
            else:
                return json.dumps({
                    "status": "error",
                    "message": f"Unknown action: {action}"
                })
                
        except Exception as e:
            logging.error(f"Error in DataCache: {str(e)}")
            return json.dumps({
                "status": "error",
                "message": str(e)
            })
    
    def _initialize_cache_directories(self):
        """Initialize cache-related directories."""
        directories = [
            "data_cache",
            "schemas",
            "transformations",
            "query_templates"
        ]
        
        for directory in directories:
            try:
                self.storage_manager.ensure_directory_exists(directory)
                logging.info(f"Ensured cache directory exists: {directory}")
            except Exception as e:
                logging.warning(f"Could not create directory {directory}: {str(e)}")
    
    def cache_data(self, key, data, ttl=None):
        """Cache data with optional TTL."""
        if ttl is None:
            ttl = self.cache_ttl
        
        cache_key = hashlib.md5(key.encode()).hexdigest()
        cache_entry = {
            'data': data,
            'timestamp': datetime.now().isoformat(),
            'ttl': ttl,
            'original_key': key
        }
        
        # Store in local cache
        self.local_cache[cache_key] = cache_entry
        self.cache_stats['stores'] += 1
        
        # Store in Azure for persistence
        try:
            self.storage_manager.write_json_to_path(
                cache_entry, 
                "data_cache", 
                f"{cache_key}.json"
            )
        except Exception as e:
            logging.warning(f"Could not persist cache to Azure: {str(e)}")
        
        # Clean up old entries
        self._cleanup_expired_cache()
        
        return cache_key
    
    def get_cached_data(self, key):
        """Retrieve cached data if still valid."""
        cache_key = hashlib.md5(key.encode()).hexdigest()
        
        # Check local cache first
        if cache_key in self.local_cache:
            cache_entry = self.local_cache[cache_key]
            timestamp = datetime.fromisoformat(cache_entry['timestamp'])
            if datetime.now() - timestamp < timedelta(seconds=cache_entry['ttl']):
                return cache_entry['data']
            else:
                del self.local_cache[cache_key]
                self.cache_stats['evictions'] += 1
        
        # Check Azure cache
        try:
            cache_entry = self.storage_manager.read_json_from_path(
                "data_cache", 
                f"{cache_key}.json"
            )
            if cache_entry:
                timestamp = datetime.fromisoformat(cache_entry['timestamp'])
                if datetime.now() - timestamp < timedelta(seconds=cache_entry['ttl']):
                    # Restore to local cache
                    self.local_cache[cache_key] = cache_entry
                    return cache_entry['data']
                else:
                    self.cache_stats['evictions'] += 1
        except Exception as e:
            logging.warning(f"Could not read cache from Azure: {str(e)}")
        
        return None
    
    def _cleanup_expired_cache(self):
        """Remove expired entries from local cache."""
        expired_keys = []
        for cache_key, cache_entry in self.local_cache.items():
            timestamp = datetime.fromisoformat(cache_entry['timestamp'])
            if datetime.now() - timestamp >= timedelta(seconds=cache_entry['ttl']):
                expired_keys.append(cache_key)
        
        for key in expired_keys:
            del self.local_cache[key]
            self.cache_stats['evictions'] += 1
    
    def clear_cache(self, pattern=""):
        """Clear cache entries matching the pattern."""
        cleared_count = 0
        
        if pattern:
            # Clear entries matching pattern
            keys_to_clear = []
            for cache_key, cache_entry in self.local_cache.items():
                if pattern in cache_entry.get('original_key', ''):
                    keys_to_clear.append(cache_key)
            
            for key in keys_to_clear:
                del self.local_cache[key]
                cleared_count += 1
        else:
            # Clear all cache
            cleared_count = len(self.local_cache)
            self.local_cache.clear()
        
        return cleared_count
    
    def get_cache_statistics(self):
        """Get cache performance statistics."""
        total_requests = self.cache_stats['hits'] + self.cache_stats['misses']
        hit_rate = (self.cache_stats['hits'] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'total_entries': len(self.local_cache),
            'hits': self.cache_stats['hits'],
            'misses': self.cache_stats['misses'],
            'stores': self.cache_stats['stores'],
            'evictions': self.cache_stats['evictions'],
            'hit_rate': hit_rate,
            'total_requests': total_requests
        }