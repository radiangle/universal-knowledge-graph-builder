import requests
from bs4 import BeautifulSoup
import re
from typing import List, Dict, Any
import streamlit as st


class DocumentProcessor:
    def __init__(self, chunk_size: int = 500):
        self.chunk_size = chunk_size
    
    def process_text_file(self, file_content: str) -> List[Dict[str, Any]]:
        """Process uploaded text file into chunks"""
        try:
            chunks = self._chunk_text(file_content)
            return [
                {
                    'id': f'chunk_{i}',
                    'text': chunk,
                    'source': 'uploaded_file',
                    'chunk_index': i
                }
                for i, chunk in enumerate(chunks)
            ]
        except Exception as e:
            st.error(f"Error processing text file: {str(e)}")
            return []
    
    def process_url(self, url: str) -> List[Dict[str, Any]]:
        """Scrape and process web content"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Extract text
            text = soup.get_text()
            text = self._clean_text(text)
            
            chunks = self._chunk_text(text)
            return [
                {
                    'id': f'url_chunk_{i}',
                    'text': chunk,
                    'source': url,
                    'chunk_index': i
                }
                for i, chunk in enumerate(chunks)
            ]
        except Exception as e:
            st.error(f"Error processing URL {url}: {str(e)}")
            return []
    
    def _clean_text(self, text: str) -> str:
        """Clean extracted text"""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters but keep punctuation
        text = re.sub(r'[^\w\s.,!?;:()\-\'""]', ' ', text)
        return text.strip()
    
    def _chunk_text(self, text: str) -> List[str]:
        """Split text into chunks of approximately chunk_size words"""
        words = text.split()
        chunks = []
        
        for i in range(0, len(words), self.chunk_size):
            chunk = ' '.join(words[i:i + self.chunk_size])
            if len(chunk.strip()) > 50:  # Only include substantial chunks
                chunks.append(chunk)
        
        return chunks
    
    def validate_file_size(self, file_content: str, max_size_mb: int = 100) -> bool:
        """Validate file size doesn't exceed limit"""
        size_mb = len(file_content.encode('utf-8')) / (1024 * 1024)
        return size_mb <= max_size_mb