from agents.basic_agent import BasicAgent
import json
import logging
import hashlib
import os
import ast
import traceback
from datetime import datetime
from typing import Dict, List, Any, Optional
from copy import deepcopy
from utils.azure_file_storage import AzureFileStorageManager
from openai import AzureOpenAI

class FrameAgent(BasicAgent):
    def __init__(self):
        self.name = "Frame"
        self.metadata = {
            "name": self.name,
            "description": "Universal frame simulation agent that can create and manage ANY type of simulation world. The agent is completely generic - ALL simulation logic must be provided by the caller through rules (Python code). The agent does NOT have any built-in physics or simulation behavior.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "Action to perform on the simulation",
                        "enum": [
                            "create_world", "advance_frame", "rewind_frame", "query_state", 
                            "modify_entity", "add_entity", "remove_entity", "get_history", 
                            "save_state", "load_state", "apply_rules", "update_frame", 
                            "simulate_frame", "reset_frame", "analyze_frame", 
                            "list_worlds", "delete_world", "export_world", "import_world",
                            "modify_environment", "execute_code"
                        ]
                    },
                    "world_type": {
                        "type": "string",
                        "description": "ANY type of world/simulation (e.g., 'particle_physics', 'ecosystem', 'economy', 'cellular_automaton'). This is just a label - behavior is determined by your rules."
                    },
                    "world_config": {
                        "type": "object",
                        "description": "Complete configuration for your world. Should include: entities (array of objects with 'id', 'type', 'properties'), rules (array of objects with 'name' and 'code'), environment (object with any variables), global_state (object with tracking metrics). ALL simulation logic must be in the rules' code.",
                        "additionalProperties": True
                    },
                    "world_id": {
                        "type": "string",
                        "description": "ID of world. Auto-generated if not provided."
                    },
                    "entities": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "Array of entities for create_world action. Each entity MUST have: type (string), properties (object with ANY attributes you need). Example: [{'type': 'particle', 'properties': {'x': 0, 'y': 0, 'vx': 1, 'vy': 0, 'mass': 1}}]"
                    },
                    "rules": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "Simulation rules that define ALL behavior. Each rule MUST have: name (string) and code (string of Python code). The code has access to 'frame' dict which it should modify in-place. Available imports: math, random, datetime, json, deepcopy. Example: [{'name': 'gravity', 'code': 'for e in frame.get(\"entities\", []):\\n    e[\"properties\"][\"vy\"] += -9.81 * 0.01'}]"
                    },
                    "entity": {
                        "type": "object",
                        "description": "FOR add_entity ACTION ONLY: Single entity object to add. MUST contain 'type' (string) and 'properties' (object). Example: {'type': 'particle', 'properties': {'x': 0, 'y': 0, 'vx': 1, 'vy': 0, 'mass': 1}}. An 'id' will be auto-generated if not provided in the entity.",
                        "additionalProperties": True
                    },
                    "entity_id": {
                        "type": "string",
                        "description": "ID of entity to modify/remove"
                    },
                    "modifications": {
                        "type": "object",
                        "description": "Properties to change on entity or environment. For entities, use {'properties': {...}} to modify nested properties.",
                        "additionalProperties": True
                    },
                    "environment_updates": {
                        "type": "object",
                        "description": "Environment parameters to update (e.g., {'gravity': 9.81, 'temperature': 300})",
                        "additionalProperties": True
                    },
                    "steps": {
                        "type": "integer",
                        "description": "Number of simulation steps. Default: 1"
                    },
                    "event": {
                        "type": "string",
                        "description": "Event name to trigger (only works with AI enabled)"
                    },
                    "context": {
                        "type": "object",
                        "description": "Additional context for operation",
                        "additionalProperties": True
                    },
                    "query": {
                        "type": "string",
                        "description": "Query format: 'count:type', 'find:property=value', 'average:property', 'sum:property', 'max:property', 'min:property', 'full'"
                    },
                    "state_name": {
                        "type": "string",
                        "description": "Name for save/load"
                    },
                    "code": {
                        "type": "string",
                        "description": "Python code to execute on the frame. Has access to 'frame' variable and can set 'result'. Available: math, random, datetime, json, deepcopy. Make sure to use proper Python indentation with spaces (not tabs) and newlines."
                    },
                    "use_ai": {
                        "type": "boolean",
                        "description": "Use AI for operations. Default: false"
                    },
                    "auto_generate": {
                        "type": "boolean",
                        "description": "Auto-generate world config using AI based on world_type. Default: false"
                    }
                },
                "required": ["action"],
                "additionalProperties": True
            },
            "examples": [
                {
                    "description": "Create a particle physics world with collision detection",
                    "params": {
                        "action": "create_world",
                        "world_type": "particle_physics",
                        "world_config": {
                            "entities": [
                                {"type": "particle", "properties": {"x": 0, "y": 0, "vx": 1, "vy": 0, "mass": 1, "charge": -1}},
                                {"type": "particle", "properties": {"x": 10, "y": 0, "vx": -1, "vy": 0, "mass": 1, "charge": 1}}
                            ],
                            "rules": [
                                {
                                    "name": "update_positions",
                                    "code": "for e in frame.get('entities', []):\\n    e['properties']['x'] += e['properties'].get('vx', 0) * 0.01\\n    e['properties']['y'] += e['properties'].get('vy', 0) * 0.01"
                                },
                                {
                                    "name": "detect_collisions",
                                    "code": "import math\\nentities = frame.get('entities', [])\\nfor i, e1 in enumerate(entities):\\n    for e2 in entities[i+1:]:\\n        dx = e1['properties']['x'] - e2['properties']['x']\\n        dy = e1['properties']['y'] - e2['properties']['y']\\n        dist = math.sqrt(dx*dx + dy*dy)\\n        if dist < 1:\\n            frame['global_state']['collisions'] = frame['global_state'].get('collisions', 0) + 1"
                                }
                            ],
                            "environment": {"gravity": 0, "electric_field": 1000},
                            "global_state": {"collisions": 0, "total_energy": 0}
                        }
                    }
                },
                {
                    "description": "Add a single entity to existing world",
                    "params": {
                        "action": "add_entity",
                        "world_id": "YOUR_WORLD_ID",
                        "entity": {
                            "type": "particle",
                            "properties": {"x": 5.0, "y": 5.0, "vx": 0.5, "vy": -0.5, "mass": 2.0}
                        }
                    }
                },
                {
                    "description": "Apply rules to current frame",
                    "params": {
                        "action": "apply_rules",
                        "world_id": "YOUR_WORLD_ID",
                        "rules": [
                            {
                                "name": "apply_gravity",
                                "code": "for e in frame.get('entities', []):\\n    if e.get('type') == 'particle':\\n        e['properties']['vy'] = e['properties'].get('vy', 0) - 0.01"
                            }
                        ]
                    }
                },
                {
                    "description": "Advance simulation with custom rules",
                    "params": {
                        "action": "advance_frame",
                        "world_id": "YOUR_WORLD_ID",
                        "steps": 100,
                        "rules": [
                            {
                                "name": "check_collision_threshold",
                                "code": "if frame['global_state'].get('collisions', 0) > 0:\\n    print(f\"Collision detected at frame {frame['frame_number']}\")"
                            }
                        ]
                    }
                }
            ]
        }
        
        # Initialize storage
        self.storage_manager = AzureFileStorageManager()
        
        # State management
        self.worlds = {}
        self.current_world_id = None
        self.frame_history = {}
        
        # Initialize AI
        self.ai_enabled = False
        self.ai_client = None
        self.deployment_name = None
        self._initialize_ai()
        
        # Load persisted data
        self._load_persisted_data()
        
        super().__init__(name=self.name, metadata=self.metadata)
    
    def _initialize_ai(self):
        """Initialize AI for intelligent simulations"""
        try:
            api_key = os.environ.get('AZURE_OPENAI_API_KEY')
            endpoint = os.environ.get('AZURE_OPENAI_ENDPOINT')
            api_version = os.environ.get('AZURE_OPENAI_API_VERSION', '2024-02-01')
            deployment = os.environ.get('AZURE_OPENAI_DEPLOYMENT_NAME', 'gpt-deployment')
            
            if api_key and endpoint:
                self.ai_client = AzureOpenAI(
                    api_key=api_key,
                    api_version=api_version,
                    azure_endpoint=endpoint
                )
                self.deployment_name = deployment
                self.ai_enabled = True
                logging.info("Frame AI enabled")
            else:
                self.ai_enabled = False
                logging.info("Frame running without AI")
        except Exception as e:
            self.ai_enabled = False
            logging.warning(f"AI initialization failed: {str(e)}")
    
    def _load_persisted_data(self):
        """Load saved worlds"""
        try:
            data = self.storage_manager.read_json_from_path("frames", "worlds.json")
            if data:
                self.worlds = data.get('worlds', {})
                self.current_world_id = data.get('current_world_id')
                self.frame_history = data.get('history', {})
                logging.info(f"Loaded {len(self.worlds)} worlds")
        except Exception as e:
            logging.debug(f"No persisted worlds: {str(e)}")
    
    def _save_persisted_data(self):
        """Save all worlds"""
        try:
            data = {
                'worlds': self.worlds,
                'current_world_id': self.current_world_id,
                'history': self.frame_history,
                'saved_at': datetime.now().isoformat()
            }
            self.storage_manager.write_json_to_path(data, "frames", "worlds.json")
        except Exception as e:
            logging.error(f"Error saving: {str(e)}")
    
    def _validate_python_syntax(self, code, rule_name="code"):
        """Validate Python syntax and provide helpful error messages"""
        try:
            # First check if it compiles
            compile(code, f"<{rule_name}>", 'exec')
            return True, None
        except SyntaxError as e:
            # Provide detailed error info
            error_msg = f"Python syntax error in '{rule_name}' at line {e.lineno}: {e.msg}"
            if e.text:
                error_msg += f"\nProblematic line: {e.text.strip()}"
            return False, error_msg
        except Exception as e:
            return False, f"Code validation error in '{rule_name}': {str(e)}"
    
    def _validate_rule(self, rule):
        """Validate rule structure and provide helpful error messages"""
        if not isinstance(rule, dict):
            return False, "Rule must be a dictionary object with 'name' and 'code' keys"
        if 'name' not in rule:
            return False, "Rule must have a 'name' field (string)"
        if 'code' not in rule:
            return False, "Rule must have a 'code' field containing Python code as a string"
        if not isinstance(rule['code'], str):
            return False, "Rule 'code' must be a string containing Python code"
        if len(rule['code'].strip()) == 0:
            return False, f"Rule '{rule['name']}' has empty code"
        
        # Validate Python syntax
        valid, error = self._validate_python_syntax(rule['code'], rule.get('name', 'unnamed'))
        if not valid:
            return False, error
        
        return True, None
    
    def _validate_entity(self, entity):
        """Validate entity structure"""
        if not isinstance(entity, dict):
            return False, "Entity must be a dictionary object with 'type' and 'properties' keys. Example: {'type': 'particle', 'properties': {'x': 0, 'y': 0}}"
        if 'type' not in entity:
            return False, "Entity must have a 'type' field (string). Example: {'type': 'particle', 'properties': {...}}"
        if 'properties' not in entity:
            return False, "Entity must have a 'properties' field (can be an empty dict {}). Example: {'type': 'particle', 'properties': {'x': 0, 'y': 0}}"
        if not isinstance(entity['properties'], dict):
            return False, "Entity 'properties' must be a dictionary"
        return True, None
    
    def _execute_rule_code(self, code, frame, rule_name="rule"):
        """Execute rule code with proper error handling"""
        try:
            exec_globals = {
                'frame': frame,
                'math': __import__('math'),
                'random': __import__('random'),
                'datetime': datetime,
                'json': json,
                'deepcopy': deepcopy
            }
            exec(code, exec_globals)
            return exec_globals.get('frame', frame), None
        except SyntaxError as e:
            error_msg = f"Syntax error in {rule_name} at line {e.lineno}: {e.msg}"
            if e.text:
                error_msg += f" - {e.text.strip()}"
            return frame, error_msg
        except NameError as e:
            return frame, f"Name error in {rule_name}: {str(e)}. Make sure all variables are defined."
        except TypeError as e:
            return frame, f"Type error in {rule_name}: {str(e)}. Check data types in operations."
        except KeyError as e:
            return frame, f"Key error in {rule_name}: {str(e)}. Check dictionary keys exist."
        except Exception as e:
            return frame, f"Error in {rule_name}: {type(e).__name__}: {str(e)}"
    
    def perform(self, **kwargs):
        """Execute action"""
        action = kwargs.get('action')
        
        try:
            if action == 'create_world':
                return self._create_world(kwargs)
            elif action == 'advance_frame':
                return self._advance_frame(kwargs)
            elif action == 'rewind_frame':
                return self._rewind_frame(kwargs)
            elif action == 'add_entity':
                return self._add_entity(kwargs)
            elif action == 'remove_entity':
                return self._remove_entity(kwargs)
            elif action == 'modify_entity':
                return self._modify_entity(kwargs)
            elif action == 'modify_environment':
                return self._modify_environment(kwargs)
            elif action == 'apply_rules':
                return self._apply_rules(kwargs)
            elif action == 'query_state':
                return self._query_state(kwargs)
            elif action == 'get_history':
                return self._get_history(kwargs)
            elif action == 'update_frame':
                return self._update_frame(kwargs)
            elif action == 'simulate_frame':
                return self._simulate_frame(kwargs)
            elif action == 'reset_frame':
                return self._reset_frame(kwargs)
            elif action == 'analyze_frame':
                return self._analyze_frame(kwargs)
            elif action == 'list_worlds':
                return self._list_worlds()
            elif action == 'delete_world':
                return self._delete_world(kwargs)
            elif action == 'save_state':
                return self._save_state(kwargs)
            elif action == 'load_state':
                return self._load_state(kwargs)
            elif action == 'export_world':
                return self._export_world(kwargs)
            elif action == 'import_world':
                return self._import_world(kwargs)
            elif action == 'execute_code':
                return self._execute_code(kwargs)
            else:
                return json.dumps({"success": False, "error": f"Unknown action: {action}"})
        except Exception as e:
            logging.error(f"Error: {str(e)}")
            return json.dumps({"success": False, "error": str(e)})
    
    def _create_world(self, params):
        """Create any type of simulation world"""
        world_type = params.get('world_type', 'generic_simulation')
        world_config = params.get('world_config')
        auto_generate = params.get('auto_generate', False)
        use_ai = params.get('use_ai', self.ai_enabled)
        
        # Generate ID if not provided
        world_id = params.get('world_id') or self._generate_id()
        
        # Handle configuration
        if world_config:
            # Validate entities if provided
            for entity in world_config.get('entities', []):
                valid, error = self._validate_entity(entity)
                if not valid:
                    return json.dumps({"success": False, "error": f"Invalid entity in world_config: {error}"})
            
            # Validate rules if provided
            for rule in world_config.get('rules', []):
                valid, error = self._validate_rule(rule)
                if not valid:
                    return json.dumps({"success": False, "error": f"Invalid rule in world_config: {error}"})
            
            # Use provided config exactly as given
            world_config['id'] = world_id
            world_config.setdefault('world_type', world_type)
            world_config.setdefault('frame_number', 0)
            # Don't set defaults for entities, rules, etc - let caller control everything
        elif auto_generate and self.ai_enabled and use_ai:
            # Generate with AI if requested
            world_config = self._ai_generate_world(world_type, world_id)
        else:
            # Minimal config - completely empty world
            world_config = {
                'id': world_id,
                'world_type': world_type,
                'frame_number': 0,
                'entities': params.get('entities', []),
                'rules': params.get('rules', []),
                'environment': params.get('environment', {}),
                'global_state': params.get('global_state', {})
            }
        
        # Ensure all entities have IDs
        for entity in world_config.get('entities', []):
            if 'id' not in entity:
                entity['id'] = self._generate_id()[:12]
        
        # Create world container
        world = {
            'current_frame': world_config,
            'history': [],
            'created_at': datetime.now().isoformat(),
            'type': world_type,
            'ai_enabled': use_ai
        }
        
        # Add metadata
        world['current_frame']['timestamp'] = datetime.now().isoformat()
        world['current_frame']['version'] = 1
        world['current_frame']['metadata'] = {
            'total_updates': 0,
            'last_event': None,
            'world_type': world_type
        }
        
        # Store
        self.worlds[world_id] = world
        self.current_world_id = world_id
        self.frame_history[world_id] = [{
            'version': 1,
            'timestamp': world['created_at'],
            'state': deepcopy(world_config),
            'event': 'world_created'
        }]
        
        self._save_persisted_data()
        
        return json.dumps({
            "success": True,
            "world_id": world_id,
            "world_type": world_type,
            "entity_count": len(world_config.get('entities', [])),
            "rule_count": len(world_config.get('rules', [])),
            "frame_number": 0,
            "ai_enabled": use_ai,
            "environment": world_config.get('environment', {}),
            "global_state": world_config.get('global_state', {}),
            "message": f"Created {world_type} world '{world_id}'. Remember: ALL simulation behavior must be defined in your rules."
        }, indent=2)
    
    def _ai_generate_world(self, world_type, world_id):
        """Use AI to generate world configuration"""
        try:
            prompt = f"""Generate a complete configuration for a {world_type} simulation world.
Return a JSON object with these exact keys:
- environment: object with relevant variables for {world_type}
- entities: array of entity objects, each with 'type' and 'properties' keys
- rules: array of rule objects, each with 'name' and 'code' (Python code string)
- global_state: object with metrics to track

IMPORTANT: 
- Each entity must have 'type' (string) and 'properties' (object) keys
- The code in rules should modify the 'frame' dictionary in-place.
- The code has access to: math, random, datetime, json, deepcopy
- Example rule code: 'for e in frame.get("entities", []):\\n    e["properties"]["x"] += e["properties"].get("vx", 0) * 0.01'
- Include all necessary logic in the rules - there is NO built-in physics or behavior.
- Use proper Python indentation with spaces and \\n for newlines.
Return ONLY valid JSON."""

            response = self.ai_client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": "Generate simulation configurations. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,
                max_tokens=2000
            )
            
            config_text = response.choices[0].message.content.strip()
            if config_text.startswith('```'):
                config_text = config_text[config_text.find('{'):config_text.rfind('}')+1]
            
            config = json.loads(config_text)
            config['id'] = world_id
            config['world_type'] = world_type
            config['frame_number'] = 0
            
            return config
            
        except Exception as e:
            logging.error(f"AI generation failed: {str(e)}")
            # Return minimal config on failure
            return {
                'id': world_id,
                'world_type': world_type,
                'frame_number': 0,
                'entities': [],
                'rules': [],
                'environment': {},
                'global_state': {}
            }
    
    def _advance_frame(self, params):
        """Advance simulation by applying rules"""
        world_id = params.get('world_id') or self.current_world_id
        steps = params.get('steps', 1)
        event = params.get('event')
        context = params.get('context', {})
        rules = params.get('rules', [])
        
        if not world_id or world_id not in self.worlds:
            return json.dumps({"success": False, "error": f"World '{world_id}' not found"})
        
        # Validate additional rules
        for rule in rules:
            valid, error = self._validate_rule(rule)
            if not valid:
                return json.dumps({"success": False, "error": f"Invalid rule: {error}"})
        
        world = self.worlds[world_id]
        results = []
        
        for step in range(steps):
            # Save history
            world['history'].append(deepcopy(world['current_frame']))
            if len(world['history']) > 100:
                world['history'] = world['history'][-100:]
            
            # Create new frame
            new_frame = deepcopy(world['current_frame'])
            new_frame['frame_number'] = new_frame.get('frame_number', 0) + 1
            new_frame['timestamp'] = datetime.now().isoformat()
            new_frame['version'] = new_frame.get('version', 1) + 1
            
            changes = []
            
            # Apply event if specified
            if event:
                if world.get('ai_enabled') and self.ai_enabled:
                    new_frame = self._ai_apply_event(new_frame, event, context)
                    changes.append({'type': 'ai_event', 'event': event})
                else:
                    # Event without AI - just record it
                    changes.append({'type': 'event', 'event': event})
                    if 'metadata' in new_frame:
                        new_frame['metadata']['last_event'] = event
            
            # Apply world's built-in rules
            for rule in new_frame.get('rules', []):
                if 'code' in rule:
                    new_frame, error = self._execute_rule_code(
                        rule['code'], 
                        new_frame, 
                        f"rule '{rule.get('name', 'unnamed')}'"
                    )
                    if error:
                        logging.error(error)
                    else:
                        changes.append({'type': 'rule', 'rule_name': rule.get('name', 'unnamed')})
            
            # Apply additional rules from params
            for rule in rules:
                if 'code' in rule:
                    new_frame, error = self._execute_rule_code(
                        rule['code'], 
                        new_frame, 
                        f"custom rule '{rule.get('name', 'unnamed')}'"
                    )
                    if error:
                        logging.error(error)
                    else:
                        changes.append({'type': 'custom_rule', 'name': rule.get('name', 'unnamed')})
            
            # Update metadata
            if 'metadata' in new_frame:
                new_frame['metadata']['total_updates'] = new_frame['metadata'].get('total_updates', 0) + 1
                if event:
                    new_frame['metadata']['last_event'] = event
            
            world['current_frame'] = new_frame
            results.append({
                'frame': new_frame['frame_number'],
                'changes': len(changes),
                'changes_detail': changes,
                'timestamp': new_frame['timestamp']
            })
        
        self._save_persisted_data()
        
        return json.dumps({
            "success": True,
            "world_id": world_id,
            "frames_advanced": steps,
            "current_frame": world['current_frame']['frame_number'],
            "results": results
        }, indent=2)
    
    def _ai_apply_event(self, frame, event, context):
        """Use AI to apply event to frame"""
        try:
            prompt = f"""Apply the event '{event}' to this simulation frame.
Current frame: {json.dumps(frame, indent=2)}
Context: {json.dumps(context, indent=2) if context else 'None'}

Modify the frame realistically based on the event.
Return the complete modified frame as JSON."""

            response = self.ai_client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": "Apply events to simulation frames. Return valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            result = response.choices[0].message.content.strip()
            if result.startswith('```'):
                result = result[result.find('{'):result.rfind('}')+1]
            
            return json.loads(result)
        except Exception as e:
            logging.error(f"AI event application failed: {str(e)}")
            return frame
    
    def _add_entity(self, params):
        """Add entity to world"""
        world_id = params.get('world_id') or self.current_world_id
        entity = params.get('entity')
        
        if not world_id or world_id not in self.worlds:
            return json.dumps({"success": False, "error": f"World '{world_id}' not found"})
        
        if not entity:
            return json.dumps({
                "success": False, 
                "error": "Parameter 'entity' is required. It must be an object with 'type' and 'properties' keys. Example: {'entity': {'type': 'particle', 'properties': {'x': 0, 'y': 0, 'vx': 1, 'vy': 0}}}"
            })
        
        # Validate entity
        valid, error = self._validate_entity(entity)
        if not valid:
            return json.dumps({"success": False, "error": error})
        
        # Ensure entity has an ID
        if 'id' not in entity:
            entity['id'] = self._generate_id()[:12]
        
        world = self.worlds[world_id]
        world['current_frame'].setdefault('entities', []).append(entity)
        
        self._save_persisted_data()
        
        return json.dumps({
            "success": True,
            "world_id": world_id,
            "entity_id": entity['id'],
            "entity_type": entity['type'],
            "total_entities": len(world['current_frame']['entities'])
        }, indent=2)
    
    def _remove_entity(self, params):
        """Remove entity from world"""
        world_id = params.get('world_id') or self.current_world_id
        entity_id = params.get('entity_id')
        
        if not world_id or world_id not in self.worlds:
            return json.dumps({"success": False, "error": f"World '{world_id}' not found"})
        
        if not entity_id:
            return json.dumps({"success": False, "error": "entity_id required"})
        
        world = self.worlds[world_id]
        entities = world['current_frame'].get('entities', [])
        
        original_count = len(entities)
        world['current_frame']['entities'] = [e for e in entities if e.get('id') != entity_id]
        removed_count = original_count - len(world['current_frame']['entities'])
        
        self._save_persisted_data()
        
        return json.dumps({
            "success": True,
            "world_id": world_id,
            "removed": removed_count,
            "remaining_entities": len(world['current_frame']['entities'])
        }, indent=2)
    
    def _modify_entity(self, params):
        """Modify entity properties"""
        world_id = params.get('world_id') or self.current_world_id
        entity_id = params.get('entity_id')
        modifications = params.get('modifications', {})
        
        if not world_id or world_id not in self.worlds:
            return json.dumps({"success": False, "error": f"World '{world_id}' not found"})
        
        if not entity_id:
            return json.dumps({"success": False, "error": "entity_id required"})
        
        world = self.worlds[world_id]
        modified = False
        
        for entity in world['current_frame'].get('entities', []):
            if entity.get('id') == entity_id:
                # Apply modifications to properties
                if 'properties' in modifications:
                    entity['properties'].update(modifications['properties'])
                # Apply other modifications directly
                for key, value in modifications.items():
                    if key != 'properties':
                        entity[key] = value
                modified = True
                break
        
        self._save_persisted_data()
        
        return json.dumps({
            "success": True,
            "world_id": world_id,
            "entity_id": entity_id,
            "modified": modified
        }, indent=2)
    
    def _modify_environment(self, params):
        """Modify environment parameters"""
        world_id = params.get('world_id') or self.current_world_id
        environment_updates = params.get('environment_updates', {})
        
        if not world_id or world_id not in self.worlds:
            return json.dumps({"success": False, "error": f"World '{world_id}' not found"})
        
        world = self.worlds[world_id]
        
        # Update environment
        if 'environment' not in world['current_frame']:
            world['current_frame']['environment'] = {}
        
        world['current_frame']['environment'].update(environment_updates)
        
        # Update frame metadata
        world['current_frame']['version'] = world['current_frame'].get('version', 1) + 1
        world['current_frame']['timestamp'] = datetime.now().isoformat()
        
        self._save_persisted_data()
        
        return json.dumps({
            "success": True,
            "world_id": world_id,
            "environment": world['current_frame']['environment'],
            "version": world['current_frame']['version']
        }, indent=2)
    
    def _apply_rules(self, params):
        """Apply custom rules to current frame"""
        world_id = params.get('world_id') or self.current_world_id
        rules = params.get('rules', [])
        
        if not world_id or world_id not in self.worlds:
            return json.dumps({"success": False, "error": f"World '{world_id}' not found"})
        
        if not rules:
            return json.dumps({
                "success": False, 
                "error": "Parameter 'rules' is required. It must be an array of objects, each with 'name' and 'code' keys. Example: [{'name': 'gravity', 'code': 'for e in frame[\"entities\"]:\\n    e[\"properties\"][\"vy\"] -= 0.01'}]"
            })
        
        # Validate rules
        for i, rule in enumerate(rules):
            valid, error = self._validate_rule(rule)
            if not valid:
                return json.dumps({"success": False, "error": f"Invalid rule at index {i}: {error}"})
        
        world = self.worlds[world_id]
        frame = world['current_frame']
        applied = []
        errors = []
        
        for rule in rules:
            frame, error = self._execute_rule_code(
                rule.get('code', ''), 
                frame, 
                f"rule '{rule.get('name', 'unnamed')}'"
            )
            if error:
                errors.append(error)
                logging.error(error)
            else:
                applied.append(rule.get('name', 'unnamed'))
        
        world['current_frame'] = frame
        self._save_persisted_data()
        
        return json.dumps({
            "success": True,
            "world_id": world_id,
            "applied_rules": applied,
            "errors": errors,
            "frame_number": frame.get('frame_number', 0)
        }, indent=2)
    
    def _execute_code(self, params):
        """Execute arbitrary code on the frame"""
        world_id = params.get('world_id') or self.current_world_id
        code = params.get('code')
        
        if not world_id or world_id not in self.worlds:
            return json.dumps({"success": False, "error": f"World '{world_id}' not found"})
        
        if not code:
            return json.dumps({
                "success": False, 
                "error": "Parameter 'code' is required. It must be a string containing Python code. The code has access to 'frame' variable and can set 'result'. Example: 'result = len(frame[\"entities\"])'"
            })
        
        # Validate syntax first
        valid, error = self._validate_python_syntax(code, "execute_code")
        if not valid:
            return json.dumps({"success": False, "error": error})
        
        world = self.worlds[world_id]
        frame = world['current_frame']
        
        try:
            exec_globals = {
                'frame': frame,
                'math': __import__('math'),
                'random': __import__('random'),
                'datetime': datetime,
                'json': json,
                'deepcopy': deepcopy,
                'result': None  # Allow code to set a result
            }
            exec(code, exec_globals)
            frame = exec_globals.get('frame', frame)
            result = exec_globals.get('result')
            
            world['current_frame'] = frame
            self._save_persisted_data()
            
            return json.dumps({
                "success": True,
                "world_id": world_id,
                "frame_number": frame.get('frame_number', 0),
                "result": result
            }, indent=2)
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "hint": "Make sure your code is valid Python with proper indentation. Available variables: frame (the current world state), math, random, datetime, json, deepcopy. You can set 'result' to return a value."
            })
    
    def _query_state(self, params):
        """Query world state"""
        world_id = params.get('world_id') or self.current_world_id
        query = params.get('query', 'full')
        
        if not world_id or world_id not in self.worlds:
            # Return list of worlds
            return json.dumps({
                "success": True,
                "worlds": list(self.worlds.keys()),
                "current": self.current_world_id
            }, indent=2)
        
        world = self.worlds[world_id]
        frame = world['current_frame']
        
        if query == 'full':
            return json.dumps({
                "success": True,
                "world_id": world_id,
                "frame": frame
            }, indent=2)
        
        elif query.startswith('count:'):
            entity_type = query.split(':', 1)[1]
            count = len([e for e in frame.get('entities', []) if e.get('type') == entity_type])
            return json.dumps({
                "success": True,
                "world_id": world_id,
                "query": query,
                "result": count
            }, indent=2)
        
        elif query.startswith('find:'):
            condition = query.split(':', 1)[1]
            if '=' in condition:
                prop, value = condition.split('=', 1)
                matching = []
                for e in frame.get('entities', []):
                    # Check direct properties and nested properties
                    if prop in e and str(e[prop]) == value:
                        matching.append(e)
                    elif 'properties' in e and prop in e['properties'] and str(e['properties'][prop]) == value:
                        matching.append(e)
                return json.dumps({
                    "success": True,
                    "world_id": world_id,
                    "query": query,
                    "results": matching
                }, indent=2)
        
        elif query.startswith(('average:', 'sum:', 'max:', 'min:')):
            operation, prop = query.split(':', 1)
            values = []
            for e in frame.get('entities', []):
                # Check both direct and nested properties
                if prop in e:
                    try:
                        values.append(float(e[prop]))
                    except:
                        pass
                elif 'properties' in e and prop in e['properties']:
                    try:
                        values.append(float(e['properties'][prop]))
                    except:
                        pass
            
            result = None
            if values:
                if operation == 'average':
                    result = sum(values) / len(values)
                elif operation == 'sum':
                    result = sum(values)
                elif operation == 'max':
                    result = max(values)
                elif operation == 'min':
                    result = min(values)
            
            return json.dumps({
                "success": True,
                "world_id": world_id,
                "query": query,
                "result": result,
                "value_count": len(values)
            }, indent=2)
        
        else:
            return json.dumps({
                "success": True,
                "world_id": world_id,
                "world_type": world.get('type'),
                "frame_number": frame.get('frame_number', 0),
                "entity_count": len(frame.get('entities', [])),
                "rule_count": len(frame.get('rules', [])),
                "environment": frame.get('environment', {}),
                "global_state": frame.get('global_state', {}),
                "hint": "Use query formats: 'full', 'count:type', 'find:property=value', 'average:property', 'sum:property', 'max:property', 'min:property'"
            }, indent=2)
    
    def _get_history(self, params):
        """Get world history"""
        world_id = params.get('world_id') or self.current_world_id
        
        if not world_id or world_id not in self.worlds:
            return json.dumps({"success": False, "error": f"World '{world_id}' not found"})
        
        world = self.worlds[world_id]
        history = []
        
        for frame in world.get('history', [])[-10:]:
            history.append({
                'frame_number': frame.get('frame_number'),
                'timestamp': frame.get('timestamp'),
                'entity_count': len(frame.get('entities', [])),
                'version': frame.get('version')
            })
        
        return json.dumps({
            "success": True,
            "world_id": world_id,
            "current_frame": world['current_frame'].get('frame_number', 0),
            "history": history,
            "total_history": len(world.get('history', []))
        }, indent=2)
    
    def _rewind_frame(self, params):
        """Rewind to previous frame"""
        world_id = params.get('world_id') or self.current_world_id
        steps = params.get('steps', 1)
        
        if not world_id or world_id not in self.worlds:
            return json.dumps({"success": False, "error": f"World '{world_id}' not found"})
        
        world = self.worlds[world_id]
        
        if not world.get('history'):
            return json.dumps({"success": False, "error": "No history to rewind"})
        
        rewound = 0
        for _ in range(min(steps, len(world['history']))):
            world['current_frame'] = world['history'].pop()
            rewound += 1
        
        self._save_persisted_data()
        
        return json.dumps({
            "success": True,
            "world_id": world_id,
            "frames_rewound": rewound,
            "current_frame": world['current_frame'].get('frame_number', 0)
        }, indent=2)
    
    def _update_frame(self, params):
        """Update frame with event"""
        world_id = params.get('world_id') or self.current_world_id
        event = params.get('event')
        context = params.get('context', {})
        
        if not world_id or world_id not in self.worlds:
            return json.dumps({"success": False, "error": f"World '{world_id}' not found"})
        
        if not event:
            return json.dumps({"success": False, "error": "event required"})
        
        world = self.worlds[world_id]
        old_frame = deepcopy(world['current_frame'])
        
        if world.get('ai_enabled') and self.ai_enabled:
            world['current_frame'] = self._ai_apply_event(world['current_frame'], event, context)
        else:
            # Without AI, just record the event in metadata
            if 'metadata' not in world['current_frame']:
                world['current_frame']['metadata'] = {}
            world['current_frame']['metadata']['last_event'] = event
        
        # Update metadata
        world['current_frame']['version'] = world['current_frame'].get('version', 1) + 1
        world['current_frame']['timestamp'] = datetime.now().isoformat()
        if 'metadata' in world['current_frame']:
            world['current_frame']['metadata']['total_updates'] = world['current_frame']['metadata'].get('total_updates', 0) + 1
        
        # Add to history
        if world_id not in self.frame_history:
            self.frame_history[world_id] = []
        self.frame_history[world_id].append({
            'version': world['current_frame']['version'],
            'timestamp': world['current_frame']['timestamp'],
            'event': event,
            'state': deepcopy(world['current_frame'])
        })
        
        self._save_persisted_data()
        
        return json.dumps({
            "success": True,
            "world_id": world_id,
            "event": event,
            "version": world['current_frame']['version'],
            "ai_applied": world.get('ai_enabled', False) and self.ai_enabled
        }, indent=2)
    
    def _simulate_frame(self, params):
        """Simulate multiple steps"""
        world_id = params.get('world_id') or self.current_world_id
        steps = params.get('steps', 5)
        
        if not world_id or world_id not in self.worlds:
            return json.dumps({"success": False, "error": f"World '{world_id}' not found"})
        
        results = []
        for i in range(steps):
            result = self._advance_frame({
                'world_id': world_id,
                'steps': 1,
                'event': params.get('event'),
                'context': params.get('context'),
                'rules': params.get('rules')
            })
            results.append(json.loads(result))
        
        return json.dumps({
            "success": True,
            "world_id": world_id,
            "steps_simulated": steps,
            "results": results
        }, indent=2)
    
    def _reset_frame(self, params):
        """Reset to initial state"""
        world_id = params.get('world_id') or self.current_world_id
        
        if not world_id or world_id not in self.worlds:
            return json.dumps({"success": False, "error": f"World '{world_id}' not found"})
        
        if world_id in self.frame_history and self.frame_history[world_id]:
            initial = self.frame_history[world_id][0]['state']
            self.worlds[world_id]['current_frame'] = deepcopy(initial)
            self.worlds[world_id]['history'] = []
            
            self._save_persisted_data()
            
            return json.dumps({
                "success": True,
                "world_id": world_id,
                "reset": True,
                "frame_number": initial.get('frame_number', 0)
            }, indent=2)
        
        return json.dumps({"success": False, "error": "No initial state found"})
    
    def _analyze_frame(self, params):
        """Analyze world patterns"""
        world_id = params.get('world_id') or self.current_world_id
        
        if not world_id or world_id not in self.worlds:
            return json.dumps({"success": False, "error": f"World '{world_id}' not found"})
        
        world = self.worlds[world_id]
        frame = world['current_frame']
        
        analysis = {
            "world_id": world_id,
            "world_type": world.get('type'),
            "frame_number": frame.get('frame_number', 0),
            "entity_count": len(frame.get('entities', [])),
            "rule_count": len(frame.get('rules', [])),
            "history_length": len(world.get('history', [])),
            "ai_enabled": world.get('ai_enabled', False),
            "environment": frame.get('environment', {}),
            "global_state": frame.get('global_state', {}),
            "entity_types": {}
        }
        
        # Count entity types
        for entity in frame.get('entities', []):
            entity_type = entity.get('type', 'unknown')
            analysis['entity_types'][entity_type] = analysis['entity_types'].get(entity_type, 0) + 1
        
        if self.ai_enabled and params.get('use_ai'):
            try:
                prompt = f"""Analyze this simulation world and provide insights.
World type: {world.get('type')}
Current state: {json.dumps(frame, indent=2)}

Provide insights about patterns, anomalies, and recommendations."""

                response = self.ai_client.chat.completions.create(
                    model=self.deployment_name,
                    messages=[
                        {"role": "system", "content": "Analyze simulations and provide insights."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.5,
                    max_tokens=500
                )
                
                analysis['ai_insights'] = response.choices[0].message.content
            except Exception as e:
                logging.error(f"AI analysis failed: {str(e)}")
        
        return json.dumps({
            "success": True,
            "analysis": analysis
        }, indent=2)
    
    def _list_worlds(self):
        """List all worlds"""
        worlds = []
        for world_id, world in self.worlds.items():
            worlds.append({
                'id': world_id,
                'type': world.get('type'),
                'created': world.get('created_at'),
                'frame_number': world['current_frame'].get('frame_number', 0),
                'entities': len(world['current_frame'].get('entities', [])),
                'ai_enabled': world.get('ai_enabled', False)
            })
        
        return json.dumps({
            "success": True,
            "worlds": worlds,
            "current": self.current_world_id,
            "count": len(worlds)
        }, indent=2)
    
    def _delete_world(self, params):
        """Delete a world"""
        world_id = params.get('world_id')
        
        if not world_id:
            return json.dumps({"success": False, "error": "world_id required"})
        
        if world_id not in self.worlds:
            return json.dumps({"success": False, "error": f"World '{world_id}' not found"})
        
        del self.worlds[world_id]
        if world_id in self.frame_history:
            del self.frame_history[world_id]
        
        if self.current_world_id == world_id:
            self.current_world_id = None
        
        self._save_persisted_data()
        
        return json.dumps({"success": True, "deleted": world_id})
    
    def _save_state(self, params):
        """Save current state"""
        state_name = params.get('state_name', f'state_{datetime.now().isoformat()}')
        
        try:
            state = {
                'worlds': self.worlds,
                'frame_history': self.frame_history,
                'current_world_id': self.current_world_id,
                'saved_at': datetime.now().isoformat()
            }
            
            self.storage_manager.write_json_to_path(
                state, "frames", f"{state_name}.json"
            )
            
            return json.dumps({
                "success": True,
                "state_name": state_name,
                "saved_at": state['saved_at']
            })
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})
    
    def _load_state(self, params):
        """Load saved state"""
        state_name = params.get('state_name')
        
        if not state_name:
            return json.dumps({"success": False, "error": "state_name required"})
        
        try:
            state = self.storage_manager.read_json_from_path(
                "frames", f"{state_name}.json"
            )
            
            if state:
                self.worlds = state.get('worlds', {})
                self.frame_history = state.get('frame_history', {})
                self.current_world_id = state.get('current_world_id')
                
                return json.dumps({
                    "success": True,
                    "state_name": state_name,
                    "worlds_loaded": len(self.worlds),
                    "saved_at": state.get('saved_at')
                })
            
            return json.dumps({"success": False, "error": f"State '{state_name}' not found"})
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})
    
    def _export_world(self, params):
        """Export world configuration"""
        world_id = params.get('world_id') or self.current_world_id
        
        if not world_id or world_id not in self.worlds:
            return json.dumps({"success": False, "error": f"World '{world_id}' not found"})
        
        world = self.worlds[world_id]
        
        return json.dumps({
            "success": True,
            "world_id": world_id,
            "export": {
                "world": world,
                "history": self.frame_history.get(world_id, [])
            }
        }, indent=2)
    
    def _import_world(self, params):
        """Import world configuration"""
        world_data = params.get('world_data')
        
        if not world_data:
            return json.dumps({"success": False, "error": "world_data required"})
        
        try:
            world_id = world_data.get('world', {}).get('current_frame', {}).get('id', self._generate_id())
            self.worlds[world_id] = world_data.get('world')
            self.frame_history[world_id] = world_data.get('history', [])
            self.current_world_id = world_id
            
            self._save_persisted_data()
            
            return json.dumps({
                "success": True,
                "world_id": world_id,
                "imported": True
            })
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})
    
    def _generate_id(self):
        """Generate unique ID"""
        return hashlib.md5(f"{datetime.now().isoformat()}{id(self)}".encode()).hexdigest()[:16]