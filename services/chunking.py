import nltk
from tiktoken import get_encoding
import logging
import os
from services.html_stripper import clean_text_advanced

logger = logging.getLogger(__name__)

# Global variables for encoding and initialization status
encoding = None
is_initialized = False

def download_nltk_data():
    """Download required NLTK data with proper error handling"""
    required_packages = [
        'punkt',
        'punkt_tab', 
        'stopwords',
        'wordnet',
        'averaged_perceptron_tagger'  # Often needed for tokenization
    ]
    
    for package in required_packages:
        try:
            logger.info(f"Checking NLTK package: {package}")
            # Try to find the data first
            try:
                nltk.data.find(f'tokenizers/{package}')
                logger.info(f"NLTK package {package} already exists")
                continue
            except LookupError:
                pass
            
            try:
                nltk.data.find(f'corpora/{package}')
                logger.info(f"NLTK package {package} already exists")
                continue
            except LookupError:
                pass
                
            try:
                nltk.data.find(f'taggers/{package}')
                logger.info(f"NLTK package {package} already exists")
                continue
            except LookupError:
                pass
            
            # If not found, download it
            logger.info(f"Downloading NLTK package: {package}")
            nltk.download(package, quiet=False)
            logger.info(f"Successfully downloaded NLTK package: {package}")
            
        except Exception as e:
            logger.warning(f"Failed to download NLTK package {package}: {e}")
            # Continue with other packages even if one fails
            continue
    
    # Test if the essential tokenizers work
    try:
        nltk.sent_tokenize("Test sentence.")
        logger.info("NLTK sentence tokenizer test passed")
    except Exception as e:
        logger.error(f"NLTK sentence tokenizer test failed: {e}")
        raise
        
    try:
        nltk.word_tokenize("Test sentence.")
        logger.info("NLTK word tokenizer test passed")
    except Exception as e:
        logger.error(f"NLTK word tokenizer test failed: {e}")
        raise

def initialize_chunking_service():
    """Initialize the chunking service - download NLTK data and set up encoding"""
    global encoding, is_initialized
    
    if is_initialized:
        logger.info("Chunking service already initialized")
        return
    
    try:
        # Try to download and verify NLTK data
        logger.info("Initializing NLTK data...")
        try:
            download_nltk_data()
            logger.info("NLTK data initialized successfully")
        except Exception as e:
            logger.warning(f"NLTK initialization failed: {e}")
            logger.warning("Chunking service will use fallback methods without NLTK")
        
        # Initialize tiktoken encoding
        logger.info("Initializing tiktoken encoding...")
        encoding = get_encoding("cl100k_base")
        
        is_initialized = True
        logger.info("Chunking service initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize chunking service: {e}")
        raise

def num_tokens(text: str) -> int:
    """Count tokens in text using tiktoken encoding"""
    if not is_initialized:
        raise RuntimeError("Chunking service not initialized")
    return len(encoding.encode(text))

