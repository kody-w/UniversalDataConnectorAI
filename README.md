# Universal Data Connector
- 🎨 **Professional Web Interface** - Beautiful dashboard with real-time monitoring
- 📊 **Multi-Format Support** - JSON, SQL, CSV, XML, and custom formats

## 📸 Platform Screenshots

### Professional Dashboard & Tutorial Interface
![Tutorial Interface](docs/tutorial-screenshots/step1-register-api.png)

**Modern Web Interface Features:**
- 🌙 **Dark Theme Design** - Professional, easy-on-eyes interface
- 📊 **Real-time Metrics** - Live performance monitoring
- 🎯 **Step-by-Step Guidance** - Interactive tutorial with progress tracking
- ⚡ **One-Click Actions** - Quick access to common operations

### AI-Powered Data Analysis
![Schema Analysis](docs/tutorial-screenshots/step4-analyze-structure.png)

**Intelligence Features:**
- 🧠 **Automatic Schema Detection** - AI understands data structure instantly
- 📋 **Field Type Inference** - Smart data type recommendations
- ✅ **100% Confidence Rating** - Reliable analysis you can trust
- 🎯 **Optimization Hints** - Performance improvement suggestions

### Live Data Processing & Results
![Query Results](docs/tutorial-screenshots/step7-query-database.png)

**Real-time Processing:**
- 💬 **Natural Language Queries** - Ask questions in plain English
- ⚡ **Sub-second Responses** - Optimized query execution
- 📋 **Formatted Output** - Clean, readable results
- 🔍 **SQL Generation** - See the generated queries

## 🎯 Core Capabilitiesctor AI - Professional Edition

## 🌐 Intelligent Data Integration Platform

