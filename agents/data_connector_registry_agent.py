import logging
import json
from datetime import datetime
import hashlib
from agents.basic_agent import BasicAgent
from utils.azure_file_storage import AzureFileStorageManager

class ConnectorRegistryAgent(BasicAgent):
    def __init__(self):
        self.name = "ConnectorRegistry"
        self.metadata = {
            "name": self.name,
            "description": "Manages data connector registry. Registers connectors, tracks usage, stores configs, and recommends optimal connectors.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "The registry operation to perform",
                        "enum": ["register", "get", "find_by_type", "find_by_capability", "update_usage", "store_config", "get_config", "get_best", "performance_report", "recommend"]
                    },
                    "connector_info": {
                        "type": "object",
                        "description": "Information about the connector to register",
                        "properties": {
                            "id": {"type": "string"},
                            "type": {"type": "string"},
                            "name": {"type": "string"},
                            "description": {"type": "string"},
                            "capabilities": {"type": "array", "items": {"type": "string"}},
                            "required_params": {"type": "array", "items": {"type": "string"}},
                            "optional_params": {"type": "array", "items": {"type": "string"}}
                        }
                    },
                    "connector_id": {
                        "type": "string",
                        "description": "ID of the connector"
                    },
                    "connector_type": {
                        "type": "string",
                        "description": "Type of connector to find"
                    },
                    "capability": {
                        "type": "string",
                        "description": "Capability to search for"
                    },
                    "success": {
                        "type": "boolean",
                        "description": "Whether the usage was successful"
                    },
                    "response_time": {
                        "type": "number",
                        "description": "Response time in seconds"
                    },
                    "config": {
                        "type": "object",
                        "description": "Connection configuration to store"
                    },
                    "config_id": {
                        "type": "string",
                        "description": "ID of the stored configuration"
                    },
                    "source_info": {
                        "type": "object",
                        "description": "Information about the data source",
                        "properties": {
                            "type": {"type": "string"},
                            "required_capabilities": {"type": "array", "items": {"type": "string"}}
                        }
                    },
                    "query_context": {
                        "type": "string",
                        "description": "Query context for connector recommendation"
                    }
                },
                "required": ["action"]
            }
        }
        self.storage_manager = AzureFileStorageManager()
        self.registry = {}
        self.connection_configs = {}
        self.performance_metrics = {}
        self._load_registry()
        super().__init__(name=self.name, metadata=self.metadata)
    
    def perform(self, **kwargs):
        action = kwargs.get('action')
        
        try:
            if action == 'register':
                connector_info = kwargs.get('connector_info', {})
                connector_id = self.register_connector(connector_info)
                return json.dumps({
                    "status": "success",
                    "action": "register",
                    "connector_id": connector_id
                })
            
            elif action == 'get':
                connector_id = kwargs.get('connector_id')
                connector = self.get_connector(connector_id)
                if connector:
                    return json.dumps({
                        "status": "success",
                        "action": "get",
                        "connector": connector
                    })
                else:
                    return json.dumps({
                        "status": "error",
                        "message": f"Connector {connector_id} not found"
                    })
            
            elif action == 'find_by_type':
                connector_type = kwargs.get('connector_type')
                connectors = self.find_connectors_by_type(connector_type)
                return json.dumps({
                    "status": "success",
                    "action": "find_by_type",
                    "connectors": connectors
                })
            
            elif action == 'find_by_capability':
                capability = kwargs.get('capability')
                connectors = self.find_connector_by_capability(capability)
                return json.dumps({
                    "status": "success",
                    "action": "find_by_capability",
                    "connectors": connectors
                })
            
            elif action == 'update_usage':
                connector_id = kwargs.get('connector_id')
                success = kwargs.get('success', True)
                response_time = kwargs.get('response_time', 0)
                self.update_connector_usage(connector_id, success, response_time)
                return json.dumps({
                    "status": "success",
                    "action": "update_usage",
                    "connector_id": connector_id
                })
            
            elif action == 'store_config':
                connector_id = kwargs.get('connector_id')
                config = kwargs.get('config', {})
                config_id = self.store_connection_config(connector_id, config)
                return json.dumps({
                    "status": "success",
                    "action": "store_config",
                    "config_id": config_id
                })
            
            elif action == 'get_config':
                config_id = kwargs.get('config_id')
                config_data = self.get_connection_config(config_id)
                if config_data:
                    return json.dumps({
                        "status": "success",
                        "action": "get_config",
                        "config": config_data
                    })
                else:
                    return json.dumps({
                        "status": "error",
                        "message": f"Config {config_id} not found"
                    })
            
            elif action == 'get_best':
                source_info = kwargs.get('source_info', {})
                best_connector = self.get_best_connector_for_source(source_info)
                if best_connector:
                    return json.dumps({
                        "status": "success",
                        "action": "get_best",
                        "connector": best_connector
                    })
                else:
                    return json.dumps({
                        "status": "error",
                        "message": "No suitable connector found"
                    })
            
            elif action == 'performance_report':
                connector_id = kwargs.get('connector_id')
                report = self.get_performance_report(connector_id)
                return json.dumps({
                    "status": "success",
                    "action": "performance_report",
                    "report": report
                })
            
            elif action == 'recommend':
                query_context = kwargs.get('query_context', '')
                recommendation = self.recommend_connector(query_context)
                if recommendation:
                    return json.dumps({
                        "status": "success",
                        "action": "recommend",
                        "recommendation": recommendation
                    })
                else:
                    return json.dumps({
                        "status": "error",
                        "message": "No recommendation available"
                    })
            
            else:
                return json.dumps({
                    "status": "error",
                    "message": f"Unknown action: {action}"
                })
                
        except Exception as e:
            logging.error(f"Error in ConnectorRegistry: {str(e)}")
            return json.dumps({
                "status": "error",
                "message": str(e)
            })
    
    def _load_registry(self):
        """Load the connector registry from storage."""
        try:
            registry_data = self.storage_manager.read_json_from_path(
                "data_connectors", 
                "registry.json"
            )
            if registry_data:
                self.registry = registry_data.get('connectors', {})
                self.connection_configs = registry_data.get('configs', {})
                self.performance_metrics = registry_data.get('metrics', {})
                logging.info(f"Loaded {len(self.registry)} registered connectors")
        except Exception as e:
            logging.warning(f"Could not load connector registry: {str(e)}")
            self.registry = {}
            self.connection_configs = {}
            self.performance_metrics = {}
    
    def _save_registry(self):
        """Save the connector registry to storage."""
        try:
            registry_data = {
                'connectors': self.registry,
                'configs': self.connection_configs,
                'metrics': self.performance_metrics,
                'last_updated': datetime.now().isoformat()
            }
            self.storage_manager.write_json_to_path(
                registry_data,
                "data_connectors",
                "registry.json"
            )
            logging.info("Saved connector registry")
        except Exception as e:
            logging.error(f"Error saving connector registry: {str(e)}")
    
    def register_connector(self, connector_info):
        """Register a new data connector."""
        connector_id = connector_info.get('id')
        if not connector_id:
            connector_id = self._generate_connector_id(connector_info)
        
        self.registry[connector_id] = {
            'type': connector_info.get('type', 'unknown'),
            'name': connector_info.get('name', connector_id),
            'description': connector_info.get('description', ''),
            'capabilities': connector_info.get('capabilities', []),
            'required_params': connector_info.get('required_params', []),
            'optional_params': connector_info.get('optional_params', []),
            'registered_at': datetime.now().isoformat(),
            'last_used': None,
            'usage_count': 0,
            'success_rate': 1.0
        }
        
        self.performance_metrics[connector_id] = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'average_response_time': 0,
            'last_response_time': 0
        }
        
        self._save_registry()
        logging.info(f"Registered connector: {connector_id}")
        return connector_id
    
    def _generate_connector_id(self, connector_info):
        """Generate a unique ID for a connector."""
        unique_string = f"{connector_info.get('type')}_{connector_info.get('name')}_{datetime.now().isoformat()}"
        return hashlib.md5(unique_string.encode()).hexdigest()[:12]
    
    def get_connector(self, connector_id):
        """Get connector information by ID."""
        return self.registry.get(connector_id)
    
    def find_connectors_by_type(self, connector_type):
        """Find all connectors of a specific type."""
        matching_connectors = []
        for connector_id, info in self.registry.items():
            if info['type'].lower() == connector_type.lower():
                matching_connectors.append({
                    'id': connector_id,
                    **info
                })
        return matching_connectors
    
    def find_connector_by_capability(self, capability):
        """Find connectors that have a specific capability."""
        matching_connectors = []
        for connector_id, info in self.registry.items():
            if capability in info.get('capabilities', []):
                matching_connectors.append({
                    'id': connector_id,
                    **info
                })
        return matching_connectors
    
    def update_connector_usage(self, connector_id, success=True, response_time=0):
        """Update usage statistics for a connector."""
        if connector_id in self.registry:
            self.registry[connector_id]['last_used'] = datetime.now().isoformat()
            self.registry[connector_id]['usage_count'] += 1
            
            metrics = self.performance_metrics[connector_id]
            metrics['total_requests'] += 1
            
            if success:
                metrics['successful_requests'] += 1
            else:
                metrics['failed_requests'] += 1
            
            if response_time > 0:
                metrics['last_response_time'] = response_time
                current_avg = metrics['average_response_time']
                total_requests = metrics['total_requests']
                metrics['average_response_time'] = (
                    (current_avg * (total_requests - 1) + response_time) / total_requests
                )
            
            self.registry[connector_id]['success_rate'] = (
                metrics['successful_requests'] / metrics['total_requests']
            )
            
            self._save_registry()
    
    def store_connection_config(self, connector_id, config):
        """Store connection configuration for a connector."""
        config_id = f"{connector_id}_{hashlib.md5(json.dumps(config, sort_keys=True).encode()).hexdigest()[:8]}"
        
        self.connection_configs[config_id] = {
            'connector_id': connector_id,
            'config': config,
            'created_at': datetime.now().isoformat(),
            'last_used': datetime.now().isoformat(),
            'usage_count': 1
        }
        
        self._save_registry()
        return config_id
    
    def get_connection_config(self, config_id):
        """Retrieve a stored connection configuration."""
        config_data = self.connection_configs.get(config_id)
        if config_data:
            config_data['last_used'] = datetime.now().isoformat()
            config_data['usage_count'] = config_data.get('usage_count', 0) + 1
            self._save_registry()
        return config_data
    
    def get_best_connector_for_source(self, source_info):
        """Determine the best connector for a given data source."""
        source_type = source_info.get('type', '').lower()
        
        type_matches = self.find_connectors_by_type(source_type)
        if type_matches:
            best_connector = max(type_matches, key=lambda x: x.get('success_rate', 0))
            return best_connector
        
        required_capabilities = source_info.get('required_capabilities', [])
        if required_capabilities:
            compatible_connectors = []
            for connector_id, info in self.registry.items():
                connector_capabilities = set(info.get('capabilities', []))
                if all(cap in connector_capabilities for cap in required_capabilities):
                    compatible_connectors.append({
                        'id': connector_id,
                        **info
                    })
            
            if compatible_connectors:
                best_connector = max(compatible_connectors, key=lambda x: x.get('success_rate', 0))
                return best_connector
        
        return None
    
    def get_performance_report(self, connector_id=None):
        """Get performance report for one or all connectors."""
        if connector_id:
            if connector_id in self.performance_metrics:
                return {
                    'connector_id': connector_id,
                    'connector_name': self.registry[connector_id]['name'],
                    'metrics': self.performance_metrics[connector_id]
                }
            return None
        
        report = []
        for conn_id, metrics in self.performance_metrics.items():
            if conn_id in self.registry:
                report.append({
                    'connector_id': conn_id,
                    'connector_name': self.registry[conn_id]['name'],
                    'connector_type': self.registry[conn_id]['type'],
                    'success_rate': self.registry[conn_id]['success_rate'],
                    'metrics': metrics
                })
        
        report.sort(key=lambda x: (x['success_rate'], x['metrics']['total_requests']), reverse=True)
        return report
    
    def recommend_connector(self, query_context):
        """Recommend the best connector based on query context."""
        recommendations = []
        
        query_lower = query_context.lower()
        
        if 'sql' in query_lower or 'database' in query_lower:
            sql_connectors = self.find_connectors_by_type('sql')
            recommendations.extend(sql_connectors)
        
        if 'nosql' in query_lower or 'mongodb' in query_lower or 'cosmos' in query_lower:
            nosql_connectors = self.find_connectors_by_type('nosql')
            recommendations.extend(nosql_connectors)
        
        if 'api' in query_lower or 'rest' in query_lower:
            api_connectors = self.find_connectors_by_type('api')
            recommendations.extend(api_connectors)
        
        if 'csv' in query_lower or 'excel' in query_lower or 'file' in query_lower:
            file_connectors = self.find_connectors_by_type('file')
            recommendations.extend(file_connectors)
        
        if 'stream' in query_lower or 'kafka' in query_lower or 'event' in query_lower:
            stream_connectors = self.find_connectors_by_type('stream')
            recommendations.extend(stream_connectors)
        
        if recommendations:
            unique_recommendations = {r['id']: r for r in recommendations}.values()
            best_recommendation = max(unique_recommendations, key=lambda x: x.get('success_rate', 0))
            return best_recommendation
        
        if self.registry:
            all_connectors = [
                {'id': conn_id, **info} 
                for conn_id, info in self.registry.items()
            ]
            good_connectors = [c for c in all_connectors if c.get('success_rate', 0) > 0.7]
            if good_connectors:
                best_connector = max(good_connectors, key=lambda x: x.get('usage_count', 0))
                return best_connector
        
        return None