class SmartChunker:
    def __init__(self, chunk_token_limit=100, overlap_tokens=20):
        if not is_initialized:
            raise RuntimeError("Chunking service not initialized. Call initialize_chunking_service() first.")
        
        self.chunk_limit = chunk_token_limit
        self.overlap = overlap_tokens
        logger.info(f"SmartChunker initialized with limit: {chunk_token_limit}, overlap: {overlap_tokens}")

    def split(self, text: str):
        """Split text into chunks with overlap using sentence tokenization first, then word tokenization"""
        logger.info(f"Splitting text of length: {len(text)} characters")
        
        # First, try sentence tokenization
        try:
            text = clean_text_advanced(text)
            sentences = nltk.sent_tokenize(text)
        except Exception as e:
            logger.warning(f"Sentence tokenization failed: {e}, falling back to simple sentence splitting")
            # If sentence tokenization fails, fall back to simple sentence splitting
            sentences = self._simple_sentence_split(text)
        
        chunks, current_chunk = [], []

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            sentence_tokens = num_tokens(sentence)
            chunk_limit_with_buffer = self.chunk_limit + int(self.chunk_limit * 0.1)  # Add 10% buffer
            
            # If sentence is larger than chunk_limit + 10%, split by word tokenization
            if sentence_tokens > chunk_limit_with_buffer:
                logger.debug(f"Long sentence detected ({sentence_tokens} tokens > {chunk_limit_with_buffer}), splitting by words")
                subchunks = self._split_long_sentence(sentence)
                
                for sub in subchunks:
                    if not sub.strip():
                        continue
                    
                    sub_tokens = num_tokens(sub)
                    # If subchunk is less than chunk_limit, try to add to current chunk
                    if sub_tokens <= self.chunk_limit:
                        self._add_to_chunks(sub.strip(), chunks, current_chunk)
                    else:
                        # Subchunk is still too large, treat as separate chunk
                        # First save current chunk if it has content
                        if current_chunk:
                            chunks.append(" ".join(current_chunk))
                            current_chunk.clear()
                        
                        # Add the large subchunk as its own chunk
                        chunks.append(sub.strip())
            else:
                # Normal sentence, add to chunks
                self._add_to_chunks(sentence, chunks, current_chunk)

        # Add remaining chunk if exists
        if current_chunk:
            chunks.append(" ".join(current_chunk))

        logger.info(f"Created {len(chunks)} chunks")
        return chunks

    def _simple_sentence_split(self, text: str):
        """Simple sentence splitting as fallback when NLTK is not available"""
        import re
        # Simple regex-based sentence splitting
        sentences = re.split(r'[.!?]+\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _split_by_words(self, text: str):
        """Fallback method to split text by words when sentence tokenization fails"""
        logger.info("Using word-based chunking as fallback")
        
        try:
            words = nltk.word_tokenize(text)
        except:
            # Ultimate fallback to simple split
            logger.warning("NLTK word tokenization failed, using simple string split")
            words = text.split()
        
        chunks = []
        current_words = []
        
        for word in words:
            test_words = current_words + [word]
            test_text = " ".join(test_words)
            
            if num_tokens(test_text) > self.chunk_limit and current_words:
                # Save current chunk
                chunks.append(" ".join(current_words))
                
                # Create overlap
                overlap_size = min(len(current_words), self.overlap)
                overlap_words = current_words[-overlap_size:] if overlap_size > 0 else []
                current_words = overlap_words + [word]
            else:
                current_words.append(word)
        
        # Add remaining words
        if current_words:
            chunks.append(" ".join(current_words))
        
        return chunks

    def _split_long_sentence(self, sentence):
        """Split long sentences using word tokenization"""
        # Use word tokenization directly
        try:
            words = nltk.word_tokenize(sentence)
        except:
            # Fallback to simple split if word_tokenize fails
            words = sentence.split()
        
        if len(words) <= 1:
            return [sentence]  # Can't split further
        
        # Create chunks based on word tokenization
        word_chunks = []
        current_words = []
        
        for word in words:
            # Test adding this word
            test_words = current_words + [word]
            test_text = " ".join(test_words)
            
            # If adding this word exceeds limit and we have words, start new chunk
            if num_tokens(test_text) > self.chunk_limit and current_words:
                # Save current chunk
                word_chunks.append(" ".join(current_words))
                current_words = [word]  # Start new chunk with current word
            else:
                current_words.append(word)
        
        # Add remaining words as final chunk
        if current_words:
            word_chunks.append(" ".join(current_words))
        
        return word_chunks if word_chunks else [sentence]

    def _add_to_chunks(self, sentence, chunks, current_chunk):
        """Add sentence to current chunk, creating new chunk if token limit is exceeded."""
        test_chunk = current_chunk + [sentence]
        test_tokens = num_tokens(" ".join(test_chunk))

        if test_tokens > self.chunk_limit:
            # Save the current chunk
            chunks.append(" ".join(current_chunk))

            # Get last N tokens from the saved chunk as overlap
            flat_chunk = " ".join(current_chunk)
            tokens = encoding.encode(flat_chunk)

            # Get the last self.overlap tokens and decode to text
            overlap_token_ids = tokens[-self.overlap:]
            overlap_text = encoding.decode(overlap_token_ids)

            # Start a new chunk with the overlap + current sentence
            current_chunk.clear()
            current_chunk.append(overlap_text.strip())  # prepend overlap
            current_chunk.append(sentence)
        else:
            current_chunk.append(sentence)

