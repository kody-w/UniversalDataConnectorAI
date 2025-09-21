import json
import logging
import os
from datetime import datetime
import hashlib
from agents.basic_agent import BasicAgent
from utils.azure_file_storage import AzureFileStorageManager
from openai import AzureOpenAI

class FrameStateAgent(BasicAgent):
    def __init__(self):
        self.name = "FrameState"
        self.metadata = {
            "name": self.name,
            "description": "Manages intelligent frame-based state objects that evolve through AI-guided transitions. Maintains a JSON 'frame' that represents any entity/process and updates it based on context, events, and goals.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "The frame operation to perform",
                        "enum": ["create", "update", "query", "simulate", "reset", "history", "save", "load", "analyze"]
                    },
                    "frame_id": {
                        "type": "string",
                        "description": "Unique identifier for the frame"
                    },
                    "frame_type": {
                        "type": "string",
                        "description": "Type of frame to create (entity, process, workflow, simulation, custom)"
                    },
                    "initial_state": {
                        "type": "object",
                        "description": "Initial state for new frame"
                    },
                    "event": {
                        "type": "string",
                        "description": "Event or action to apply to the frame"
                    },
                    "context": {
                        "type": "object",
                        "description": "Additional context for frame updates"
                    },
                    "rules": {
                        "type": "object",
                        "description": "Rules or constraints for frame evolution"
                    },
                    "target_state": {
                        "type": "object",
                        "description": "Desired target state for simulation"
                    },
                    "steps": {
                        "type": "integer",
                        "description": "Number of simulation steps"
                    }
                },
                "required": ["action"]
            }
        }
        
        self.storage_manager = AzureFileStorageManager()
        self.frames = {}  # In-memory frame storage
        self.frame_history = {}  # Track frame evolution
        
        # Initialize Azure OpenAI for intelligent state transitions
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
                logging.info("FrameState AI capabilities enabled")
            else:
                self.ai_enabled = False
                logging.warning("FrameState running without AI - using rule-based transitions")
        except Exception as e:
            self.ai_enabled = False
            logging.warning(f"FrameState AI initialization failed: {str(e)}")
        
        self._load_frames()
        super().__init__(name=self.name, metadata=self.metadata)
    
    def perform(self, **kwargs):
        action = kwargs.get('action')
        
        try:
            if action == 'create':
                return self._create_frame(kwargs)
            elif action == 'update':
                return self._update_frame(kwargs)
            elif action == 'query':
                return self._query_frame(kwargs)
            elif action == 'simulate':
                return self._simulate_frame(kwargs)
            elif action == 'reset':
                return self._reset_frame(kwargs)
            elif action == 'history':
                return self._get_history(kwargs)
            elif action == 'save':
                return self._save_frame(kwargs)
            elif action == 'load':
                return self._load_frame(kwargs)
            elif action == 'analyze':
                return self._analyze_frame(kwargs)
            else:
                return json.dumps({"status": "error", "message": f"Unknown action: {action}"})
                
        except Exception as e:
            logging.error(f"Error in FrameState: {str(e)}")
            return json.dumps({"status": "error", "message": str(e)})
    
    def _create_frame(self, params):
        """Create a new frame with initial state"""
        frame_id = params.get('frame_id') or self._generate_frame_id()
        frame_type = params.get('frame_type', 'entity')
        initial_state = params.get('initial_state')
        
        # Use default templates if no initial state provided
        if not initial_state:
            initial_state = self._get_default_template(frame_type)
        
        # Create frame structure
        frame = {
            "id": frame_id,
            "type": frame_type,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "version": 1,
            "state": initial_state,
            "metadata": {
                "total_updates": 0,
                "last_event": None,
                "goals": params.get('context', {}).get('goals', []),
                "constraints": params.get('rules', {})
            }
        }
        
        # Store frame
        self.frames[frame_id] = frame
        self.frame_history[frame_id] = [
            {
                "version": 1,
                "timestamp": frame["created_at"],
                "state": initial_state.copy(),
                "event": "frame_created"
            }
        ]
        
        self._save_frames()
        
        return json.dumps({
            "status": "success",
            "message": f"Frame {frame_id} created",
            "frame_id": frame_id,
            "initial_state": initial_state
        }, indent=2)
    
    def _update_frame(self, params):
        """Update frame state based on event"""
        frame_id = params.get('frame_id')
        event = params.get('event')
        context = params.get('context', {})
        
        if not frame_id or frame_id not in self.frames:
            return json.dumps({"status": "error", "message": f"Frame {frame_id} not found"})
        
        if not event:
            return json.dumps({"status": "error", "message": "Event required for update"})
        
        frame = self.frames[frame_id]
        old_state = frame["state"].copy()
        
        # Use AI to determine state transition if enabled
        if self.ai_enabled:
            new_state = self._ai_state_transition(frame, event, context)
        else:
            new_state = self._rule_based_transition(frame, event, context)
        
        # Update frame
        frame["state"] = new_state
        frame["updated_at"] = datetime.now().isoformat()
        frame["version"] += 1
        frame["metadata"]["total_updates"] += 1
        frame["metadata"]["last_event"] = event
        
        # Add to history
        self.frame_history[frame_id].append({
            "version": frame["version"],
            "timestamp": frame["updated_at"],
            "state": new_state.copy(),
            "event": event,
            "changes": self._calculate_changes(old_state, new_state)
        })
        
        self._save_frames()
        
        return json.dumps({
            "status": "success",
            "message": f"Frame {frame_id} updated",
            "frame_id": frame_id,
            "version": frame["version"],
            "old_state": old_state,
            "new_state": new_state,
            "changes": self._calculate_changes(old_state, new_state)
        }, indent=2)
    
    def _simulate_frame(self, params):
        """Simulate frame evolution over multiple steps"""
        frame_id = params.get('frame_id')
        steps = params.get('steps', 5)
        target_state = params.get('target_state')
        context = params.get('context', {})
        
        if not frame_id or frame_id not in self.frames:
            return json.dumps({"status": "error", "message": f"Frame {frame_id} not found"})
        
        frame = self.frames[frame_id]
        simulation_results = []
        current_state = frame["state"].copy()
        
        for step in range(steps):
            # Generate next event based on current state and target
            if self.ai_enabled:
                event = self._ai_generate_event(current_state, target_state, step, steps)
                next_state = self._ai_state_transition(
                    {"state": current_state, "type": frame["type"]}, 
                    event, 
                    {"target": target_state, "step": step, "total_steps": steps}
                )
            else:
                event = f"simulation_step_{step + 1}"
                next_state = self._rule_based_transition(
                    {"state": current_state, "type": frame["type"]}, 
                    event, 
                    context
                )
            
            simulation_results.append({
                "step": step + 1,
                "event": event,
                "state": next_state,
                "timestamp": datetime.now().isoformat()
            })
            
            current_state = next_state
        
        return json.dumps({
            "status": "success",
            "message": f"Simulated {steps} steps for frame {frame_id}",
            "frame_id": frame_id,
            "initial_state": frame["state"],
            "target_state": target_state,
            "simulation_results": simulation_results,
            "final_state": current_state
        }, indent=2)
    
    def _ai_state_transition(self, frame, event, context):
        """Use AI to determine next state based on event"""
        prompt = f"""Given this frame state and event, determine the next state.

Current Frame:
Type: {frame.get('type', 'entity')}
State: {json.dumps(frame['state'], indent=2)}

Event: {event}

Context: {json.dumps(context, indent=2) if context else 'None'}

Rules/Constraints: {json.dumps(frame.get('metadata', {}).get('constraints', {}), indent=2) if frame.get('metadata') else 'None'}

Determine the next state by:
1. Applying the event logically to the current state
2. Respecting any constraints or rules
3. Moving toward goals if specified in context
4. Maintaining consistency and realism

Return ONLY a valid JSON object representing the new state. The structure should match the current state structure but with updated values based on the event.

Think step by step:
- What does this event mean for each property?
- What would realistically change?
- What cascading effects might occur?"""

        try:
            response = self.ai_client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": "You are a state transition engine. Return only valid JSON for the new state."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1500
            )
            
            response_text = response.choices[0].message.content
            # Clean response and parse JSON
            response_text = response_text.strip()
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.startswith('```'):
                response_text = response_text[3:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            
            new_state = json.loads(response_text.strip())
            return new_state
            
        except Exception as e:
            logging.error(f"AI state transition failed: {str(e)}")
            # Fallback to rule-based
            return self._rule_based_transition(frame, event, context)
    
    def _ai_generate_event(self, current_state, target_state, step, total_steps):
        """Use AI to generate appropriate event for simulation"""
        if not target_state:
            return f"evolution_step_{step + 1}"
        
        prompt = f"""Generate an appropriate event to move from current state toward target state.

Current State: {json.dumps(current_state, indent=2)}
Target State: {json.dumps(target_state, indent=2)}
Progress: Step {step + 1} of {total_steps}

Generate a single, specific event name that would naturally occur to move the current state closer to the target.
The event should be realistic and incremental.

Return ONLY the event name as a short string (e.g., "increase_energy", "move_north", "acquire_resource")."""

        try:
            response = self.ai_client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": "Generate single event names for state transitions."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,
                max_tokens=50
            )
            
            event = response.choices[0].message.content.strip().strip('"').strip("'")
            return event
            
        except Exception as e:
            logging.error(f"AI event generation failed: {str(e)}")
            return f"evolution_step_{step + 1}"
    
    def _rule_based_transition(self, frame, event, context):
        """Fallback rule-based state transition"""
        state = frame["state"].copy()
        frame_type = frame.get("type", "entity")
        
        # Simple rule-based transitions for different frame types
        if frame_type == "entity":
            # Entity rules
            if "move" in event.lower():
                if "position" in state:
                    if isinstance(state["position"], dict):
                        state["position"]["x"] = state["position"].get("x", 0) + 1
                        state["position"]["y"] = state["position"].get("y", 0) + 1
                if "energy" in state:
                    state["energy"] = max(0, state.get("energy", 100) - 10)
            
            elif "rest" in event.lower():
                if "energy" in state:
                    state["energy"] = min(100, state.get("energy", 50) + 20)
                if "health" in state:
                    state["health"] = min(100, state.get("health", 50) + 10)
            
            elif "work" in event.lower() or "action" in event.lower():
                if "energy" in state:
                    state["energy"] = max(0, state.get("energy", 100) - 15)
                if "experience" in state:
                    state["experience"] = state.get("experience", 0) + 5
                if "resources" in state:
                    state["resources"] = state.get("resources", 0) + 10
        
        elif frame_type == "process":
            # Process rules
            if "start" in event.lower():
                state["status"] = "running"
                state["progress"] = 0
            elif "advance" in event.lower() or "step" in event.lower():
                if "progress" in state:
                    state["progress"] = min(100, state.get("progress", 0) + 20)
                if state.get("progress", 0) >= 100:
                    state["status"] = "completed"
            elif "error" in event.lower():
                state["status"] = "error"
            elif "pause" in event.lower():
                state["status"] = "paused"
            elif "reset" in event.lower():
                state["status"] = "idle"
                state["progress"] = 0
        
        elif frame_type == "workflow":
            # Workflow rules
            if "approve" in event.lower():
                state["approval_status"] = "approved"
                if "stage" in state:
                    state["stage"] = "next_stage"
            elif "reject" in event.lower():
                state["approval_status"] = "rejected"
                state["stage"] = "revision"
            elif "submit" in event.lower():
                state["stage"] = "review"
                state["status"] = "pending"
        
        # Generic updates for any frame type
        if "timestamp" in state:
            state["timestamp"] = datetime.now().isoformat()
        
        if "counter" in state and "increment" in event.lower():
            state["counter"] = state.get("counter", 0) + 1
        
        if "active" in state:
            if "activate" in event.lower():
                state["active"] = True
            elif "deactivate" in event.lower():
                state["active"] = False
        
        return state
    
    def _query_frame(self, params):
        """Query current frame state"""
        frame_id = params.get('frame_id')
        
        if not frame_id:
            # Return all frames
            return json.dumps({
                "status": "success",
                "frames": list(self.frames.keys()),
                "total": len(self.frames)
            }, indent=2)
        
        if frame_id not in self.frames:
            return json.dumps({"status": "error", "message": f"Frame {frame_id} not found"})
        
        frame = self.frames[frame_id]
        return json.dumps({
            "status": "success",
            "frame": frame
        }, indent=2)
    
    def _reset_frame(self, params):
        """Reset frame to initial state"""
        frame_id = params.get('frame_id')
        
        if not frame_id or frame_id not in self.frames:
            return json.dumps({"status": "error", "message": f"Frame {frame_id} not found"})
        
        if frame_id in self.frame_history and self.frame_history[frame_id]:
            initial_state = self.frame_history[frame_id][0]["state"]
            self.frames[frame_id]["state"] = initial_state.copy()
            self.frames[frame_id]["updated_at"] = datetime.now().isoformat()
            self.frames[frame_id]["version"] += 1
            
            self._save_frames()
            
            return json.dumps({
                "status": "success",
                "message": f"Frame {frame_id} reset to initial state",
                "state": initial_state
            }, indent=2)
        
        return json.dumps({"status": "error", "message": "No history found for frame"})
    
    def _get_history(self, params):
        """Get frame evolution history"""
        frame_id = params.get('frame_id')
        
        if not frame_id or frame_id not in self.frame_history:
            return json.dumps({"status": "error", "message": f"No history for frame {frame_id}"})
        
        history = self.frame_history[frame_id]
        
        return json.dumps({
            "status": "success",
            "frame_id": frame_id,
            "total_versions": len(history),
            "history": history[-10:]  # Last 10 versions
        }, indent=2)
    
    def _analyze_frame(self, params):
        """Analyze frame patterns and suggest optimizations"""
        frame_id = params.get('frame_id')
        
        if not frame_id or frame_id not in self.frames:
            return json.dumps({"status": "error", "message": f"Frame {frame_id} not found"})
        
        frame = self.frames[frame_id]
        history = self.frame_history.get(frame_id, [])
        
        analysis = {
            "frame_id": frame_id,
            "type": frame["type"],
            "age": self._calculate_age(frame["created_at"]),
            "total_updates": frame["metadata"]["total_updates"],
            "version": frame["version"],
            "state_complexity": len(json.dumps(frame["state"])),
            "patterns": self._detect_patterns(history),
            "recommendations": []
        }
        
        # Generate recommendations
        if analysis["total_updates"] > 100:
            analysis["recommendations"].append("Consider archiving old history")
        
        if analysis["state_complexity"] > 1000:
            analysis["recommendations"].append("State object is large, consider optimization")
        
        if self.ai_enabled:
            # Get AI insights
            analysis["ai_insights"] = self._ai_analyze_patterns(frame, history)
        
        return json.dumps({
            "status": "success",
            "analysis": analysis
        }, indent=2)
    
    def _ai_analyze_patterns(self, frame, history):
        """Use AI to analyze frame patterns"""
        recent_history = history[-5:] if len(history) > 5 else history
        
        prompt = f"""Analyze this frame's evolution pattern and provide insights.

Frame Type: {frame['type']}
Current State: {json.dumps(frame['state'], indent=2)}

Recent History:
{json.dumps(recent_history, indent=2)}

Provide insights on:
1. Patterns in state evolution
2. Potential optimizations
3. Predicted future states
4. Anomalies or concerns

Return as JSON with keys: patterns, optimizations, predictions, concerns"""

        try:
            response = self.ai_client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": "Analyze data patterns and provide insights."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=800
            )
            
            response_text = response.choices[0].message.content
            # Clean and parse JSON
            if response_text.startswith('```'):
                response_text = response_text[response_text.find('{'):response_text.rfind('}')+1]
            
            return json.loads(response_text)
            
        except Exception as e:
            logging.error(f"AI analysis failed: {str(e)}")
            return {"error": "AI analysis unavailable"}
    
    def _detect_patterns(self, history):
        """Detect patterns in frame history"""
        patterns = {
            "common_events": {},
            "state_cycles": [],
            "growth_trends": {}
        }
        
        # Count event frequency
        for entry in history:
            event = entry.get("event", "unknown")
            patterns["common_events"][event] = patterns["common_events"].get(event, 0) + 1
        
        # Detect cycles (simplified)
        if len(history) > 3:
            states_str = [json.dumps(h["state"], sort_keys=True) for h in history]
            for i in range(len(states_str) - 1):
                for j in range(i + 2, len(states_str)):
                    if states_str[i] == states_str[j]:
                        patterns["state_cycles"].append({
                            "start_version": history[i]["version"],
                            "end_version": history[j]["version"]
                        })
        
        return patterns
    
    def _calculate_changes(self, old_state, new_state):
        """Calculate what changed between states"""
        changes = {
            "added": {},
            "removed": {},
            "modified": {}
        }
        
        old_flat = self._flatten_dict(old_state)
        new_flat = self._flatten_dict(new_state)
        
        # Find additions
        for key in new_flat:
            if key not in old_flat:
                changes["added"][key] = new_flat[key]
        
        # Find removals
        for key in old_flat:
            if key not in new_flat:
                changes["removed"][key] = old_flat[key]
        
        # Find modifications
        for key in old_flat:
            if key in new_flat and old_flat[key] != new_flat[key]:
                changes["modified"][key] = {
                    "old": old_flat[key],
                    "new": new_flat[key]
                }
        
        return changes
    
    def _flatten_dict(self, d, parent_key='', sep='.'):
        """Flatten nested dictionary"""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)
    
    def _calculate_age(self, created_at):
        """Calculate age of frame"""
        created = datetime.fromisoformat(created_at)
        age = datetime.now() - created
        return f"{age.days} days, {age.seconds // 3600} hours"
    
    def _get_default_template(self, frame_type):
        """Get default template for frame type"""
        templates = {
            "entity": {
                "name": "Entity_" + self._generate_frame_id()[:8],
                "type": "generic",
                "health": 100,
                "energy": 100,
                "position": {"x": 0, "y": 0, "z": 0},
                "inventory": [],
                "status": "idle",
                "experience": 0,
                "level": 1,
                "attributes": {
                    "strength": 10,
                    "intelligence": 10,
                    "speed": 10
                },
                "active": True,
                "timestamp": datetime.now().isoformat()
            },
            "process": {
                "name": "Process_" + self._generate_frame_id()[:8],
                "status": "idle",
                "progress": 0,
                "stage": "initialization",
                "started_at": None,
                "completed_at": None,
                "errors": [],
                "warnings": [],
                "inputs": {},
                "outputs": {},
                "metrics": {
                    "duration": 0,
                    "iterations": 0,
                    "success_rate": 0
                }
            },
            "workflow": {
                "name": "Workflow_" + self._generate_frame_id()[:8],
                "stage": "draft",
                "approval_status": "pending",
                "assignee": None,
                "created_by": "system",
                "participants": [],
                "deadlines": {},
                "documents": [],
                "comments": [],
                "priority": "normal",
                "tags": []
            },
            "simulation": {
                "name": "Simulation_" + self._generate_frame_id()[:8],
                "environment": {
                    "temperature": 20,
                    "pressure": 1,
                    "humidity": 50,
                    "time": 0
                },
                "entities": [],
                "resources": {
                    "energy": 1000,
                    "matter": 1000,
                    "information": 1000
                },
                "rules": {},
                "events_queue": [],
                "statistics": {}
            },
            "custom": {
                "id": self._generate_frame_id()[:8],
                "data": {},
                "metadata": {},
                "timestamp": datetime.now().isoformat()
            }
        }
        
        return templates.get(frame_type, templates["custom"])
    
    def _generate_frame_id(self):
        """Generate unique frame ID"""
        return hashlib.md5(f"{datetime.now().isoformat()}".encode()).hexdigest()[:16]
    
    def _save_frame(self, params):
        """Save frame to persistent storage"""
        frame_id = params.get('frame_id')
        
        if not frame_id or frame_id not in self.frames:
            return json.dumps({"status": "error", "message": f"Frame {frame_id} not found"})
        
        self._save_frames()
        return json.dumps({
            "status": "success",
            "message": f"Frame {frame_id} saved to storage"
        })
    
    def _load_frame(self, params):
        """Load frame from storage"""
        frame_id = params.get('frame_id')
        
        if frame_id and frame_id in self.frames:
            return json.dumps({
                "status": "success",
                "message": f"Frame {frame_id} already loaded",
                "frame": self.frames[frame_id]
            }, indent=2)
        
        # Try to load from storage
        self._load_frames()
        
        if frame_id and frame_id in self.frames:
            return json.dumps({
                "status": "success",
                "message": f"Frame {frame_id} loaded from storage",
                "frame": self.frames[frame_id]
            }, indent=2)
        
        return json.dumps({"status": "error", "message": f"Frame {frame_id} not found in storage"})
    
    def _save_frames(self):
        """Save all frames to storage"""
        try:
            frames_data = {
                "frames": self.frames,
                "history": self.frame_history,
                "saved_at": datetime.now().isoformat()
            }
            
            self.storage_manager.write_json_to_path(
                frames_data,
                "frames",
                "frame_states.json"
            )
            logging.info(f"Saved {len(self.frames)} frames to storage")
            
        except Exception as e:
            logging.error(f"Error saving frames: {str(e)}")
    
    def _load_frames(self):
        """Load frames from storage"""
        try:
            frames_data = self.storage_manager.read_json_from_path(
                "frames",
                "frame_states.json"
            )
            
            if frames_data:
                self.frames = frames_data.get("frames", {})
                self.frame_history = frames_data.get("history", {})
                logging.info(f"Loaded {len(self.frames)} frames from storage")
                
        except Exception as e:
            logging.warning(f"Could not load frames: {str(e)}")
            self.frames = {}
            self.frame_history = {}