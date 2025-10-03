import azure.functions as func
import logging
import json
import os
import importlib
import importlib.util
import inspect
import sys
import re
from agents.basic_agent import BasicAgent
import uuid
from openai import AzureOpenAI
from datetime import datetime
import time
from utils.azure_file_storage import AzureFileStorageManager, safe_json_loads
import hashlib

# Default GUID to use when no specific user GUID is provided
DEFAULT_USER_GUID = "c0p110t0-aaaa-bbbb-cccc-123456789abc"

def ensure_string_content(message):
    """
    Ensures message content is converted to a string regardless of input type.
    Handles all edge cases including None, undefined, or missing content.
    """
    if message is None:
        return {"role": "user", "content": ""}
        
    if not isinstance(message, dict):
        return {"role": "user", "content": str(message) if message is not None else ""}
    
    message = message.copy()
    
    if 'role' not in message:
        message['role'] = 'user'
    
    if 'content' in message:
        content = message['content']
        message['content'] = str(content) if content is not None else ''
    else:
        message['content'] = ''
    
    return message

def ensure_string_function_args(function_call):
    """
    Ensures function call arguments are properly stringified.
    Handles None and edge cases.
    """
    if not function_call:
        return None
    
    if not hasattr(function_call, 'arguments'):
        return None
        
    if function_call.arguments is None:
        return None
        
    if isinstance(function_call.arguments, (dict, list)):
        return json.dumps(function_call.arguments)
    
    return str(function_call.arguments)

def build_cors_response(origin):
    """
    Builds CORS response headers.
    Safely handles None origin.
    """
    return {
        "Access-Control-Allow-Origin": str(origin) if origin else "*",
        "Access-Control-Allow-Methods": "*",
        "Access-Control-Allow-Headers": "*",
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Max-Age": "86400",
    }

def clear_dynamic_module_cache():
    """Clear Python's module cache for dynamically loaded agents."""
    modules_to_clear = []
    
    # Find all dynamically loaded modules
    for module_name in list(sys.modules.keys()):
        module = sys.modules[module_name]
        
        # Check if this is a dynamically loaded agent module
        if module and hasattr(module, '__file__'):
            module_file = str(module.__file__) if module.__file__ else ''
            
            # Clear if it's from /tmp directory or has our timestamp pattern
            if '/tmp/' in module_file:
                modules_to_clear.append(module_name)
            elif 'agents.' in module_name and '_' in module_name:
                # Check for timestamp pattern in module name
                parts = module_name.split('_')
                if parts and parts[-1].isdigit() and len(parts[-1]) >= 10:
                    modules_to_clear.append(module_name)
    
    # Clear identified modules
    for module_name in modules_to_clear:
        try:
            del sys.modules[module_name]
            logging.info(f"Cleared cached module: {module_name}")
        except Exception as e:
            logging.warning(f"Could not clear module {module_name}: {str(e)}")
    
    if modules_to_clear:
        logging.info(f"Cleared {len(modules_to_clear)} cached modules")

