from agents.basic_agent import BasicAgent
import json
import re
import logging
import os
import base64
import math
from datetime import datetime
from collections import Counter, defaultdict
from utils.azure_file_storage import AzureFileStorageManager
from openai import AzureOpenAI

class UniversalDataTranslatorAgent(BasicAgent):
    def __init__(self):
        self.name = "UniversalDataTranslator"
        self.metadata = {
            "name": self.name,
            "description": "Universal pattern analyzer that examines ANY data format without assumptions. Produces comprehensive analysis reports describing what the data is, how it's structured, and how to parse it - without actually parsing.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file in Azure storage"
                    },
                    "file_content": {
                        "type": "string",
                        "description": "Direct content to analyze (alternative to file_path)"
                    },
                    "format_hint": {
                        "type": "string",
                        "description": "Optional hint about the format (e.g., 'morse code', 'medical device output')"
                    },
                    "context_clues": {
                        "type": "string",
                        "description": "Additional context to help AI understand the data (e.g., 'recorded underwater', 'from 1970s mainframe', 'encrypted communication')"
                    }
                },
                "required": []
            }
        }
        self.storage_manager = AzureFileStorageManager()
        
        # Initialize Azure OpenAI for AI-powered analysis
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
                logging.warning("AI features disabled - Azure OpenAI not configured")
        except Exception as e:
            self.ai_enabled = False
            logging.warning(f"AI features disabled: {str(e)}")
            
        super().__init__(name=self.name, metadata=self.metadata)

    def perform(self, **kwargs):
        try:
            # Get parameters
            file_path = kwargs.get('file_path')
            file_content = kwargs.get('file_content')
            format_hint = kwargs.get('format_hint', 'unknown format')
            context_clues = kwargs.get('context_clues', '')
            
            # Get content
            if file_content:
                content = file_content
            elif file_path:
                content = self._read_file(file_path)
                if not content:
                    return f"Error: Could not read file from path: {file_path}"
            else:
                return "Error: Either file_path or file_content must be provided"
            
            # Phase 1: Statistical analysis (no format assumptions)
            statistical_analysis = self._perform_statistical_analysis(content)
            
            # Phase 2: Pattern discovery (no format assumptions)
            pattern_analysis = self._discover_patterns(content)
            
            # Phase 3: Fixed-width detection and field analysis
            fixed_width_analysis = self._analyze_fixed_width_structure(content)
            
            # Phase 4: Multi-hypothesis generation and ranking
            hypotheses_analysis = {}
            if self.ai_enabled:
                # Include fixed-width analysis in context for AI
                enhanced_context = {
                    "original_context": context_clues,
                    "fixed_width_detected": fixed_width_analysis.get('is_fixed_width', False),
                    "detected_fields": fixed_width_analysis.get('detected_fields', [])
                }
                hypotheses_analysis = self._generate_and_rank_hypotheses(
                    content, 
                    format_hint, 
                    json.dumps(enhanced_context)
                )
            
            # Phase 5: Synthesize comprehensive analysis report
            analysis_report = self._synthesize_analysis_report(
                content,
                statistical_analysis,
                pattern_analysis,
                hypotheses_analysis,
                format_hint,
                context_clues,
                fixed_width_analysis
            )
            
            # Return comprehensive analysis (NOT parsed data)
            return json.dumps(analysis_report, indent=2)
            
        except Exception as e:
            logging.error(f"Error in analysis: {str(e)}")
            return f"Error analyzing data: {str(e)}"

    def _read_file(self, file_path):
        """Read file from Azure storage"""
        try:
            parts = file_path.rsplit('/', 1)
            if len(parts) == 2:
                directory, filename = parts
            else:
                directory = ''
                filename = parts[0]
            
            return self.storage_manager.read_file(directory, filename)
        except Exception as e:
            logging.error(f"Error reading file: {str(e)}")
            return None

    def _perform_statistical_analysis(self, content):
        """Perform statistical analysis without format assumptions"""
        analysis = {
            'size_bytes': len(content.encode('utf-8')),
            'character_count': len(content),
            'line_count': len(content.split('\n')),
            'non_empty_line_count': len([l for l in content.split('\n') if l.strip()]),
            'paragraph_count': len(content.split('\n\n')),
            'character_distribution': {},
            'entropy': 0,
            'unique_characters': 0,
            'whitespace_ratio': 0,
            'numeric_ratio': 0,
            'alphabetic_ratio': 0,
            'special_char_ratio': 0
        }
        
        # Character frequency analysis
        char_freq = Counter(content[:10000])  # Sample for performance
        total_chars = sum(char_freq.values())
        
        # Calculate ratios
        whitespace_count = sum(char_freq[c] for c in char_freq if c.isspace())
        numeric_count = sum(char_freq[c] for c in char_freq if c.isdigit())
        alphabetic_count = sum(char_freq[c] for c in char_freq if c.isalpha())
        
        analysis['whitespace_ratio'] = whitespace_count / total_chars if total_chars > 0 else 0
        analysis['numeric_ratio'] = numeric_count / total_chars if total_chars > 0 else 0
        analysis['alphabetic_ratio'] = alphabetic_count / total_chars if total_chars > 0 else 0
        analysis['special_char_ratio'] = 1 - (analysis['whitespace_ratio'] + 
                                               analysis['numeric_ratio'] + 
                                               analysis['alphabetic_ratio'])
        
        # Entropy calculation (Shannon entropy)
        entropy = 0
        for count in char_freq.values():
            if count > 0:
                prob = count / total_chars
                entropy -= prob * math.log2(prob)
        analysis['entropy'] = entropy
        
        # Character categories
        analysis['unique_characters'] = len(char_freq)
        analysis['character_categories'] = {
            'brackets': sum(char_freq[c] for c in '[]{}()<>' if c in char_freq),
            'quotes': sum(char_freq[c] for c in '\'\"' if c in char_freq),
            'delimiters': sum(char_freq[c] for c in ',;:|' if c in char_freq),
            'operators': sum(char_freq[c] for c in '+-*/=' if c in char_freq),
            'punctuation': sum(char_freq[c] for c in '.!?' if c in char_freq),
            'slashes': sum(char_freq[c] for c in '/\\' if c in char_freq)
        }
        
        return analysis

    def _discover_patterns(self, content):
        """Discover patterns without assuming any format"""
        patterns = {
            'repetitive_structures': [],
            'boundary_markers': [],
            'recurring_sequences': [],
            'structural_indicators': {},
            'line_patterns': {},
            'chunk_patterns': {},
            'distance_patterns': {}
        }
        
        lines = content.split('\n')[:1000]  # Sample for analysis
        
        # Analyze line beginnings and endings
        line_starts = Counter()
        line_ends = Counter()
        line_lengths = []
        
        for line in lines:
            if line.strip():
                # Get first and last meaningful sequences
                if len(line) > 0:
                    line_starts[line[:min(10, len(line))]] += 1
                    line_ends[line[max(-10, -len(line)):]] += 1
                    line_lengths.append(len(line))
        
        # Find common patterns
        patterns['common_line_starts'] = line_starts.most_common(10)
        patterns['common_line_ends'] = line_ends.most_common(10)
        
        # Analyze line length distribution
        if line_lengths:
            unique_lengths = list(set(line_lengths))
            patterns['line_length_stats'] = {
                'min': min(line_lengths),
                'max': max(line_lengths),
                'avg': sum(line_lengths) / len(line_lengths),
                'consistent': len(unique_lengths) == 1,
                'all_same_length': len(unique_lengths) == 1,
                'unique_lengths': unique_lengths[:10],  # First 10 unique lengths
                'most_common_length': Counter(line_lengths).most_common(1)[0] if line_lengths else None
            }
        
        # Find repeating n-grams
        ngram_sizes = [3, 5, 10, 20]
        for n in ngram_sizes:
            ngrams = Counter()
            for i in range(len(content) - n):
                ngram = content[i:i+n]
                if not ngram.isspace():
                    ngrams[ngram] += 1
            
            # Find ngrams that repeat
            repeating = [(ng, count) for ng, count in ngrams.items() if count > 2]
            if repeating:
                patterns[f'{n}_char_repetitions'] = sorted(repeating, key=lambda x: x[1], reverse=True)[:5]
        
        # Detect structural patterns
        patterns['structural_indicators'] = {
            'has_consistent_indentation': self._check_indentation(lines),
            'has_header_like_structure': self._check_header_structure(lines),
            'has_record_like_structure': self._check_record_structure(lines),
            'has_nested_structure': self._check_nesting(content),
            'has_tabular_structure': self._check_tabular(lines),
            'has_key_value_patterns': self._check_key_value(lines),
            'has_fixed_width_pattern': self._check_fixed_width(lines)
        }
        
        return patterns

    def _analyze_fixed_width_structure(self, content):
        """Analyze if content has fixed-width structure and detect fields"""
        lines = content.split('\n')
        # Filter out empty lines
        lines = [l for l in lines if l]
        
        if len(lines) < 2:
            return {'is_fixed_width': False}
        
        # Check if all lines have the same length
        line_lengths = [len(l) for l in lines]
        if len(set(line_lengths)) != 1:
            return {'is_fixed_width': False}
        
        common_length = line_lengths[0]
        
        # Analyze character patterns at each position
        position_analysis = []
        for pos in range(common_length):
            chars_at_pos = [line[pos] if pos < len(line) else ' ' for line in lines[:100]]  # Sample first 100 lines
            char_freq = Counter(chars_at_pos)
            
            # Determine character type at this position
            space_count = char_freq.get(' ', 0)
            digit_count = sum(1 for c in chars_at_pos if c.isdigit())
            alpha_count = sum(1 for c in chars_at_pos if c.isalpha())
            
            total = len(chars_at_pos)
            position_info = {
                'position': pos,
                'is_mostly_space': space_count > total * 0.8,
                'is_mostly_digit': digit_count > total * 0.7,
                'is_mostly_alpha': alpha_count > total * 0.7,
                'is_mixed': not (space_count > total * 0.8 or digit_count > total * 0.7 or alpha_count > total * 0.7),
                'unique_chars': len(char_freq),
                'most_common': char_freq.most_common(1)[0] if char_freq else (' ', 0)
            }
            position_analysis.append(position_info)
        
        # Detect field boundaries
        detected_fields = []
        current_field_start = 0
        current_field_type = None
        
        for i, pos_info in enumerate(position_analysis):
            # Determine position type
            if pos_info['is_mostly_space']:
                pos_type = 'space'
            elif pos_info['is_mostly_digit']:
                pos_type = 'digit'
            elif pos_info['is_mostly_alpha']:
                pos_type = 'alpha'
            else:
                pos_type = 'mixed'
            
            # Detect field transitions
            if i == 0:
                current_field_type = pos_type
            elif pos_type != current_field_type or i == len(position_analysis) - 1:
                # Field boundary detected
                field_end = i if i < len(position_analysis) - 1 else common_length
                
                # Get sample value for this field
                sample_values = []
                for line in lines[:5]:  # Sample from first 5 lines
                    if current_field_start < len(line) and field_end <= len(line):
                        sample_values.append(line[current_field_start:field_end])
                
                # Analyze field content
                field_info = self._analyze_field_content(sample_values)
                
                detected_fields.append({
                    'start': current_field_start,
                    'end': field_end,
                    'length': field_end - current_field_start,
                    'type': field_info['type'],
                    'data_type': field_info['data_type'],
                    'sample': sample_values[0] if sample_values else '',
                    'samples': sample_values[:3]
                })
                
                current_field_start = i
                current_field_type = pos_type
        
        # Filter out small space-only fields (likely field separators)
        significant_fields = []
        for field in detected_fields:
            if not (field['type'] == 'space' and field['length'] <= 2):
                significant_fields.append(field)
        
        return {
            'is_fixed_width': True,
            'record_length': common_length,
            'detected_fields': significant_fields,
            'field_count': len(significant_fields),
            'position_analysis': position_analysis[:20]  # First 20 positions for reference
        }

    def _analyze_field_content(self, sample_values):
        """Analyze content of a field from sample values"""
        if not sample_values:
            return {'type': 'unknown', 'data_type': 'unknown'}
        
        # Clean samples (strip whitespace)
        cleaned_samples = [s.strip() for s in sample_values]
        
        # Check patterns
        all_numeric = all(s.replace('.', '').replace('-', '').isdigit() or s == '' for s in cleaned_samples)
        all_alpha = all(s.replace(' ', '').isalpha() or s == '' for s in cleaned_samples)
        all_alphanumeric = all(s.replace(' ', '').replace('-', '').isalnum() or s == '' for s in cleaned_samples)
        
        # Check for specific patterns
        date_pattern = re.compile(r'^\d{8}$|^\d{6}$|^\d{4}-\d{2}-\d{2}$')
        currency_pattern = re.compile(r'^\d+\.\d{2}$')
        id_pattern = re.compile(r'^\d{3,10}$')
        single_char_pattern = re.compile(r'^[A-Z]$|^[YN]$|^[MF]$')
        
        # Determine field type
        if all(date_pattern.match(s) for s in cleaned_samples if s):
            return {'type': 'date', 'data_type': 'date_yyyymmdd'}
        elif all(currency_pattern.match(s) for s in cleaned_samples if s):
            return {'type': 'currency', 'data_type': 'numeric_decimal'}
        elif all(id_pattern.match(s) for s in cleaned_samples if s):
            return {'type': 'id', 'data_type': 'numeric_id'}
        elif all(single_char_pattern.match(s) for s in cleaned_samples if s):
            return {'type': 'flag', 'data_type': 'single_char'}
        elif all_numeric:
            return {'type': 'numeric', 'data_type': 'numeric'}
        elif all_alpha:
            if all(len(s.strip()) <= 10 for s in sample_values):
                return {'type': 'code', 'data_type': 'text_code'}
            else:
                return {'type': 'text', 'data_type': 'text_padded'}
        elif all_alphanumeric:
            return {'type': 'mixed', 'data_type': 'alphanumeric'}
        elif all(s.isspace() or s == '' for s in sample_values):
            return {'type': 'space', 'data_type': 'padding'}
        else:
            return {'type': 'text', 'data_type': 'text_general'}

    def _generate_and_rank_hypotheses(self, content, format_hint, context_clues):
        """Generate multiple hypotheses and rank them"""
        if not self.ai_enabled:
            return {}
        
        try:
            sample = content[:3000] if len(content) > 3000 else content
            
            # Step 1: Generate diverse hypotheses
            hypotheses = self._ai_generate_hypotheses(sample, format_hint, context_clues)
            
            # Validate hypotheses is a list
            if not isinstance(hypotheses, list) or len(hypotheses) == 0:
                logging.warning(f"No valid hypotheses generated")
                return {}
            
            # Step 2: Test and score each hypothesis
            scored_hypotheses = []
            for i, hypothesis in enumerate(hypotheses):
                # Ensure hypothesis is a dict
                if not isinstance(hypothesis, dict):
                    logging.warning(f"Hypothesis {i} is not a dictionary: {type(hypothesis)}")
                    continue
                
                try:
                    score = self._ai_score_hypothesis(hypothesis, sample)
                    scored_hypotheses.append({
                        'hypothesis': hypothesis,
                        'score': score,
                        'confidence': score.get('overall_confidence', 0.0)
                    })
                except Exception as e:
                    logging.error(f"Failed to score hypothesis {i}: {str(e)}")
                    # Add with zero confidence
                    scored_hypotheses.append({
                        'hypothesis': hypothesis,
                        'score': {
                            "coverage": 0.0,
                            "contradiction_count": 999,
                            "complexity": 1.0,
                            "information_preservation": 0.0,
                            "overall_confidence": 0.0
                        },
                        'confidence': 0.0
                    })
            
            # If no hypotheses were scored successfully, return empty
            if not scored_hypotheses:
                logging.warning("No hypotheses were successfully scored")
                return {}
            
            # Step 3: Sort by confidence
            scored_hypotheses.sort(key=lambda x: x.get('confidence', 0.0), reverse=True)
            
            # Step 4: Get detailed analysis for top hypothesis
            best_hypothesis = scored_hypotheses[0] if scored_hypotheses else None
            detailed_analysis = {}
            if best_hypothesis and best_hypothesis.get('hypothesis'):
                try:
                    detailed_analysis = self._ai_detailed_analysis(best_hypothesis['hypothesis'], sample)
                except Exception as e:
                    logging.error(f"Failed to get detailed analysis: {str(e)}")
                    detailed_analysis = {}
            
            return {
                'hypotheses': scored_hypotheses,
                'best_hypothesis': best_hypothesis,
                'detailed_analysis': detailed_analysis,
                'confidence_distribution': [h.get('confidence', 0.0) for h in scored_hypotheses]
            }
            
        except Exception as e:
            logging.error(f"Hypothesis generation failed: {str(e)}")
            return {}

    def _ai_generate_hypotheses(self, sample, format_hint, context_clues):
        """Generate diverse hypotheses about the data"""
        prompt = f"""Analyze this data sample. Format hint: {format_hint}. Context: {context_clues}

Data sample:
{sample}

Generate 5 COMPLETELY DIFFERENT hypotheses about what this data is. 
Each should approach from a totally different angle.

Return as JSON array where each hypothesis has these fields:
[
  {{
    "interpretation": "what you think this data is",
    "evidence": ["specific patterns you see that support this"],
    "format": "the format/structure type",
    "format_family": "category of format (structured/text/binary/encoded/etc)",
    "structure_type": "how data is organized (flat/nested/hierarchical/sequential/etc)",
    "parsing_approach": "how to extract data from this format",
    "confidence": 0.0-1.0
  }},
  ... (4 more different hypotheses)
]

Consider diverse interpretations:
1. One hypothesis should assume it's a standard structured format
2. One should assume it's encoded or compressed
3. One should assume it's natural language or communication  
4. One should assume it's scientific/mathematical data
5. One should be creative/exotic (biological, artistic, alien, etc.)

Pay special attention to:
- Line length consistency
- Character patterns at specific positions
- Repeating structures
- Data type patterns (dates, IDs, currency, names)"""

        try:
            response = self.ai_client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": "You are a universal pattern recognition system. Analyze data without assumptions."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,
                max_tokens=2000
            )
            
            hypotheses = self._parse_json_from_response(response.choices[0].message.content)
            
            # Validate that we have a list of hypotheses
            if isinstance(hypotheses, list):
                # Filter out any non-dictionary items
                valid_hypotheses = []
                for h in hypotheses:
                    if isinstance(h, dict):
                        # Ensure required fields exist with defaults
                        h.setdefault('interpretation', 'Unknown interpretation')
                        h.setdefault('evidence', [])
                        h.setdefault('format', 'unknown')
                        h.setdefault('format_family', 'unknown')
                        h.setdefault('structure_type', 'unknown')
                        h.setdefault('parsing_approach', 'adaptive')
                        h.setdefault('confidence', 0.5)
                        valid_hypotheses.append(h)
                return valid_hypotheses
            
            # If we got a single dict, wrap it in a list
            elif isinstance(hypotheses, dict):
                hypotheses.setdefault('interpretation', 'Unknown interpretation')
                hypotheses.setdefault('evidence', [])
                hypotheses.setdefault('format', 'unknown')
                hypotheses.setdefault('format_family', 'unknown')
                hypotheses.setdefault('structure_type', 'unknown')
                hypotheses.setdefault('parsing_approach', 'adaptive')
                hypotheses.setdefault('confidence', 0.5)
                return [hypotheses]
            
            return []
            
        except Exception as e:
            logging.error(f"Failed to generate hypotheses: {str(e)}")
            return []

    def _ai_score_hypothesis(self, hypothesis, sample):
        """Score how well a hypothesis fits the data"""
        # Ensure hypothesis is a dictionary
        if not isinstance(hypothesis, dict):
            logging.warning(f"Hypothesis is not a dict: {type(hypothesis)}")
            return {
                "coverage": 0.0,
                "contradiction_count": 999,
                "complexity": 1.0,
                "information_preservation": 0.0,
                "overall_confidence": 0.0
            }
        
        prompt = f"""Score this hypothesis against the data:

Hypothesis: {json.dumps(hypothesis, indent=2)}

Data sample:
{sample}

Evaluate:
1. How much of the data does this explanation cover?
2. Are there patterns that contradict this hypothesis?
3. How complex is this interpretation?
4. Does it preserve information effectively?

Return JSON with:
{{
  "coverage": 0.0-1.0,
  "contradiction_count": number,
  "complexity": 0.0-1.0,
  "information_preservation": 0.0-1.0,
  "overall_confidence": 0.0-1.0
}}"""

        try:
            response = self.ai_client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": "Score hypotheses objectively."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            score = self._parse_json_from_response(response.choices[0].message.content)
            
            # Ensure we have a dictionary with the required fields
            if not isinstance(score, dict):
                logging.warning(f"Score response is not a dict: {type(score)}")
                return {
                    "coverage": 0.0,
                    "contradiction_count": 999,
                    "complexity": 1.0,
                    "information_preservation": 0.0,
                    "overall_confidence": 0.0
                }
            
            # Ensure all required fields exist
            default_score = {
                "coverage": 0.0,
                "contradiction_count": 0,
                "complexity": 1.0,
                "information_preservation": 0.0,
                "overall_confidence": 0.0
            }
            
            for key, default_value in default_score.items():
                if key not in score:
                    score[key] = default_value
            
            return score
            
        except Exception as e:
            logging.error(f"Failed to score hypothesis: {str(e)}")
            return {
                "coverage": 0.0,
                "contradiction_count": 999,
                "complexity": 1.0,
                "information_preservation": 0.0,
                "overall_confidence": 0.0
            }

    def _ai_detailed_analysis(self, hypothesis, sample):
        """Get detailed analysis for the best hypothesis"""
        prompt = f"""Provide detailed analysis for this hypothesis:

{json.dumps(hypothesis, indent=2)}

Data sample:
{sample}

Provide:
1. Detailed structure analysis
2. Field/component identification  
3. Record/unit boundaries
4. Parsing strategy
5. Special considerations

Return comprehensive JSON analysis."""

        try:
            response = self.ai_client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": "Provide detailed data structure analysis."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1500
            )
            
            return self._parse_json_from_response(response.choices[0].message.content)
            
        except Exception as e:
            logging.error(f"Failed to get detailed analysis: {str(e)}")
            return {}

    def _synthesize_analysis_report(self, content, statistical, patterns, hypotheses, format_hint, context_clues, fixed_width_analysis):
        """Synthesize all analyses into comprehensive report"""
        report = {
            "analysis_metadata": {
                "timestamp": datetime.now().isoformat(),
                "format_hint": format_hint,
                "context_clues": context_clues,
                "ai_analysis_available": bool(hypotheses)
            },
            
            "data_characteristics": {
                "statistical_profile": statistical,
                "discovered_patterns": patterns
            },
            
            "format_determination": {
                "confidence": 0.0,
                "detected_format": "unknown",
                "format_family": "unknown",
                "structure_type": "unknown"
            },
            
            "parsing_recommendation": {
                "recommended_approach": "unknown",
                "parsing_steps": [],
                "field_extraction_rules": {},
                "record_boundaries": "unknown",
                "special_handlers_needed": []
            }
        }
        
        # Add fixed-width analysis if detected
        if fixed_width_analysis.get('is_fixed_width'):
            report["fixed_width_analysis"] = {
                "detected": True,
                "record_length": fixed_width_analysis.get('record_length'),
                "field_count": fixed_width_analysis.get('field_count'),
                "detected_fields": fixed_width_analysis.get('detected_fields', [])
            }
            
            # Update format determination if fixed-width is strongly indicated
            if not hypotheses or (hypotheses and hypotheses.get('best_hypothesis', {}).get('confidence', 0) < 0.7):
                report["format_determination"] = {
                    "confidence": 0.85,
                    "detected_format": "Fixed-Width Text File",
                    "format_family": "structured",
                    "structure_type": "flat/tabular",
                    "evidence": [
                        f"All lines exactly {fixed_width_analysis.get('record_length')} characters",
                        f"{fixed_width_analysis.get('field_count')} fields detected",
                        "Consistent spacing patterns",
                        "Space-padded text fields"
                    ]
                }
                
                report["parsing_recommendation"] = {
                    "recommended_approach": "fixed_width_extraction",
                    "detected_fields": fixed_width_analysis.get('detected_fields', []),
                    "record_boundaries": "newline_delimited",
                    "special_handlers_needed": [
                        "Trim whitespace from text fields",
                        "Parse dates from compact format",
                        "Convert numeric fields",
                        "Handle decimal alignment"
                    ]
                }
        
        # If we have AI hypothesis analysis, use it (but prefer fixed-width if strongly detected)
        if hypotheses and 'best_hypothesis' in hypotheses and hypotheses['best_hypothesis']:
            best = hypotheses['best_hypothesis']
            hypothesis_data = best.get('hypothesis', {})
            detailed = hypotheses.get('detailed_analysis', {})
            
            # Only override fixed-width if AI is very confident about something else
            if not fixed_width_analysis.get('is_fixed_width') or best.get('confidence', 0) > 0.9:
                report["format_determination"] = {
                    "confidence": best.get('confidence', 0.0),
                    "detected_format": hypothesis_data.get('format', 'unknown'),
                    "format_family": hypothesis_data.get('format_family', 'unknown'),
                    "structure_type": hypothesis_data.get('structure_type', 'unknown'),
                    "evidence": hypothesis_data.get('evidence', []),
                    "all_hypotheses_tested": len(hypotheses.get('hypotheses', []))
                }
                
                report["parsing_recommendation"] = {
                    "recommended_approach": hypothesis_data.get('parsing_approach', 'adaptive'),
                    "parsing_steps": detailed.get('parsing_steps', []),
                    "field_extraction_rules": detailed.get('field_rules', {}),
                    "record_boundaries": detailed.get('record_boundaries', 'unknown'),
                    "special_handlers_needed": detailed.get('special_considerations', [])
                }
            
            report["hypothesis_ranking"] = [
                {
                    "rank": i + 1,
                    "interpretation": h.get('hypothesis', {}).get('interpretation', 'unknown'),
                    "confidence": h.get('confidence', 0.0)
                }
                for i, h in enumerate(hypotheses.get('hypotheses', []))
            ]
        
        # Add pattern-based insights
        report["structural_insights"] = self._derive_structural_insights(patterns, statistical, fixed_width_analysis)
        
        # Sample of actual data for reference
        report["data_sample"] = {
            "first_100_chars": content[:100],
            "first_5_lines": content.split('\n')[:5],
            "random_middle_sample": content[len(content)//2:len(content)//2 + 100] if len(content) > 200 else ""
        }
        
        return report

    def _derive_structural_insights(self, patterns, statistical, fixed_width_analysis):
        """Derive insights from patterns and statistics"""
        insights = []
        
        # Fixed-width insight
        if fixed_width_analysis.get('is_fixed_width'):
            insights.append(f"Fixed-width format with {fixed_width_analysis.get('record_length')} characters per record")
            insights.append(f"{fixed_width_analysis.get('field_count')} fields detected with consistent positions")
        
        # High entropy suggests compressed or encrypted
        if statistical.get('entropy', 0) > 7:
            insights.append("High entropy detected - possibly compressed or encrypted data")
        
        # Character distribution insights
        if statistical.get('alphabetic_ratio', 0) > 0.7:
            insights.append("Primarily alphabetic - likely text or natural language")
        elif statistical.get('numeric_ratio', 0) > 0.5:
            insights.append("High numeric content - possibly measurements or data tables")
        
        # Line consistency
        if patterns.get('line_length_stats', {}).get('all_same_length'):
            insights.append(f"All lines have exactly {patterns['line_length_stats']['min']} characters")
        
        # Structural insights
        if patterns.get('structural_indicators', {}).get('has_consistent_indentation'):
            insights.append("Consistent indentation detected - hierarchical structure likely")
        
        if patterns.get('structural_indicators', {}).get('has_tabular_structure'):
            insights.append("Tabular patterns detected - possibly delimited data")
        
        if patterns.get('structural_indicators', {}).get('has_key_value_patterns'):
            insights.append("Key-value patterns detected - configuration or record format likely")
        
        return insights

    # Helper methods for pattern checking
    def _check_indentation(self, lines):
        """Check for consistent indentation"""
        indents = []
        for line in lines[:100]:
            if line and not line.lstrip() == line:
                indent = len(line) - len(line.lstrip())
                indents.append(indent)
        
        if indents:
            # Check if indents follow a pattern
            unique_indents = set(indents)
            return len(unique_indents) < 5  # Consistent if only a few indent levels
        return False

    def _check_header_structure(self, lines):
        """Check for header-like structure"""
        if len(lines) < 2:
            return False
        
        # Check if first line looks different from others
        first_line = lines[0] if lines else ""
        if not first_line:
            return False
            
        # Simple heuristic: first line has different pattern
        first_pattern = self._get_line_pattern(first_line)
        other_patterns = [self._get_line_pattern(l) for l in lines[1:10] if l.strip()]
        
        if other_patterns:
            return first_pattern != self._most_common(other_patterns)
        return False

    def _check_record_structure(self, lines):
        """Check for record-like repeating structure"""
        patterns = []
        for line in lines[:100]:
            if line.strip():
                patterns.append(self._get_line_pattern(line))
        
        if patterns:
            pattern_counts = Counter(patterns)
            most_common_count = pattern_counts.most_common(1)[0][1] if pattern_counts else 0
            return most_common_count > len(patterns) * 0.3  # 30% lines have same pattern
        return False

    def _check_nesting(self, content):
        """Check for nested structures"""
        nesting_chars = [
            ('{', '}'),
            ('[', ']'),
            ('(', ')'),
            ('<', '>')
        ]
        
        for open_char, close_char in nesting_chars:
            open_count = content.count(open_char)
            close_count = content.count(close_char)
            if open_count > 2 and close_count > 2 and abs(open_count - close_count) < 3:
                return True
        return False

    def _check_tabular(self, lines):
        """Check for tabular structure"""
        delimiter_counts = defaultdict(list)
        
        for line in lines[:50]:
            if line.strip():
                for delim in [',', '\t', '|', ';']:
                    count = line.count(delim)
                    if count > 0:
                        delimiter_counts[delim].append(count)
        
        # Check if any delimiter appears consistently
        for delim, counts in delimiter_counts.items():
            if len(counts) > 5:
                # Check consistency
                if len(set(counts)) == 1 or (max(counts) - min(counts)) <= 1:
                    return True
        return False

    def _check_key_value(self, lines):
        """Check for key-value patterns"""
        kv_patterns = [
            r'\w+\s*:\s*\S+',  # key: value
            r'\w+\s*=\s*\S+',   # key=value
            r'\w+\s*->\s*\S+',  # key->value
        ]
        
        kv_count = 0
        for line in lines[:50]:
            for pattern in kv_patterns:
                if re.search(pattern, line):
                    kv_count += 1
                    break
        
        return kv_count > len(lines[:50]) * 0.3  # 30% of lines have key-value pattern

    def _check_fixed_width(self, lines):
        """Check for fixed-width format"""
        # Filter non-empty lines
        non_empty = [l for l in lines if l]
        
        if len(non_empty) < 2:
            return False
        
        # Check if all lines have the same length
        lengths = [len(l) for l in non_empty[:100]]  # Sample first 100
        return len(set(lengths)) == 1

    def _get_line_pattern(self, line):
        """Get abstract pattern of a line"""
        pattern = ""
        for char in line[:30]:  # First 30 chars
            if char.isalpha():
                pattern += 'A'
            elif char.isdigit():
                pattern += 'D'
            elif char.isspace():
                pattern += 'S'
            elif char in '.,;:':
                pattern += 'P'
            else:
                pattern += 'X'
        return pattern

    def _parse_json_from_response(self, response_text):
        """Extract JSON from AI response"""
        if not response_text:
            return {}
        
        # Try direct parsing
        try:
            parsed = json.loads(response_text)
            return parsed
        except:
            pass
        
        # Try to find JSON blocks in the response
        json_candidates = []
        
        # Look for array
        start_idx = 0
        while True:
            start = response_text.find('[', start_idx)
            if start == -1:
                break
            
            # Find matching closing bracket
            depth = 0
            end = -1
            for i in range(start, len(response_text)):
                if response_text[i] == '[':
                    depth += 1
                elif response_text[i] == ']':
                    depth -= 1
                    if depth == 0:
                        end = i
                        break
            
            if end > start:
                try:
                    candidate = json.loads(response_text[start:end + 1])
                    json_candidates.append(candidate)
                except:
                    pass
            
            start_idx = start + 1
        
        # Look for object
        start_idx = 0
        while True:
            start = response_text.find('{', start_idx)
            if start == -1:
                break
            
            # Find matching closing brace
            depth = 0
            end = -1
            for i in range(start, len(response_text)):
                if response_text[i] == '{':
                    depth += 1
                elif response_text[i] == '}':
                    depth -= 1
                    if depth == 0:
                        end = i
                        break
            
            if end > start:
                try:
                    candidate = json.loads(response_text[start:end + 1])
                    json_candidates.append(candidate)
                except:
                    pass
            
            start_idx = start + 1
        
        # Return the largest valid JSON structure found
        if json_candidates:
            # Prefer lists over single objects for hypotheses
            for candidate in json_candidates:
                if isinstance(candidate, list):
                    return candidate
            # Return the first valid structure if no list found
            return json_candidates[0]
        
        return {}
    
    def _most_common(self, lst):
        """Helper to get most common element"""
        if not lst:
            return None
        return Counter(lst).most_common(1)[0][0]