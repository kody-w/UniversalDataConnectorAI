from agents.basic_agent import BasicAgent
import json
import logging
import random
import math
import hashlib
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from copy import deepcopy

class FrameSimulationAgent(BasicAgent):
    def __init__(self):
        self.name = "FrameSimulation"
        self.metadata = {
            "name": self.name,
            "description": "Manages frame-based simulations with mixed deterministic and AI-driven entities. Tracks state, history, and reasoning.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "Action to perform",
                        "enum": ["create_world", "load_frame", "advance_frame", "rewind_frame", "query_state", "modify_entity", "add_entity", "interact", "get_history", "analyze_frame", "predict_future", "save_checkpoint", "load_checkpoint"]
                    },
                    "world_config": {
                        "type": "object",
                        "description": "Configuration for creating a new world",
                        "properties": {
                            "type": {"type": "string", "description": "World type: ecosystem, city, game, social, physical"},
                            "size": {"type": "object", "properties": {"x": {"type": "number"}, "y": {"type": "number"}, "z": {"type": "number"}}},
                            "rules": {"type": "array", "items": {"type": "object"}},
                            "entities": {"type": "array", "items": {"type": "object"}}
                        }
                    },
                    "frame_id": {
                        "type": "string",
                        "description": "ID of frame to load or manipulate"
                    },
                    "steps": {
                        "type": "integer",
                        "description": "Number of frames to advance or rewind"
                    },
                    "ai_prompt": {
                        "type": "string",
                        "description": "AI prompt to influence non-deterministic entities"
                    },
                    "entity_id": {
                        "type": "string",
                        "description": "ID of entity to modify or query"
                    },
                    "modifications": {
                        "type": "object",
                        "description": "Changes to apply to entity or world"
                    },
                    "interaction": {
                        "type": "object",
                        "description": "Interaction between entities",
                        "properties": {
                            "source_entity": {"type": "string"},
                            "target_entity": {"type": "string"},
                            "action_type": {"type": "string"}
                        }
                    },
                    "query": {
                        "type": "string",
                        "description": "Query about current state"
                    },
                    "prediction_depth": {
                        "type": "integer",
                        "description": "How many frames ahead to predict"
                    }
                },
                "required": ["action"]
            }
        }
        
        # Initialize frame storage
        self.current_frame = None
        self.frame_history = []
        self.frame_future = []  # For storing predicted frames
        self.checkpoints = {}
        self.world_rules = {}
        self.entity_behaviors = {}
        
        super().__init__(name=self.name, metadata=self.metadata)
    
    def perform(self, **kwargs):
        action = kwargs.get('action')
        
        try:
            if action == 'create_world':
                world_config = kwargs.get('world_config', {})
                return self.create_world(world_config)
            
            elif action == 'advance_frame':
                steps = kwargs.get('steps', 1)
                ai_prompt = kwargs.get('ai_prompt', '')
                return self.advance_frame(steps, ai_prompt)
            
            elif action == 'rewind_frame':
                steps = kwargs.get('steps', 1)
                return self.rewind_frame(steps)
            
            elif action == 'query_state':
                query = kwargs.get('query', '')
                return self.query_state(query)
            
            elif action == 'modify_entity':
                entity_id = kwargs.get('entity_id')
                modifications = kwargs.get('modifications', {})
                return self.modify_entity(entity_id, modifications)
            
            elif action == 'add_entity':
                entity_config = kwargs.get('entity_config', {})
                return self.add_entity(entity_config)
            
            elif action == 'interact':
                interaction = kwargs.get('interaction', {})
                return self.process_interaction(interaction)
            
            elif action == 'get_history':
                depth = kwargs.get('depth', 10)
                return self.get_history(depth)
            
            elif action == 'analyze_frame':
                return self.analyze_current_frame()
            
            elif action == 'predict_future':
                depth = kwargs.get('prediction_depth', 5)
                ai_prompt = kwargs.get('ai_prompt', '')
                return self.predict_future(depth, ai_prompt)
            
            elif action == 'save_checkpoint':
                checkpoint_name = kwargs.get('checkpoint_name', f'checkpoint_{len(self.checkpoints)}')
                return self.save_checkpoint(checkpoint_name)
            
            elif action == 'load_checkpoint':
                checkpoint_name = kwargs.get('checkpoint_name')
                return self.load_checkpoint(checkpoint_name)
            
            else:
                return json.dumps({
                    "success": False,
                    "error": f"Unknown action: {action}"
                })
                
        except Exception as e:
            logging.error(f"Error in FrameSimulation: {str(e)}")
            return json.dumps({
                "success": False,
                "error": str(e)
            })
    
    def create_world(self, config: Dict) -> str:
        """Create a new simulated world with initial frame"""
        world_type = config.get('type', 'ecosystem')
        
        # Create example ecosystem world if no specific config
        if world_type == 'ecosystem':
            frame = self._create_ecosystem_world()
        elif world_type == 'city':
            frame = self._create_city_world()
        elif world_type == 'game':
            frame = self._create_game_world()
        else:
            frame = self._create_custom_world(config)
        
        self.current_frame = frame
        self.frame_history = []
        
        return json.dumps({
            "success": True,
            "frame_id": frame['id'],
            "world_type": world_type,
            "entities": len(frame['entities']),
            "rules": len(frame['rules']),
            "initial_state": self._get_frame_summary(frame)
        }, indent=2)
    
    def _create_ecosystem_world(self) -> Dict:
        """Create a simple ecosystem simulation"""
        frame = {
            "id": self._generate_frame_id(),
            "timestamp": datetime.now().isoformat(),
            "frame_number": 0,
            "world_type": "ecosystem",
            "environment": {
                "size": {"x": 100, "y": 100, "z": 1},
                "time_of_day": 12.0,  # 24-hour cycle
                "temperature": 20.0,  # Celsius
                "weather": "sunny",
                "resources": {
                    "water": 1000,
                    "food": 500,
                    "shelter_spots": 20
                }
            },
            "entities": [],
            "rules": [
                {
                    "id": "day_night_cycle",
                    "type": "deterministic",
                    "description": "Time advances 0.5 hours per frame",
                    "formula": "time_of_day = (time_of_day + 0.5) % 24"
                },
                {
                    "id": "temperature_cycle",
                    "type": "deterministic",
                    "description": "Temperature varies with time of day",
                    "formula": "temp = 20 + 10 * sin((time_of_day - 6) * pi / 12)"
                },
                {
                    "id": "resource_regeneration",
                    "type": "deterministic",
                    "description": "Resources regenerate slowly",
                    "rates": {
                        "water": 10,  # per frame
                        "food": 5     # per frame
                    }
                },
                {
                    "id": "entity_interaction",
                    "type": "mixed",
                    "description": "Entities interact based on proximity and needs"
                }
            ],
            "global_state": {
                "total_energy": 10000,
                "entropy": 0.1,
                "stability": 0.9
            },
            "history": [],
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "version": "1.0",
                "seed": random.randint(0, 1000000)
            }
        }
        
        # Add initial entities
        # Deterministic entities (plants)
        for i in range(10):
            plant = {
                "id": f"plant_{i}",
                "type": "plant",
                "behavior": "deterministic",
                "position": {"x": random.uniform(0, 100), "y": random.uniform(0, 100), "z": 0},
                "properties": {
                    "energy": 100,
                    "growth_rate": 1.5,
                    "max_energy": 200,
                    "produces_food": 2  # per frame
                },
                "state": "growing",
                "age": 0
            }
            frame['entities'].append(plant)
        
        # Non-deterministic entities (animals with AI-driven behavior)
        for i in range(5):
            animal = {
                "id": f"animal_{i}",
                "type": "animal",
                "behavior": "ai_driven",
                "position": {"x": random.uniform(0, 100), "y": random.uniform(0, 100), "z": 0},
                "velocity": {"x": 0, "y": 0, "z": 0},
                "properties": {
                    "energy": 80,
                    "hunger": 30,
                    "thirst": 20,
                    "fear": 0,
                    "aggression": random.uniform(0, 0.5),
                    "social": random.uniform(0.3, 0.8),
                    "speed": 2.0,
                    "vision_range": 15
                },
                "state": "idle",
                "memory": {
                    "last_food_location": None,
                    "last_water_location": None,
                    "friends": [],
                    "threats": []
                },
                "goals": ["survive", "find_food", "find_water"],
                "age": 0,
                "generation": 0
            }
            frame['entities'].append(animal)
        
        # Mixed behavior entity (weather system)
        weather_system = {
            "id": "weather_system",
            "type": "environmental",
            "behavior": "mixed",
            "properties": {
                "cloud_coverage": 0.2,
                "wind_speed": 5,
                "wind_direction": 180,
                "precipitation": 0,
                "pressure": 1013
            },
            "rules": {
                "deterministic": ["pressure_changes", "wind_patterns"],
                "ai_influenced": ["storm_formation", "seasonal_patterns"]
            }
        }
        frame['entities'].append(weather_system)
        
        return frame
    
    def _create_city_world(self) -> Dict:
        """Create a simple city simulation"""
        frame = {
            "id": self._generate_frame_id(),
            "timestamp": datetime.now().isoformat(),
            "frame_number": 0,
            "world_type": "city",
            "environment": {
                "size": {"x": 500, "y": 500, "z": 100},
                "time_of_day": 8.0,
                "population": 1000,
                "economy": {
                    "gdp": 1000000,
                    "unemployment": 0.05,
                    "inflation": 0.02
                },
                "infrastructure": {
                    "roads": 100,
                    "buildings": 50,
                    "utilities": 0.95
                }
            },
            "entities": [],
            "rules": [],
            "global_state": {
                "happiness": 0.7,
                "safety": 0.8,
                "efficiency": 0.6
            },
            "history": [],
            "metadata": {
                "created_at": datetime.now().isoformat()
            }
        }
        
        # Add city-specific entities
        # Traffic lights (deterministic)
        for i in range(10):
            traffic_light = {
                "id": f"traffic_light_{i}",
                "type": "infrastructure",
                "behavior": "deterministic",
                "position": {"x": i * 50, "y": i * 50, "z": 0},
                "state": ["red", "yellow", "green"][i % 3],
                "cycle_time": 60,
                "current_time": 0
            }
            frame['entities'].append(traffic_light)
        
        # Citizens (AI-driven)
        for i in range(20):
            citizen = {
                "id": f"citizen_{i}",
                "type": "person",
                "behavior": "ai_driven",
                "position": {"x": random.uniform(0, 500), "y": random.uniform(0, 500), "z": 0},
                "properties": {
                    "wealth": random.uniform(1000, 100000),
                    "happiness": random.uniform(0.4, 0.9),
                    "employment": random.choice(["employed", "unemployed", "student", "retired"]),
                    "needs": {
                        "housing": random.uniform(0.5, 1.0),
                        "food": random.uniform(0.6, 1.0),
                        "entertainment": random.uniform(0.3, 0.8)
                    }
                },
                "daily_routine": [],
                "relationships": []
            }
            frame['entities'].append(citizen)
        
        return frame
    
    def _create_game_world(self) -> Dict:
        """Create a simple game world simulation"""
        frame = {
            "id": self._generate_frame_id(),
            "timestamp": datetime.now().isoformat(),
            "frame_number": 0,
            "world_type": "game",
            "environment": {
                "size": {"x": 200, "y": 200, "z": 50},
                "level": 1,
                "difficulty": "normal",
                "score": 0
            },
            "entities": [],
            "rules": [
                {
                    "id": "gravity",
                    "type": "deterministic",
                    "acceleration": -9.8
                },
                {
                    "id": "collision",
                    "type": "deterministic",
                    "elasticity": 0.8
                },
                {
                    "id": "scoring",
                    "type": "mixed",
                    "points_per_action": {"collect": 10, "defeat": 50, "complete": 100}
                }
            ],
            "global_state": {
                "game_time": 0,
                "active_quests": [],
                "unlocked_abilities": []
            },
            "history": [],
            "metadata": {
                "created_at": datetime.now().isoformat()
            }
        }
        
        # Add game entities
        # Player (AI-influenced)
        player = {
            "id": "player_1",
            "type": "player",
            "behavior": "ai_influenced",
            "position": {"x": 100, "y": 100, "z": 0},
            "velocity": {"x": 0, "y": 0, "z": 0},
            "properties": {
                "health": 100,
                "mana": 50,
                "stamina": 100,
                "level": 1,
                "experience": 0,
                "inventory": []
            },
            "abilities": ["move", "jump", "attack"],
            "state": "idle"
        }
        frame['entities'].append(player)
        
        # NPCs (mixed behavior)
        for i in range(5):
            npc = {
                "id": f"npc_{i}",
                "type": "npc",
                "behavior": "mixed",
                "position": {"x": random.uniform(0, 200), "y": random.uniform(0, 200), "z": 0},
                "properties": {
                    "health": 50,
                    "friendly": random.choice([True, False]),
                    "patrol_route": [],
                    "dialogue_tree": {}
                },
                "ai_personality": {
                    "helpful": random.uniform(0, 1),
                    "aggressive": random.uniform(0, 0.5),
                    "curious": random.uniform(0.3, 0.8)
                }
            }
            frame['entities'].append(npc)
        
        return frame
    
    def _create_custom_world(self, config: Dict) -> Dict:
        """Create a custom world from config"""
        frame = {
            "id": self._generate_frame_id(),
            "timestamp": datetime.now().isoformat(),
            "frame_number": 0,
            "world_type": "custom",
            "environment": config.get('environment', {}),
            "entities": config.get('entities', []),
            "rules": config.get('rules', []),
            "global_state": config.get('global_state', {}),
            "history": [],
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "config": config
            }
        }
        return frame
    
    def advance_frame(self, steps: int, ai_prompt: str = '') -> str:
        """Advance the simulation by n frames"""
        if not self.current_frame:
            return json.dumps({
                "success": False,
                "error": "No world loaded"
            })
        
        results = []
        for step in range(steps):
            # Store current frame in history
            self.frame_history.append(deepcopy(self.current_frame))
            
            # Create new frame
            new_frame = deepcopy(self.current_frame)
            new_frame['id'] = self._generate_frame_id()
            new_frame['timestamp'] = datetime.now().isoformat()
            new_frame['frame_number'] += 1
            
            # Apply deterministic rules
            changes_deterministic = self._apply_deterministic_rules(new_frame)
            
            # Apply AI-driven changes
            changes_ai = self._apply_ai_behavior(new_frame, ai_prompt)
            
            # Process interactions
            interactions = self._process_entity_interactions(new_frame)
            
            # Update global state
            self._update_global_state(new_frame)
            
            # Record reasoning
            frame_reasoning = {
                "frame": new_frame['frame_number'],
                "deterministic_changes": changes_deterministic,
                "ai_changes": changes_ai,
                "interactions": interactions,
                "ai_prompt_influence": ai_prompt if ai_prompt else "none"
            }
            
            new_frame['history'].append(frame_reasoning)
            
            # Limit history size
            if len(new_frame['history']) > 100:
                new_frame['history'] = new_frame['history'][-100:]
            
            self.current_frame = new_frame
            
            results.append({
                "frame": new_frame['frame_number'],
                "changes": len(changes_deterministic) + len(changes_ai),
                "interactions": len(interactions)
            })
        
        return json.dumps({
            "success": True,
            "frames_advanced": steps,
            "current_frame": self.current_frame['frame_number'],
            "results": results,
            "current_state": self._get_frame_summary(self.current_frame)
        }, indent=2)
    
    def _apply_deterministic_rules(self, frame: Dict) -> List[Dict]:
        """Apply deterministic rules to the frame"""
        changes = []
        
        if frame['world_type'] == 'ecosystem':
            # Day/night cycle
            frame['environment']['time_of_day'] = (frame['environment']['time_of_day'] + 0.5) % 24
            changes.append({
                "type": "environment",
                "rule": "day_night_cycle",
                "change": f"Time advanced to {frame['environment']['time_of_day']:.1f}"
            })
            
            # Temperature cycle
            time = frame['environment']['time_of_day']
            frame['environment']['temperature'] = 20 + 10 * math.sin((time - 6) * math.pi / 12)
            changes.append({
                "type": "environment",
                "rule": "temperature_cycle",
                "change": f"Temperature adjusted to {frame['environment']['temperature']:.1f}°C"
            })
            
            # Resource regeneration
            frame['environment']['resources']['water'] = min(1500, frame['environment']['resources']['water'] + 10)
            frame['environment']['resources']['food'] = min(1000, frame['environment']['resources']['food'] + 5)
            changes.append({
                "type": "resources",
                "rule": "regeneration",
                "change": "Resources regenerated"
            })
            
            # Plant growth
            for entity in frame['entities']:
                if entity['type'] == 'plant' and entity['behavior'] == 'deterministic':
                    entity['properties']['energy'] = min(
                        entity['properties']['max_energy'],
                        entity['properties']['energy'] * entity['properties']['growth_rate']
                    )
                    entity['age'] += 1
                    changes.append({
                        "type": "entity",
                        "entity_id": entity['id'],
                        "rule": "growth",
                        "change": f"Energy increased to {entity['properties']['energy']:.1f}"
                    })
        
        elif frame['world_type'] == 'city':
            # Traffic light cycles
            for entity in frame['entities']:
                if entity['type'] == 'infrastructure' and 'traffic_light' in entity['id']:
                    entity['current_time'] = (entity['current_time'] + 1) % entity['cycle_time']
                    if entity['current_time'] == 0:
                        states = ["red", "yellow", "green"]
                        current_idx = states.index(entity['state'])
                        entity['state'] = states[(current_idx + 1) % 3]
                        changes.append({
                            "type": "infrastructure",
                            "entity_id": entity['id'],
                            "change": f"Changed to {entity['state']}"
                        })
        
        elif frame['world_type'] == 'game':
            # Apply gravity
            for entity in frame['entities']:
                if 'velocity' in entity and entity.get('position', {}).get('z', 0) > 0:
                    entity['velocity']['z'] -= 9.8 / 60  # Assuming 60 FPS
                    entity['position']['z'] = max(0, entity['position']['z'] + entity['velocity']['z'])
                    if entity['position']['z'] == 0:
                        entity['velocity']['z'] = 0
                    changes.append({
                        "type": "physics",
                        "entity_id": entity['id'],
                        "rule": "gravity",
                        "change": "Applied gravity"
                    })
        
        return changes
    
    def _apply_ai_behavior(self, frame: Dict, ai_prompt: str) -> List[Dict]:
        """Apply AI-driven behavior to entities"""
        changes = []
        
        for entity in frame['entities']:
            if entity['behavior'] in ['ai_driven', 'ai_influenced', 'mixed']:
                if frame['world_type'] == 'ecosystem' and entity['type'] == 'animal':
                    # AI-driven animal behavior
                    decision = self._make_ai_decision_animal(entity, frame, ai_prompt)
                    if decision:
                        self._apply_decision(entity, decision)
                        changes.append({
                            "type": "ai_decision",
                            "entity_id": entity['id'],
                            "decision": decision['action'],
                            "reasoning": decision.get('reasoning', 'instinctive')
                        })
                
                elif frame['world_type'] == 'city' and entity['type'] == 'person':
                    # AI-driven citizen behavior
                    decision = self._make_ai_decision_citizen(entity, frame, ai_prompt)
                    if decision:
                        self._apply_decision(entity, decision)
                        changes.append({
                            "type": "ai_decision",
                            "entity_id": entity['id'],
                            "decision": decision['action'],
                            "reasoning": decision.get('reasoning', 'personal choice')
                        })
                
                elif frame['world_type'] == 'game' and entity['type'] in ['player', 'npc']:
                    # AI-influenced game character behavior
                    decision = self._make_ai_decision_game(entity, frame, ai_prompt)
                    if decision:
                        self._apply_decision(entity, decision)
                        changes.append({
                            "type": "ai_decision",
                            "entity_id": entity['id'],
                            "decision": decision['action'],
                            "reasoning": decision.get('reasoning', 'tactical')
                        })
        
        return changes
    
    def _make_ai_decision_animal(self, entity: Dict, frame: Dict, ai_prompt: str) -> Optional[Dict]:
        """Make AI decision for animal entity"""
        # Simplified AI decision making
        # In production, this would call the actual AI model
        
        needs = []
        if entity['properties']['hunger'] > 50:
            needs.append('food')
        if entity['properties']['thirst'] > 40:
            needs.append('water')
        if entity['properties']['energy'] < 30:
            needs.append('rest')
        
        # Check for threats
        for other in frame['entities']:
            if other['id'] != entity['id'] and other['type'] == 'animal':
                distance = self._calculate_distance(entity['position'], other['position'])
                if distance < entity['properties']['vision_range']:
                    if other['properties'].get('aggression', 0) > 0.7:
                        needs.append('escape')
                        break
        
        # Make decision based on needs and AI prompt
        if 'escape' in needs:
            return {
                'action': 'flee',
                'target': self._find_safe_location(entity, frame),
                'reasoning': 'Detected threat nearby'
            }
        elif 'food' in needs:
            return {
                'action': 'seek_food',
                'target': self._find_food_source(entity, frame),
                'reasoning': 'Hungry, seeking food'
            }
        elif 'water' in needs:
            return {
                'action': 'seek_water',
                'target': {'x': 50, 'y': 50},  # Assuming water at center
                'reasoning': 'Thirsty, seeking water'
            }
        elif 'rest' in needs:
            return {
                'action': 'rest',
                'reasoning': 'Low energy, resting'
            }
        else:
            # Explore or socialize
            if random.random() < entity['properties']['social']:
                return {
                    'action': 'socialize',
                    'target': self._find_nearest_friendly(entity, frame),
                    'reasoning': 'No immediate needs, socializing'
                }
            else:
                return {
                    'action': 'explore',
                    'target': self._random_nearby_location(entity),
                    'reasoning': 'Exploring territory'
                }
    
    def _make_ai_decision_citizen(self, entity: Dict, frame: Dict, ai_prompt: str) -> Optional[Dict]:
        """Make AI decision for citizen entity"""
        hour = frame['environment']['time_of_day']
        
        # Simple daily routine based on time
        if 6 <= hour < 9:
            return {
                'action': 'commute',
                'destination': 'work',
                'reasoning': 'Morning commute'
            }
        elif 9 <= hour < 17:
            if entity['properties']['employment'] == 'employed':
                return {
                    'action': 'work',
                    'productivity': entity['properties']['happiness'] * 0.8,
                    'reasoning': 'Working hours'
                }
            else:
                return {
                    'action': 'seek_employment',
                    'reasoning': 'Looking for job opportunities'
                }
        elif 17 <= hour < 20:
            if entity['properties']['needs']['entertainment'] < 0.5:
                return {
                    'action': 'entertainment',
                    'reasoning': 'Seeking entertainment after work'
                }
            else:
                return {
                    'action': 'shopping',
                    'reasoning': 'Shopping for necessities'
                }
        else:
            return {
                'action': 'rest_at_home',
                'reasoning': 'Evening rest'
            }
    
    def _make_ai_decision_game(self, entity: Dict, frame: Dict, ai_prompt: str) -> Optional[Dict]:
        """Make AI decision for game entity"""
        if entity['type'] == 'player' and ai_prompt:
            # Let AI prompt influence player decisions
            if 'aggressive' in ai_prompt.lower():
                return {
                    'action': 'attack',
                    'target': self._find_nearest_enemy(entity, frame),
                    'reasoning': 'AI prompt suggests aggressive play'
                }
            elif 'defensive' in ai_prompt.lower():
                return {
                    'action': 'defend',
                    'reasoning': 'AI prompt suggests defensive play'
                }
            elif 'explore' in ai_prompt.lower():
                return {
                    'action': 'explore',
                    'target': self._find_unexplored_area(entity, frame),
                    'reasoning': 'AI prompt suggests exploration'
                }
        
        # Default NPC behavior
        if entity['type'] == 'npc':
            if entity['properties'].get('friendly', True):
                return {
                    'action': 'patrol',
                    'reasoning': 'Routine patrol'
                }
            else:
                return {
                    'action': 'guard',
                    'position': entity['position'],
                    'reasoning': 'Guarding territory'
                }
        
        return None
    
    def _apply_decision(self, entity: Dict, decision: Dict):
        """Apply a decision to an entity"""
        if decision['action'] == 'flee':
            # Move away from threat
            if 'target' in decision and decision['target']:
                direction = self._calculate_direction(entity['position'], decision['target'])
                entity['velocity'] = {
                    'x': direction['x'] * entity['properties'].get('speed', 2),
                    'y': direction['y'] * entity['properties'].get('speed', 2),
                    'z': 0
                }
                entity['state'] = 'fleeing'
        
        elif decision['action'] in ['seek_food', 'seek_water', 'explore']:
            if 'target' in decision and decision['target']:
                direction = self._calculate_direction(entity['position'], decision['target'])
                entity['velocity'] = {
                    'x': direction['x'] * entity['properties'].get('speed', 1),
                    'y': direction['y'] * entity['properties'].get('speed', 1),
                    'z': 0
                }
                entity['state'] = decision['action']
        
        elif decision['action'] == 'rest':
            entity['velocity'] = {'x': 0, 'y': 0, 'z': 0}
            entity['state'] = 'resting'
            entity['properties']['energy'] = min(100, entity['properties']['energy'] + 5)
        
        elif decision['action'] == 'work':
            if 'productivity' in decision:
                entity['properties']['wealth'] += decision['productivity'] * 10
        
        # Update position based on velocity
        if 'velocity' in entity and 'position' in entity:
            entity['position']['x'] += entity['velocity']['x']
            entity['position']['y'] += entity['velocity']['y']
            entity['position']['z'] = entity['position'].get('z', 0) + entity['velocity'].get('z', 0)
            
            # Keep within bounds (simple boundary check)
            entity['position']['x'] = max(0, min(100, entity['position']['x']))
            entity['position']['y'] = max(0, min(100, entity['position']['y']))
            entity['position']['z'] = max(0, entity['position']['z'])
    
    def _process_entity_interactions(self, frame: Dict) -> List[Dict]:
        """Process interactions between entities"""
        interactions = []
        
        # Check all entity pairs for potential interactions
        entities = frame['entities']
        for i, entity1 in enumerate(entities):
            for entity2 in entities[i+1:]:
                if self._can_interact(entity1, entity2):
                    distance = self._calculate_distance(
                        entity1.get('position', {}),
                        entity2.get('position', {})
                    )
                    
                    if distance < 5:  # Interaction range
                        interaction = self._determine_interaction(entity1, entity2, frame)
                        if interaction:
                            self._execute_interaction(entity1, entity2, interaction, frame)
                            interactions.append({
                                "entities": [entity1['id'], entity2['id']],
                                "type": interaction['type'],
                                "result": interaction.get('result', 'completed')
                            })
        
        return interactions
    
    def _can_interact(self, entity1: Dict, entity2: Dict) -> bool:
        """Check if two entities can interact"""
        # Simple check - entities of certain types can interact
        interactive_types = ['animal', 'person', 'player', 'npc']
        return (entity1.get('type') in interactive_types or 
                entity2.get('type') in interactive_types)
    
    def _determine_interaction(self, entity1: Dict, entity2: Dict, frame: Dict) -> Optional[Dict]:
        """Determine the type of interaction between entities"""
        if frame['world_type'] == 'ecosystem':
            if entity1['type'] == 'animal' and entity2['type'] == 'animal':
                # Animals can socialize, compete, or avoid
                agg1 = entity1['properties'].get('aggression', 0)
                agg2 = entity2['properties'].get('aggression', 0)
                
                if agg1 > 0.7 or agg2 > 0.7:
                    return {'type': 'compete', 'resource': 'territory'}
                elif entity1['properties'].get('social', 0) > 0.5:
                    return {'type': 'socialize'}
            
            elif entity1['type'] == 'animal' and entity2['type'] == 'plant':
                if entity1['properties'].get('hunger', 0) > 30:
                    return {'type': 'consume', 'resource': 'food'}
        
        elif frame['world_type'] == 'city':
            if entity1['type'] == 'person' and entity2['type'] == 'person':
                return {'type': 'social_interaction', 'nature': 'casual'}
        
        elif frame['world_type'] == 'game':
            if 'player' in entity1['type'] and entity2.get('properties', {}).get('friendly', True):
                return {'type': 'dialogue'}
            elif 'player' in entity1['type'] and not entity2.get('properties', {}).get('friendly', True):
                return {'type': 'combat'}
        
        return None
    
    def _execute_interaction(self, entity1: Dict, entity2: Dict, interaction: Dict, frame: Dict):
        """Execute an interaction between entities"""
        if interaction['type'] == 'consume':
            # Entity1 consumes resources from entity2
            if entity2['type'] == 'plant':
                food_produced = entity2['properties'].get('produces_food', 0)
                entity1['properties']['hunger'] = max(0, entity1['properties']['hunger'] - food_produced * 10)
                entity2['properties']['energy'] *= 0.9  # Plant loses some energy
        
        elif interaction['type'] == 'socialize':
            # Entities form social bonds
            if 'memory' in entity1:
                if 'friends' not in entity1['memory']:
                    entity1['memory']['friends'] = []
                if entity2['id'] not in entity1['memory']['friends']:
                    entity1['memory']['friends'].append(entity2['id'])
            
            if 'memory' in entity2:
                if 'friends' not in entity2['memory']:
                    entity2['memory']['friends'] = []
                if entity1['id'] not in entity2['memory']['friends']:
                    entity2['memory']['friends'].append(entity1['id'])
        
        elif interaction['type'] == 'compete':
            # Competition for resources
            strength1 = entity1['properties'].get('energy', 50) * (1 + entity1['properties'].get('aggression', 0))
            strength2 = entity2['properties'].get('energy', 50) * (1 + entity2['properties'].get('aggression', 0))
            
            if strength1 > strength2:
                entity2['properties']['fear'] = min(1.0, entity2['properties'].get('fear', 0) + 0.2)
                interaction['result'] = f"{entity1['id']} dominated"
            else:
                entity1['properties']['fear'] = min(1.0, entity1['properties'].get('fear', 0) + 0.2)
                interaction['result'] = f"{entity2['id']} dominated"
    
    def _update_global_state(self, frame: Dict):
        """Update global state based on current conditions"""
        if frame['world_type'] == 'ecosystem':
            # Calculate ecosystem health
            total_energy = sum(e['properties'].get('energy', 0) for e in frame['entities'])
            frame['global_state']['total_energy'] = total_energy
            
            # Calculate diversity (simplified)
            entity_types = set(e['type'] for e in frame['entities'])
            frame['global_state']['entropy'] = len(entity_types) / 10  # Normalized
            
            # Calculate stability
            avg_fear = sum(e['properties'].get('fear', 0) for e in frame['entities'] 
                          if e['type'] == 'animal') / max(1, len([e for e in frame['entities'] 
                                                                  if e['type'] == 'animal']))
            frame['global_state']['stability'] = 1.0 - avg_fear
        
        elif frame['world_type'] == 'city':
            # Calculate city metrics
            citizens = [e for e in frame['entities'] if e['type'] == 'person']
            if citizens:
                avg_happiness = sum(c['properties'].get('happiness', 0.5) for c in citizens) / len(citizens)
                frame['global_state']['happiness'] = avg_happiness
                
                employed = len([c for c in citizens if c['properties'].get('employment') == 'employed'])
                frame['environment']['economy']['unemployment'] = 1.0 - (employed / len(citizens))
        
        elif frame['world_type'] == 'game':
            # Update game time
            frame['global_state']['game_time'] += 1
    
    def rewind_frame(self, steps: int) -> str:
        """Rewind the simulation by n frames"""
        if not self.frame_history:
            return json.dumps({
                "success": False,
                "error": "No history to rewind"
            })
        
        rewound = 0
        for _ in range(min(steps, len(self.frame_history))):
            # Store current frame in future (for potential forward movement)
            self.frame_future.insert(0, self.current_frame)
            # Restore previous frame
            self.current_frame = self.frame_history.pop()
            rewound += 1
        
        return json.dumps({
            "success": True,
            "frames_rewound": rewound,
            "current_frame": self.current_frame['frame_number'],
            "history_remaining": len(self.frame_history),
            "future_available": len(self.frame_future),
            "current_state": self._get_frame_summary(self.current_frame)
        }, indent=2)
    
    def query_state(self, query: str) -> str:
        """Query information about current state"""
        if not self.current_frame:
            return json.dumps({
                "success": False,
                "error": "No world loaded"
            })
        
        # Simple query processor
        result = {
            "success": True,
            "query": query,
            "frame": self.current_frame['frame_number'],
            "results": {}
        }
        
        query_lower = query.lower()
        
        if 'count' in query_lower:
            if 'entities' in query_lower:
                result['results']['entity_count'] = len(self.current_frame['entities'])
            if 'animals' in query_lower:
                result['results']['animal_count'] = len([e for e in self.current_frame['entities'] 
                                                         if e['type'] == 'animal'])
            if 'plants' in query_lower:
                result['results']['plant_count'] = len([e for e in self.current_frame['entities'] 
                                                       if e['type'] == 'plant'])
        
        if 'average' in query_lower or 'avg' in query_lower:
            if 'energy' in query_lower:
                energies = [e['properties'].get('energy', 0) for e in self.current_frame['entities']]
                result['results']['average_energy'] = sum(energies) / len(energies) if energies else 0
            
            if 'happiness' in query_lower:
                happiness_values = [e['properties'].get('happiness', 0) for e in self.current_frame['entities'] 
                                   if 'happiness' in e.get('properties', {})]
                result['results']['average_happiness'] = sum(happiness_values) / len(happiness_values) if happiness_values else 0
        
        if 'find' in query_lower or 'locate' in query_lower:
            if 'hungry' in query_lower:
                hungry = [e['id'] for e in self.current_frame['entities'] 
                         if e.get('properties', {}).get('hunger', 0) > 50]
                result['results']['hungry_entities'] = hungry
            
            if 'low energy' in query_lower:
                low_energy = [e['id'] for e in self.current_frame['entities'] 
                             if e.get('properties', {}).get('energy', 100) < 30]
                result['results']['low_energy_entities'] = low_energy
        
        if 'environment' in query_lower:
            result['results']['environment'] = self.current_frame['environment']
        
        if 'global' in query_lower:
            result['results']['global_state'] = self.current_frame['global_state']
        
        return json.dumps(result, indent=2)
    
    def modify_entity(self, entity_id: str, modifications: Dict) -> str:
        """Modify an entity's properties"""
        if not self.current_frame:
            return json.dumps({
                "success": False,
                "error": "No world loaded"
            })
        
        entity = None
        for e in self.current_frame['entities']:
            if e['id'] == entity_id:
                entity = e
                break
        
        if not entity:
            return json.dumps({
                "success": False,
                "error": f"Entity {entity_id} not found"
            })
        
        # Apply modifications
        for key, value in modifications.items():
            if key in entity:
                if isinstance(entity[key], dict) and isinstance(value, dict):
                    entity[key].update(value)
                else:
                    entity[key] = value
            elif 'properties' in entity and key in entity['properties']:
                entity['properties'][key] = value
        
        return json.dumps({
            "success": True,
            "entity_id": entity_id,
            "modifications": modifications,
            "updated_entity": entity
        }, indent=2)
    
    def add_entity(self, entity_config: Dict) -> str:
        """Add a new entity to the world"""
        if not self.current_frame:
            return json.dumps({
                "success": False,
                "error": "No world loaded"
            })
        
        # Generate ID if not provided
        if 'id' not in entity_config:
            entity_type = entity_config.get('type', 'entity')
            entity_count = len([e for e in self.current_frame['entities'] 
                               if entity_type in e.get('type', '')])
            entity_config['id'] = f"{entity_type}_{entity_count + 1}"
        
        # Set default position if not provided
        if 'position' not in entity_config:
            entity_config['position'] = {
                'x': random.uniform(0, self.current_frame['environment'].get('size', {}).get('x', 100)),
                'y': random.uniform(0, self.current_frame['environment'].get('size', {}).get('y', 100)),
                'z': 0
            }
        
        # Add entity
        self.current_frame['entities'].append(entity_config)
        
        return json.dumps({
            "success": True,
            "entity_id": entity_config['id'],
            "entity": entity_config,
            "total_entities": len(self.current_frame['entities'])
        }, indent=2)
    
    def process_interaction(self, interaction: Dict) -> str:
        """Process a specific interaction between entities"""
        if not self.current_frame:
            return json.dumps({
                "success": False,
                "error": "No world loaded"
            })
        
        source_id = interaction.get('source_entity')
        target_id = interaction.get('target_entity')
        action_type = interaction.get('action_type')
        
        source = None
        target = None
        
        for e in self.current_frame['entities']:
            if e['id'] == source_id:
                source = e
            if e['id'] == target_id:
                target = e
        
        if not source or not target:
            return json.dumps({
                "success": False,
                "error": "Source or target entity not found"
            })
        
        # Process the interaction
        interaction_detail = {
            'type': action_type,
            'custom': True
        }
        
        self._execute_interaction(source, target, interaction_detail, self.current_frame)
        
        return json.dumps({
            "success": True,
            "interaction": {
                "source": source_id,
                "target": target_id,
                "type": action_type
            },
            "source_state": source,
            "target_state": target
        }, indent=2)
    
    def get_history(self, depth: int = 10) -> str:
        """Get frame history with reasoning"""
        if not self.current_frame:
            return json.dumps({
                "success": False,
                "error": "No world loaded"
            })
        
        history = []
        
        # Get recent frames from history
        recent_frames = self.frame_history[-depth:] if len(self.frame_history) > depth else self.frame_history
        
        for frame in recent_frames:
            frame_summary = {
                "frame_number": frame['frame_number'],
                "timestamp": frame['timestamp'],
                "entity_count": len(frame['entities']),
                "global_state": frame['global_state'],
                "reasoning": frame['history'][-1] if frame.get('history') else None
            }
            history.append(frame_summary)
        
        # Add current frame
        current_summary = {
            "frame_number": self.current_frame['frame_number'],
            "timestamp": self.current_frame['timestamp'],
            "entity_count": len(self.current_frame['entities']),
            "global_state": self.current_frame['global_state'],
            "reasoning": self.current_frame['history'][-1] if self.current_frame.get('history') else None,
            "is_current": True
        }
        history.append(current_summary)
        
        return json.dumps({
            "success": True,
            "history_depth": len(history),
            "frames": history
        }, indent=2)
    
    def analyze_current_frame(self) -> str:
        """Analyze the current frame for patterns and insights"""
        if not self.current_frame:
            return json.dumps({
                "success": False,
                "error": "No world loaded"
            })
        
        analysis = {
            "frame_number": self.current_frame['frame_number'],
            "world_type": self.current_frame['world_type'],
            "statistics": {},
            "patterns": {},
            "predictions": {},
            "anomalies": []
        }
        
        # Entity statistics
        entities = self.current_frame['entities']
        analysis['statistics']['total_entities'] = len(entities)
        
        # Group by type
        entity_types = {}
        for e in entities:
            e_type = e.get('type', 'unknown')
            if e_type not in entity_types:
                entity_types[e_type] = []
            entity_types[e_type].append(e)
        
        analysis['statistics']['entity_distribution'] = {k: len(v) for k, v in entity_types.items()}
        
        # Behavior analysis
        behavior_types = {}
        for e in entities:
            b_type = e.get('behavior', 'unknown')
            behavior_types[b_type] = behavior_types.get(b_type, 0) + 1
        
        analysis['statistics']['behavior_distribution'] = behavior_types
        
        # Pattern detection
        if self.current_frame['world_type'] == 'ecosystem':
            # Ecosystem patterns
            animals = [e for e in entities if e['type'] == 'animal']
            if animals:
                avg_hunger = sum(a['properties'].get('hunger', 0) for a in animals) / len(animals)
                avg_energy = sum(a['properties'].get('energy', 0) for a in animals) / len(animals)
                
                analysis['patterns']['resource_stress'] = avg_hunger > 60
                analysis['patterns']['population_health'] = 'good' if avg_energy > 60 else 'poor'
                
                # Predict population changes
                if avg_hunger > 70 and avg_energy < 40:
                    analysis['predictions']['population_trend'] = 'declining'
                elif avg_hunger < 30 and avg_energy > 70:
                    analysis['predictions']['population_trend'] = 'growing'
                else:
                    analysis['predictions']['population_trend'] = 'stable'
        
        # Detect anomalies
        for e in entities:
            anomalies = []
            
            # Check for out-of-bounds
            if 'position' in e:
                size = self.current_frame['environment'].get('size', {})
                if (e['position'].get('x', 0) < 0 or 
                    e['position'].get('x', 0) > size.get('x', 100) or
                    e['position'].get('y', 0) < 0 or 
                    e['position'].get('y', 0) > size.get('y', 100)):
                    anomalies.append(f"Entity {e['id']} is out of bounds")
            
            # Check for invalid states
            if 'properties' in e:
                if e['properties'].get('energy', 0) < 0:
                    anomalies.append(f"Entity {e['id']} has negative energy")
                if e['properties'].get('health', 100) > 200:
                    anomalies.append(f"Entity {e['id']} has abnormal health")
            
            analysis['anomalies'].extend(anomalies)
        
        return json.dumps(analysis, indent=2)
    
    def predict_future(self, depth: int, ai_prompt: str = '') -> str:
        """Predict future frames without actually advancing"""
        if not self.current_frame:
            return json.dumps({
                "success": False,
                "error": "No world loaded"
            })
        
        # Create a copy to simulate on
        simulated_frame = deepcopy(self.current_frame)
        predictions = []
        
        for i in range(depth):
            # Simulate next frame
            future_frame = deepcopy(simulated_frame)
            future_frame['frame_number'] += 1
            
            # Apply rules and behaviors
            det_changes = self._apply_deterministic_rules(future_frame)
            ai_changes = self._apply_ai_behavior(future_frame, ai_prompt)
            interactions = self._process_entity_interactions(future_frame)
            self._update_global_state(future_frame)
            
            prediction = {
                "frame": future_frame['frame_number'],
                "predicted_changes": {
                    "deterministic": len(det_changes),
                    "ai_driven": len(ai_changes),
                    "interactions": len(interactions)
                },
                "predicted_state": {
                    "entity_count": len(future_frame['entities']),
                    "global_state": future_frame['global_state'],
                    "environment": future_frame['environment']
                },
                "confidence": 1.0 - (i * 0.1)  # Confidence decreases with distance
            }
            
            predictions.append(prediction)
            simulated_frame = future_frame
        
        return json.dumps({
            "success": True,
            "current_frame": self.current_frame['frame_number'],
            "predictions": predictions
        }, indent=2)
    
    def save_checkpoint(self, name: str) -> str:
        """Save current frame as checkpoint"""
        if not self.current_frame:
            return json.dumps({
                "success": False,
                "error": "No world loaded"
            })
        
        self.checkpoints[name] = {
            "frame": deepcopy(self.current_frame),
            "history": deepcopy(self.frame_history[-10:]) if self.frame_history else [],
            "saved_at": datetime.now().isoformat()
        }
        
        return json.dumps({
            "success": True,
            "checkpoint_name": name,
            "frame_number": self.current_frame['frame_number'],
            "total_checkpoints": len(self.checkpoints)
        }, indent=2)
    
    def load_checkpoint(self, name: str) -> str:
        """Load a saved checkpoint"""
        if name not in self.checkpoints:
            return json.dumps({
                "success": False,
                "error": f"Checkpoint '{name}' not found",
                "available_checkpoints": list(self.checkpoints.keys())
            })
        
        checkpoint = self.checkpoints[name]
        self.current_frame = deepcopy(checkpoint['frame'])
        self.frame_history = deepcopy(checkpoint['history'])
        
        return json.dumps({
            "success": True,
            "checkpoint_name": name,
            "loaded_frame": self.current_frame['frame_number'],
            "saved_at": checkpoint['saved_at']
        }, indent=2)
    
    # Helper methods
    def _generate_frame_id(self) -> str:
        """Generate unique frame ID"""
        timestamp = datetime.now().isoformat()
        random_component = random.randint(0, 999999)
        return hashlib.md5(f"{timestamp}_{random_component}".encode()).hexdigest()[:12]
    
    def _get_frame_summary(self, frame: Dict) -> Dict:
        """Get summary of frame state"""
        return {
            "frame_number": frame['frame_number'],
            "world_type": frame['world_type'],
            "entity_count": len(frame['entities']),
            "entity_types": list(set(e.get('type', 'unknown') for e in frame['entities'])),
            "environment_snapshot": {
                k: v for k, v in frame['environment'].items() 
                if k in ['time_of_day', 'temperature', 'weather', 'population', 'level']
            },
            "global_metrics": frame['global_state']
        }
    
    def _calculate_distance(self, pos1: Dict, pos2: Dict) -> float:
        """Calculate Euclidean distance between two positions"""
        if not pos1 or not pos2:
            return float('inf')
        
        dx = pos1.get('x', 0) - pos2.get('x', 0)
        dy = pos1.get('y', 0) - pos2.get('y', 0)
        dz = pos1.get('z', 0) - pos2.get('z', 0)
        
        return math.sqrt(dx*dx + dy*dy + dz*dz)
    
    def _calculate_direction(self, from_pos: Dict, to_pos: Dict) -> Dict:
        """Calculate normalized direction vector"""
        if not from_pos or not to_pos:
            return {'x': 0, 'y': 0, 'z': 0}
        
        dx = to_pos.get('x', 0) - from_pos.get('x', 0)
        dy = to_pos.get('y', 0) - from_pos.get('y', 0)
        
        magnitude = math.sqrt(dx*dx + dy*dy)
        if magnitude > 0:
            return {'x': dx/magnitude, 'y': dy/magnitude, 'z': 0}
        return {'x': 0, 'y': 0, 'z': 0}
    
    def _find_safe_location(self, entity: Dict, frame: Dict) -> Dict:
        """Find safe location away from threats"""
        # Simple implementation - move away from aggressive entities
        threats = [e for e in frame['entities'] 
                  if e['id'] != entity['id'] and 
                  e.get('properties', {}).get('aggression', 0) > 0.7]
        
        if threats:
            # Move opposite to nearest threat
            nearest_threat = min(threats, 
                               key=lambda t: self._calculate_distance(entity['position'], t['position']))
            
            direction = self._calculate_direction(nearest_threat['position'], entity['position'])
            
            return {
                'x': entity['position']['x'] + direction['x'] * 20,
                'y': entity['position']['y'] + direction['y'] * 20,
                'z': 0
            }
        
        return self._random_nearby_location(entity)
    
    def _find_food_source(self, entity: Dict, frame: Dict) -> Optional[Dict]:
        """Find nearest food source"""
        # Look for plants or food resources
        food_sources = [e for e in frame['entities'] if e['type'] == 'plant']
        
        if food_sources:
            nearest = min(food_sources, 
                         key=lambda f: self._calculate_distance(entity['position'], f['position']))
            return nearest['position']
        
        # Check environment resources
        return {'x': 50, 'y': 50, 'z': 0}  # Default to center
    
    def _find_nearest_friendly(self, entity: Dict, frame: Dict) -> Optional[Dict]:
        """Find nearest friendly entity"""
        friendlies = []
        
        for e in frame['entities']:
            if e['id'] != entity['id'] and e['type'] == entity['type']:
                if 'memory' in entity and entity['memory'].get('friends') and e['id'] in entity['memory']['friends']:
                    friendlies.append(e)
                elif e.get('properties', {}).get('aggression', 0) < 0.3:
                    friendlies.append(e)
        
        if friendlies:
            nearest = min(friendlies, 
                         key=lambda f: self._calculate_distance(entity['position'], f['position']))
            return nearest['position']
        
        return None
    
    def _random_nearby_location(self, entity: Dict) -> Dict:
        """Generate random nearby location"""
        angle = random.uniform(0, 2 * math.pi)
        distance = random.uniform(5, 20)
        
        return {
            'x': entity['position']['x'] + math.cos(angle) * distance,
            'y': entity['position']['y'] + math.sin(angle) * distance,
            'z': 0
        }
    
    def _find_nearest_enemy(self, entity: Dict, frame: Dict) -> Optional[Dict]:
        """Find nearest enemy for game world"""
        enemies = [e for e in frame['entities'] 
                  if e['id'] != entity['id'] and 
                  not e.get('properties', {}).get('friendly', True)]
        
        if enemies:
            nearest = min(enemies, 
                         key=lambda e: self._calculate_distance(entity['position'], e['position']))
            return nearest['position']
        
        return None
    
    def _find_unexplored_area(self, entity: Dict, frame: Dict) -> Dict:
        """Find unexplored area for game world"""
        # Simple implementation - random far location
        return {
            'x': random.uniform(0, frame['environment']['size']['x']),
            'y': random.uniform(0, frame['environment']['size']['y']),
            'z': 0
        }