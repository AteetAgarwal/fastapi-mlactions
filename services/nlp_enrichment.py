"""
NLP Enrichment Service for extracting entities, keyword phrases, and generating questions
"""
import spacy
from keybert import KeyBERT
import logging
import subprocess
import sys
from typing import Dict, List, Optional


logger = logging.getLogger(__name__)

def download_spacy_model(model_name: str = "en_core_web_sm") -> bool:
    """
    Download spaCy model if it doesn't exist
    
    Args:
        model_name: Name of the spaCy model to download
    
    Returns:
        True if model is available (either already existed or was downloaded successfully)
    """
    try:
        # Try to load the model to check if it exists
        spacy.load(model_name)
        logger.info(f"spaCy model '{model_name}' already exists")
        return True
    except OSError:
        # Model doesn't exist, try to download it
        logger.info(f"spaCy model '{model_name}' not found. Downloading...")
        try:
            # Use uv to run the spacy download command
            logger.info(f"Downloading spaCy model '{model_name}' using uv...")
            result = subprocess.run([
                "uv", "run", "python", "-m", "spacy", "download", model_name
            ], capture_output=True, text=True, check=True)
            
            logger.info(f"Successfully downloaded spaCy model '{model_name}'")
            logger.debug(f"Download output: {result.stdout}")
            
            # Verify the model can be loaded after download
            try:
                spacy.load(model_name)
                return True
            except OSError as e:
                logger.error(f"Model downloaded but cannot be loaded: {e}")
                return False
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to download spaCy model '{model_name}': {e}")
            logger.error(f"Error output: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error downloading spaCy model '{model_name}': {e}")
            return False

class NLPEnrichmentService:
    """Service for NLP enrichment including entity extraction, keyword extraction, and question generation"""
    
    def __init__(self):
        self.nlp = None
        self.kw_model = None
        self._initialized = False
        
    def initialize(self):
        """Initialize the NLP models"""
        try:
            logger.info("Initializing NLP enrichment service...")
            
            # Download spaCy model if it doesn't exist
            model_name = "en_core_web_sm"
            if not download_spacy_model(model_name):
                raise Exception(f"Failed to download or load spaCy model '{model_name}'")
            
            # Load spaCy model
            self.nlp = spacy.load(model_name)
            
            # Load KeyBERT model
            self.kw_model = KeyBERT()
            
            self._initialized = True
            logger.info("NLP enrichment service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize NLP enrichment service: {e}")
            raise
    
    @property
    def is_initialized(self) -> bool:
        """Check if the service is properly initialized"""
        return self._initialized and self.nlp is not None and self.kw_model is not None
    
    def is_valid_phrase(self, phrase: str) -> bool:
        """Filter out noisy phrases"""
        phrase = phrase.strip().lower()
        if not phrase or len(phrase.split()) < 2:
            return False
            
        bad_chars = [":", "\\", "/", "[", "]", "|", "http", "@", "#", "main content"]
        if any(ch in phrase for ch in bad_chars):
            return False
            
        if phrase.startswith(("the ", "a ", "an ")):
            return False
            
        return True
    
    def extract_entities(self, text: str) -> List[str]:
        """Extract named entities from text"""
        if not self.is_initialized:
            raise RuntimeError("NLP service not initialized")
            
        doc = self.nlp(text)
        # Filter out date, time, and percent entities as they're usually less useful
        entities = [
            ent.text.strip() 
            for ent in doc.ents 
            if ent.label_ not in ["DATE", "TIME", "PERCENT"] and ent.text.strip()
        ]
        return list(set(entities))
    
    def extract_keyword_phrases(self, text: str) -> List[str]:
        """Extract keyword phrases using both KeyBERT and spaCy"""
        if not self.is_initialized:
            raise RuntimeError("NLP service not initialized")
            
        # KeyBERT keyword phrases (semantic)
        try:
          
            try:
                # with top_k first 
                keybert_results = self.kw_model.extract_keywords(
                    text, 
                    keyphrase_ngram_range=(1, 3), 
                    stop_words='english',
                    top_k=15
                )
            except TypeError:
                keybert_results = self.kw_model.extract_keywords(
                    text, 
                    keyphrase_ngram_range=(1, 3), 
                    stop_words='english'
                )
                # Limit to top 15 manually
                keybert_results = keybert_results[:15]
            
            keybert_keywords = [
                kw for kw, score in keybert_results
                if self.is_valid_phrase(kw)
            ]
        except Exception as e:
            logger.warning(f"KeyBERT extraction failed: {e}")
            keybert_keywords = []
        
        # spaCy noun chunks (linguistic)
        doc = self.nlp(text)
        spacy_phrases = [
            chunk.text.strip() 
            for chunk in doc.noun_chunks 
            if self.is_valid_phrase(chunk.text)
        ]
        
        # Merge and deduplicate
        keyword_phrases = list(set(keybert_keywords + spacy_phrases))
        return keyword_phrases[:20]  # Return top 20 to avoid overwhelming the LLM
    
    def generate_potential_questions(self, keyword_phrases: List[str]) -> List[str]:
        """Generate potential questions from keyword phrases"""
        potential_questions = []
        
        top_phrases = keyword_phrases[:5]
        
        question_templates = [
            "What is {}?",
            "How does {} work?", 
            "Why is {} important?",
            "How to implement {}?",
            "What are the benefits of {}?",
            "How to troubleshoot {}?",
            "What are {} best practices?"
        ]
        
        for phrase in top_phrases:
            for template in question_templates:
                potential_questions.append(template.format(phrase))
                
        return potential_questions[:25] 
    
    def enrich_content(self, title: str, description: str, body_content: str = "") -> Dict:
        """
        Perform complete NLP enrichment on content
        
        Args:
            title: Document title
            description: Document description
            body_content: Main body content
            
        Returns:
            Dictionary containing entities, keyword_phrases, and potential_questions
        """
        if not self.is_initialized:
            raise RuntimeError("NLP service not initialized. Call initialize() first.")
            
        # Combine all text for analysis
        combined_text = f"{title}. {description}. {body_content}".strip()
        
        if not combined_text or len(combined_text) < 10:
            return {
                "entities": [],
                "keyword_phrases": [],
                "potential_questions": []
            }
        
        try:
            # Extract entities
            entities = self.extract_entities(combined_text)
            
            # Extract keyword phrases
            keyword_phrases = self.extract_keyword_phrases(combined_text)
            
            # Generate questions
            potential_questions = self.generate_potential_questions(keyword_phrases)
            
            return {
                "entities": entities,
                "keyword_phrases": keyword_phrases,
                "potential_questions": potential_questions
            }
            
        except Exception as e:
            logger.error(f"Error during NLP enrichment: {e}")
            # Return empty results on error rather than failing
            return {
                "entities": [],
                "keyword_phrases": [],
                "potential_questions": []
            }

# Global service instance
nlp_enrichment_service = NLPEnrichmentService()

def initialize_nlp_service():
    """Initialize the global NLP enrichment service"""
    nlp_enrichment_service.initialize()

def get_nlp_service() -> NLPEnrichmentService:
    """Get the global NLP enrichment service instance"""
    return nlp_enrichment_service