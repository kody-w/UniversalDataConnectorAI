import logging
import json
from datetime import datetime
import re
from typing import Any, Dict, List, Optional
from agents.basic_agent import BasicAgent
from utils.azure_file_storage import AzureFileStorageManager

class SchemaLearnerAgent(BasicAgent):
    def __init__(self):
        self.name = "SchemaLearner"
        self.metadata = {
            "name": self.name,
            "description": "Learns, analyzes, and manages data source schemas. Can auto-detect schemas, suggest transformations, and validate data against learned patterns.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "The schema operation to perform",
                        "enum": ["analyze", "learn", "validate", "suggest_transformation", "auto_map", "get_compatibility", "save", "load"]
                    },
                    "source_info": {
                        "type": "object",
                        "description": "Information about the data source (for analyze/learn actions)",
                        "properties": {
                            "type": {
                                "type": "string",
                                "description": "Type of data source: json, csv, sql, api, xml"
                            },
                            "sample_data": {
                                "type": "object",
                                "description": "Sample data for analysis"
                            },
                            "headers": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "CSV headers (for CSV type)"
                            },
                            "sample_rows": {
                                "type": "array",
                                "items": {
                                    "type": "array",
                                    "items": {"type": "string"}
                                },
                                "description": "Sample CSV rows (for CSV type)"
                            },
                            "table_info": {
                                "type": "object",
                                "description": "Table information (for SQL type)"
                            },
                            "response_sample": {
                                "type": "object",
                                "description": "API response sample (for API type)"
                            }
                        }
                    },
                    "schema": {
                        "type": "object",
                        "description": "Schema to use for validation or comparison"
                    },
                    "target_schema": {
                        "type": "object",
                        "description": "Target schema for transformation suggestions"
                    },
                    "source_schema": {
                        "type": "object",
                        "description": "Source schema for transformation or compatibility check"
                    },
                    "data": {
                        "type": "object",
                        "description": "Data to validate against schema"
                    },
                    "mapping_rules": {
                        "type": "object",
                        "description": "Rules for field mapping between schemas"
                    },
                    "source_fields": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of source field names for auto-mapping"
                    },
                    "target_fields": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of target field names for auto-mapping"
                    },
                    "target_type": {
                        "type": "string",
                        "description": "Target schema type for transformation suggestions"
                    },
                    "schema_id": {
                        "type": "string",
                        "description": "ID for saving/loading schemas"
                    }
                },
                "required": ["action"]
            }
        }
        self.storage_manager = AzureFileStorageManager()
        self.learned_schemas = {}
        self.schema_patterns = {}
        self.transformation_rules = {}
        self._load_schemas()
        super().__init__(name=self.name, metadata=self.metadata)
    
    def perform(self, **kwargs):
        action = kwargs.get('action')
        
        try:
            if action == 'analyze':
                source_info = kwargs.get('source_info', {})
                result = self.analyze_source(source_info)
                return json.dumps({
                    "status": "success",
                    "action": "analyze",
                    "schema": result
                })
            
            elif action == 'learn':
                source_schema = kwargs.get('source_schema')
                target_schema = kwargs.get('target_schema')
                mapping_rules = kwargs.get('mapping_rules', {})
                transformation_id = self.learn_transformation(source_schema, target_schema, mapping_rules)
                return json.dumps({
                    "status": "success",
                    "action": "learn",
                    "transformation_id": transformation_id
                })
            
            elif action == 'validate':
                data = kwargs.get('data')
                schema = kwargs.get('schema')
                validation_result = self.validate_schema(data, schema)
                return json.dumps({
                    "status": "success",
                    "action": "validate",
                    "validation": validation_result
                })
            
            elif action == 'suggest_transformation':
                source_schema = kwargs.get('source_schema')
                target_type = kwargs.get('target_type')
                suggestions = self.suggest_transformations(source_schema, target_type)
                return json.dumps({
                    "status": "success",
                    "action": "suggest_transformation",
                    "suggestions": suggestions
                })
            
            elif action == 'auto_map':
                source_fields = kwargs.get('source_fields', [])
                target_fields = kwargs.get('target_fields', [])
                mapping = self.auto_map_fields(source_fields, target_fields)
                return json.dumps({
                    "status": "success",
                    "action": "auto_map",
                    "mapping": mapping
                })
            
            elif action == 'get_compatibility':
                source_schema = kwargs.get('source_schema')
                target_schema = kwargs.get('target_schema')
                compatibility = self.get_schema_compatibility(source_schema, target_schema)
                return json.dumps({
                    "status": "success",
                    "action": "get_compatibility",
                    "compatibility": compatibility
                })
            
            elif action == 'save':
                schema_id = kwargs.get('schema_id')
                schema = kwargs.get('schema')
                if schema_id and schema:
                    self.learned_schemas[schema_id] = schema
                    self._save_schemas()
                    return json.dumps({
                        "status": "success",
                        "action": "save",
                        "schema_id": schema_id
                    })
                else:
                    return json.dumps({
                        "status": "error",
                        "message": "schema_id and schema are required"
                    })
            
            elif action == 'load':
                schema_id = kwargs.get('schema_id')
                if schema_id in self.learned_schemas:
                    return json.dumps({
                        "status": "success",
                        "action": "load",
                        "schema": self.learned_schemas[schema_id]
                    })
                else:
                    return json.dumps({
                        "status": "error",
                        "message": f"Schema {schema_id} not found"
                    })
            
            else:
                return json.dumps({
                    "status": "error",
                    "message": f"Unknown action: {action}"
                })
                
        except Exception as e:
            logging.error(f"Error in SchemaLearner: {str(e)}")
            return json.dumps({
                "status": "error",
                "message": str(e)
            })
    
    def _load_schemas(self):
        """Load previously learned schemas from storage."""
        try:
            schemas_data = self.storage_manager.read_json_from_path(
                "schemas",
                "learned_schemas.json"
            )
            if schemas_data:
                self.learned_schemas = schemas_data.get('schemas', {})
                self.schema_patterns = schemas_data.get('patterns', {})
                self.transformation_rules = schemas_data.get('rules', {})
                logging.info(f"Loaded {len(self.learned_schemas)} learned schemas")
        except Exception as e:
            logging.warning(f"Could not load learned schemas: {str(e)}")
            self.learned_schemas = {}
            self.schema_patterns = {}
            self.transformation_rules = {}
    
    def _save_schemas(self):
        """Save learned schemas to storage."""
        try:
            schemas_data = {
                'schemas': self.learned_schemas,
                'patterns': self.schema_patterns,
                'rules': self.transformation_rules,
                'last_updated': datetime.now().isoformat()
            }
            self.storage_manager.write_json_to_path(
                schemas_data,
                "schemas",
                "learned_schemas.json"
            )
            logging.info("Saved learned schemas")
        except Exception as e:
            logging.error(f"Error saving learned schemas: {str(e)}")
    
    def analyze_source(self, source_info):
        """Analyze a data source and learn its schema."""
        source_type = source_info.get('type', 'unknown')
        
        if source_type == 'json':
            return self._analyze_json_schema(source_info.get('sample_data'))
        elif source_type == 'csv':
            return self._analyze_csv_schema(source_info.get('headers'), source_info.get('sample_rows'))
        elif source_type == 'sql':
            return self._analyze_sql_schema(source_info.get('table_info'))
        elif source_type == 'api':
            return self._analyze_api_schema(source_info.get('response_sample'))
        elif source_type == 'xml':
            return self._analyze_xml_schema(source_info.get('sample_data'))
        else:
            return self._analyze_generic_schema(source_info)
    
    def _analyze_json_schema(self, json_data):
        """Analyze JSON data and extract schema."""
        if not json_data:
            return None
        
        schema = {
            'type': 'json',
            'structure': self._extract_json_structure(json_data),
            'analyzed_at': datetime.now().isoformat()
        }
        
        patterns = self._extract_patterns(json_data)
        if patterns:
            schema['patterns'] = patterns
        
        return schema
    
    def _extract_json_structure(self, data, path=""):
        """Recursively extract structure from JSON data."""
        if isinstance(data, dict):
            structure = {
                'type': 'object',
                'properties': {}
            }
            for key, value in data.items():
                current_path = f"{path}.{key}" if path else key
                structure['properties'][key] = self._extract_json_structure(value, current_path)
            return structure
        elif isinstance(data, list):
            if len(data) > 0:
                first_element = data[0]
                return {
                    'type': 'array',
                    'items': self._extract_json_structure(first_element, f"{path}[]")
                }
            else:
                return {'type': 'array', 'items': {'type': 'unknown'}}
        else:
            data_type = self._determine_data_type(data)
            return {
                'type': data_type,
                'sample_value': str(data)[:100] if data else None
            }
    
    def _determine_data_type(self, value):
        """Determine the data type of a value."""
        if value is None:
            return 'null'
        elif isinstance(value, bool):
            return 'boolean'
        elif isinstance(value, int):
            return 'integer'
        elif isinstance(value, float):
            return 'number'
        elif isinstance(value, str):
            if self._is_date(value):
                return 'date'
            elif self._is_email(value):
                return 'email'
            elif self._is_url(value):
                return 'url'
            else:
                return 'string'
        else:
            return 'unknown'
    
    def _is_date(self, value):
        """Check if a string value is a date."""
        date_patterns = [
            r'^\d{4}-\d{2}-\d{2}$',
            r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}',
            r'^\d{2}/\d{2}/\d{4}$'
        ]
        for pattern in date_patterns:
            if re.match(pattern, str(value)):
                return True
        return False
    
    def _is_email(self, value):
        """Check if a string value is an email."""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(email_pattern, str(value)))
    
    def _is_url(self, value):
        """Check if a string value is a URL."""
        url_pattern = r'^https?://[^\s/$.?#].[^\s]*$'
        return bool(re.match(url_pattern, str(value)))
    
    def _extract_patterns(self, data):
        """Extract patterns from data."""
        patterns = []
        
        if isinstance(data, dict):
            id_fields = [k for k in data.keys() if 'id' in k.lower()]
            if id_fields:
                patterns.append({'type': 'id_fields', 'fields': id_fields})
            
            time_fields = [k for k in data.keys() if any(t in k.lower() for t in ['time', 'date', 'created', 'updated'])]
            if time_fields:
                patterns.append({'type': 'timestamp_fields', 'fields': time_fields})
            
            nested_objects = [k for k, v in data.items() if isinstance(v, dict)]
            if nested_objects:
                patterns.append({'type': 'nested_objects', 'fields': nested_objects})
            
            array_fields = [k for k, v in data.items() if isinstance(v, list)]
            if array_fields:
                patterns.append({'type': 'array_fields', 'fields': array_fields})
        
        return patterns if patterns else None
    
    def _analyze_csv_schema(self, headers, sample_rows):
        """Analyze CSV data and extract schema."""
        if not headers:
            return None
        
        schema = {
            'type': 'csv',
            'headers': headers,
            'columns': {},
            'analyzed_at': datetime.now().isoformat()
        }
        
        for i, header in enumerate(headers):
            column_info = {
                'name': header,
                'position': i,
                'data_types': []
            }
            
            if sample_rows:
                for row in sample_rows[:10]:
                    if i < len(row):
                        value = row[i]
                        data_type = self._determine_data_type(value)
                        if data_type not in column_info['data_types']:
                            column_info['data_types'].append(data_type)
            
            schema['columns'][header] = column_info
        
        return schema
    
    def _analyze_sql_schema(self, table_info):
        """Analyze SQL table schema."""
        if not table_info:
            return None
        
        schema = {
            'type': 'sql',
            'tables': {},
            'relationships': [],
            'analyzed_at': datetime.now().isoformat()
        }
        
        for table_name, table_details in table_info.items():
            schema['tables'][table_name] = {
                'columns': table_details.get('columns', {}),
                'primary_key': table_details.get('primary_key'),
                'foreign_keys': table_details.get('foreign_keys', []),
                'indexes': table_details.get('indexes', [])
            }
            
            for fk in table_details.get('foreign_keys', []):
                relationship = {
                    'from_table': table_name,
                    'from_column': fk.get('column'),
                    'to_table': fk.get('references_table'),
                    'to_column': fk.get('references_column')
                }
                schema['relationships'].append(relationship)
        
        return schema
    
    def _analyze_api_schema(self, response_sample):
        """Analyze API response schema."""
        if not response_sample:
            return None
        
        if isinstance(response_sample, (dict, list)):
            base_schema = self._analyze_json_schema(response_sample)
            base_schema['type'] = 'api_json'
            return base_schema
        
        return {
            'type': 'api',
            'response_type': 'text',
            'sample': str(response_sample)[:500],
            'analyzed_at': datetime.now().isoformat()
        }
    
    def _analyze_xml_schema(self, xml_data):
        """Analyze XML data schema."""
        return {
            'type': 'xml',
            'structure': 'xml_document',
            'analyzed_at': datetime.now().isoformat(),
            'note': 'Full XML parsing would require additional libraries'
        }
    
    def _analyze_generic_schema(self, source_info):
        """Analyze generic data source schema."""
        return {
            'type': source_info.get('type', 'unknown'),
            'info': source_info,
            'analyzed_at': datetime.now().isoformat()
        }
    
    def learn_transformation(self, source_schema, target_schema, mapping_rules):
        """Learn transformation rules between schemas."""
        transformation_id = f"{source_schema.get('type')}_{target_schema.get('type')}_{datetime.now().timestamp()}"
        
        self.transformation_rules[transformation_id] = {
            'source_schema': source_schema,
            'target_schema': target_schema,
            'mapping_rules': mapping_rules,
            'learned_at': datetime.now().isoformat(),
            'usage_count': 0,
            'success_rate': 1.0
        }
        
        self._save_schemas()
        return transformation_id
    
    def suggest_transformations(self, source_schema, target_type):
        """Suggest transformations based on learned patterns."""
        suggestions = []
        
        for rule_id, rule in self.transformation_rules.items():
            if (rule['source_schema'].get('type') == source_schema.get('type') and
                rule['target_schema'].get('type') == target_type):
                suggestions.append({
                    'rule_id': rule_id,
                    'mapping_rules': rule['mapping_rules'],
                    'success_rate': rule['success_rate']
                })
        
        suggestions.sort(key=lambda x: x['success_rate'], reverse=True)
        return suggestions
    
    def auto_map_fields(self, source_fields, target_fields):
        """Automatically map fields between schemas based on similarity."""
        field_mapping = {}
        
        for source_field in source_fields:
            best_match = None
            best_score = 0
            
            for target_field in target_fields:
                score = self._calculate_field_similarity(source_field, target_field)
                if score > best_score:
                    best_score = score
                    best_match = target_field
            
            if best_match and best_score > 0.5:
                field_mapping[source_field] = best_match
        
        return field_mapping
    
    def _calculate_field_similarity(self, field1, field2):
        """Calculate similarity between two field names."""
        f1 = field1.lower()
        f2 = field2.lower()
        
        if f1 == f2:
            return 1.0
        
        if f1 in f2 or f2 in f1:
            return 0.8
        
        common_mappings = {
            'id': ['identifier', 'key', 'uid'],
            'name': ['title', 'label', 'description'],
            'email': ['mail', 'email_address', 'contact'],
            'phone': ['telephone', 'mobile', 'contact_number'],
            'date': ['timestamp', 'datetime', 'created', 'updated'],
            'amount': ['value', 'price', 'cost', 'total']
        }
        
        for key, values in common_mappings.items():
            if (key in f1 and any(v in f2 for v in values)) or \
               (key in f2 and any(v in f1 for v in values)):
                return 0.7
        
        common_chars = set(f1) & set(f2)
        if len(set(f1)) > 0:
            return len(common_chars) / len(set(f1))
        
        return 0.0
    
    def validate_schema(self, data, schema):
        """Validate data against a schema."""
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        try:
            if schema.get('type') == 'json':
                self._validate_json_data(data, schema['structure'], validation_result)
            elif schema.get('type') == 'csv':
                self._validate_csv_data(data, schema, validation_result)
            
        except Exception as e:
            validation_result['valid'] = False
            validation_result['errors'].append(f"Validation error: {str(e)}")
        
        return validation_result
    
    def _validate_json_data(self, data, structure, result, path=""):
        """Validate JSON data against structure."""
        if structure.get('type') == 'object' and isinstance(data, dict):
            for prop, prop_structure in structure.get('properties', {}).items():
                current_path = f"{path}.{prop}" if path else prop
                if prop in data:
                    self._validate_json_data(data[prop], prop_structure, result, current_path)
                else:
                    result['warnings'].append(f"Missing expected property: {current_path}")
        elif structure.get('type') == 'array' and isinstance(data, list):
            for i, item in enumerate(data):
                item_path = f"{path}[{i}]"
                self._validate_json_data(item, structure.get('items', {}), result, item_path)
        else:
            expected_type = structure.get('type')
            actual_type = self._determine_data_type(data)
            if expected_type and expected_type != actual_type:
                result['errors'].append(f"Type mismatch at {path}: expected {expected_type}, got {actual_type}")
                result['valid'] = False
    
    def _validate_csv_data(self, data, schema, result):
        """Validate CSV data against schema."""
        expected_headers = schema.get('headers', [])
        
        if 'headers' in data:
            actual_headers = data['headers']
            if actual_headers != expected_headers:
                result['errors'].append(f"Header mismatch: expected {expected_headers}, got {actual_headers}")
                result['valid'] = False
    
    def get_schema_compatibility(self, schema1, schema2):
        """Check compatibility between two schemas."""
        compatibility_score = 0.0
        compatibility_details = {
            'compatible_fields': [],
            'incompatible_fields': [],
            'transformation_required': False
        }
        
        if schema1.get('type') == schema2.get('type'):
            compatibility_score += 0.3
        else:
            compatibility_details['transformation_required'] = True
        
        if schema1.get('type') == 'json' and schema2.get('type') == 'json':
            props1 = schema1.get('structure', {}).get('properties', {})
            props2 = schema2.get('structure', {}).get('properties', {})
            
            common_props = set(props1.keys()) & set(props2.keys())
            all_props = set(props1.keys()) | set(props2.keys())
            
            if all_props:
                field_compatibility = len(common_props) / len(all_props)
                compatibility_score += field_compatibility * 0.7
                
                compatibility_details['compatible_fields'] = list(common_props)
                compatibility_details['incompatible_fields'] = list(all_props - common_props)
        
        return {
            'score': compatibility_score,
            'details': compatibility_details
        }