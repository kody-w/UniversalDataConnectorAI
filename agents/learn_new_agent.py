import os
import logging
from agents.basic_agent import BasicAgent
from azure.storage.file import FileService

class AzureFileStorageManager:
    def __init__(self):
        storage_connection = os.environ.get('AzureWebJobsStorage', '')
        if not storage_connection:
            raise ValueError("AzureWebJobsStorage connection string is required")
        
        connection_parts = dict(part.split('=', 1) for part in storage_connection.split(';'))
        
        self.account_name = connection_parts.get('AccountName')
        self.account_key = connection_parts.get('AccountKey')
        self.share_name = os.environ.get('AZURE_FILES_SHARE_NAME', 'azfbusinessbot3c92ab')
        
        if not all([self.account_name, self.account_key]):
            raise ValueError("Invalid storage connection string")
        
        self.file_service = FileService(
            account_name=self.account_name,
            account_key=self.account_key
        )
        self._initialize_storage()

    def _initialize_storage(self):
        try:
            self.file_service.create_share(self.share_name, fail_on_exist=True)
        except:
            pass

        try:
            self.file_service.create_directory(
                self.share_name,
                'agents',
                fail_on_exist=True
            )
        except Exception as e:
            logging.error(f"Error creating agents directory: {str(e)}")

    def write_agent_file(self, agent_name, content):
        try:
            file_name = f"{agent_name}_agent.py"
            self.file_service.create_file_from_text(
                self.share_name,
                'agents',
                file_name,
                content
            )
            return True
        except Exception as e:
            logging.error(f"Error writing agent file: {str(e)}")
            return False
    
    def read_agent_file(self, agent_name):
        try:
            file_name = f"{agent_name}_agent.py"
            file_content = self.file_service.get_file_to_text(
                self.share_name,
                'agents',
                file_name
            )
            return file_content.content
        except Exception as e:
            logging.error(f"Error reading agent file: {str(e)}")
            return None

class LearnNewAgentAgent(BasicAgent):
    def __init__(self):
        self.name = "LearnNewAgent"
        self.metadata = {
            "name": self.name,
            "description": "Creates a New Python File For a Specified Agent and Allows The GPT Model to Perform That Agent",
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_name": {
                        "type": "string",
                        "description": "The Name of the New Agent"
                    },
                    "python_implementation": {
                        "type": "string",
                        "description": """The Python Code That is Behind The New Agent. The code should follow the following template:
                            
                            from agents.basic_agent import BasicAgent
                            {import any other libraries}
                            class {name of the new agent}Agent (BasicAgent):
                            def __init__(self):
                                self.name = {AgentName (no spaces)}
                                self.metadata = {
                                    \"name\": self.name,
                                    \"description\": \"{a description of the agent that describes when it should be used and what it does}\",
                                    \"parameters\": {
                                        \"type\": \"object\",
                                        \"properties\": {
                                        \"{parameter 1 name}\": {
                                            \"type\": \"{parameter type, i.e: string}\",
                                            \"description\": \"{description of what the parameter is used for}\"              
                                        },
                                        \"{parameter 2 name}\": {
                                            \"type\": \"{parameter type, i.e: string}\",
                                            \"description\": \"{description of what the parameter is used for}\"
                                        },
                                        },
                                        \"required\": [\"{name of required parameter}\", \"{name of required parameter}\"]
                                    }
                                }
                                super().__init__(name=self.name, metadata=self.metadata)

                            def perform(self, {parameter_1}, {parameter_2}):
                                {agent functionality}
                                return {A STRING that describes the result of the function, NOT A DICTIONARY. Output a STRING}
                            
                    """
                    }
                },
                "required": ["agent_name", "python_implementation"]
            }
        }
        self.storage_manager = AzureFileStorageManager()
        super().__init__(name=self.name, metadata=self.metadata)

    def _clean_template_markers(self, content):
        """Remove template markers from the content"""
        # Remove the opening and closing markers
        cleaned = content.replace('[[[', '').replace(']]]', '')
        
        # Also handle any whitespace-only lines that might be left
        lines = cleaned.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Skip lines that are only whitespace
            if line.strip():
                cleaned_lines.append(line)
        
        # Join back and ensure proper formatting
        result = '\n'.join(cleaned_lines)
        
        # Make sure we have proper indentation
        if result and not result.startswith('from'):
            # If the first non-empty line doesn't start with 'from', try to fix indentation
            lines = result.split('\n')
            fixed_lines = []
            for line in lines:
                if line.strip():
                    # Remove any leading whitespace and add back proper indentation if needed
                    stripped = line.lstrip()
                    if stripped.startswith('class ') or stripped.startswith('def ') or stripped.startswith('from ') or stripped.startswith('import '):
                        fixed_lines.append(stripped)
                    else:
                        # This might be inside a class or function, preserve some indentation
                        fixed_lines.append(line)
                else:
                    fixed_lines.append('')
            result = '\n'.join(fixed_lines)
        
        return result

    def perform(self, **kwargs):
        """
        Creates a new agent file in the Azure File Storage.
        
        Args:
            agent_name (str): Name of the new agent
            python_implementation (str): Python code for the agent implementation
            
        Returns:
            str: Status message indicating success or failure
        """
        agent_name = kwargs.get('agent_name')
        python_implementation = kwargs.get('python_implementation')
        
        if not agent_name or not python_implementation:
            return "Error: Both agent_name and python_implementation are required"

        # Sanitize agent name
        agent_name = ''.join(c for c in agent_name if c.isalnum())
        
        # STEP 1: Clean the template markers from the implementation
        cleaned_implementation = self._clean_template_markers(python_implementation)
        
        # STEP 2: Write the cleaned file to Azure File Storage
        success = self.storage_manager.write_agent_file(agent_name, cleaned_implementation)
        
        if not success:
            return f"Failed to create agent: {agent_name}"
        
        # STEP 3: Read the file back and verify it's clean
        try:
            file_content = self.storage_manager.read_agent_file(agent_name)
            
            if file_content is None:
                return f"Successfully created agent: {agent_name} (but could not verify content)"
            
            # Check if the file still contains the markers
            if '[[[' in file_content or ']]]' in file_content:
                # Clean the file content again
                cleaned_content = self._clean_template_markers(file_content)
                
                # Write the cleaned content back
                cleanup_success = self.storage_manager.write_agent_file(agent_name, cleaned_content)
                
                if cleanup_success:
                    return f"Successfully created new agent: {agent_name} (removed template markers on second pass)"
                else:
                    return f"Created agent: {agent_name} but failed to clean template markers"
            else:
                return f"Successfully created new agent: {agent_name} (clean file verified)"
                
        except Exception as e:
            logging.error(f"Error during file verification: {str(e)}")
            return f"Successfully created new agent: {agent_name} (but could not verify cleanup: {str(e)})"