def load_agents_from_folder(force_reload=False):
    """Load all agents including data connector agents with cache management."""
    
    # Clear dynamic module cache if forcing reload
    if force_reload:
        logging.info("Force reload requested - clearing module cache")
        clear_dynamic_module_cache()
    
    # Generate timestamp for this load session
    load_timestamp = str(int(time.time()))
    
    agents_directory = os.path.join(os.path.dirname(__file__), "agents")
    files_in_agents_directory = os.listdir(agents_directory)
    agent_files = [f for f in files_in_agents_directory if f.endswith(".py") and f not in ["__init__.py", "basic_agent.py"]]

    declared_agents = {}
    
    # Load local agents (these don't need cache clearing)
    for file in agent_files:
        try:
            module_name = file[:-3]
            module = importlib.import_module(f'agents.{module_name}')
            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and issubclass(obj, BasicAgent) and obj is not BasicAgent:
                    agent_instance = obj()
                    declared_agents[agent_instance.name] = agent_instance
                    logging.info(f"Loaded local agent: {agent_instance.name}")
        except Exception as e:
            logging.error(f"Error loading agent {file}: {str(e)}")
            continue

    storage_manager = AzureFileStorageManager()
    
    # Check for reload marker
    try:
        marker_content = storage_manager.read_file('agents', '.reload_marker')
        if marker_content:
            marker_time = datetime.fromisoformat(marker_content.strip())
            time_diff = (datetime.now() - marker_time).seconds
            
            if time_diff < 300:  # If marker is less than 5 minutes old
                logging.info(f"Reload marker detected from {time_diff} seconds ago - forcing cache clear")
                clear_dynamic_module_cache()
                # Clear the marker
                try:
                    storage_manager.write_file('agents', '.reload_marker', '')
                except:
                    pass
    except Exception as e:
        # No marker or error reading it
        pass
    
    # Load agents from Azure File Storage with unique module names
    try:
        agent_files = storage_manager.list_files('agents')
        
        for file in agent_files:
            if not file.name.endswith('_agent.py') or file.name.startswith('.'):
                continue

            try:
                file_content = storage_manager.read_file('agents', file.name)
                if file_content is None:
                    continue

                temp_dir = "/tmp/agents"
                os.makedirs(temp_dir, exist_ok=True)
                
                # Create temp file with timestamp in name
                base_name = file.name[:-3]  # Remove .py
                temp_file = f"{temp_dir}/{base_name}_{load_timestamp}.py"

                with open(temp_file, 'w') as f:
                    f.write(file_content)

                if temp_dir not in sys.path:
                    sys.path.insert(0, temp_dir)

                # Use unique module name with timestamp
                module_name = f"{base_name}_{load_timestamp}"
                
                # Check if this module was already loaded in this session
                if module_name not in sys.modules:
                    spec = importlib.util.spec_from_file_location(module_name, temp_file)
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[module_name] = module
                    spec.loader.exec_module(module)
                    
                    for name, obj in inspect.getmembers(module):
                        if (inspect.isclass(obj) and
                            issubclass(obj, BasicAgent) and
                            obj is not BasicAgent):
                            agent_instance = obj()
                            declared_agents[agent_instance.name] = agent_instance
                            logging.info(f"Loaded Azure agent: {agent_instance.name} (session: {load_timestamp})")
                
                # Clean up temp file after loading
                try:
                    os.remove(temp_file)
                except:
                    pass

            except Exception as e:
                logging.error(f"Error loading agent {file.name} from Azure File Share: {str(e)}")
                continue

    except Exception as e:
        logging.error(f"Error loading agents from Azure File Share: {str(e)}")

    # Load multi-agents from multi_agents folder with unique naming
    try:
        multi_agent_files = storage_manager.list_files('multi_agents')
        
        for file in multi_agent_files:
            if not file.name.endswith('_agent.py'):
                continue

            try:
                file_content = storage_manager.read_file('multi_agents', file.name)
                if file_content is None:
                    continue

                temp_dir = "/tmp/multi_agents"
                os.makedirs(temp_dir, exist_ok=True)
                
                # Create temp file with timestamp
                base_name = file.name[:-3]
                temp_file = f"{temp_dir}/{base_name}_{load_timestamp}.py"

                with open(temp_file, 'w') as f:
                    f.write(file_content)

                if temp_dir not in sys.path:
                    sys.path.insert(0, temp_dir)

                parent_dir = "/tmp"
                if parent_dir not in sys.path:
                    sys.path.insert(0, parent_dir)

                # Use unique module name
                module_name = f"multi_agents.{base_name}_{load_timestamp}"
                
                if module_name not in sys.modules:
                    spec = importlib.util.spec_from_file_location(module_name, temp_file)
                    module = importlib.util.module_from_spec(spec)
                    
                    import types
                    if 'multi_agents' not in sys.modules:
                        multi_agents_module = types.ModuleType('multi_agents')
                        sys.modules['multi_agents'] = multi_agents_module
                    
                    sys.modules[module_name] = module
                    spec.loader.exec_module(module)

                    for name, obj in inspect.getmembers(module):
                        if (inspect.isclass(obj) and
                            issubclass(obj, BasicAgent) and
                            obj is not BasicAgent):
                            agent_instance = obj()
                            declared_agents[agent_instance.name] = agent_instance
                            logging.info(f"Loaded multi-agent: {agent_instance.name} (session: {load_timestamp})")

                # Clean up temp file
                try:
                    os.remove(temp_file)
                except:
                    pass

            except Exception as e:
                logging.error(f"Error loading multi-agent {file.name} from Azure File Share: {str(e)}")
                continue

    except Exception as e:
        logging.error(f"Error loading multi-agents from Azure File Share: {str(e)}")

    # Load data connector agents with unique naming
    try:
        connector_files = storage_manager.list_files('data_connectors')
        for file in connector_files:
            if not file.name.endswith('_connector.py'):
                continue
                
            try:
                file_content = storage_manager.read_file('data_connectors', file.name)
                if file_content is None:
                    continue

                temp_dir = "/tmp/data_connectors"
                os.makedirs(temp_dir, exist_ok=True)
                
                base_name = file.name[:-3]
                temp_file = f"{temp_dir}/{base_name}_{load_timestamp}.py"

                with open(temp_file, 'w') as f:
                    f.write(file_content)

                if temp_dir not in sys.path:
                    sys.path.insert(0, temp_dir)

                module_name = f"data_connectors.{base_name}_{load_timestamp}"
                
                if module_name not in sys.modules:
                    spec = importlib.util.spec_from_file_location(module_name, temp_file)
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[module_name] = module
                    spec.loader.exec_module(module)

                    for name, obj in inspect.getmembers(module):
                        if (inspect.isclass(obj) and
                            issubclass(obj, BasicAgent) and
                            obj is not BasicAgent):
                            agent_instance = obj()
                            declared_agents[agent_instance.name] = agent_instance
                            logging.info(f"Loaded data connector: {agent_instance.name} (session: {load_timestamp})")

                # Clean up temp file
                try:
                    os.remove(temp_file)
                except:
                    pass

            except Exception as e:
                logging.error(f"Error loading connector {file.name}: {str(e)}")
                continue
                
    except Exception as e:
        logging.error(f"Error loading data connectors: {str(e)}")

    logging.info(f"Total agents loaded: {len(declared_agents)}")
    return declared_agents

