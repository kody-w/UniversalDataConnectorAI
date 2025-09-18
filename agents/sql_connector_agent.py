import logging
import json
from agents.basic_agent import BasicAgent
from utils.azure_file_storage import AzureFileStorageManager
from datetime import datetime
import hashlib

class SQLConnectorAgent(BasicAgent):
    def __init__(self):
        self.name = 'SQLConnector'
        self.metadata = {
            "name": self.name,
            "description": "Connects to SQL databases, executes queries, and manages database operations with learning capabilities",
            "parameters": {
                "type": "object",
                "properties": {
                    "connection_string": {
                        "type": "string",
                        "description": "Database connection string or configuration"
                    },
                    "query": {
                        "type": "string",
                        "description": "SQL query to execute"
                    },
                    "operation": {
                        "type": "string",
                        "description": "Operation type: query, insert, update, delete, schema",
                        "enum": ["query", "insert", "update", "delete", "schema"]
                    },
                    "parameters": {
                        "type": "object",
                        "description": "Query parameters for parameterized queries"
                    },
                    "cache_result": {
                        "type": "boolean",
                        "description": "Whether to cache the query result"
                    },
                    "learn_pattern": {
                        "type": "boolean",
                        "description": "Whether to learn from this query pattern"
                    }
                },
                "required": ["connection_string", "operation"]
            }
        }
        self.storage_manager = AzureFileStorageManager()
        self.query_patterns = self._load_query_patterns()
        super().__init__(name=self.name, metadata=self.metadata)

    def _load_query_patterns(self):
        """Load learned query patterns."""
        try:
            patterns = self.storage_manager.read_json_from_path(
                "query_templates",
                "sql_patterns.json"
            )
            return patterns if patterns else {}
        except Exception:
            return {}

    def _save_query_patterns(self):
        """Save learned query patterns."""
        try:
            self.storage_manager.write_json_to_path(
                self.query_patterns,
                "query_templates",
                "sql_patterns.json"
            )
        except Exception as e:
            logging.error(f"Error saving query patterns: {str(e)}")

    def perform(self, **kwargs):
        """Execute SQL operations with learning capabilities."""
        connection_string = kwargs.get('connection_string', '')
        query = kwargs.get('query', '')
        operation = kwargs.get('operation', 'query')
        parameters = kwargs.get('parameters', {})
        cache_result = kwargs.get('cache_result', True)
        learn_pattern = kwargs.get('learn_pattern', True)
        
        if not connection_string:
            return "Error: Connection string is required"
        
        try:
            # Check cache first if caching is enabled
            if cache_result and query:
                cache_key = f"{connection_string}_{query}_{json.dumps(parameters, sort_keys=True)}"
                cached_data = self.storage_manager.get_cached_data(cache_key)
                if cached_data:
                    logging.info(f"Returning cached result for SQL query")
                    return json.dumps({
                        'status': 'success',
                        'source': 'cache',
                        'data': cached_data
                    })
            
            # Parse connection string to extract database info
            db_info = self._parse_connection_string(connection_string)
            
            # Execute operation based on type
            if operation == 'schema':
                result = self._get_database_schema(db_info)
            elif operation == 'query':
                result = self._execute_query(db_info, query, parameters)
            elif operation == 'insert':
                result = self._execute_insert(db_info, query, parameters)
            elif operation == 'update':
                result = self._execute_update(db_info, query, parameters)
            elif operation == 'delete':
                result = self._execute_delete(db_info, query, parameters)
            else:
                return f"Error: Unknown operation type: {operation}"
            
            # Learn from successful queries
            if learn_pattern and query and result.get('status') == 'success':
                self._learn_query_pattern(query, parameters, result)
            
            # Cache successful results
            if cache_result and result.get('status') == 'success' and query:
                cache_key = f"{connection_string}_{query}_{json.dumps(parameters, sort_keys=True)}"
                self.storage_manager.cache_data(cache_key, result.get('data'))
            
            return json.dumps(result)
            
        except Exception as e:
            logging.error(f"Error in SQL connector: {str(e)}")
            return json.dumps({
                'status': 'error',
                'error': str(e)
            })

    def _parse_connection_string(self, connection_string):
        """Parse connection string to extract database information."""
        # This is a simplified parser - in production, use proper parsing
        db_info = {
            'type': 'unknown',
            'host': '',
            'database': '',
            'user': '',
            'password': ''
        }
        
        # Check for common database types
        if 'mysql' in connection_string.lower():
            db_info['type'] = 'mysql'
        elif 'postgresql' in connection_string.lower() or 'postgres' in connection_string.lower():
            db_info['type'] = 'postgresql'
        elif 'sqlserver' in connection_string.lower() or 'mssql' in connection_string.lower():
            db_info['type'] = 'sqlserver'
        elif 'sqlite' in connection_string.lower():
            db_info['type'] = 'sqlite'
        elif 'oracle' in connection_string.lower():
            db_info['type'] = 'oracle'
        
        # Parse connection parameters (simplified)
        # In production, use proper URL parsing
        parts = connection_string.split(';')
        for part in parts:
            if '=' in part:
                key, value = part.split('=', 1)
                key = key.lower().strip()
                value = value.strip()
                
                if key in ['server', 'host', 'data source']:
                    db_info['host'] = value
                elif key in ['database', 'initial catalog']:
                    db_info['database'] = value
                elif key in ['user', 'user id', 'uid']:
                    db_info['user'] = value
                elif key in ['password', 'pwd']:
                    db_info['password'] = value
        
        return db_info

    def _get_database_schema(self, db_info):
        """Get database schema information."""
        # This is a simulated implementation
        # In production, use actual database connection libraries
        
        # For demonstration, return a sample schema
        sample_schema = {
            'tables': {
                'customers': {
                    'columns': {
                        'id': {'type': 'integer', 'primary_key': True},
                        'name': {'type': 'varchar(100)', 'nullable': False},
                        'email': {'type': 'varchar(100)', 'nullable': False},
                        'created_at': {'type': 'datetime', 'nullable': False}
                    }
                },
                'orders': {
                    'columns': {
                        'id': {'type': 'integer', 'primary_key': True},
                        'customer_id': {'type': 'integer', 'foreign_key': 'customers.id'},
                        'order_date': {'type': 'datetime', 'nullable': False},
                        'total': {'type': 'decimal(10,2)', 'nullable': False}
                    }
                }
            }
        }
        
        # Store schema for learning
        schema_id = hashlib.md5(f"{db_info['host']}_{db_info['database']}".encode()).hexdigest()[:12]
        self.storage_manager.store_schema(schema_id, sample_schema)
        
        return {
            'status': 'success',
            'schema_id': schema_id,
            'data': sample_schema
        }

    def _execute_query(self, db_info, query, parameters):
        """Execute a SELECT query."""
        # This is a simulated implementation
        # In production, use actual database connection libraries (pymysql, psycopg2, etc.)
        
        # For demonstration, return sample data
        sample_data = [
            {'id': 1, 'name': 'John Doe', 'email': 'john@example.com'},
            {'id': 2, 'name': 'Jane Smith', 'email': 'jane@example.com'}
        ]
        
        return {
            'status': 'success',
            'operation': 'query',
            'rows_returned': len(sample_data),
            'data': sample_data
        }

    def _execute_insert(self, db_info, query, parameters):
        """Execute an INSERT query."""
        # Simulated implementation
        return {
            'status': 'success',
            'operation': 'insert',
            'rows_affected': 1,
            'message': 'Insert operation completed'
        }

    def _execute_update(self, db_info, query, parameters):
        """Execute an UPDATE query."""
        # Simulated implementation
        return {
            'status': 'success',
            'operation': 'update',
            'rows_affected': 1,
            'message': 'Update operation completed'
        }

    def _execute_delete(self, db_info, query, parameters):
        """Execute a DELETE query."""
        # Simulated implementation
        return {
            'status': 'success',
            'operation': 'delete',
            'rows_affected': 1,
            'message': 'Delete operation completed'
        }

    def _learn_query_pattern(self, query, parameters, result):
        """Learn from successful query patterns."""
        try:
            # Extract query pattern
            pattern = self._extract_query_pattern(query)
            pattern_id = hashlib.md5(pattern.encode()).hexdigest()[:12]
            
            if pattern_id not in self.query_patterns:
                self.query_patterns[pattern_id] = {
                    'pattern': pattern,
                    'examples': [],
                    'success_count': 0,
                    'avg_rows_returned': 0,
                    'learned_at': datetime.now().isoformat()
                }
            
            # Update pattern statistics
            self.query_patterns[pattern_id]['success_count'] += 1
            self.query_patterns[pattern_id]['examples'].append({
                'query': query,
                'parameters': parameters,
                'timestamp': datetime.now().isoformat()
            })
            
            # Keep only last 10 examples
            if len(self.query_patterns[pattern_id]['examples']) > 10:
                self.query_patterns[pattern_id]['examples'] = \
                    self.query_patterns[pattern_id]['examples'][-10:]
            
            # Update average rows returned for SELECT queries
            if result.get('rows_returned') is not None:
                current_avg = self.query_patterns[pattern_id]['avg_rows_returned']
                count = self.query_patterns[pattern_id]['success_count']
                new_avg = ((current_avg * (count - 1)) + result['rows_returned']) / count
                self.query_patterns[pattern_id]['avg_rows_returned'] = new_avg
            
            self._save_query_patterns()
            
        except Exception as e:
            logging.error(f"Error learning query pattern: {str(e)}")

    def _extract_query_pattern(self, query):
        """Extract pattern from SQL query."""
        # Remove values and keep structure
        pattern = query.upper()
        
        # Replace specific values with placeholders
        import re
        
        # Replace quoted strings
        pattern = re.sub(r"'[^']*'", "'?'", pattern)
        pattern = re.sub(r'"[^"]*"', '"?"', pattern)
        
        # Replace numbers
        pattern = re.sub(r'\b\d+\b', '?', pattern)
        
        # Remove extra spaces
        pattern = ' '.join(pattern.split())
        
        return pattern

    def suggest_optimizations(self, query):
        """Suggest query optimizations based on learned patterns."""
        pattern = self._extract_query_pattern(query)
        pattern_id = hashlib.md5(pattern.encode()).hexdigest()[:12]
        
        suggestions = []
        
        if pattern_id in self.query_patterns:
            pattern_info = self.query_patterns[pattern_id]
            
            # Suggest based on average rows returned
            if pattern_info['avg_rows_returned'] > 1000:
                suggestions.append({
                    'type': 'performance',
                    'suggestion': 'Consider adding LIMIT clause for large result sets',
                    'priority': 'high'
                })
            
            # Suggest based on frequency
            if pattern_info['success_count'] > 10:
                suggestions.append({
                    'type': 'caching',
                    'suggestion': 'This query pattern is frequently used. Consider caching results.',
                    'priority': 'medium'
                })
        
        # General suggestions based on query analysis
        query_upper = query.upper()
        
        if 'SELECT *' in query_upper:
            suggestions.append({
                'type': 'performance',
                'suggestion': 'Avoid SELECT *. Specify only needed columns.',
                'priority': 'medium'
            })
        
        if 'JOIN' in query_upper and 'INDEX' not in query_upper:
            suggestions.append({
                'type': 'performance',
                'suggestion': 'Ensure proper indexes exist on JOIN columns.',
                'priority': 'high'
            })
        
        return suggestions
