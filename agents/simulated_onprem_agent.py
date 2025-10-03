import logging
import json
import random
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import hashlib
import re
from agents.basic_agent import BasicAgent
from utils.azure_file_storage import AzureFileStorageManager

class SimulatedOnPremAgent(BasicAgent):
    """
    Simulates various on-premise legacy systems with realistic data patterns.
    Supports: Old Dynamics versions, Siebel, Custom SQL, DB2, Oracle, SAP
    """
    def __init__(self):
        self.name = "SimulatedOnPrem"
        self.metadata = {
            "name": self.name,
            "description": "Simulates legacy on-premise systems with realistic data patterns for testing migrations and sizing",
            "parameters": {
                "type": "object",
                "properties": {
                    "system_type": {
                        "type": "string",
                        "description": "Type of legacy system to simulate",
                        "enum": ["dynamics_crm_4", "dynamics_2011", "dynamics_2013", "siebel", "custom_sql", "db2", "oracle_crm", "sap", "salesforce_classic", "mainframe_cobol"]
                    },
                    "data_profile": {
                        "type": "string",
                        "description": "Data accumulation profile",
                        "enum": ["small_business", "enterprise", "enterprise_messy", "decades_old", "highly_customized"]
                    },
                    "years_in_operation": {
                        "type": "integer",
                        "description": "How many years of data to simulate (affects volume)",
                        "minimum": 1,
                        "maximum": 30
                    },
                    "record_counts": {
                        "type": "object",
                        "description": "Override default record counts",
                        "properties": {
                            "accounts": {"type": "integer"},
                            "contacts": {"type": "integer"},
                            "opportunities": {"type": "integer"},
                            "activities": {"type": "integer"},
                            "custom_entities": {"type": "integer"}
                        }
                    },
                    "include_problems": {
                        "type": "boolean",
                        "description": "Include realistic data quality issues (duplicates, orphans, corruption)"
                    },
                    "output_format": {
                        "type": "string",
                        "description": "Format of the simulated data",
                        "enum": ["sql_dump", "csv_export", "fixed_width", "xml", "json", "native_backup"]
                    },
                    "action": {
                        "type": "string",
                        "description": "What to do with the simulated system",
                        "enum": ["generate_schema", "generate_sample_data", "generate_full_dataset", "get_statistics", "simulate_query", "export_metadata"]
                    }
                },
                "required": ["system_type", "action"]
            }
        }
        self.storage_manager = AzureFileStorageManager()
        
        # System profiles with realistic characteristics
        self.system_profiles = {
            "dynamics_crm_4": {
                "version": "4.0.7333.3",
                "year": 2007,
                "schema_style": "traditional_crm",
                "naming_convention": "new_",  # new_accountid, new_customfield
                "has_custom_entities": True,
                "typical_customizations": ["ISV_solutions", "workflow_entities", "marketing_lists"],
                "database_type": "sql_server_2005",
                "encoding_issues": True,
                "storage_inefficiencies": ["duplicate_indexes", "unused_columns", "audit_bloat"]
            },
            "dynamics_2011": {
                "version": "5.0.9690.3448", 
                "year": 2011,
                "schema_style": "early_xrm",
                "naming_convention": "new_",
                "has_custom_entities": True,
                "typical_customizations": ["plugins", "custom_workflows", "silverlight_resources"],
                "database_type": "sql_server_2008r2",
                "encoding_issues": False,
                "storage_inefficiencies": ["audit_logs", "async_operation_bloat", "duplicate_detection_jobs"]
            },
            "siebel": {
                "version": "8.1.1.11",
                "year": 2004,
                "schema_style": "siebel_repository",
                "naming_convention": "S_",  # S_PARTY, S_CONTACT, etc.
                "has_custom_entities": True,
                "typical_customizations": ["custom_BCs", "workflows", "assignment_rules"],
                "database_type": "oracle_11g",
                "encoding_issues": True,
                "storage_inefficiencies": ["EIM_tables", "interface_tables", "unused_columns"]
            },
            "custom_sql": {
                "version": "custom_v1",
                "year": 1999,
                "schema_style": "adhoc_relational",
                "naming_convention": "tbl",  # tblCustomer, tblOrder
                "has_custom_entities": False,
                "typical_customizations": ["stored_procedures", "triggers", "views"],
                "database_type": "sql_server_2000",
                "encoding_issues": True,
                "storage_inefficiencies": ["no_normalization", "varchar_max_everywhere", "no_indexes"]
            },
            "mainframe_cobol": {
                "version": "CICS/VSAM",
                "year": 1985,
                "schema_style": "fixed_width_records",
                "naming_convention": "COPY",  # COPYBOOK definitions
                "has_custom_entities": False,
                "typical_customizations": ["REDEFINES", "OCCURS", "COMP-3"],
                "database_type": "vsam",
                "encoding_issues": True,  # EBCDIC
                "storage_inefficiencies": ["space_padding", "packed_decimal", "no_delimiters"]
            }
        }
        
        # Data quality problem patterns
        self.data_problems = {
            "duplicates": {
                "rate": 0.15,  # 15% duplicate rate
                "patterns": ["exact", "near_match", "merged_incomplete"]
            },
            "orphaned_records": {
                "rate": 0.08,
                "patterns": ["deleted_parent", "broken_lookup", "invalid_reference"]
            },
            "encoding_issues": {
                "rate": 0.05,
                "patterns": ["mojibake", "mixed_encoding", "html_entities", "double_encoded"]
            },
            "data_corruption": {
                "rate": 0.02,
                "patterns": ["truncated", "null_where_required", "type_mismatch"]
            },
            "legacy_artifacts": {
                "rate": 0.20,
                "patterns": ["test_data", "import_staging", "backup_tables", "archive_records"]
            }
        }
        
        super().__init__(name=self.name, metadata=self.metadata)

    def perform(self, **kwargs):
        system_type = kwargs.get('system_type', 'dynamics_2011')
        action = kwargs.get('action', 'generate_schema')
        data_profile = kwargs.get('data_profile', 'enterprise')
        years_in_operation = kwargs.get('years_in_operation', 10)
        include_problems = kwargs.get('include_problems', True)
        output_format = kwargs.get('output_format', 'sql_dump')
        record_counts = kwargs.get('record_counts', {})
        
        try:
            if action == 'generate_schema':
                schema = self._generate_schema(system_type, data_profile, years_in_operation)
                return json.dumps({
                    "success": True,
                    "action": "generate_schema",
                    "system_type": system_type,
                    "schema": schema,
                    "statistics": self._calculate_schema_statistics(schema)
                }, indent=2)
            
            elif action == 'generate_sample_data':
                sample_data = self._generate_sample_data(
                    system_type, data_profile, years_in_operation, 
                    include_problems, record_counts, sample_size=100
                )
                formatted_output = self._format_output(sample_data, output_format, system_type)
                
                # Save to storage
                filename = f"{system_type}_sample_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                self._save_output(formatted_output, output_format, filename)
                
                return json.dumps({
                    "success": True,
                    "action": "generate_sample_data",
                    "system_type": system_type,
                    "record_count": len(sample_data.get('accounts', [])),
                    "output_file": f"simulated_data/{filename}",
                    "sample": formatted_output[:2000] if isinstance(formatted_output, str) else str(formatted_output)[:2000]
                }, indent=2)
            
            elif action == 'generate_full_dataset':
                full_data = self._generate_full_dataset(
                    system_type, data_profile, years_in_operation,
                    include_problems, record_counts
                )
                
                statistics = self._calculate_data_statistics(full_data)
                
                # Generate multiple output files for large datasets
                self._generate_dataset_files(full_data, system_type, output_format)
                
                return json.dumps({
                    "success": True,
                    "action": "generate_full_dataset",
                    "system_type": system_type,
                    "statistics": statistics,
                    "files_generated": self._list_generated_files(system_type)
                }, indent=2)
            
            elif action == 'get_statistics':
                stats = self._get_system_statistics(system_type, data_profile, years_in_operation)
                return json.dumps({
                    "success": True,
                    "action": "get_statistics",
                    "system_type": system_type,
                    "statistics": stats
                }, indent=2)
            
            elif action == 'simulate_query':
                query = kwargs.get('query', 'SELECT * FROM accounts LIMIT 10')
                result = self._simulate_query(system_type, query, data_profile, years_in_operation)
                return json.dumps({
                    "success": True,
                    "action": "simulate_query",
                    "query": query,
                    "result": result
                }, indent=2)
            
            elif action == 'export_metadata':
                metadata = self._export_metadata(system_type, data_profile, years_in_operation)
                return json.dumps({
                    "success": True,
                    "action": "export_metadata",
                    "system_type": system_type,
                    "metadata": metadata
                }, indent=2)
            
            else:
                return json.dumps({
                    "success": False,
                    "error": f"Unknown action: {action}"
                }, indent=2)
                
        except Exception as e:
            logging.error(f"Error in SimulatedOnPrem: {str(e)}")
            return json.dumps({
                "success": False,
                "error": str(e)
            }, indent=2)

    def _generate_schema(self, system_type, data_profile, years):
        """Generate realistic schema for the system type"""
        profile = self.system_profiles.get(system_type, self.system_profiles['custom_sql'])
        schema = {
            "system_info": profile,
            "tables": {},
            "relationships": [],
            "indexes": [],
            "stored_procedures": [],
            "custom_fields": []
        }
        
        # Base CRM tables (common across systems)
        if system_type in ['dynamics_crm_4', 'dynamics_2011', 'dynamics_2013']:
            schema['tables'] = self._generate_dynamics_schema(profile, data_profile, years)
        elif system_type == 'siebel':
            schema['tables'] = self._generate_siebel_schema(profile, data_profile, years)
        elif system_type == 'mainframe_cobol':
            schema['tables'] = self._generate_cobol_copybooks(profile, data_profile, years)
        else:
            schema['tables'] = self._generate_custom_sql_schema(profile, data_profile, years)
        
        # Add relationships
        schema['relationships'] = self._generate_relationships(schema['tables'])
        
        # Add realistic customizations based on profile
        if data_profile in ['enterprise', 'enterprise_messy', 'highly_customized']:
            schema['custom_fields'] = self._generate_custom_fields(system_type, years)
            schema['stored_procedures'] = self._generate_stored_procedures(system_type)
        
        return schema

    def _generate_dynamics_schema(self, profile, data_profile, years):
        """Generate Dynamics CRM schema"""
        prefix = profile['naming_convention']
        tables = {}
        
        # Core entities
        tables['AccountBase'] = {
            'columns': {
                'AccountId': 'uniqueidentifier PRIMARY KEY',
                'Name': 'nvarchar(160)',
                'AccountNumber': 'nvarchar(20)',
                f'{prefix}CustomerTypeCode': 'int',
                'ParentAccountId': 'uniqueidentifier',
                'CreatedOn': 'datetime',
                'ModifiedOn': 'datetime',
                'StateCode': 'int',
                'StatusCode': 'int',
                'OwnerId': 'uniqueidentifier',
                'OwnerIdType': 'int'
            }
        }
        
        tables['ContactBase'] = {
            'columns': {
                'ContactId': 'uniqueidentifier PRIMARY KEY',
                'FirstName': 'nvarchar(50)',
                'LastName': 'nvarchar(50)',
                'EmailAddress1': 'nvarchar(100)',
                'ParentCustomerId': 'uniqueidentifier',
                'ParentCustomerIdType': 'int',
                'CreatedOn': 'datetime',
                'ModifiedOn': 'datetime'
            }
        }
        
        # Add custom entities based on years and profile
        if years > 5:
            for i in range(min(years, 20)):
                tables[f'{prefix}custom_entity_{i}'] = self._generate_custom_entity(i, prefix)
        
        # Add extension tables (common in old Dynamics)
        tables['AccountExtensionBase'] = {
            'columns': {
                'AccountId': 'uniqueidentifier PRIMARY KEY',
                f'{prefix}LegacyId': 'nvarchar(50)',
                f'{prefix}CustomField1': 'nvarchar(max)',
                f'{prefix}CustomField2': 'nvarchar(max)'
            }
        }
        
        # Add audit tables if enterprise
        if data_profile in ['enterprise', 'enterprise_messy']:
            tables['AuditBase'] = {
                'columns': {
                    'AuditId': 'uniqueidentifier PRIMARY KEY',
                    'ObjectId': 'uniqueidentifier',
                    'ObjectTypeCode': 'int',
                    'Operation': 'int',
                    'UserId': 'uniqueidentifier',
                    'CreatedOn': 'datetime',
                    'ChangeData': 'nvarchar(max)'
                }
            }
        
        return tables

    def _generate_siebel_schema(self, profile, data_profile, years):
        """Generate Siebel schema with characteristic naming"""
        tables = {}
        
        # Siebel's characteristic S_ prefix tables
        tables['S_PARTY'] = {
            'columns': {
                'ROW_ID': 'VARCHAR2(15) PRIMARY KEY',
                'PARTY_TYPE_CD': 'VARCHAR2(30)',
                'PARTY_UID': 'VARCHAR2(100)',
                'NAME': 'VARCHAR2(100)',
                'CREATED': 'DATE',
                'CREATED_BY': 'VARCHAR2(15)',
                'LAST_UPD': 'DATE',
                'LAST_UPD_BY': 'VARCHAR2(15)',
                'MODIFICATION_NUM': 'NUMBER(10)',
                'CONFLICT_ID': 'VARCHAR2(15)'
            }
        }
        
        tables['S_CONTACT'] = {
            'columns': {
                'ROW_ID': 'VARCHAR2(15) PRIMARY KEY',
                'PAR_ROW_ID': 'VARCHAR2(15)',
                'PERSON_UID': 'VARCHAR2(100)',
                'FST_NAME': 'VARCHAR2(50)',
                'LAST_NAME': 'VARCHAR2(50)',
                'WORK_PH_NUM': 'VARCHAR2(40)',
                'EMAIL_ADDR': 'VARCHAR2(350)',
                'CREATED': 'DATE',
                'CREATED_BY': 'VARCHAR2(15)'
            }
        }
        
        # Siebel extension tables (X_ prefix)
        tables['S_CONTACT_X'] = {
            'columns': {
                'ROW_ID': 'VARCHAR2(15) PRIMARY KEY',
                'ATTRIB_01': 'VARCHAR2(100)',
                'ATTRIB_02': 'VARCHAR2(100)',
                'ATTRIB_03': 'VARCHAR2(100)',
                'ATTRIB_04': 'VARCHAR2(100)',
                'ATTRIB_05': 'VARCHAR2(100)'
            }
        }
        
        # EIM tables for integration
        if years > 3:
            tables['EIM_ACCOUNT'] = {
                'columns': {
                    'ROW_ID': 'VARCHAR2(15)',
                    'IF_ROW_BATCH_NUM': 'NUMBER(10)',
                    'IF_ROW_STAT': 'VARCHAR2(30)',
                    'ACCNT_NAME': 'VARCHAR2(100)',
                    'ACCNT_LOC': 'VARCHAR2(50)'
                }
            }
        
        return tables

    def _generate_cobol_copybooks(self, profile, data_profile, years):
        """Generate COBOL/Mainframe style fixed-width definitions"""
        # This represents COBOL COPYBOOK style definitions
        copybooks = {
            'CUSTOMER-RECORD': {
                'type': 'fixed_width',
                'record_length': 256,
                'fields': [
                    {'name': 'CUST-ID', 'start': 1, 'end': 10, 'type': 'PIC X(10)'},
                    {'name': 'CUST-NAME', 'start': 11, 'end': 40, 'type': 'PIC X(30)'},
                    {'name': 'CUST-ADDR', 'start': 41, 'end': 90, 'type': 'PIC X(50)'},
                    {'name': 'CUST-PHONE', 'start': 91, 'end': 110, 'type': 'PIC X(20)'},
                    {'name': 'CUST-BAL', 'start': 111, 'end': 125, 'type': 'PIC 9(13)V99 COMP-3'},
                    {'name': 'CUST-DATE', 'start': 126, 'end': 133, 'type': 'PIC X(8)'},  # YYYYMMDD
                    {'name': 'CUST-STATUS', 'start': 134, 'end': 134, 'type': 'PIC X'},
                    {'name': 'FILLER', 'start': 135, 'end': 256, 'type': 'PIC X(122)'}
                ]
            },
            'TRANSACTION-RECORD': {
                'type': 'fixed_width',
                'record_length': 128,
                'fields': [
                    {'name': 'TRANS-ID', 'start': 1, 'end': 15, 'type': 'PIC X(15)'},
                    {'name': 'TRANS-DATE', 'start': 16, 'end': 23, 'type': 'PIC X(8)'},
                    {'name': 'TRANS-AMT', 'start': 24, 'end': 38, 'type': 'PIC 9(13)V99'},
                    {'name': 'TRANS-TYPE', 'start': 39, 'end': 40, 'type': 'PIC XX'},
                    {'name': 'CUST-ID-REF', 'start': 41, 'end': 50, 'type': 'PIC X(10)'},
                    {'name': 'TRANS-DESC', 'start': 51, 'end': 100, 'type': 'PIC X(50)'},
                    {'name': 'FILLER', 'start': 101, 'end': 128, 'type': 'PIC X(28)'}
                ]
            }
        }
        
        return copybooks

    def _generate_custom_sql_schema(self, profile, data_profile, years):
        """Generate custom SQL schema with realistic bad practices"""
        tables = {}
        
        # Typical custom app tables with poor naming
        tables['tblCustomer'] = {
            'columns': {
                'CustomerID': 'int IDENTITY(1,1) PRIMARY KEY',
                'CustName': 'varchar(255)',
                'CustAddr': 'varchar(max)',
                'Phone1': 'varchar(50)',
                'Phone2': 'varchar(50)',
                'Phone3': 'varchar(50)',  # Poor normalization
                'Notes': 'text',
                'CreatedDate': 'datetime',
                'ModifiedDate': 'varchar(50)',  # Wrong data type
                'IsActive': 'varchar(10)',  # Should be bit
                'CustomerType': 'varchar(100)'
            }
        }
        
        # Duplicate table (common issue)
        tables['tblCustomer_backup_2019'] = tables['tblCustomer'].copy()
        tables['tblCustomer_temp'] = tables['tblCustomer'].copy()
        
        # Orders with denormalized data
        tables['Orders'] = {
            'columns': {
                'OrderID': 'bigint',  # No primary key!
                'CustomerID': 'varchar(50)',  # Inconsistent type
                'OrderDate': 'varchar(20)',  # String instead of datetime
                'CustomerName': 'varchar(255)',  # Denormalized
                'CustomerAddress': 'varchar(500)',  # Denormalized
                'TotalAmount': 'varchar(50)',  # String for money
                'Status': 'int'
            }
        }
        
        return tables

    def _generate_custom_entity(self, index, prefix):
        """Generate a custom entity schema"""
        return {
            'columns': {
                f'{prefix}custom_entity_{index}id': 'uniqueidentifier PRIMARY KEY',
                f'{prefix}name': 'nvarchar(100)',
                f'{prefix}description': 'nvarchar(max)',
                f'{prefix}customfield1': 'nvarchar(500)',
                f'{prefix}customfield2': 'nvarchar(500)',
                f'{prefix}customfield3': 'decimal(18,2)',
                f'{prefix}lookupfield': 'uniqueidentifier',
                f'{prefix}optionset': 'int',
                'CreatedOn': 'datetime',
                'ModifiedOn': 'datetime'
            }
        }

    def _generate_sample_data(self, system_type, data_profile, years, include_problems, record_counts, sample_size=100):
        """Generate sample data based on system type"""
        data = {}
        
        # Calculate volumes based on profile
        base_counts = self._calculate_record_counts(data_profile, years, sample_size)
        base_counts.update(record_counts)  # Override with user-specified counts
        
        if system_type in ['dynamics_crm_4', 'dynamics_2011', 'dynamics_2013']:
            data = self._generate_dynamics_data(base_counts, years, include_problems)
        elif system_type == 'siebel':
            data = self._generate_siebel_data(base_counts, years, include_problems)
        elif system_type == 'mainframe_cobol':
            data = self._generate_mainframe_data(base_counts, years, include_problems)
        else:
            data = self._generate_custom_sql_data(base_counts, years, include_problems)
        
        return data

    def _generate_dynamics_data(self, counts, years, include_problems):
        """Generate Dynamics-style data"""
        data = {
            'accounts': [],
            'contacts': [],
            'opportunities': [],
            'activities': []
        }
        
        # Generate accounts
        for i in range(counts.get('accounts', 100)):
            account = {
                'AccountId': str(uuid.uuid4()),
                'Name': f"{random.choice(['Acme', 'Contoso', 'Fabrikam', 'Alpine'])} {random.choice(['Corp', 'Inc', 'LLC', 'Partners'])} {i}",
                'AccountNumber': f"ACC{str(i).zfill(6)}",
                'new_CustomerTypeCode': random.choice([1, 2, 3, 4]),
                'CreatedOn': self._generate_date(years),
                'ModifiedOn': self._generate_date(1),
                'StateCode': 0 if random.random() > 0.1 else 1,
                'StatusCode': 1 if random.random() > 0.1 else 2
            }
            
            # Add data quality issues
            if include_problems:
                account = self._inject_problems(account, 'account')
            
            data['accounts'].append(account)
        
        # Generate contacts with relationships
        for i in range(counts.get('contacts', 200)):
            contact = {
                'ContactId': str(uuid.uuid4()),
                'FirstName': random.choice(['John', 'Jane', 'Bob', 'Alice', 'Charlie', 'Eve']),
                'LastName': random.choice(['Smith', 'Johnson', 'Williams', 'Brown', 'Jones']),
                'EmailAddress1': f"user{i}@{random.choice(['example.com', 'test.com', 'demo.com'])}",
                'ParentCustomerId': random.choice(data['accounts'])['AccountId'] if data['accounts'] else None,
                'CreatedOn': self._generate_date(years),
                'ModifiedOn': self._generate_date(1)
            }
            
            if include_problems:
                contact = self._inject_problems(contact, 'contact')
            
            data['contacts'].append(contact)
        
        return data

    def _generate_siebel_data(self, counts, years, include_problems):
        """Generate Siebel-style data with ROW_ID format"""
        data = {
            'S_PARTY': [],
            'S_CONTACT': [],
            'S_OPTY': []
        }
        
        # Generate parties (accounts)
        for i in range(counts.get('accounts', 100)):
            party = {
                'ROW_ID': self._generate_siebel_rowid(),
                'PARTY_TYPE_CD': 'Organization',
                'NAME': f"Company_{i}_{random.choice(['Global', 'Regional', 'Local'])}",
                'CREATED': self._generate_oracle_date(years),
                'LAST_UPD': self._generate_oracle_date(1),
                'MODIFICATION_NUM': random.randint(0, 100),
                'CONFLICT_ID': '0'
            }
            
            if include_problems:
                party = self._inject_problems(party, 'siebel_party')
            
            data['S_PARTY'].append(party)
        
        return data

    def _generate_mainframe_data(self, counts, years, include_problems):
        """Generate fixed-width mainframe-style data"""
        data = {
            'CUSTOMER_RECORDS': [],
            'TRANSACTION_RECORDS': []
        }
        
        # Generate fixed-width customer records
        for i in range(counts.get('accounts', 100)):
            # Create fixed-width record (256 characters)
            cust_id = str(i).zfill(10)
            cust_name = f"CUSTOMER {i}".ljust(30)
            cust_addr = f"{random.randint(100,9999)} MAIN ST".ljust(50)
            cust_phone = f"{random.randint(100,999)}-{random.randint(100,999)}-{random.randint(1000,9999)}".ljust(20)
            cust_bal = str(random.randint(0, 999999999)).zfill(15)
            cust_date = (datetime.now() - timedelta(days=random.randint(0, years*365))).strftime('%Y%m%d')
            cust_status = random.choice(['A', 'I', 'S'])
            filler = ' ' * 122
            
            record = cust_id + cust_name + cust_addr + cust_phone + cust_bal + cust_date + cust_status + filler
            
            if include_problems and random.random() < 0.1:
                # Simulate EBCDIC encoding issues or truncation
                record = record[:250] + '??????'
            
            data['CUSTOMER_RECORDS'].append(record)
        
        return data

    def _generate_custom_sql_data(self, counts, years, include_problems):
        """Generate poorly structured custom SQL data"""
        data = {
            'tblCustomer': [],
            'Orders': [],
            'tblCustomer_backup_2019': []  # Duplicate table
        }
        
        # Generate customers with typical issues
        for i in range(counts.get('accounts', 100)):
            customer = {
                'CustomerID': i + 1,
                'CustName': f"Customer{i}",
                'CustAddr': f"{random.randint(1, 9999)} Street Name, City, State, {random.randint(10000, 99999)}",
                'Phone1': f"({random.randint(100,999)}) {random.randint(100,999)}-{random.randint(1000,9999)}",
                'Phone2': f"({random.randint(100,999)}) {random.randint(100,999)}-{random.randint(1000,9999)}" if random.random() > 0.5 else None,
                'Phone3': None,  # Usually empty
                'Notes': 'Lorem ipsum ' * random.randint(0, 50),
                'CreatedDate': self._generate_date(years),
                'ModifiedDate': str(self._generate_date(1)),  # Wrong type
                'IsActive': 'Yes' if random.random() > 0.2 else 'No',  # Should be boolean
                'CustomerType': random.choice(['Regular', 'Premium', 'VIP', 'REGULAR', 'premium'])  # Inconsistent casing
            }
            
            if include_problems:
                customer = self._inject_problems(customer, 'custom_sql')
            
            data['tblCustomer'].append(customer)
            
            # Add some to backup table (duplicate data)
            if random.random() < 0.3:
                data['tblCustomer_backup_2019'].append(customer.copy())
        
        return data

    def _inject_problems(self, record, record_type):
        """Inject realistic data quality problems"""
        problems = []
        
        # Duplicates
        if random.random() < self.data_problems['duplicates']['rate']:
            if 'Name' in record:
                record['Name'] = record['Name'].upper() if random.random() > 0.5 else record['Name']
            problems.append('potential_duplicate')
        
        # Encoding issues
        if random.random() < self.data_problems['encoding_issues']['rate']:
            for field in record:
                if isinstance(record[field], str) and random.random() < 0.2:
                    # Inject encoding artifacts
                    record[field] = record[field].replace('a', 'Ã¡').replace('e', 'Ã©')
            problems.append('encoding_issue')
        
        # Null where required
        if random.random() < self.data_problems['data_corruption']['rate']:
            critical_fields = ['Name', 'AccountId', 'ContactId', 'ROW_ID']
            for field in critical_fields:
                if field in record and random.random() < 0.1:
                    record[field] = None
            problems.append('missing_required')
        
        # Add problem markers
        if problems and '_data_quality' not in record:
            record['_data_quality'] = problems
        
        return record

    def _format_output(self, data, output_format, system_type):
        """Format data according to output format"""
        if output_format == 'sql_dump':
            return self._format_as_sql(data, system_type)
        elif output_format == 'csv_export':
            return self._format_as_csv(data)
        elif output_format == 'fixed_width':
            return self._format_as_fixed_width(data, system_type)
        elif output_format == 'xml':
            return self._format_as_xml(data)
        elif output_format == 'json':
            return json.dumps(data, indent=2, default=str)
        else:
            return str(data)

    def _format_as_sql(self, data, system_type):
        """Generate SQL dump format"""
        sql_lines = []
        
        # Add header
        sql_lines.append(f"-- SQL Dump for {system_type}")
        sql_lines.append(f"-- Generated: {datetime.now().isoformat()}")
        sql_lines.append("-- Warning: Legacy system dump - may contain data quality issues")
        sql_lines.append("")
        
        for table_name, records in data.items():
            if not records:
                continue
                
            sql_lines.append(f"-- Table: {table_name}")
            sql_lines.append(f"-- Records: {len(records)}")
            
            for record in records[:10]:  # Sample
                columns = ', '.join(record.keys())
                values = []
                for value in record.values():
                    if value is None:
                        values.append('NULL')
                    elif isinstance(value, str):
                        values.append(f"'{value.replace("'", "''")}'")
                    else:
                        values.append(str(value))
                
                sql_lines.append(f"INSERT INTO {table_name} ({columns}) VALUES ({', '.join(values)});")
            
            sql_lines.append("")
        
        return '\n'.join(sql_lines)

    def _format_as_csv(self, data):
        """Generate CSV format with tables concatenated"""
        csv_output = []
        
        for table_name, records in data.items():
            if not records:
                continue
            
            csv_output.append(f"### TABLE: {table_name} ###")
            
            if records:
                # Header
                headers = list(records[0].keys())
                csv_output.append(','.join(headers))
                
                # Data
                for record in records:
                    values = []
                    for header in headers:
                        value = record.get(header, '')
                        if value is None:
                            value = ''
                        elif ',' in str(value):
                            value = f'"{value}"'
                        values.append(str(value))
                    csv_output.append(','.join(values))
            
            csv_output.append("")  # Empty line between tables
        
        return '\n'.join(csv_output)

    def _format_as_fixed_width(self, data, system_type):
        """Generate fixed-width format (mainframe style)"""
        if system_type == 'mainframe_cobol':
            # Return the raw fixed-width records
            output = []
            for table_name, records in data.items():
                output.append(f"**** {table_name} ****")
                output.extend(records)
            return '\n'.join(output)
        else:
            # Convert other formats to fixed-width
            output = []
            for table_name, records in data.items():
                for record in records:
                    # Create fixed-width line (simplified)
                    line = ""
                    for key, value in record.items():
                        if value is None:
                            value = ""
                        field_value = str(value)[:30].ljust(30)  # 30 chars per field
                        line += field_value
                    output.append(line[:256])  # Limit to 256 chars
            return '\n'.join(output)

    def _format_as_xml(self, data):
        """Generate XML format"""
        xml_lines = ['<?xml version="1.0" encoding="UTF-8"?>']
        xml_lines.append('<LegacyDataExport>')
        
        for table_name, records in data.items():
            xml_lines.append(f'  <Table name="{table_name}">')
            
            for record in records:
                xml_lines.append('    <Record>')
                for key, value in record.items():
                    if value is not None:
                        # Escape XML special characters
                        value_str = str(value).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                        xml_lines.append(f'      <{key}>{value_str}</{key}>')
                xml_lines.append('    </Record>')
            
            xml_lines.append('  </Table>')
        
        xml_lines.append('</LegacyDataExport>')
        return '\n'.join(xml_lines)

    def _save_output(self, content, format_type, filename):
        """Save generated data to storage"""
        try:
            directory = 'simulated_data'
            self.storage_manager.ensure_directory_exists(directory)
            
            extension = {
                'sql_dump': 'sql',
                'csv_export': 'csv',
                'fixed_width': 'dat',
                'xml': 'xml',
                'json': 'json'
            }.get(format_type, 'txt')
            
            full_filename = f"{filename}.{extension}"
            
            success = self.storage_manager.write_file(
                directory,
                full_filename,
                content if isinstance(content, bytes) else content.encode('utf-8')
            )
            
            return success
            
        except Exception as e:
            logging.error(f"Error saving output: {str(e)}")
            return False

    def _calculate_record_counts(self, data_profile, years, sample_size):
        """Calculate realistic record counts based on profile"""
        if sample_size:
            # For samples, use smaller numbers
            return {
                'accounts': min(sample_size, 100),
                'contacts': min(sample_size * 2, 200),
                'opportunities': min(sample_size, 100),
                'activities': min(sample_size * 5, 500)
            }
        
        # Full dataset sizing
        profiles = {
            'small_business': {
                'accounts': 500 * years,
                'contacts': 2000 * years,
                'opportunities': 1000 * years,
                'activities': 10000 * years
            },
            'enterprise': {
                'accounts': 10000 * years,
                'contacts': 50000 * years,
                'opportunities': 20000 * years,
                'activities': 500000 * years
            },
            'enterprise_messy': {
                'accounts': 10000 * years * 1.5,  # Duplicates
                'contacts': 50000 * years * 1.8,  # More duplicates
                'opportunities': 20000 * years,
                'activities': 500000 * years * 2  # Never purged
            },
            'decades_old': {
                'accounts': 5000 * years * years,  # Exponential growth
                'contacts': 10000 * years * years,
                'opportunities': 5000 * years * years,
                'activities': 100000 * years * years
            }
        }
        
        return profiles.get(data_profile, profiles['enterprise'])

    def _generate_date(self, years_back):
        """Generate a random date within the specified years"""
        days_back = random.randint(0, years_back * 365)
        return datetime.now() - timedelta(days=days_back)

    def _generate_oracle_date(self, years_back):
        """Generate Oracle-style date string"""
        date = self._generate_date(years_back)
        return date.strftime('%d-%b-%y').upper()  # Oracle default format

    def _generate_siebel_rowid(self):
        """Generate Siebel-style ROW_ID"""
        chars = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        return '1-' + ''.join(random.choices(chars, k=6))

    def _generate_full_dataset(self, system_type, data_profile, years, include_problems, record_counts):
        """Generate full dataset with realistic volumes"""
        base_counts = self._calculate_record_counts(data_profile, years, None)
        base_counts.update(record_counts)
        
        # Generate in batches to avoid memory issues
        batch_size = 1000
        total_generated = 0
        
        full_data = {}
        
        # Process each entity type
        for entity_type, total_count in base_counts.items():
            full_data[entity_type] = []
            
            while total_generated < total_count:
                current_batch_size = min(batch_size, total_count - total_generated)
                batch_counts = {entity_type: current_batch_size}
                
                batch_data = self._generate_sample_data(
                    system_type, data_profile, years,
                    include_problems, batch_counts, current_batch_size
                )
                
                if entity_type in batch_data:
                    full_data[entity_type].extend(batch_data[entity_type])
                
                total_generated += current_batch_size
        
        return full_data

    def _calculate_data_statistics(self, data):
        """Calculate statistics for generated data"""
        stats = {
            'total_records': 0,
            'tables': {},
            'data_quality_issues': 0,
            'estimated_size_mb': 0
        }
        
        for table_name, records in data.items():
            table_stats = {
                'record_count': len(records),
                'avg_record_size': 0,
                'has_duplicates': False,
                'has_orphans': False
            }
            
            if records:
                # Calculate average size
                sample = records[:100]
                total_size = sum(len(json.dumps(r, default=str)) for r in sample)
                table_stats['avg_record_size'] = total_size // len(sample)
                
                # Check for data quality markers
                for record in sample:
                    if '_data_quality' in record:
                        stats['data_quality_issues'] += 1
            
            stats['tables'][table_name] = table_stats
            stats['total_records'] += table_stats['record_count']
            stats['estimated_size_mb'] += (table_stats['record_count'] * table_stats['avg_record_size']) / (1024 * 1024)
        
        return stats

    def _generate_dataset_files(self, data, system_type, output_format):
        """Generate multiple files for large datasets"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        for table_name, records in data.items():
            if not records:
                continue
            
            # Split large tables into multiple files
            chunk_size = 10000
            for i in range(0, len(records), chunk_size):
                chunk = records[i:i+chunk_size]
                chunk_data = {table_name: chunk}
                
                formatted_output = self._format_output(chunk_data, output_format, system_type)
                
                filename = f"{system_type}_{table_name}_{timestamp}_part{i//chunk_size}"
                self._save_output(formatted_output, output_format, filename)

    def _list_generated_files(self, system_type):
        """List files generated for a system type"""
        try:
            files = self.storage_manager.list_files('simulated_data')
            system_files = [f.name for f in files if system_type in f.name]
            return system_files
        except:
            return []

    def _get_system_statistics(self, system_type, data_profile, years):
        """Get statistics without generating data"""
        profile = self.system_profiles.get(system_type)
        counts = self._calculate_record_counts(data_profile, years, None)
        
        stats = {
            'system_info': profile,
            'estimated_records': counts,
            'estimated_total_records': sum(counts.values()),
            'estimated_storage_gb': self._estimate_storage(counts, system_type),
            'typical_problems': self._get_typical_problems(system_type, data_profile),
            'migration_complexity': self._assess_complexity(system_type, data_profile, years)
        }
        
        return stats

    def _estimate_storage(self, counts, system_type):
        """Estimate storage requirements"""
        # Average bytes per record by system type
        avg_record_sizes = {
            'dynamics_crm_4': 2048,
            'dynamics_2011': 2560,
            'siebel': 3072,
            'mainframe_cobol': 256,  # Fixed width
            'custom_sql': 1536
        }
        
        avg_size = avg_record_sizes.get(system_type, 2048)
        total_records = sum(counts.values())
        total_bytes = total_records * avg_size
        
        # Add overhead for indexes, logs, etc.
        overhead_multiplier = 1.5
        total_bytes *= overhead_multiplier
        
        return round(total_bytes / (1024 ** 3), 2)  # Convert to GB

    def _get_typical_problems(self, system_type, data_profile):
        """Get typical data quality problems for system/profile combination"""
        problems = []
        
        # System-specific problems
        if system_type == 'dynamics_crm_4':
            problems.extend(['Unicode issues', 'Orphaned customizations', 'Duplicate detection jobs'])
        elif system_type == 'siebel':
            problems.extend(['EIM table bloat', 'Position-based security complexity', 'MVG relationships'])
        elif system_type == 'mainframe_cobol':
            problems.extend(['EBCDIC encoding', 'Packed decimal fields', 'REDEFINES clauses'])
        
        # Profile-specific problems
        if data_profile == 'enterprise_messy':
            problems.extend(['30-40% duplicate records', 'Inconsistent data types', 'Multiple backup tables'])
        elif data_profile == 'decades_old':
            problems.extend(['Multiple migration artifacts', 'Obsolete custom fields', '90% inactive data'])
        
        return problems

    def _assess_complexity(self, system_type, data_profile, years):
        """Assess migration complexity score (1-10)"""
        base_complexity = {
            'dynamics_crm_4': 6,
            'dynamics_2011': 5,
            'dynamics_2013': 4,
            'siebel': 8,
            'custom_sql': 5,
            'mainframe_cobol': 9,
            'db2': 7
        }.get(system_type, 5)
        
        # Adjust for profile
        if data_profile == 'enterprise_messy':
            base_complexity += 2
        elif data_profile == 'decades_old':
            base_complexity += 3
        elif data_profile == 'highly_customized':
            base_complexity += 2
        
        # Adjust for age
        if years > 10:
            base_complexity += 1
        if years > 20:
            base_complexity += 1
        
        return min(10, base_complexity)

    def _simulate_query(self, system_type, query, data_profile, years):
        """Simulate running a query against the legacy system"""
        # Parse query (simplified)
        query_lower = query.lower()
        
        # Generate appropriate response based on query
        if 'select count' in query_lower:
            # Return count
            counts = self._calculate_record_counts(data_profile, years, None)
            return {
                'query': query,
                'result': [{'count': random.randint(1000, counts.get('accounts', 10000))}],
                'execution_time_ms': random.randint(100, 5000)
            }
        elif 'select' in query_lower and 'from' in query_lower:
            # Return sample rows
            sample_data = self._generate_sample_data(
                system_type, data_profile, years, True, {}, 10
            )
            
            # Extract table name from query
            table_match = re.search(r'from\s+(\w+)', query_lower)
            if table_match:
                table_name = table_match.group(1)
                
                # Find matching table in sample data
                for key in sample_data.keys():
                    if table_name.lower() in key.lower():
                        return {
                            'query': query,
                            'result': sample_data[key][:10],
                            'execution_time_ms': random.randint(50, 1000)
                        }
            
            return {
                'query': query,
                'result': [],
                'error': 'Table not found',
                'execution_time_ms': 0
            }
        else:
            return {
                'query': query,
                'error': 'Query type not supported in simulation',
                'execution_time_ms': 0
            }

    def _export_metadata(self, system_type, data_profile, years):
        """Export system metadata for analysis"""
        schema = self._generate_schema(system_type, data_profile, years)
        stats = self._get_system_statistics(system_type, data_profile, years)
        
        metadata = {
            'system_type': system_type,
            'profile': data_profile,
            'years_in_operation': years,
            'schema': schema,
            'statistics': stats,
            'export_timestamp': datetime.now().isoformat(),
            'compatibility_notes': self._get_compatibility_notes(system_type)
        }
        
        # Save metadata to file
        filename = f"{system_type}_metadata_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        self.storage_manager.write_file(
            'simulated_data',
            filename,
            json.dumps(metadata, indent=2, default=str)
        )
        
        return metadata

    def _get_compatibility_notes(self, system_type):
        """Get Dataverse migration compatibility notes"""
        notes = {
            'dynamics_crm_4': {
                'compatibility': 'Medium',
                'challenges': [
                    'Plugin code incompatible',
                    'Workflow XAML conversion required',
                    'Custom entity relationships need mapping'
                ],
                'recommendations': [
                    'Archive data older than 5 years',
                    'Consolidate duplicate entities',
                    'Modernize customizations'
                ]
            },
            'siebel': {
                'compatibility': 'Low', 
                'challenges': [
                    'Complex data model mapping',
                    'Position-based security model',
                    'MVG and MVL relationships'
                ],
                'recommendations': [
                    'Consider phased migration',
                    'Build custom transformation layer',
                    'Redesign security model'
                ]
            },
            'mainframe_cobol': {
                'compatibility': 'Very Low',
                'challenges': [
                    'Fixed-width to relational conversion',
                    'EBCDIC encoding',
                    'Hierarchical data structures'
                ],
                'recommendations': [
                    'Use ETL tools for transformation',
                    'Consider data warehouse approach',
                    'Archive historical data'
                ]
            }
        }
        
        return notes.get(system_type, {
            'compatibility': 'Unknown',
            'challenges': ['Requires detailed analysis'],
            'recommendations': ['Perform proof of concept']
        })
