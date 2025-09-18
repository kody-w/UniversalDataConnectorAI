from agents.basic_agent import BasicAgent
import json
import csv
import re
import logging
import os
import base64
import xml.etree.ElementTree as ET
from datetime import datetime
from collections import OrderedDict, Counter
from io import StringIO, BytesIO
from utils.azure_file_storage import AzureFileStorageManager
from openai import AzureOpenAI

class IntelligentFormatSynthesisAgent(BasicAgent):
    def __init__(self):
        self.name = "IntelligentFormatSynthesis"
        self.metadata = {
            "name": self.name,
            "description": "Intelligently converts JSON data to ANY format with proper file export. Automatically detects JSON structure and creates appropriate output format with full file writing capability.",
            "parameters": {
                "type": "object",
                "properties": {
                    "source_json_path": {
                        "type": "string",
                        "description": "Path to the JSON file in Azure storage (e.g., 'ai_translations/data.json')"
                    },
                    "source_json": {
                        "type": "object",
                        "description": "Direct JSON object to convert (alternative to path)"
                    },
                    "target_format": {
                        "type": "string",
                        "description": "Target format: 'csv', 'xml', 'tsv', 'html', 'markdown', 'sql', 'yaml', 'ini', 'jsonl', 'parquet_schema', or any custom format"
                    },
                    "output_directory": {
                        "type": "string",
                        "description": "Directory to save the output file (e.g., 'csv_exports'). Default: 'converted_exports'"
                    },
                    "output_filename": {
                        "type": "string",
                        "description": "Name for the output file (without extension). If not provided, generates from source"
                    },
                    "include_headers": {
                        "type": "boolean",
                        "description": "Include headers in output (for CSV, TSV, etc.). Default: true"
                    },
                    "delimiter": {
                        "type": "string",
                        "description": "Custom delimiter for delimited formats. Default: comma for CSV, tab for TSV"
                    },
                    "encoding": {
                        "type": "string",
                        "description": "Output encoding: 'utf-8', 'utf-16', 'ascii', 'latin-1'. Default: 'utf-8'"
                    },
                    "flatten_nested": {
                        "type": "boolean",
                        "description": "Flatten nested JSON structures. Default: true"
                    },
                    "custom_format_spec": {
                        "type": "object",
                        "description": "Custom format specification for exotic formats"
                    }
                },
                "required": ["target_format"]
            }
        }
        self.storage_manager = AzureFileStorageManager()
        
        # Initialize Azure OpenAI for intelligent conversion
        try:
            api_key = os.environ.get('AZURE_OPENAI_API_KEY')
            endpoint = os.environ.get('AZURE_OPENAI_ENDPOINT')
            api_version = os.environ.get('AZURE_OPENAI_API_VERSION', '2024-02-01')
            
            if api_key and endpoint:
                self.ai_client = AzureOpenAI(
                    api_key=api_key,
                    api_version=api_version,
                    azure_endpoint=endpoint
                )
                self.ai_enabled = True
                self.deployment_name = os.environ.get('AZURE_OPENAI_DEPLOYMENT_NAME', 'gpt-deployment')
            else:
                self.ai_enabled = False
        except Exception as e:
            self.ai_enabled = False
            logging.warning(f"AI features disabled: {str(e)}")
            
        super().__init__(name=self.name, metadata=self.metadata)

    def perform(self, **kwargs):
        try:
            # Extract parameters
            source_json_path = kwargs.get('source_json_path')
            source_json = kwargs.get('source_json')
            target_format = kwargs.get('target_format', 'csv').lower()
            output_directory = kwargs.get('output_directory', 'converted_exports')
            output_filename = kwargs.get('output_filename')
            include_headers = kwargs.get('include_headers', True)
            delimiter = kwargs.get('delimiter')
            encoding = kwargs.get('encoding', 'utf-8')
            flatten_nested = kwargs.get('flatten_nested', True)
            custom_format_spec = kwargs.get('custom_format_spec', {})
            
            # Load JSON data
            if source_json:
                json_data = source_json
                source_name = "direct_input"
            elif source_json_path:
                json_data = self._load_json_file(source_json_path)
                if not json_data:
                    return json.dumps({
                        "success": False,
                        "error": f"Could not load JSON from {source_json_path}"
                    })
                # Extract filename for output naming
                source_name = os.path.basename(source_json_path).replace('.json', '')
            else:
                return json.dumps({
                    "success": False,
                    "error": "Either source_json_path or source_json must be provided"
                })
            
            # Analyze JSON structure
            structure_analysis = self._analyze_json_structure(json_data)
            
            # Extract actual data from various JSON formats
            actual_data = self._extract_data_from_json(json_data, structure_analysis)
            
            # Generate output filename if not provided
            if not output_filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_filename = f"{source_name}_{timestamp}"
            
            # Convert based on target format
            conversion_result = self._convert_to_format(
                actual_data,
                target_format,
                structure_analysis,
                include_headers,
                delimiter,
                flatten_nested,
                custom_format_spec
            )
            
            # Save the file
            save_result = self._save_output_file(
                conversion_result['content'],
                conversion_result['extension'],
                output_directory,
                output_filename,
                encoding,
                conversion_result.get('is_binary', False)
            )
            
            # Generate download URL if possible
            download_url = self._generate_download_url(
                output_directory,
                f"{output_filename}.{conversion_result['extension']}"
            )
            
            # Return comprehensive result
            return json.dumps({
                "success": True,
                "message": f"Successfully converted to {target_format}",
                "output_path": save_result['path'],
                "download_url": download_url,
                "file_info": {
                    "directory": output_directory,
                    "filename": f"{output_filename}.{conversion_result['extension']}",
                    "format": target_format,
                    "encoding": encoding,
                    "size_bytes": save_result.get('size', 0),
                    "record_count": structure_analysis['record_count'],
                    "field_count": len(structure_analysis['fields'])
                },
                "structure_analysis": structure_analysis,
                "sample_output": conversion_result['content'][:500] if not conversion_result.get('is_binary') else "Binary content",
                "conversion_notes": conversion_result.get('notes', [])
            }, indent=2)
            
        except Exception as e:
            logging.error(f"Error in format synthesis: {str(e)}")
            return json.dumps({
                "success": False,
                "error": str(e)
            }, indent=2)

    def _load_json_file(self, path):
        """Load JSON file from Azure storage"""
        try:
            parts = path.rsplit('/', 1)
            if len(parts) == 2:
                directory, filename = parts
            else:
                directory = ''
                filename = parts[0]
            
            content = self.storage_manager.read_file(directory, filename)
            if content:
                return json.loads(content)
            return None
        except Exception as e:
            logging.error(f"Error loading JSON file: {str(e)}")
            return None

    def _analyze_json_structure(self, json_data):
        """Analyze the structure of JSON data"""
        analysis = {
            'type': 'unknown',
            'record_count': 0,
            'fields': [],
            'field_types': {},
            'nested_fields': [],
            'is_uniform': True,
            'has_data_key': False,
            'actual_data_path': None
        }
        
        # Check if it's a wrapped format (like from UniversalDataTranslator)
        if isinstance(json_data, dict):
            # Check for common data wrapper keys
            data_keys = ['data', 'records', 'items', 'results', 'rows', 'entries', 'content']
            for key in data_keys:
                if key in json_data and isinstance(json_data[key], list):
                    analysis['has_data_key'] = True
                    analysis['actual_data_path'] = key
                    json_data = json_data[key]  # Focus on actual data
                    break
            
            # If still dict and not a data wrapper, might be single record
            if not analysis['has_data_key'] and not isinstance(json_data, list):
                # Check if it's a single record or key-value pairs
                if all(not isinstance(v, (dict, list)) for v in json_data.values()):
                    # Simple key-value pairs, treat as single record
                    analysis['type'] = 'single_record'
                    analysis['record_count'] = 1
                    analysis['fields'] = list(json_data.keys())
                    for field, value in json_data.items():
                        analysis['field_types'][field] = type(value).__name__
                    return analysis
        
        # Handle list of records
        if isinstance(json_data, list):
            analysis['type'] = 'array_of_records'
            analysis['record_count'] = len(json_data)
            
            if json_data:
                # Analyze first few records to understand structure
                sample_size = min(100, len(json_data))
                field_sets = []
                
                for record in json_data[:sample_size]:
                    if isinstance(record, dict):
                        field_sets.append(set(record.keys()))
                        
                        # Analyze field types
                        for field, value in record.items():
                            if field not in analysis['field_types']:
                                analysis['field_types'][field] = []
                            
                            value_type = type(value).__name__
                            if value_type not in analysis['field_types'][field]:
                                analysis['field_types'][field].append(value_type)
                            
                            # Check for nested structures
                            if isinstance(value, (dict, list)):
                                if field not in analysis['nested_fields']:
                                    analysis['nested_fields'].append(field)
                    else:
                        # Records are not dictionaries
                        analysis['type'] = 'array_of_values'
                        analysis['fields'] = ['value']
                        break
                
                # Determine if structure is uniform
                if field_sets:
                    common_fields = field_sets[0]
                    for field_set in field_sets[1:]:
                        if field_set != common_fields:
                            analysis['is_uniform'] = False
                            common_fields = common_fields.union(field_set)
                    
                    analysis['fields'] = sorted(list(common_fields))
        
        return analysis

    def _extract_data_from_json(self, json_data, structure_analysis):
        """Extract the actual data from various JSON structures"""
        # If we identified a data wrapper, extract it
        if structure_analysis['has_data_key'] and structure_analysis['actual_data_path']:
            if isinstance(json_data, dict) and structure_analysis['actual_data_path'] in json_data:
                json_data = json_data[structure_analysis['actual_data_path']]
        
        # Ensure we have a list of records
        if not isinstance(json_data, list):
            if isinstance(json_data, dict):
                # Single record - wrap in list
                json_data = [json_data]
            else:
                # Single value - wrap in dict in list
                json_data = [{"value": json_data}]
        
        # Normalize records
        normalized_data = []
        for record in json_data:
            if isinstance(record, dict):
                normalized_data.append(record)
            else:
                # Wrap non-dict values
                normalized_data.append({"value": record})
        
        return normalized_data

    def _convert_to_format(self, data, target_format, structure_analysis, include_headers, delimiter, flatten_nested, custom_spec):
        """Convert data to target format"""
        converters = {
            'csv': self._convert_to_csv,
            'tsv': self._convert_to_tsv,
            'xml': self._convert_to_xml,
            'html': self._convert_to_html,
            'markdown': self._convert_to_markdown,
            'md': self._convert_to_markdown,
            'sql': self._convert_to_sql,
            'yaml': self._convert_to_yaml,
            'yml': self._convert_to_yaml,
            'ini': self._convert_to_ini,
            'jsonl': self._convert_to_jsonl,
            'json': self._convert_to_json,
            'txt': self._convert_to_text,
            'parquet_schema': self._convert_to_parquet_schema
        }
        
        if target_format in converters:
            return converters[target_format](data, structure_analysis, include_headers, delimiter, flatten_nested)
        else:
            # Use AI for custom formats
            return self._convert_to_custom_format(data, target_format, custom_spec)

    def _convert_to_csv(self, data, structure_analysis, include_headers, delimiter, flatten_nested):
        """Convert to CSV format"""
        if delimiter is None:
            delimiter = ','
        
        output = StringIO()
        
        if not data:
            return {
                'content': '',
                'extension': 'csv',
                'notes': ['No data to convert']
            }
        
        # Flatten nested structures if requested
        if flatten_nested:
            data = self._flatten_records(data)
        
        # Get all unique fields across all records
        all_fields = set()
        for record in data:
            if isinstance(record, dict):
                all_fields.update(record.keys())
        
        fieldnames = sorted(list(all_fields))
        
        # Write CSV
        writer = csv.DictWriter(output, fieldnames=fieldnames, delimiter=delimiter)
        
        if include_headers:
            writer.writeheader()
        
        for record in data:
            if isinstance(record, dict):
                # Convert any remaining complex types to strings
                clean_record = {}
                for field in fieldnames:
                    value = record.get(field, '')
                    if isinstance(value, (dict, list)):
                        clean_record[field] = json.dumps(value)
                    elif value is None:
                        clean_record[field] = ''
                    else:
                        clean_record[field] = str(value)
                writer.writerow(clean_record)
        
        content = output.getvalue()
        output.close()
        
        return {
            'content': content,
            'extension': 'csv',
            'notes': [
                f"Created CSV with {len(fieldnames)} columns",
                f"Exported {len(data)} records",
                f"Delimiter: '{delimiter}'"
            ]
        }

    def _convert_to_tsv(self, data, structure_analysis, include_headers, delimiter, flatten_nested):
        """Convert to TSV format"""
        return self._convert_to_csv(data, structure_analysis, include_headers, '\t', flatten_nested)

    def _convert_to_xml(self, data, structure_analysis, include_headers, delimiter, flatten_nested):
        """Convert to XML format"""
        root = ET.Element("data")
        root.set("record_count", str(len(data)))
        
        for i, record in enumerate(data):
            record_elem = ET.SubElement(root, "record")
            record_elem.set("index", str(i))
            
            if isinstance(record, dict):
                for field, value in record.items():
                    field_elem = ET.SubElement(record_elem, self._sanitize_xml_tag(field))
                    if isinstance(value, (dict, list)):
                        field_elem.text = json.dumps(value)
                    elif value is not None:
                        field_elem.text = str(value)
            else:
                value_elem = ET.SubElement(record_elem, "value")
                value_elem.text = str(record)
        
        # Pretty print XML
        xml_str = ET.tostring(root, encoding='unicode')
        
        # Add XML declaration
        content = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_str
        
        return {
            'content': content,
            'extension': 'xml',
            'notes': [f"Created XML with {len(data)} records"]
        }

    def _convert_to_html(self, data, structure_analysis, include_headers, delimiter, flatten_nested):
        """Convert to HTML table format"""
        if not data:
            return {
                'content': '<html><body><p>No data</p></body></html>',
                'extension': 'html',
                'notes': ['No data to convert']
            }
        
        # Flatten if needed
        if flatten_nested:
            data = self._flatten_records(data)
        
        # Get fields
        all_fields = set()
        for record in data:
            if isinstance(record, dict):
                all_fields.update(record.keys())
        fieldnames = sorted(list(all_fields))
        
        html = []
        html.append('<!DOCTYPE html>')
        html.append('<html>')
        html.append('<head>')
        html.append('<title>Converted Data</title>')
        html.append('<style>')
        html.append('table { border-collapse: collapse; width: 100%; }')
        html.append('th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }')
        html.append('th { background-color: #4CAF50; color: white; }')
        html.append('tr:nth-child(even) { background-color: #f2f2f2; }')
        html.append('</style>')
        html.append('</head>')
        html.append('<body>')
        html.append('<h1>Data Export</h1>')
        html.append(f'<p>Total Records: {len(data)}</p>')
        html.append('<table>')
        
        # Headers
        if include_headers:
            html.append('<thead><tr>')
            for field in fieldnames:
                html.append(f'<th>{self._escape_html(field)}</th>')
            html.append('</tr></thead>')
        
        # Data
        html.append('<tbody>')
        for record in data:
            html.append('<tr>')
            for field in fieldnames:
                value = record.get(field, '') if isinstance(record, dict) else record
                if isinstance(value, (dict, list)):
                    value = json.dumps(value)
                html.append(f'<td>{self._escape_html(str(value))}</td>')
            html.append('</tr>')
        html.append('</tbody>')
        
        html.append('</table>')
        html.append('</body>')
        html.append('</html>')
        
        return {
            'content': '\n'.join(html),
            'extension': 'html',
            'notes': [f"Created HTML table with {len(data)} records"]
        }

    def _convert_to_markdown(self, data, structure_analysis, include_headers, delimiter, flatten_nested):
        """Convert to Markdown table format"""
        if not data:
            return {
                'content': '# No Data\n\nNo records to display.',
                'extension': 'md',
                'notes': ['No data to convert']
            }
        
        # Flatten if needed
        if flatten_nested:
            data = self._flatten_records(data)
        
        # Get fields
        all_fields = set()
        for record in data:
            if isinstance(record, dict):
                all_fields.update(record.keys())
        fieldnames = sorted(list(all_fields))
        
        md = []
        md.append('# Data Export')
        md.append('')
        md.append(f'**Total Records:** {len(data)}')
        md.append('')
        
        # Create table
        if fieldnames:
            # Header
            md.append('| ' + ' | '.join(fieldnames) + ' |')
            md.append('| ' + ' | '.join(['---'] * len(fieldnames)) + ' |')
            
            # Data rows
            for record in data[:1000]:  # Limit to 1000 for readability
                row = []
                for field in fieldnames:
                    value = record.get(field, '') if isinstance(record, dict) else ''
                    if isinstance(value, (dict, list)):
                        value = json.dumps(value)
                    elif value is None:
                        value = ''
                    # Escape pipe characters
                    value = str(value).replace('|', '\\|')
                    row.append(value)
                md.append('| ' + ' | '.join(row) + ' |')
            
            if len(data) > 1000:
                md.append('')
                md.append(f'*Note: Showing first 1000 of {len(data)} records*')
        
        return {
            'content': '\n'.join(md),
            'extension': 'md',
            'notes': [f"Created Markdown table with {min(1000, len(data))} of {len(data)} records"]
        }

    def _convert_to_sql(self, data, structure_analysis, include_headers, delimiter, flatten_nested):
        """Convert to SQL INSERT statements"""
        if not data:
            return {
                'content': '-- No data to convert',
                'extension': 'sql',
                'notes': ['No data to convert']
            }
        
        # Flatten if needed
        if flatten_nested:
            data = self._flatten_records(data)
        
        # Get fields
        all_fields = set()
        for record in data:
            if isinstance(record, dict):
                all_fields.update(record.keys())
        fieldnames = sorted(list(all_fields))
        
        sql = []
        table_name = 'imported_data'
        
        # Create table statement
        sql.append(f'-- SQL Insert Statements for {len(data)} records')
        sql.append(f'-- Generated on {datetime.now().isoformat()}')
        sql.append('')
        sql.append('-- Create table (adjust data types as needed)')
        sql.append(f'CREATE TABLE IF NOT EXISTS {table_name} (')
        
        for i, field in enumerate(fieldnames):
            field_type = 'TEXT'  # Default to TEXT, adjust based on actual data
            sql.append(f'    {self._sanitize_sql_field(field)} {field_type}{"," if i < len(fieldnames)-1 else ""}')
        sql.append(');')
        sql.append('')
        
        # Insert statements
        sql.append(f'-- Insert data')
        for record in data:
            values = []
            for field in fieldnames:
                value = record.get(field, None) if isinstance(record, dict) else None
                if value is None:
                    values.append('NULL')
                elif isinstance(value, (dict, list)):
                    values.append(f"'{self._escape_sql(json.dumps(value))}'")
                elif isinstance(value, bool):
                    values.append('TRUE' if value else 'FALSE')
                elif isinstance(value, (int, float)):
                    values.append(str(value))
                else:
                    values.append(f"'{self._escape_sql(str(value))}'")
            
            sql.append(f"INSERT INTO {table_name} ({', '.join([self._sanitize_sql_field(f) for f in fieldnames])}) VALUES ({', '.join(values)});")
        
        return {
            'content': '\n'.join(sql),
            'extension': 'sql',
            'notes': [f"Created SQL with {len(data)} INSERT statements"]
        }

    def _convert_to_yaml(self, data, structure_analysis, include_headers, delimiter, flatten_nested):
        """Convert to YAML format"""
        import yaml
        
        try:
            content = yaml.dump(data, default_flow_style=False, allow_unicode=True)
            return {
                'content': content,
                'extension': 'yaml',
                'notes': [f"Created YAML with {len(data)} records"]
            }
        except Exception as e:
            # Fallback to manual YAML generation
            yaml_lines = []
            yaml_lines.append('# Generated YAML')
            yaml_lines.append('records:')
            
            for i, record in enumerate(data):
                yaml_lines.append(f'  - index: {i}')
                if isinstance(record, dict):
                    for field, value in record.items():
                        yaml_lines.append(f'    {field}: {json.dumps(value)}')
                else:
                    yaml_lines.append(f'    value: {json.dumps(record)}')
            
            return {
                'content': '\n'.join(yaml_lines),
                'extension': 'yaml',
                'notes': [f"Created YAML with {len(data)} records (manual generation)"]
            }

    def _convert_to_ini(self, data, structure_analysis, include_headers, delimiter, flatten_nested):
        """Convert to INI format"""
        ini_lines = []
        ini_lines.append('; Generated INI file')
        ini_lines.append(f'; Total records: {len(data)}')
        ini_lines.append('')
        
        for i, record in enumerate(data):
            ini_lines.append(f'[record_{i}]')
            if isinstance(record, dict):
                for field, value in record.items():
                    if isinstance(value, (dict, list)):
                        value = json.dumps(value)
                    elif value is None:
                        value = ''
                    # INI format doesn't handle multiline well
                    value = str(value).replace('\n', ' ')
                    ini_lines.append(f'{self._sanitize_ini_key(field)} = {value}')
            else:
                ini_lines.append(f'value = {record}')
            ini_lines.append('')
        
        return {
            'content': '\n'.join(ini_lines),
            'extension': 'ini',
            'notes': [f"Created INI with {len(data)} sections"]
        }

    def _convert_to_jsonl(self, data, structure_analysis, include_headers, delimiter, flatten_nested):
        """Convert to JSON Lines format"""
        jsonl_lines = []
        
        for record in data:
            jsonl_lines.append(json.dumps(record, ensure_ascii=False))
        
        return {
            'content': '\n'.join(jsonl_lines),
            'extension': 'jsonl',
            'notes': [f"Created JSONL with {len(data)} lines"]
        }

    def _convert_to_json(self, data, structure_analysis, include_headers, delimiter, flatten_nested):
        """Convert to formatted JSON"""
        return {
            'content': json.dumps(data, indent=2, ensure_ascii=False),
            'extension': 'json',
            'notes': [f"Created formatted JSON with {len(data)} records"]
        }

    def _convert_to_text(self, data, structure_analysis, include_headers, delimiter, flatten_nested):
        """Convert to plain text format"""
        text_lines = []
        text_lines.append(f'Data Export - {len(data)} Records')
        text_lines.append('=' * 50)
        text_lines.append('')
        
        for i, record in enumerate(data):
            text_lines.append(f'Record {i + 1}:')
            text_lines.append('-' * 20)
            
            if isinstance(record, dict):
                for field, value in record.items():
                    if isinstance(value, (dict, list)):
                        value = json.dumps(value)
                    text_lines.append(f'{field}: {value}')
            else:
                text_lines.append(f'Value: {record}')
            
            text_lines.append('')
        
        return {
            'content': '\n'.join(text_lines),
            'extension': 'txt',
            'notes': [f"Created text file with {len(data)} records"]
        }

    def _convert_to_parquet_schema(self, data, structure_analysis, include_headers, delimiter, flatten_nested):
        """Generate Parquet schema (not actual Parquet file, but schema definition)"""
        schema = {
            "type": "struct",
            "fields": []
        }
        
        # Analyze data types
        for field in structure_analysis['fields']:
            field_types = structure_analysis['field_types'].get(field, ['string'])
            
            # Determine Parquet type
            if 'int' in field_types:
                parquet_type = 'int64'
            elif 'float' in field_types:
                parquet_type = 'double'
            elif 'bool' in field_types:
                parquet_type = 'boolean'
            elif 'dict' in field_types:
                parquet_type = 'struct'
            elif 'list' in field_types:
                parquet_type = 'array'
            else:
                parquet_type = 'string'
            
            schema['fields'].append({
                "name": field,
                "type": parquet_type,
                "nullable": True
            })
        
        content = json.dumps(schema, indent=2)
        
        return {
            'content': content,
            'extension': 'parquet.schema.json',
            'notes': [f"Created Parquet schema for {len(structure_analysis['fields'])} fields"]
        }

    def _convert_to_custom_format(self, data, target_format, custom_spec):
        """Convert to custom format using AI or predefined rules"""
        if self.ai_enabled and custom_spec.get('use_ai', False):
            return self._ai_custom_format(data, target_format, custom_spec)
        
        # Default custom format
        content = f"# Custom Format: {target_format}\n\n"
        for i, record in enumerate(data):
            content += f"[{i}] {json.dumps(record)}\n"
        
        return {
            'content': content,
            'extension': target_format.replace(' ', '_')[:10],
            'notes': [f"Created custom {target_format} format with {len(data)} records"]
        }

    def _ai_custom_format(self, data, target_format, custom_spec):
        """Use AI to create custom format"""
        try:
            sample_data = data[:5]  # Use sample for AI
            
            prompt = f"""Convert this JSON data to {target_format} format.
            
Sample data:
{json.dumps(sample_data, indent=2)}

Requirements:
{json.dumps(custom_spec, indent=2)}

Provide the converted format for these sample records."""

            response = self.ai_client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": "You are a data format conversion expert."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            ai_format = response.choices[0].message.content
            
            # Apply to all data (simplified - in reality would parse AI response for pattern)
            content = ai_format + "\n\n[... remaining records follow same pattern ...]"
            
            return {
                'content': content,
                'extension': target_format.replace(' ', '_')[:10],
                'notes': [f"AI-generated {target_format} format"]
            }
            
        except Exception as e:
            logging.error(f"AI conversion failed: {str(e)}")
            return self._convert_to_custom_format(data, target_format, {})

    def _flatten_records(self, data):
        """Flatten nested dictionary structures"""
        flattened = []
        
        for record in data:
            if isinstance(record, dict):
                flat_record = self._flatten_dict(record)
                flattened.append(flat_record)
            else:
                flattened.append({"value": record})
        
        return flattened

    def _flatten_dict(self, d, parent_key='', sep='_'):
        """Recursively flatten a dictionary"""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            elif isinstance(v, list):
                # Convert list to string representation
                items.append((new_key, json.dumps(v)))
            else:
                items.append((new_key, v))
        return dict(items)

    def _save_output_file(self, content, extension, directory, filename, encoding, is_binary=False):
        """Save the output file to Azure storage"""
        try:
            # Ensure directory exists
            self.storage_manager.ensure_directory_exists(directory)
            
            # Full filename with extension
            full_filename = f"{filename}.{extension}"
            
            # Convert content to bytes if needed
            if is_binary:
                if isinstance(content, str):
                    content_bytes = content.encode(encoding)
                else:
                    content_bytes = content
            else:
                if isinstance(content, str):
                    content_bytes = content.encode(encoding)
                else:
                    content_bytes = str(content).encode(encoding)
            
            # Write file
            success = self.storage_manager.write_file(directory, full_filename, content_bytes)
            
            if success:
                return {
                    'success': True,
                    'path': f"{directory}/{full_filename}",
                    'size': len(content_bytes)
                }
            else:
                return {
                    'success': False,
                    'path': None,
                    'error': 'Failed to write file'
                }
            
        except Exception as e:
            logging.error(f"Error saving file: {str(e)}")
            return {
                'success': False,
                'path': None,
                'error': str(e)
            }

    def _generate_download_url(self, directory, filename):
        """Generate a download URL for the file"""
        try:
            expiry_time = datetime.utcnow() + timedelta(hours=24)
            url = self.storage_manager.generate_download_url(directory, filename, expiry_time)
            return url
        except Exception as e:
            logging.error(f"Error generating download URL: {str(e)}")
            return None

    def _sanitize_xml_tag(self, tag):
        """Sanitize string for use as XML tag"""
        # Replace invalid characters
        tag = re.sub(r'[^a-zA-Z0-9_\-]', '_', tag)
        # Ensure it starts with letter or underscore
        if tag and tag[0].isdigit():
            tag = '_' + tag
        return tag or 'field'

    def _escape_html(self, text):
        """Escape HTML special characters"""
        return (text
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
                .replace("'", '&#39;'))

    def _sanitize_sql_field(self, field):
        """Sanitize field name for SQL"""
        # Replace invalid characters with underscore
        field = re.sub(r'[^a-zA-Z0-9_]', '_', field)
        # Ensure it starts with letter or underscore
        if field and field[0].isdigit():
            field = '_' + field
        return field or 'field'

    def _escape_sql(self, text):
        """Escape SQL special characters"""
        return text.replace("'", "''")

    def _sanitize_ini_key(self, key):
        """Sanitize key for INI format"""
        # Replace invalid characters
        key = re.sub(r'[^\w\-.]', '_', key)
        return key or 'key'

# Add timedelta import at the top if not already present
from datetime import datetime, timedelta