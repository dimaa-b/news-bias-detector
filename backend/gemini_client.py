import google.generativeai as genai
import os
from dotenv import load_dotenv
import json
from typing import Optional, List, Dict, Any
import logging

# Load environment variables
load_dotenv()

class GeminiClient:
    """
    A client for interacting with Google's Gemini API for text generation and analysis
    """
    
    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-2.5-pro"):
        """
        Initialize the Gemini client
        
        Args:
            api_key (str, optional): Gemini API key. If not provided, loads from GEMINI_API_KEY env var
            model_name (str): The Gemini model to use (default: gemini-2.5-pro)
        """
        # Get API key from parameter or environment
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables or parameters")
        
        # Configure the API
        genai.configure(api_key=self.api_key)
        
        # Initialize the model
        self.model_name = model_name
        self.model = genai.GenerativeModel(model_name)
        
        # Set up logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Generation configuration
        self.generation_config = {
            'temperature': 0.7,
            'top_p': 0.95,
            'top_k': 40,
            'max_output_tokens': 8192,
        }
        
        # Safety settings
        self.safety_settings = [
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
            {
                "category": "HARM_CATEGORY_HATE_SPEECH",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
            {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
        ]
    
    def generate_text(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """
        Generate text using Gemini
        
        Args:
            prompt (str): The input prompt
            **kwargs: Additional generation config parameters
            
        Returns:
            dict: Response containing generated text and metadata
        """
        try:
            # Merge custom config with defaults
            config = {**self.generation_config, **kwargs}
            
            # Generate content
            response = self.model.generate_content(
                prompt,
                generation_config=config,
                safety_settings=self.safety_settings
            )
            
            return {
                'success': True,
                'text': response.text,
                'prompt_tokens': response.usage_metadata.prompt_token_count if hasattr(response, 'usage_metadata') else None,
                'completion_tokens': response.usage_metadata.candidates_token_count if hasattr(response, 'usage_metadata') else None,
                'total_tokens': response.usage_metadata.total_token_count if hasattr(response, 'usage_metadata') else None,
                'model': self.model_name
            }
            
        except Exception as error:
            self.logger.error(f"Error generating text: {error}")
            return {
                'success': False,
                'error': str(error),
                'text': None
            }
    
    def analyze_claims_and_rhetoric(
        self, 
        target_title: str,
        target_text: str,
        references: List[Dict[str, Any]],
        target_date: str = "Unknown"
    ) -> Dict[str, Any]:
        """
        Analyze claims and rhetoric in a target article against reference articles
        
        Args:
            target_title (str): Title of the target article to analyze
            target_text (str): Full text of the target article
            references (list): List of reference articles with keys: title, text, date (optional), url (optional)
            target_date (str, optional): Publication date of target article (YYYY-MM-DD or "Unknown")
            
        Returns:
            dict: Detailed claims and rhetoric analysis
        """
        # Format references as JSON array
        references_json = []
        for i, ref in enumerate(references, 1):
            references_json.append({
                "ref_id": f"R{i}",
                "title": ref.get('title', 'Untitled'),
                "date": ref.get('date') or ref.get('publish_date') or None,
                "url": ref.get('url', None),
                "text": ref.get('text', '')
            })
        
        references_json_str = json.dumps(references_json, indent=2)
        
        prompt = f"""You are an impartial claims-and-rhetoric analyst.

You will review a TARGET article sentence-by-sentence against trusted REFERENCE articles (treated as ground truth for this task).

########################
# INPUT (fill in below)
########################
TARGET_TITLE: {target_title}
TARGET_DATE: {target_date}
TARGET_TEXT:
{target_text}

REFERENCES_JSON:
{references_json_str}

########################
# OBJECTIVES
########################
1) For each sentence in TARGET_TEXT:
   - Detect if it contains a factual claim.
   - Assign a verdict:
     Supported | Contradicted | Unverifiable | Misleading by context | No factual claim
   - Tag sentence type (multi-select):
     Factual claim | Opinion/Value | Reported speech/Quote | Rhetorical/Framing
   - Identify issues (multi-select, as applicable):
     Cherry-picking, Missing context, Loaded language, False equivalence, Strawman,
     Out-of-date statistic, Ambiguous attribution, Anecdotal evidence, Hasty generalization,
     Appeal to authority, Whataboutism, Motte-and-Bailey, Gish gallop
   - Extract a succinct checkable claim (or null).
   - Provide evidence citations from REFERENCES_JSON with brief quotes (≤20 words) and a locator.
   - Give a concise explanation ≤40 words.
   - Add a confidence score 0.00–1.00.

2) Provide an overall pattern summary, suggested corrections, and an overall assessment.

########################
# GROUND RULES
########################
- Evidence scope: Use ONLY REFERENCES_JSON. If coverage is insufficient, mark Unverifiable; do NOT speculate.
- Attribution: Distinguish author narration vs. quoted/attributed speech. Flag selective or misleading quoting.
- Numbers & stats: Check rates, denominators, units, date ranges, and comparability. Prefer the most recent relevant reference when conflicts exist.
- Time/context: If key bounds/denominators/context are omitted vs. references, use "Misleading by context" and specify what's missing.
- Conciseness: Per-sentence explanations ≤40 words; quotes from references ≤20 words.
- No chain-of-thought: Do all reasoning internally and output ONLY the JSON specified below.
- Formatting: Return valid JSON (no trailing commas). Do not include any extra prose before or after the JSON.

########################
# OUTPUT (return EXACTLY this JSON shape)
########################
{{
  "document_metadata": {{
    "target_title": "{target_title}",
    "target_date": "{target_date}",
    "references_used": [
      {{"ref_id": "R1", "title": "...", "date": "YYYY-MM-DD or null", "url": "https://... or null"}}
    ]
  }},
  "sentence_reviews": [
    {{
      "index": 1,
      "sentence": "<original sentence>",
      "types": ["Factual claim" | "Opinion/Value" | "Reported speech/Quote" | "Rhetorical/Framing"],
      "verdict": "Supported" | "Contradicted" | "Unverifiable" | "Misleading by context" | "No factual claim",
      "issues": ["Cherry-picking", "Missing context", "Loaded language", "False equivalence", "Strawman", "Out-of-date statistic", "Ambiguous attribution", "Anecdotal evidence", "Hasty generalization", "Appeal to authority", "Whataboutism", "Motte-and-Bailey", "Gish gallop"],
      "claim_extracted": "<succinct restatement or null>",
      "evidence": [
        {{
          "ref_id": "R1",
          "locator": "paragraph 5",
          "quote": "<=20 words from reference>",
          "alignment": "supports" | "contradicts" | "context"
        }}
      ],
      "explanation": "<=40 words, evidence-based>",
      "confidence": 0.0
    }}
  ],
  "pattern_summary": {{
    "counts_by_verdict": {{
      "Supported": 0,
      "Contradicted": 0,
      "Unverifiable": 0,
      "Misleading by context": 0,
      "No factual claim": 0
    }},
    "top_recurring_patterns": [
      {{"pattern": "Missing context", "instances": 0, "example_sentence_index": 0}}
    ],
    "notable_omissions": [
      {{"description": "<relevant missing context>", "reference_ref_id": "R?"}}
    ]
  }},
  "suggested_corrections": [
    {{
      "sentence_index": 0,
      "problem": "<short description>",
      "proposed_fix": "<revised sentence or added context>",
      "rationale": "<=30 words>"
    }}
  ],
  "overall_assessment": {{
    "misleading_risk_score": 0,
    "summary": "3-4 sentence overview of accuracy and patterns in plain language."
  }}
}}"""

        try:
            # Use lower temperature for more consistent structured output
            response = self.generate_text(prompt, temperature=0.2, max_output_tokens=8192)
            
            if not response['success']:
                return response
            
            # Try to parse JSON from response
            text = response['text'].strip()
            
            # Extract JSON if wrapped in markdown code blocks
            if text.startswith('```'):
                parts = text.split('```')
                if len(parts) >= 2:
                    text = parts[1]
                    if text.startswith('json'):
                        text = text[4:].strip()
            
            try:
                analysis = json.loads(text)
                return {
                    'success': True,
                    'analysis': analysis,
                    'raw_response': response['text'],
                    'tokens_used': response.get('total_tokens')
                }
            except json.JSONDecodeError as e:
                # If JSON parsing fails, return error with details
                return {
                    'success': False,
                    'error': f'Failed to parse JSON response: {str(e)}',
                    'raw_response': response['text'],
                    'tokens_used': response.get('total_tokens')
                }
                
        except Exception as error:
            self.logger.error(f"Error analyzing claims and rhetoric: {error}")
            return {
                'success': False,
                'error': str(error)
            }


# Create a global instance for easy import
gemini_client = GeminiClient()


def analyze_claims_simple(target_title: str, target_text: str, references: List[Dict[str, Any]], target_date: str = "Unknown"):
    """
    Simple function to analyze claims and rhetoric in an article
    """
    return gemini_client.analyze_claims_and_rhetoric(target_title, target_text, references, target_date)

