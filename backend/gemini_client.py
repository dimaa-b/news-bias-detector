from google import genai
from google.genai import types
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
    
    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-flash-latest"):
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
        
        # Initialize the client
        self.client = genai.Client(api_key=self.api_key)
        
        # Store the model name
        self.model_name = model_name
        
        # Set up logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Generation configuration
        self.generation_config = types.GenerateContentConfig(
            temperature=0.7,
            top_p=0.95,
            top_k=40,
            max_output_tokens=65536,
            safety_settings=[
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                    threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                ),
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                    threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                ),
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                    threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                ),
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                    threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                ),
            ]
        )
    
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
            # Create config with custom parameters
            config_params = {
                'temperature': kwargs.get('temperature', 0.7),
                'top_p': kwargs.get('top_p', 0.95),
                'top_k': kwargs.get('top_k', 40),
                'max_output_tokens': kwargs.get('max_output_tokens', 65536),
                'safety_settings': self.generation_config.safety_settings
            }
            
            config = types.GenerateContentConfig(**config_params)
            
            # Generate content
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config
            )
            
            # Extract text from response
            text = None
            if hasattr(response, 'text'):
                text = response.text
            elif hasattr(response, 'candidates') and len(response.candidates) > 0:
                candidate = response.candidates[0]
                if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                    parts = candidate.content.parts
                    if len(parts) > 0 and hasattr(parts[0], 'text'):
                        text = parts[0].text
            
            # Check finish reason for truncation
            finish_reason = None
            if hasattr(response, 'candidates') and len(response.candidates) > 0:
                if hasattr(response.candidates[0], 'finish_reason'):
                    finish_reason = str(response.candidates[0].finish_reason)
            
            if text is None:
                error_msg = f"No text found in response. Response type: {type(response)}"
                if finish_reason:
                    error_msg += f", Finish reason: {finish_reason}"
                if finish_reason == 'FinishReason.MAX_TOKENS' or 'MAX_TOKENS' in str(finish_reason):
                    error_msg += ". Try increasing max_output_tokens or using a model with larger context."
                raise ValueError(error_msg)
            
            return {
                'success': True,
                'text': text,
                'prompt_tokens': response.usage_metadata.prompt_token_count if hasattr(response, 'usage_metadata') else None,
                'completion_tokens': response.usage_metadata.candidates_token_count if hasattr(response, 'usage_metadata') else None,
                'total_tokens': response.usage_metadata.total_token_count if hasattr(response, 'usage_metadata') else None,
                'model': self.model_name,
                'finish_reason': finish_reason
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
            # Use higher max_output_tokens for large analysis responses
            response = self.generate_text(prompt, temperature=0.2, max_output_tokens=65536)
            
            if not response['success']:
                return response
            
            # Check if text exists
            if response.get('text') is None:
                return {
                    'success': False,
                    'error': 'Response text is None',
                    'raw_response': str(response)
                }
            
            # Log token usage for debugging
            total_tokens = response.get('total_tokens')
            prompt_tokens = response.get('prompt_tokens')
            completion_tokens = response.get('completion_tokens')
            finish_reason = response.get('finish_reason', 'UNKNOWN')
            self.logger.info(f"Token usage - Prompt: {prompt_tokens}, Completion: {completion_tokens}, Total: {total_tokens}, Finish: {finish_reason}")
            
            # Check if response was truncated due to max tokens
            if 'MAX_TOKENS' in str(finish_reason):
                self.logger.error(f"Response was truncated! Finish reason: {finish_reason}")
                return {
                    'success': False,
                    'error': f'Response truncated due to MAX_TOKENS. Used {completion_tokens} output tokens. The article or references may be too long. Try using fewer or shorter reference articles.',
                    'raw_response': response.get('text', ''),
                    'tokens_used': total_tokens
                }
            
            # Check if we're close to max tokens (might indicate truncation)
            if completion_tokens and completion_tokens >= 64000:
                self.logger.warning(f"Response used {completion_tokens} completion tokens, very close to the 65536 limit.")
            
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
                self.logger.error(f"JSON parsing failed at line {e.lineno}, column {e.colno}")
                self.logger.error(f"Error: {e.msg}")
                # Log a snippet around the error location
                lines = text.split('\n')
                if e.lineno <= len(lines):
                    start = max(0, e.lineno - 3)
                    end = min(len(lines), e.lineno + 2)
                    self.logger.error(f"Context around error (lines {start+1}-{end+1}):")
                    for i in range(start, end):
                        marker = " >>> " if i == e.lineno - 1 else "     "
                        self.logger.error(f"{marker}{i+1}: {lines[i]}")
                
                return {
                    'success': False,
                    'error': f'Failed to parse JSON response: {str(e)}',
                    'raw_response': response['text'],
                    'tokens_used': response.get('total_tokens'),
                    'json_error_details': {
                        'line': e.lineno,
                        'column': e.colno,
                        'message': e.msg
                    }
                }
                
        except Exception as error:
            self.logger.error(f"Error analyzing claims and rhetoric: {error}")
            return {
                'success': False,
                'error': str(error)
            }


    def analyze_claims_streaming(self, target_title: str, target_text: str, references: List[Dict[str, Any]], target_date: str = "Unknown"):
        """
        Analyze claims and rhetoric in an article with streaming results sentence by sentence
        
        Yields:
            dict: Streaming chunks with analysis progress
        """
        # Split target text into sentences
        import re
        # Simple sentence splitter (you might want a more sophisticated one)
        sentences = re.split(r'(?<=[.!?])\s+', target_text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        total_sentences = len(sentences)
        
        yield {
            'type': 'analysis_start',
            'total_sentences': total_sentences,
            'target_title': target_title,
            'target_date': target_date
        }
        
        # Prepare references JSON
        references_json = []
        for i, ref in enumerate(references, start=1):
            references_json.append({
                "ref_id": f"R{i}",
                "title": ref.get('title', 'Untitled'),
                "date": ref.get('date', 'Unknown'),
                "url": ref.get('url', 'Unknown'),
                "text": ref.get('text', '')
            })
        
        # Process sentences in batches for efficiency
        batch_size = 5
        all_sentence_reviews = []
        
        for batch_start in range(0, total_sentences, batch_size):
            batch_end = min(batch_start + batch_size, total_sentences)
            batch_sentences = sentences[batch_start:batch_end]
            
            # Create prompt for this batch
            sentences_text = "\n".join([f"{i+batch_start+1}. {s}" for i, s in enumerate(batch_sentences)])
            
            prompt = f"""You are analyzing sentences from a news article for factual accuracy and bias.

TARGET ARTICLE: {target_title}
DATE: {target_date}

SENTENCES TO ANALYZE (indices {batch_start + 1} to {batch_end}):
{sentences_text}

REFERENCES (use ONLY these for verification):
{json.dumps(references_json, indent=2)}

For each sentence, provide:
- index: sentence number
- sentence: the original text
- types: array of ["Factual claim" | "Opinion/Value" | "Reported speech/Quote" | "Rhetorical/Framing"]
- verdict: "Supported" | "Contradicted" | "Unverifiable" | "Misleading by context" | "No factual claim"
- issues: array of potential issues like ["Cherry-picking", "Missing context", "Loaded language", etc.]
- claim_extracted: succinct restatement or null
- evidence: array of {{ref_id, locator, quote (≤20 words), alignment}}
- explanation: ≤40 words
- confidence: 0.0-1.0

Return ONLY valid JSON array of sentence reviews:
[
  {{
    "index": {batch_start + 1},
    "sentence": "...",
    "types": [...],
    "verdict": "...",
    "issues": [...],
    "claim_extracted": "..." or null,
    "evidence": [...],
    "explanation": "...",
    "confidence": 0.0
  }}
]"""

            try:
                # Generate analysis for this batch
                response = self.generate_text(prompt, temperature=0.2, max_output_tokens=8192)
                
                if response['success']:
                    text = response['text'].strip()
                    
                    # Extract JSON if wrapped in markdown
                    if text.startswith('```'):
                        parts = text.split('```')
                        if len(parts) >= 2:
                            text = parts[1]
                            if text.startswith('json'):
                                text = text[4:].strip()
                    
                    try:
                        batch_reviews = json.loads(text)
                        all_sentence_reviews.extend(batch_reviews)
                        
                        # Yield each sentence review
                        for review in batch_reviews:
                            yield {
                                'type': 'sentence_review',
                                'data': review,
                                'progress': {
                                    'current': review['index'],
                                    'total': total_sentences
                                }
                            }
                    except json.JSONDecodeError as e:
                        yield {
                            'type': 'error',
                            'message': f'Failed to parse batch {batch_start + 1}-{batch_end}: {str(e)}',
                            'batch_start': batch_start + 1,
                            'batch_end': batch_end
                        }
                else:
                    yield {
                        'type': 'error',
                        'message': f'Failed to analyze batch {batch_start + 1}-{batch_end}: {response.get("error")}',
                        'batch_start': batch_start + 1,
                        'batch_end': batch_end
                    }
                    
            except Exception as error:
                yield {
                    'type': 'error',
                    'message': f'Error analyzing batch {batch_start + 1}-{batch_end}: {str(error)}',
                    'batch_start': batch_start + 1,
                    'batch_end': batch_end
                }
        
        # Generate final summary
        if all_sentence_reviews:
            yield {
                'type': 'generating_summary',
                'message': 'Generating overall assessment...'
            }
            
            # Count verdicts
            verdict_counts = {}
            for review in all_sentence_reviews:
                verdict = review.get('verdict', 'Unknown')
                verdict_counts[verdict] = verdict_counts.get(verdict, 0) + 1
            
            # Calculate risk score (simple heuristic)
            total_reviews = len(all_sentence_reviews)
            risk_score = 0
            if total_reviews > 0:
                contradicted = verdict_counts.get('Contradicted', 0)
                misleading = verdict_counts.get('Misleading by context', 0)
                risk_score = min(100, int(((contradicted * 2 + misleading * 1.5) / total_reviews) * 100))
            
            # Generate summary using Gemini
            summary_prompt = f"""Based on this sentence-by-sentence analysis, provide a 3-4 sentence summary of the article's accuracy and any patterns of bias or misleading information.

Article: {target_title}
Analyzed: {total_reviews} sentences
Verdict counts: {json.dumps(verdict_counts)}

Provide a concise, plain-language summary."""

            summary_response = self.generate_text(summary_prompt, temperature=0.3, max_output_tokens=512)
            summary_text = summary_response.get('text', 'Analysis complete.') if summary_response['success'] else 'Analysis complete.'
            
            # Send final summary
            yield {
                'type': 'analysis_complete',
                'data': {
                    'pattern_summary': {
                        'counts_by_verdict': verdict_counts,
                        'total_sentences': total_reviews
                    },
                    'overall_assessment': {
                        'misleading_risk_score': risk_score,
                        'summary': summary_text
                    },
                    'document_metadata': {
                        'target_title': target_title,
                        'target_date': target_date,
                        'references_used': [
                            {
                                'ref_id': ref['ref_id'],
                                'title': ref['title'],
                                'date': ref['date'],
                                'url': ref['url']
                            } for ref in references_json
                        ]
                    }
                }
            }


# Create a global instance for easy import
gemini_client = GeminiClient()


def analyze_claims_simple(target_title: str, target_text: str, references: List[Dict[str, Any]], target_date: str = "Unknown"):
    """
    Simple function to analyze claims and rhetoric in an article
    """
    return gemini_client.analyze_claims_and_rhetoric(target_title, target_text, references, target_date)

