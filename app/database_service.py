"""
Database Service Module
Handles all database access operations for IPA transcriptions.
"""
import sqlite3
from typing import Optional
import os


class DatabaseService:
    """Service for database operations"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._validate_db()
    
    def _validate_db(self):
        """Validate that database exists and is accessible"""
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Database file not found: {self.db_path}")
    
    def lookup_word(self, word: str, accent: str) -> Optional[str]:
        """
        Lookup a word in the database
        
        Args:
            word: Word to look up
            accent: 'american' or 'rp'
            
        Returns:
            IPA transcription or None if not found
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute("SELECT us, gb FROM ipa WHERE word=?", (word.lower(),))
            row = cur.fetchone()
            conn.close()
            
            if not row:
                return None
            
            us, gb = row
            if accent == 'american':
                return us or gb
            return gb or us
            
        except sqlite3.Error as e:
            # Log error in production
            print(f"Database error: {e}")
            return None
    
    def get_word_count(self) -> int:
        """Get total number of words in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM ipa")
            count = cur.fetchone()[0]
            conn.close()
            return count
        except sqlite3.Error:
            return 0
    
    def word_exists(self, word: str) -> bool:
        """Check if a word exists in database"""
        return self.lookup_word(word, 'american') is not None or self.lookup_word(word, 'rp') is not None