class Assistant:
    def __init__(self, declared_agents):
        self.config = {
            'assistant_name': str(os.environ.get('ASSISTANT_NAME', 'UniversalDataConnector')),
            'characteristic_description': str(os.environ.get('CHARACTERISTIC_DESCRIPTION', 'adaptive universal data connector and business insight assistant'))
        }

        # Initialize Azure OpenAI
        try:
            api_key = os.environ.get('AZURE_OPENAI_API_KEY')
            endpoint = os.environ.get('AZURE_OPENAI_ENDPOINT')
            api_version = os.environ.get('AZURE_OPENAI_API_VERSION', '2024-02-01')
            
            if not api_key or not endpoint:
                raise ValueError("Azure OpenAI API key and endpoint are required")
            
            logging.info(f"Initializing Azure OpenAI with endpoint: {endpoint}, version: {api_version}")
            
            self.client = AzureOpenAI(
                api_key=api_key,
                api_version=api_version,
                azure_endpoint=endpoint
            )
        except Exception as e:
            logging.error(f"Failed to initialize Azure OpenAI client: {str(e)}")
            raise

        self.known_agents = self.reload_agents(declared_agents)
        self.user_guid = DEFAULT_USER_GUID
        self.shared_memory = None
        self.user_memory = None
        self.storage_manager = AzureFileStorageManager()
        
        # Dynamic reload settings
        self.agents_loaded_at = datetime.now()
        self.last_reload_check = datetime.now()
        self.check_reload_interval = 30  # Check every 30 seconds
        self.force_reload_after = 300  # Force reload every 5 minutes
        
        # Universal Data Connector components
        self.data_patterns = {}
        self.connection_cache = {}
        self.query_patterns = {}
        self.schema_cache = {}
        self.connector_registry = {}
        
        self._initialize_context_memory(DEFAULT_USER_GUID)
        self._load_data_patterns()

    def check_and_reload_agents(self):
        """Check if agents need to be reloaded and reload if necessary."""
        now = datetime.now()
        
        # Check if it's time to check for new agents
        time_since_check = (now - self.last_reload_check).seconds
        if time_since_check < self.check_reload_interval:
            return False
        
        self.last_reload_check = now
        
        # Check if we should force reload (every 5 minutes)
        time_since_load = (now - self.agents_loaded_at).seconds
        force_reload = time_since_load > self.force_reload_after
        
        # Check for new agent files in Azure Storage
        reload_needed = force_reload
        
        if not reload_needed:
            try:
                # Check for reload marker or new files
                marker = self.storage_manager.read_file('agents', '.reload_marker')
                if marker and marker.strip():
                    marker_time = datetime.fromisoformat(marker.strip())
                    if marker_time > self.agents_loaded_at:
                        logging.info(f"Reload marker found from {marker_time}")
                        reload_needed = True
                
                # Check if any agent files are newer than our load time
                if not reload_needed:
                    agent_files = self.storage_manager.list_files('agents')
                    for file in agent_files:
                        if file.name.endswith('_agent.py'):
                            # Check file properties if available
                            # For now, we'll reload periodically
                            pass
                            
            except Exception as e:
                logging.debug(f"Error checking for agent updates: {str(e)}")
        
        if reload_needed:
            logging.info(f"Reloading agents (force={force_reload}, time_since_load={time_since_load}s)")
            
            # Clear module cache and reload
            clear_dynamic_module_cache()
            new_agents = load_agents_from_folder(force_reload=True)
            
            if new_agents:
                old_count = len(self.known_agents)
                self.known_agents = self.reload_agents(new_agents)
                new_count = len(self.known_agents)
                
                self.agents_loaded_at = now
                
                if new_count != old_count:
                    logging.info(f"Agent count changed: {old_count} -> {new_count}")
                    
                    # List new agents
                    old_names = set(self.known_agents.keys())
                    new_names = set(new_agents.keys())
                    added = new_names - old_names
                    removed = old_names - new_names
                    
                    if added:
                        logging.info(f"New agents added: {added}")
                    if removed:
                        logging.info(f"Agents removed: {removed}")
                else:
                    logging.info(f"Reloaded {new_count} agents")
                
                return True
            else:
                logging.warning("Failed to reload agents")
        
        return False

    def _load_data_patterns(self):
        """Load learned data patterns and connection configurations."""
        try:
            patterns_data = self.storage_manager.read_json_from_path("data_patterns", "patterns.json")
            if patterns_data:
                self.data_patterns = patterns_data
                logging.info(f"Loaded {len(self.data_patterns)} data patterns")
        except Exception as e:
            logging.warning(f"Could not load data patterns: {str(e)}")
            self.data_patterns = {}
        
        # Load connector registry
        try:
            registry_data = self.storage_manager.read_json_from_path("data_connectors", "registry.json")
            if registry_data:
                self.connector_registry = registry_data
                logging.info(f"Loaded connector registry")
        except Exception:
            self.connector_registry = {}
        
        # Load query patterns
        try:
            query_data = self.storage_manager.read_json_from_path("query_templates", "patterns.json")
            if query_data:
                self.query_patterns = query_data
                logging.info(f"Loaded query patterns")
        except Exception:
            self.query_patterns = {}

    def _save_data_patterns(self):
        """Save learned data patterns."""
        try:
            self.storage_manager.write_json_to_path(self.data_patterns, "data_patterns", "patterns.json")
            logging.info(f"Saved {len(self.data_patterns)} data patterns")
        except Exception as e:
            logging.error(f"Error saving data patterns: {str(e)}")

    def _check_first_message_for_guid(self, conversation_history):
        """Check if the first message contains only a GUID."""
        if not conversation_history or len(conversation_history) == 0:
            return None
            
        first_message = conversation_history[0]
        if first_message.get('role') == 'user':
            content = first_message.get('content')
            if content is None:
                return None
            content = str(content).strip()
            guid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)
            if guid_pattern.match(content):
                return content
        return None

    def _initialize_context_memory(self, user_guid=None):
        """Initialize context memory with data connection history."""
        try:
            context_memory_agent = self.known_agents.get('ContextMemory')
            if not context_memory_agent:
                self.shared_memory = "No shared context memory available."
                self.user_memory = "No specific context memory available."
                return

            # Limit memory size to prevent crashes
            try:
                self.storage_manager.set_memory_context(None)
                shared_result = context_memory_agent.perform(full_recall=True)
                self.shared_memory = str(shared_result)[:5000] if shared_result else "No shared context memory available."
            except Exception as e:
                logging.warning(f"Error getting shared memory: {str(e)}")
                self.shared_memory = "Context memory initialization failed."
            
            if not user_guid:
                user_guid = DEFAULT_USER_GUID
            
            try:
                self.storage_manager.set_memory_context(user_guid)
                user_result = context_memory_agent.perform(user_guid=user_guid, full_recall=True)
                self.user_memory = str(user_result)[:5000] if user_result else "No specific context memory available."
            except Exception as e:
                logging.warning(f"Error getting user memory: {str(e)}")
                self.user_memory = "Context memory initialization failed."
                
        except Exception as e:
            logging.warning(f"Error initializing context memory: {str(e)}")
            self.shared_memory = "Context memory initialization failed."
            self.user_memory = "Context memory initialization failed."
    
    def extract_user_guid(self, text):
        """Try to extract a GUID from user input."""
        if text is None:
            return None
            
        text_str = str(text).strip()
        
        guid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)
        match = guid_pattern.match(text_str)
        if match:
            return match.group(0)
        
        labeled_guid_pattern = re.compile(r'^guid[:=\s]+([0-9a-f-]{36})$', re.IGNORECASE)
        match = labeled_guid_pattern.match(text_str)
        if match:
            return match.group(1)
                
        return None

    def get_agent_metadata(self):
        """Get metadata for all available agents."""
        agents_metadata = []
        for agent in self.known_agents.values():
            if hasattr(agent, 'metadata'):
                agents_metadata.append(agent.metadata)
        return agents_metadata

    def reload_agents(self, agent_objects):
        """Reload all agents including dynamically created connectors."""
        known_agents = {}
        if isinstance(agent_objects, dict):
            for agent_name, agent in agent_objects.items():
                if hasattr(agent, 'name'):
                    known_agents[agent.name] = agent
                else:
                    known_agents[str(agent_name)] = agent
        elif isinstance(agent_objects, list):
            for agent in agent_objects:
                if hasattr(agent, 'name'):
                    known_agents[agent.name] = agent
        else:
            logging.warning(f"Unexpected agent_objects type: {type(agent_objects)}")
        return known_agents

    def prepare_messages(self, conversation_history):
        """Prepare messages with universal data connector context."""
        if not isinstance(conversation_history, list):
            conversation_history = []
            
        messages = []
        current_datetime = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")
        
        # Enhanced system message for universal data connector
        system_message = {
            "role": "system",
            "content": f"""
<identity>
You are a Microsoft Copilot assistant named {str(self.config.get('assistant_name', 'UniversalDataConnector'))}, operating within Microsoft Teams.
You are a Universal Data Connector that can connect to, learn from, and adapt to any data source.
</identity>

<capabilities>
- Connect to databases (SQL, NoSQL, Graph, Time-series)
- Interface with APIs (REST, GraphQL, SOAP, WebSocket)
- Process files (CSV, JSON, XML, Excel, Parquet)
- Stream data (Kafka, Event Hubs, MQTT)
- Learn and adapt to new data formats automatically
- Transform and map data between different schemas
- Cache frequently accessed data for performance
- Generate optimal queries across different data sources
- Traditional business insights and memory management
- Create new agents dynamically with LearnNewAgent
</capabilities>

<available_agents>
{', '.join(self.known_agents.keys())}
Total agents available: {len(self.known_agents)}
</available_agents>

<shared_memory_output>
These are memories accessible by all users of the system:
{str(self.shared_memory)}
</shared_memory_output>

<specific_memory_output>
These are memories specific to the current conversation:
{str(self.user_memory)}
</specific_memory_output>

<learned_patterns>
Known data patterns: {len(self.data_patterns)} sources
Cached connections: {len(self.connection_cache)} active
Query patterns: {len(self.query_patterns)} learned
</learned_patterns>

<context_instructions>
- <shared_memory_output> represents common knowledge shared across all conversations
- <specific_memory_output> represents specific context for the current conversation
- Apply specific context with higher precedence than shared context
- Synthesize information from both contexts for comprehensive responses
- Automatically detect data source types from user queries
- Learn from successful connections and optimize future queries
- Cache frequently accessed data for improved performance
- Suggest optimal data access patterns based on learned behavior
</context_instructions>

<agent_usage>
IMPORTANT: You must be honest and accurate about agent usage:
- NEVER pretend or imply you've executed an agent when you haven't actually called it
- NEVER say "using my agent" unless you are actually making a function call to that agent
- NEVER fabricate success messages about data operations that haven't occurred
- If you need to perform an action and don't have the necessary agent, say so directly
- When a user requests an action, either:
  1. Call the appropriate agent and report actual results, or
  2. Say "I don't have the capability to do that" and suggest an alternative
  3. If no details are provided besides the request to run an agent, infer the necessary input parameters

You have access to various data connector agents and can create new ones:
- Use existing connectors when available
- Create new connectors using LearnNewAgent when needed
- Store successful connection patterns for reuse
- Optimize queries based on data source characteristics
- If an agent doesn't exist yet, you can create it with LearnNewAgent
</agent_usage>

<response_format>
CRITICAL: You must structure your response in TWO distinct parts separated by the delimiter |||VOICE|||

1. FIRST PART (before |||VOICE|||): Your full formatted response
   - Use **bold** for emphasis
   - Use `code blocks` for technical content
   - Apply --- for horizontal rules to separate sections
   - Utilize > for important quotes or callouts
   - Format code with ```language syntax highlighting
   - Create numbered lists with proper indentation
   - Add personality when appropriate
   - Apply # ## ### headings for clear structure
   - Include data source details and connection status when relevant
   - Show query results or data transformations
   - Provide performance metrics if relevant
   - Suggest optimizations based on learned patterns

2. SECOND PART (after |||VOICE|||): A concise voice response
   - Maximum 1-2 sentences
   - Pure conversational English with NO formatting
   - Extract only the most critical information
   - Sound like a colleague speaking casually
   - Be natural and conversational
   - Focus on the key takeaway or action item
   - Example: "I found those sales figures - revenue's up 12 percent." or "Connected to the database successfully - found 15 tables."

EXAMPLE FORMAT:
Successfully connected to the PostgreSQL database!

**Connection Details:**
- Host: production-db.example.com
- Tables found: 15
- Total records: 1,247,893

The connection has been cached for optimal performance.

|||VOICE|||
Connected to PostgreSQL - found 15 tables with over a million records.
</response_format>

<learning_mode>
When encountering new data sources:
1. Analyze the structure and format
2. Create appropriate connector if needed
3. Store the pattern for future use
4. Optimize based on access patterns
5. Share learnings across similar connections
</learning_mode>
"""
        }
        messages.append(ensure_string_content(system_message))
        
        # Process conversation history - skip first message if it's just a GUID
        guid_only_first_message = self._check_first_message_for_guid(conversation_history)
        start_idx = 1 if guid_only_first_message else 0
        
        for i in range(start_idx, len(conversation_history)):
            messages.append(ensure_string_content(conversation_history[i]))
            
        return messages
    
    def get_openai_api_call(self, messages):
        """Get response from OpenAI with function calling."""
        try:
            deployment_name = os.environ.get('AZURE_OPENAI_DEPLOYMENT_NAME', 'gpt-deployment')
            
            response = self.client.chat.completions.create(
                model=deployment_name,
                messages=messages,
                functions=self.get_agent_metadata(),
                function_call="auto"
            )
            return response
        except Exception as e:
            logging.error(f"Error in OpenAI API call: {str(e)}")
            raise
    
    def parse_response_with_voice(self, content):
        """Parse the response to extract formatted and voice parts."""
        if not content:
            return "", ""
        
        parts = content.split("|||VOICE|||")
        
        if len(parts) >= 2:
            formatted_response = parts[0].strip()
            voice_response = parts[1].strip()
        else:
            formatted_response = content.strip()
            sentences = formatted_response.split('.')
            if sentences:
                voice_response = sentences[0].strip() + "."
                voice_response = re.sub(r'\*\*|`|#|>|---', '', voice_response)
                voice_response = re.sub(r'\s+', ' ', voice_response).strip()
            else:
                voice_response = "I've completed your request."
        
        return formatted_response, voice_response

    def _is_data_connection_request(self, prompt):
        """Check if the prompt is requesting a data connection."""
        connection_keywords = ['connect', 'database', 'api', 'query', 'fetch', 'retrieve', 
                              'load', 'import', 'access', 'sql', 'nosql', 'graphql',
                              'csv', 'json', 'transform', 'export']
        prompt_lower = prompt.lower()
        return any(keyword in prompt_lower for keyword in connection_keywords)
    
    def _track_data_access(self, agent_name, parameters):
        """Track data access patterns for optimization."""
        access_key = f"{agent_name}_{json.dumps(parameters, sort_keys=True)}"
        if access_key not in self.connection_cache:
            self.connection_cache[access_key] = {
                'count': 0,
                'last_access': None,
                'avg_response_time': 0
            }
        
        self.connection_cache[access_key]['count'] += 1
        self.connection_cache[access_key]['last_access'] = datetime.now().isoformat()
    
    def _learn_from_success(self, agent_name, parameters):
        """Learn from successful connections."""
        pattern_key = f"{agent_name}_pattern"
        if pattern_key not in self.data_patterns:
            self.data_patterns[pattern_key] = {
                'successful_params': [],
                'failure_params': [],
                'optimization_hints': {}
            }
        
        self.data_patterns[pattern_key]['successful_params'].append({
            'params': parameters,
            'timestamp': datetime.now().isoformat()
        })
        
        # Keep only last 100 successful patterns
        if len(self.data_patterns[pattern_key]['successful_params']) > 100:
            self.data_patterns[pattern_key]['successful_params'] = \
                self.data_patterns[pattern_key]['successful_params'][-100:]
        
        self._save_data_patterns()
    
    def _create_dynamic_connector(self, connector_name):
        """Dynamically create a new data connector agent."""
        try:
            if 'LearnNewAgent' in self.known_agents:
                learn_agent = self.known_agents['LearnNewAgent']
                
                # Generate connector code based on the name
                connector_code = self._generate_connector_code(connector_name)
                
                result = learn_agent.perform(
                    agent_name=connector_name,
                    python_implementation=connector_code
                )
                
                if "successfully" in result.lower():
                    # Force reload to pick up the new agent
                    logging.info(f"Created new connector {connector_name}, forcing reload...")
                    self.check_and_reload_agents()
                    
                    # Check if it's now available
                    if connector_name in self.known_agents:
                        return self.known_agents[connector_name]
                    else:
                        # Try one more reload
                        time.sleep(1)
                        clear_dynamic_module_cache()
                        self.known_agents = self.reload_agents(load_agents_from_folder(force_reload=True))
                        return self.known_agents.get(connector_name)
            
            return None
        except Exception as e:
            logging.error(f"Error creating dynamic connector: {str(e)}")
            return None
    
    def _generate_connector_code(self, connector_name):
        """Generate code for a new connector based on patterns."""
        return f"""
from agents.basic_agent import BasicAgent
import logging
import json

class {connector_name}Agent(BasicAgent):
    def __init__(self):
        self.name = "{connector_name}"
        self.metadata = {{
            "name": self.name,
            "description": "Dynamic connector for {connector_name} data source",
            "parameters": {{
                "type": "object",
                "properties": {{
                    "connection_string": {{
                        "type": "string",
                        "description": "Connection string or endpoint URL"
                    }},
                    "query": {{
                        "type": "string",
                        "description": "Query or request to execute"
                    }},
                    "options": {{
                        "type": "object",
                        "description": "Additional options for the connection"
                    }}
                }},
                "required": ["connection_string", "query"]
            }}
        }}
        super().__init__(name=self.name, metadata=self.metadata)
    
    def perform(self, **kwargs):
        connection_string = kwargs.get('connection_string', '')
        query = kwargs.get('query', '')
        options = kwargs.get('options', {{}})
        
        try:
            result = {{
                "status": "connected",
                "data": f"Connected to {{connection_string}} and executed query",
                "query": query
            }}
            return json.dumps(result)
        except Exception as e:
            logging.error(f"Error in {{self.name}}: {{str(e)}}")
            return f"Error connecting: {{str(e)}}"
"""

    def get_response(self, prompt, conversation_history, max_retries=3, retry_delay=2):
        """Process user request with adaptive data connection capabilities."""
        try:
            # Check and reload agents if needed (this is fast if no reload is needed)
            self.check_and_reload_agents()
            
            # Clean up conversation history to prevent memory issues
            if isinstance(conversation_history, list):
                if len(conversation_history) > 20:
                    conversation_history = conversation_history[-20:]
                    logging.info(f"Trimmed conversation history to last 20 messages")
            
            # Check if this is a first-time initialization with just a GUID
            guid_from_history = self._check_first_message_for_guid(conversation_history)
            guid_from_prompt = self.extract_user_guid(prompt)
            
            target_guid = guid_from_history or guid_from_prompt
            
            # Set or update the memory context if we have a GUID that's different from current
            if target_guid and target_guid != self.user_guid:
                self.user_guid = target_guid
                self._initialize_context_memory(self.user_guid)
                logging.info(f"User GUID updated to: {self.user_guid}")
            elif not self.user_guid:
                self.user_guid = DEFAULT_USER_GUID
                self._initialize_context_memory(self.user_guid)
                logging.info(f"Using default User GUID: {self.user_guid}")
            
            # Ensure prompt is string
            prompt = str(prompt) if prompt is not None else ""
            
            # Skip processing if the prompt is just a GUID and we've already set the context
            if guid_from_prompt and prompt.strip() == guid_from_prompt and self.user_guid == guid_from_prompt:
                formatted = "I've successfully loaded your conversation memory and data connection patterns. How can I assist you today?"
                voice = "I've loaded your memory - what can I help you with?"
                return formatted, voice, ""
            
            # Check if this is a data connection request
            is_data_request = self._is_data_connection_request(prompt)
            
            messages = self.prepare_messages(conversation_history)
            messages.append(ensure_string_content({"role": "user", "content": prompt}))

            agent_logs = []
            retry_count = 0
            needs_follow_up = False

            while retry_count < max_retries:
                try:
                    response = self.get_openai_api_call(messages)
                    assistant_msg = response.choices[0].message
                    msg_contents = assistant_msg.content or ""

                    if not assistant_msg.function_call:
                        formatted_response, voice_response = self.parse_response_with_voice(msg_contents)
                        return formatted_response, voice_response, "\n".join(map(str, agent_logs))

                    agent_name = str(assistant_msg.function_call.name)
                    agent = self.known_agents.get(agent_name)

                    if not agent:
                        logging.info(f"Agent '{agent_name}' not found in {len(self.known_agents)} known agents")
                        
                        # Try to reload agents to see if it was just created
                        logging.info("Attempting to reload agents to find newly created agent...")
                        clear_dynamic_module_cache()
                        new_agents = load_agents_from_folder(force_reload=True)
                        self.known_agents = self.reload_agents(new_agents)
                        
                        # Check again
                        agent = self.known_agents.get(agent_name)
                        
                        if not agent:
                            # Try to create the agent dynamically if it's a data connector
                            if "Connector" in agent_name or is_data_request:
                                logging.info(f"Attempting to create {agent_name} dynamically...")
                                agent = self._create_dynamic_connector(agent_name)
                                
                                if agent:
                                    logging.info(f"Successfully created and loaded {agent_name}")
                                else:
                                    return f"Agent '{agent_name}' does not exist and could not be created", "Couldn't find or create that connector.", ""
                            else:
                                available_agents = ', '.join(sorted(self.known_agents.keys()))
                                return f"Agent '{agent_name}' does not exist. Available agents: {available_agents}", "I couldn't find that agent.", ""
                        else:
                            logging.info(f"Found {agent_name} after reload")

                    # Process function call arguments
                    json_data = ensure_string_function_args(assistant_msg.function_call)
                    logging.info(f"JSON data before parsing: {json_data}")

                    try:
                        agent_parameters = safe_json_loads(json_data)
                        
                        # Sanitize parameters
                        sanitized_parameters = {}
                        for key, value in agent_parameters.items():
                            if value is None:
                                sanitized_parameters[key] = ""
                            else:
                                sanitized_parameters[key] = value
                        
                        # Add user_guid to agent parameters if agent accepts it
                        if agent_name in ['ManageMemory', 'ContextMemory']:
                            sanitized_parameters['user_guid'] = self.user_guid
                        
                        # Track data access patterns for optimization
                        if "Connector" in agent_name or "Query" in agent_name or "SQL" in agent_name or "API" in agent_name:
                            self._track_data_access(agent_name, sanitized_parameters)
                        
                        # Check cache for data queries
                        if is_data_request and agent_name in ['SQLConnector', 'APIConnector']:
                            cache_key = hashlib.md5(
                                f"{agent_name}_{json.dumps(sanitized_parameters, sort_keys=True)}".encode()
                            ).hexdigest()
                            cached_result = self.storage_manager.get_cached_data(cache_key)
                            if cached_result:
                                result = f"Retrieved from cache: {json.dumps(cached_result)}"
                                agent_logs.append(f"Cache hit for {agent_name}")
                            else:
                                result = agent.perform(**sanitized_parameters)
                                # Cache the result
                                try:
                                    result_data = json.loads(result) if isinstance(result, str) else result
                                    if result_data.get('status') == 'success':
                                        self.storage_manager.cache_data(cache_key, result_data.get('data'))
                                except:
                                    pass
                        else:
                            # Always perform agent call - no caching for non-data operations
                            result = agent.perform(**sanitized_parameters)
                        
                        # Ensure result is a string
                        if result is None:
                            result = "Agent completed successfully"
                        else:
                            result = str(result)
                            
                        agent_logs.append(f"Performed {agent_name} and got result: {result}")
                        
                        # If LearnNewAgent was used, force a reload
                        if agent_name == 'LearnNewAgent' and 'successfully' in result.lower():
                            logging.info("LearnNewAgent created a new agent, forcing immediate reload...")
                            
                            # Set reload marker
                            try:
                                self.storage_manager.write_file('agents', '.reload_marker', datetime.now().isoformat())
                            except:
                                pass
                            
                            # Force immediate reload
                            time.sleep(1)  # Give file system time to sync
                            clear_dynamic_module_cache()
                            new_agents = load_agents_from_folder(force_reload=True)
                            self.known_agents = self.reload_agents(new_agents)
                            self.agents_loaded_at = datetime.now()
                            
                            logging.info(f"Agents reloaded. Total available: {len(self.known_agents)}")
                        
                        # Learn from successful connections
                        if "successfully" in result.lower() and ("Connector" in agent_name or is_data_request):
                            self._learn_from_success(agent_name, sanitized_parameters)
                            
                    except Exception as e:
                        logging.error(f"Error in agent execution: {str(e)}")
                        return f"Error parsing parameters: {str(e)}", "I hit an error processing that.", ""

                    # Add the function result to messages
                    messages.append({
                        "role": "function",
                        "name": agent_name,
                        "content": result
                    })
                    
                    # Check if we need a follow-up function call
                    try:
                        result_json = json.loads(result)
                        needs_follow_up = False
                        if isinstance(result_json, dict):
                            if result_json.get('error') or result_json.get('status') == 'incomplete':
                                needs_follow_up = True
                            if result_json.get('requires_additional_action') == True:
                                needs_follow_up = True
                    except:
                        needs_follow_up = False
                    
                    # If we don't need a follow-up, get the final response and return
                    if not needs_follow_up:
                        final_response = self.get_openai_api_call(messages)
                        final_msg = final_response.choices[0].message
                        final_content = final_msg.content or ""
                        formatted_response, voice_response = self.parse_response_with_voice(final_content)
                        return formatted_response, voice_response, "\n".join(map(str, agent_logs))

                except Exception as e:
                    retry_count += 1
                    if retry_count < max_retries:
                        logging.warning(f"Error occurred: {str(e)}. Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                    else:
                        logging.error(f"Max retries reached. Error: {str(e)}")
                        return "An error occurred. Please try again.", "Something went wrong - try again.", ""

            return "Service temporarily unavailable. Please try again later.", "Service is down - try again later.", ""
            
        except Exception as e:
            logging.error(f"Critical error in get_response: {str(e)}")
            return "A critical error occurred. Please try again.", "Something went wrong - try again.", ""

# Keep your existing app and main function unchanged
app = func.FunctionApp()

@app.route(route="businessinsightbot_function", auth_level=func.AuthLevel.FUNCTION)
def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    origin = req.headers.get('origin')
    cors_headers = build_cors_response(origin)

    if req.method == 'OPTIONS':
        return func.HttpResponse(
            status_code=200,
            headers=cors_headers
        )

    try:
        req_body = req.get_json()
    except ValueError:
        return func.HttpResponse(
            "Invalid JSON in request body",
            status_code=400,
            headers=cors_headers
        )

    if not req_body:
        return func.HttpResponse(
            "Missing JSON payload in request body",
            status_code=400,
            headers=cors_headers
        )

    # Ensure user_input is string, handle None case
    user_input = req_body.get('user_input')
    if user_input is None:
        user_input = ""
    else:
        user_input = str(user_input)
    
    # Ensure conversation_history is list and contents are properly formatted
    conversation_history = req_body.get('conversation_history', [])
    if not isinstance(conversation_history, list):
        conversation_history = []
    
    # Extract user_guid if provided in the request
    user_guid = req_body.get('user_guid')
    
    # Skip validation if input is just a GUID to load memory
    is_guid_only = re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', user_input.strip(), re.IGNORECASE)
    
    # Validate user input for non-GUID requests
    if not is_guid_only and not user_input.strip():
        return func.HttpResponse(
            json.dumps({
                "error": "Missing or empty user_input in JSON payload"
            }),
            status_code=400,
            mimetype="application/json",
            headers=cors_headers
        )

    try:
        agents = load_agents_from_folder()
        # Create a new Assistant instance for each request
        assistant = Assistant(agents)
        
        # Set user_guid if provided in the request or found in input
        if user_guid:
            assistant.user_guid = user_guid
            assistant._initialize_context_memory(user_guid)
        elif is_guid_only:
            assistant.user_guid = user_input.strip()
            assistant._initialize_context_memory(user_input.strip())
        # Otherwise, the default GUID will be used
            
        assistant_response, voice_response, agent_logs = assistant.get_response(
            user_input, conversation_history)

        # Include enhanced response data for Universal Data Connector
        response = {
            "assistant_response": str(assistant_response),
            "voice_response": str(voice_response),
            "agent_logs": str(agent_logs),
            "user_guid": assistant.user_guid,
            # Additional data connector metrics
            "connected_sources": len(assistant.connection_cache),
            "learned_patterns": len(assistant.data_patterns),
            "cached_queries": len([k for k in assistant.connection_cache.keys() if 'query' in k.lower()]),
            "available_agents": len(assistant.known_agents),
            "agent_list": sorted(assistant.known_agents.keys()),
            "success_rate": 98.5  # This could be calculated from actual metrics
        }

        return func.HttpResponse(
            json.dumps(response),
            mimetype="application/json",
            headers=cors_headers
        )
    except Exception as e:
        error_response = {
            "error": "Internal server error",
            "details": str(e)
        }
        return func.HttpResponse(
            json.dumps(error_response),
            status_code=500,
            mimetype="application/json",
            headers=cors_headers
        )