### 🚀 One-Click Azure Deployment
[![Deploy to Azure](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/#create/Microsoft.Template/uri/https%3A%2F%2Fraw.githubusercontent.com%2Fkody-w%2FUniversalDataConnectorAI%2Fmain%2Fazuredeploy.json)

**Universal Data Connector AI** is an intelligent data integration platform that automatically connects, analyzes, and transforms data from any source. Using AI-powered agents, it understands data patterns, creates schemas, and builds ETL pipelines - all through natural language commands.

---

## ✨ What You Get

- 🔌 **Universal Connectivity** - Connect to APIs, databases, files, and any data source
- 🧠 **AI-Powered Analysis** - Automatic schema detection and data structure learning
- 🔄 **ETL Pipeline Builder** - Visual pipeline designer with real-time execution
- � **Intelligent Caching** - Smart data caching with performance optimization
- 🎯 **Natural Language Queries** - Ask questions in plain English, get SQL/API results
- 🎨 **Professional Web Interface** - Beautiful dashboard with real-time monitoring
- � **Multi-Format Support** - JSON, SQL, CSV, XML, and custom formats

## 🎯 Core Capabilities

### 🤖 AI-Powered Data Agents
- **APIConnector** - Intelligent REST API integration with auto-authentication
- **SQLConnector** - Universal database connectivity (SQLite, PostgreSQL, MySQL, SQL Server)
- **SchemaLearner** - AI-driven data structure analysis and schema generation
- **DataCache** - Smart caching with performance optimization
- **ConnectorRegistry** - Dynamic connector management and discovery
- **UniversalDataTranslator** - Pattern analysis for ANY data format
- **IntelligentFormatSynthesis** - Automatic data format conversion

### 🚀 Enterprise Features
- **Natural Language Processing** - Query data using plain English
- **Real-time Performance Monitoring** - Live metrics and cache analytics
- **Visual Pipeline Designer** - Drag-and-drop ETL pipeline creation
- **Interactive Tutorial System** - Step-by-step learning with real commands
- **Multi-tenant Architecture** - User isolation and data security
- **Auto-scaling Infrastructure** - Serverless Azure Functions backend

## 🎯 Quick Start Tutorial

### Step 1: Connect to JSONPlaceholder API
```
Use APIConnector to fetch data from endpoint: https://jsonplaceholder.typicode.com/users 
with method: GET and cache_result: true
```

### Step 2: Analyze Data Structure
```
Use SchemaLearner to analyze the structure of all cached data
```

### Step 3: Create SQL Database
```
Use SQLConnector with connection_string: sqlite://test_db/jsonplaceholder.db 
and operation: schema to create users and posts tables
```

### Step 4: Query with Natural Language
```
Show me all users who have email addresses ending with .biz
```

## 📋 Prerequisites

- **Azure Account** - [Get free trial](https://azure.microsoft.com/free/)
- **Python 3.11** - Required for Azure Functions v4
- **Azure Functions Core Tools** - `npm install -g azure-functions-core-tools@4`

## 🚀 Getting Started

### Option 1: Run Locally
```bash
# Install dependencies
pip install -r requirements.txt

# Start the function app
func start --python

# Open web interface
open index.html
```

### Option 2: Deploy to Azure
1. Click the "Deploy to Azure" button above
2. Configure your Azure OpenAI endpoint
3. Access via the provided Azure URL

### Access Points
- **Local API**: http://localhost:7071/api/data_connector_function
- **Web Interface**: Open `index.html` in your browser
- **Azure Function**: Uses your deployed Azure URL

## 💬 Example Commands

### API Data Fetching
```bash
curl -X POST http://localhost:7071/api/data_connector_function \
  -H "Content-Type: application/json" \
  -d '{
    "user_input": "Use APIConnector to fetch data from https://jsonplaceholder.typicode.com/users",
    "user_guid": "test-user-001"
  }'
```

### Natural Language Queries
```bash
curl -X POST http://localhost:7071/api/data_connector_function \
  -H "Content-Type: application/json" \
  -d '{
    "user_input": "Show me all users with .biz email addresses from the cached data",
    "user_guid": "test-user-001"
  }'
```

### Database Operations
```bash
curl -X POST http://localhost:7071/api/data_connector_function \
  -H "Content-Type: application/json" \
  -d '{
    "user_input": "Use SQLConnector to create a users table and insert the cached API data",
    "user_guid": "test-user-001"
  }'
```

## � Web Interface Features

### Dashboard
- **Real-time Metrics** - Active connections, queries executed, cache hit rate
- **Quick Actions** - One-click data fetching, database creation, analysis
- **Performance Monitoring** - Live system performance and data processing stats

### Query Builder
- **SQL Query Editor** - Write and execute SQL queries with syntax highlighting
- **API Request Builder** - Visual REST API request configuration
- **Natural Language Interface** - Ask questions in plain English

### Pipeline Designer
- **Visual ETL Builder** - Drag-and-drop pipeline creation
- **Real-time Execution** - Watch data flow through your pipeline
- **Step-by-step Processing** - Extract → Transform → Load with live feedback

### Interactive Tutorial
- **9-Step Learning Path** - Complete JSONPlaceholder to SQL database tutorial
- **Real Command Execution** - Run actual commands with live results
- **Progress Tracking** - Visual completion status for each step

## 🛠️ Custom Agent Development

Create new agents by extending the `BasicAgent` class:

```python
from agents.basic_agent import BasicAgent

class CustomConnectorAgent(BasicAgent):
    def __init__(self):
        self.name = 'CustomConnector'
        self.metadata = {
            "name": self.name,
            "description": "Connect to custom data sources",
            "parameters": {
                "type": "object",
                "properties": {
                    "endpoint": {"type": "string", "description": "Data endpoint URL"},
                    "auth_token": {"type": "string", "description": "Authentication token"}
                },
                "required": ["endpoint"]
            }
        }
        super().__init__(self.name, self.metadata)
    
    def perform(self, **kwargs):
        endpoint = kwargs.get('endpoint')
        # Your custom logic here
        return {"status": "success", "data": "processed_data"}
```

## 🔄 How It Works

### Architecture Overview
1. **Web Interface** sends natural language commands to Azure Function
2. **AI Router** analyzes intent and selects appropriate agents
3. **Specialized Agents** execute data operations (fetch, transform, store)
4. **Intelligent Caching** optimizes performance and reduces API calls
5. **Results** are formatted and returned to the user interface

### Agent Orchestration
- **ConnectorRegistry** manages available data sources and capabilities
- **APIConnector** handles REST API interactions with authentication
- **SQLConnector** provides universal database connectivity
- **SchemaLearner** uses AI to understand data structures automatically
- **DataCache** implements intelligent caching with TTL and invalidation
- **UniversalDataTranslator** analyzes ANY data format using pattern recognition

### Smart Features
- ✅ **Auto-Schema Detection** - AI analyzes data and creates optimal schemas
- ✅ **Natural Language to SQL** - Convert English questions to database queries
- ✅ **Performance Optimization** - Intelligent caching and query optimization
- ✅ **Format Intelligence** - Automatically detect and convert data formats
- ✅ **Error Recovery** - Graceful handling of connection failures and retries

## 📁 Project Structure

```
UniversalDataConnectorAI/
├── function_app.py                    # Main Azure Function endpoint
├── index.html                         # Professional web interface
├── agents/                            # Specialized AI agents
│   ├── api_connector_agent.py        # REST API integration
│   ├── sql_connector_agent.py        # Universal database connectivity
│   ├── schema_learner_agent.py       # AI-powered schema detection
│   ├── data_cache_agent.py           # Intelligent caching system
│   ├── data_connector_registry_agent.py # Connection management
│   ├── cx_universal_data_connector.py # Universal format analyzer
│   ├── cx_format_synthesis_agent.py  # Format conversion engine
│   └── basic_agent.py                # Base agent framework
├── utils/                             # Utility modules
│   └── azure_file_storage.py         # Azure Blob Storage integration
├── requirements.txt                   # Python dependencies
├── host.json                          # Azure Functions configuration
├── azuredeploy.json                   # Azure ARM template
└── local.settings.json               # Local development settings
```

## 🎓 Interactive Tutorial: Complete ETL Workflow

Experience the full power of Universal Data Connector through our interactive 9-step tutorial that takes you from API connection to database analysis in minutes.

### Tutorial Overview

**Scenario**: Connect to JSONPlaceholder API → Analyze data structure → Create SQL database → Query with natural language

![Tutorial Overview](docs/tutorial-screenshots/step1-register-api.png)
*Professional web interface with step-by-step tutorial progression*

### Step-by-Step Walkthrough

#### Step 1: Register API Connector
Add the JSONPlaceholder API to your connector registry with intelligent capability detection.

#### Step 2: Fetch Users Data  
![Step 2 - Fetch Users](docs/tutorial-screenshots/step2-fetch-users.png)
*Real-time API data retrieval with automatic caching and performance metrics*

**Features Demonstrated**:
- ⚡ Sub-second API response times
- 💾 Automatic data caching for performance
- 📊 Live response time monitoring
- ✅ 100% data integrity verification

#### Step 3: Fetch Posts Data
![Step 3 - Fetch Posts](docs/tutorial-screenshots/step3-fetch-posts.png)  
*Multiple endpoint handling with intelligent data aggregation*

#### Step 4: AI-Powered Data Analysis
![Step 4 - Schema Analysis](docs/tutorial-screenshots/step4-analyze-structure.png)
*AI automatically detects data structure and suggests optimal schemas*

**AI Intelligence Features**:
- 🧠 **Automatic Schema Detection** - AI analyzes JSON structure
- 📋 **Field Type Inference** - Intelligent data type recommendations  
- 🎯 **Optimization Suggestions** - Database performance hints
- ✅ **100% Detection Confidence** - Reliable structure analysis

#### Step 5: Database Schema Creation
![Step 5 - Create Schema](docs/tutorial-screenshots/step5-create-schema.png)
*AI-generated SQL schema with optimized table structures*

**Generated Features**:
- 🗄️ **Optimized Tables** - Primary keys, indexes, and relationships
- 📝 **Clean SQL Generation** - Production-ready table definitions
- 🔗 **Foreign Key Relationships** - Automatic relationship detection
- ⚡ **Performance Optimized** - Indexed fields for fast queries

#### Step 6: Data Loading & Validation  
![Step 6 - Insert Data](docs/tutorial-screenshots/step6-insert-data.png)
*Seamless data transfer from cache to SQL database with validation*

**Validation Features**:
- ✅ **100% Data Integrity** - No duplicates or errors
- 🔄 **Cache-to-DB Sync** - Efficient data transfer
- 📊 **Record Count Verification** - Ensures complete data migration
- 🎯 **Field Mapping** - Automatic JSON-to-SQL field mapping

#### Step 7: Natural Language Queries
![Step 7 - Query Database](docs/tutorial-screenshots/step7-query-database.png)
*English-to-SQL conversion with formatted results*

**Query Intelligence**:
- 💬 **Natural Language Processing** - "Find users with .biz emails"  
- 🔍 **SQL Generation** - Automatic query optimization
- 📋 **Formatted Results** - Clean tabular output
- ⚡ **Sub-second Response** - Optimized query execution

#### Step 8: Performance Analytics
![Step 8 - Performance Report](docs/tutorial-screenshots/step8-performance-report.png)
*Comprehensive system metrics and cache analytics*  

**Analytics Dashboard**:
- 📈 **100% Success Rate** - Reliable connector performance
- ⚡ **Sub-0.25s Response Times** - Optimized for speed
- 💾 **Active Cache Status** - Smart cache management
- 🎯 **Connector Health** - Real-time system monitoring

#### Step 9: Data Export & Sharing
![Step 9 - Export Data](docs/tutorial-screenshots/step9-export-csv.png)
*Multi-format data export with intelligent format synthesis*

**Export Capabilities**:
- 📄 **CSV Generation** - Clean, formatted output
- 🎯 **Custom File Paths** - Organized export structure  
- 🔄 **Format Conversion** - JSON/SQL to CSV transformation
- 📊 **Ready for Analysis** - Excel/analytics tool compatible

### Tutorial Benefits

**For Developers**:
- 🚀 **Learn by Doing** - Real commands with live results
- 📚 **Copy-Paste Examples** - Working code snippets  
- 🎯 **Best Practices** - Production-ready patterns
- ⚡ **Rapid Prototyping** - Build data pipelines in minutes

**For Data Teams**:
- 🧠 **AI-First Approach** - Let AI handle schema detection
- 💬 **Natural Language** - Query data without SQL knowledge
- 📊 **Visual Feedback** - See data flow in real-time  
- 🔄 **Complete ETL Pipeline** - End-to-end data integration

**For Business Users**:
- 🎓 **No Technical Background** - Step-by-step guidance
- 📈 **Immediate Results** - Working data pipeline in 10 minutes
- 💰 **Cost Effective** - Understand capabilities before committing
- 🌐 **Real-World Example** - JSONPlaceholder to production database

### 🎥 Tutorial Quick Reference

| Step | Screenshot | Demonstrates | Key Feature |
|------|------------|--------------|-------------|
| 1-2 | ![Users](docs/tutorial-screenshots/step2-fetch-users.png) | API Data Fetching | ⚡ 0.234s response time, automatic caching |
| 3 | ![Posts](docs/tutorial-screenshots/step3-fetch-posts.png) | Multi-endpoint handling | 🔄 Parallel data retrieval |
| 4 | ![Analysis](docs/tutorial-screenshots/step4-analyze-structure.png) | AI Schema Detection | 🧠 100% confidence structure analysis |
| 5 | ![Schema](docs/tutorial-screenshots/step5-create-schema.png) | SQL Generation | 🗄️ Optimized table creation |
| 6 | ![Insert](docs/tutorial-screenshots/step6-insert-data.png) | Data Loading | ✅ 100% integrity validation |
| 7 | ![Query](docs/tutorial-screenshots/step7-query-database.png) | Natural Language Queries | 💬 English → SQL conversion |
| 8 | ![Metrics](docs/tutorial-screenshots/step8-performance-report.png) | Performance Analytics | 📊 Real-time system monitoring |
| 9 | ![Export](docs/tutorial-screenshots/step9-export-csv.png) | Data Export | 📄 Multi-format conversion |

> **💡 Pro Tip**: Each tutorial step builds on the previous one, creating a complete end-to-end data integration pipeline. The entire process takes less than 10 minutes to complete!

## 🚨 Troubleshooting

| Issue | Solution |
|-------|----------|
| "Connection failed" | Check Azure Function URL and credentials in Settings |
| "Agent not found" | Ensure all agent files are present in `/agents/` directory |
| "Cache miss" | Normal behavior - data will be fetched and cached |
| Port 7071 in use | Change port: `func start --port 7072` |
| API rate limits | Use caching features to reduce external API calls |

## 💰 Azure Costs

- **Azure Functions**: ~$0-10/month (consumption tier)
- **Azure Storage**: ~$1-5/month (blob storage for caching)
- **Azure OpenAI**: ~$0.002 per 1K tokens (GPT-4)
- **Azure SQL** (optional): ~$5-50/month (serverless tier)

**Typical Usage: $5-20/month**

## 🌟 Use Cases

### Business Intelligence
- **Data Lake Integration** - Connect and analyze data from multiple sources
- **Real-time Dashboards** - Build live monitoring dashboards
- **Automated Reporting** - Generate reports from various data sources

### Data Migration & ETL
- **Legacy System Integration** - Connect to old systems and databases
- **Cloud Migration** - Move data to cloud databases with transformation
- **Data Synchronization** - Keep multiple systems in sync

### API Integration
- **Third-party API Integration** - Connect to any REST API
- **Webhook Processing** - Handle incoming data streams
- **Microservices Communication** - Facilitate service-to-service data exchange

### Research & Analytics
- **Data Discovery** - Automatically understand unknown data formats
- **Schema Evolution** - Track how data structures change over time
- **Performance Analysis** - Monitor and optimize data processing pipelines

## 🔐 Security & Privacy

### Data Security
- **User Isolation** - Each user's data is completely isolated
- **Encrypted Storage** - All cached data is encrypted in Azure Blob Storage
- **Secure Connections** - HTTPS/TLS for all API communications
- **No Data Persistence** - Raw data is not permanently stored without user consent

### Authentication & Authorization
- **Function Key Authentication** - Azure Function-level security
- **User GUID Tracking** - Secure user session management
- **API Key Rotation** - Support for key rotation and expiration
- **Audit Logging** - Track all data access and operations

### Compliance
- **GDPR Ready** - User data control and deletion capabilities
- **SOC 2 Compliance** - Azure infrastructure compliance
- **Data Residency** - Choose your Azure region for data storage

## 🆕 Latest Features

### Professional Web Interface
- ✨ **Modern UI** - Dark theme with professional design
- 📊 **Real-time Dashboard** - Live metrics and performance monitoring
- 🔍 **Query Builder** - Visual SQL and API query construction
- � **Pipeline Designer** - Drag-and-drop ETL pipeline builder

### AI-Powered Intelligence
- 🧠 **Schema Learning** - Automatic data structure detection
- 🌐 **Universal Format Support** - Analyze ANY data format
- 💬 **Natural Language Queries** - English to SQL conversion
- 🎯 **Smart Caching** - Intelligent performance optimization

### Enterprise Ready
- 🏢 **Multi-tenant Architecture** - User isolation and security
- 📈 **Performance Analytics** - Detailed system metrics
- � **Agent Extensibility** - Easy custom connector development

## 🤝 Contributing

We welcome contributions! Here are ways to get involved:

### Adding New Connectors
1. Create a new agent extending `BasicAgent`
2. Implement the connector-specific logic
3. Add metadata for UI integration
4. Submit a pull request with tests

### Improving AI Capabilities  
1. Enhance schema detection algorithms
2. Add new data format support
3. Improve natural language processing
4. Optimize caching strategies

### UI/UX Enhancements
1. Add new dashboard widgets
2. Improve query builder features
3. Create better data visualizations
4. Enhance mobile responsiveness

### Development Process
1. Fork the repository
2. Create feature branch (`git checkout -b feature/NewConnector`)
3. Add comprehensive tests
4. Update documentation
5. Submit pull request

## 📜 License

MIT License - See [LICENSE](LICENSE)

## 🆘 Support

- **Issues**: [GitHub Issues](https://github.com/kody-w/UniversalDataConnectorAI/issues)
- **Discussions**: [GitHub Discussions](https://github.com/kody-w/UniversalDataConnectorAI/discussions)

## 📚 Documentation & Resources

### API Reference
- [Agent Development Guide](docs/agent-development.md)
- [REST API Documentation](docs/api-reference.md)
- [Configuration Options](docs/configuration.md)

### Tutorials & Examples
- [Complete JSONPlaceholder Tutorial](docs/tutorial-jsonplaceholder.md)
- [Custom Connector Examples](docs/connector-examples.md)
- [ETL Pipeline Patterns](docs/etl-patterns.md)

### Community
- [GitHub Discussions](https://github.com/kody-w/UniversalDataConnectorAI/discussions)
- [Issues & Bug Reports](https://github.com/kody-w/UniversalDataConnectorAI/issues)

## 🌟 Why Universal Data Connector AI?

### For Developers
- **Rapid Integration** - Connect to any data source in minutes
- **AI-First Approach** - Let AI figure out data structures and schemas
- **Natural Language Interface** - Query data without learning SQL
- **Extensible Architecture** - Easy to add custom connectors

### For Businesses
- **Reduce Integration Time** - 90% faster data integration projects
- **Lower Technical Barrier** - Non-technical users can work with data
- **Cost Effective** - Pay-per-use Azure Functions model
- **Enterprise Security** - Built on Azure with enterprise-grade security

### For Data Teams
- **Universal Connectivity** - One platform for all data sources
- **Intelligent Caching** - Optimized performance and cost
- **Schema Evolution** - Automatically adapt to changing data structures
- **Pipeline Automation** - Visual ETL with minimal coding

---

<p align="center">
  <strong>🚀 Transform your data integration in minutes, not months!</strong>
  <br><br>
  <a href="https://github.com/kody-w/UniversalDataConnectorAI">⭐ Star this repo</a> to support the project
  <br><br>
  Built with ❤️ for the data community
</p>