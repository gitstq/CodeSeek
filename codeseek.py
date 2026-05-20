#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CodeSeek - Lightweight Local Semantic Code Search Engine
轻量级本地语义代码搜索引擎

A zero-dependency, privacy-first semantic code search tool.
Supports multi-backend embedding (GLM-5.1, OpenAI-compatible, local),
hybrid search (vector + BM25), and TUI interface.

Author: gitstq
License: MIT
"""

import os
import sys
import json
import hashlib
import sqlite3
import argparse
import re
import math
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Tuple, Set
from datetime import datetime
from collections import Counter
import urllib.request
import urllib.error
import urllib.parse

__version__ = "1.0.0"
__author__ = "gitstq"

# ANSI Color Codes
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    
    # Foreground colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    
    # Bright foreground
    BRIGHT_BLACK = "\033[90m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"
    
    # Background colors
    BG_BLACK = "\033[40m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN = "\033[46m"
    BG_WHITE = "\033[47m"


@dataclass
class CodeSnippet:
    """Represents a code snippet extracted from source files."""
    file_path: str
    start_line: int
    end_line: int
    snippet_type: str  # 'function', 'class', 'method', 'module'
    name: str
    content: str
    language: str
    docstring: str = ""
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'CodeSnippet':
        return cls(**data)


@dataclass
class SearchResult:
    """Represents a search result."""
    snippet: CodeSnippet
    score: float
    match_type: str  # 'semantic', 'keyword', 'hybrid'
    
    def to_dict(self) -> Dict:
        return {
            'snippet': self.snippet.to_dict(),
            'score': self.score,
            'match_type': self.match_type
        }


class Config:
    """Configuration management for CodeSeek."""
    
    DEFAULT_CONFIG = {
        'embedding_backend': 'glm',  # 'glm', 'openai', 'local'
        'glm_api_url': 'https://open.bigmodel.cn/api/paas/v4/embeddings',
        'glm_api_key': os.environ.get('GLM_API_KEY', ''),
        'openai_api_url': 'https://api.openai.com/v1/embeddings',
        'openai_api_key': os.environ.get('OPENAI_API_KEY', ''),
        'embedding_model': 'embedding-3',
        'vector_dim': 1024,
        'index_path': '.codeseek/index.db',
        'cache_path': '.codeseek/cache',
        'supported_languages': ['py', 'js', 'ts', 'tsx', 'jsx', 'java', 'cpp', 'c', 'h', 'hpp', 'go', 'rs', 'rb', 'php', 'cs', 'swift', 'kt', 'scala', 'lua', 'pl', 'sh', 'bash', 'zsh'],
        'exclude_patterns': ['node_modules', '.git', '__pycache__', '*.pyc', '.venv', 'venv', 'dist', 'build', 'target', '.idea', '.vscode'],
        'hybrid_weight_semantic': 0.7,
        'hybrid_weight_keyword': 0.3,
        'max_results': 20,
        'context_lines': 3,
    }
    
    def __init__(self, config_dir: Path = None):
        self.config_dir = config_dir or Path.home() / '.codeseek'
        self.config_file = self.config_dir / 'config.json'
        self.config = self.DEFAULT_CONFIG.copy()
        self.load()
    
    def load(self):
        """Load configuration from file."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                    self.config.update(user_config)
            except Exception:
                pass
    
    def save(self):
        """Save configuration to file."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)
    
    def get(self, key: str, default=None):
        """Get configuration value."""
        return self.config.get(key, default)
    
    def set(self, key: str, value):
        """Set configuration value."""
        self.config[key] = value
        self.save()
    
    def get_embedding_url(self) -> Tuple[str, str, Dict]:
        """Get embedding API URL and headers."""
        backend = self.config['embedding_backend']
        
        if backend == 'glm':
            return (
                self.config['glm_api_url'],
                self.config['glm_api_key'],
                {'Authorization': f'Bearer {self.config["glm_api_key"]}'}
            )
        elif backend == 'openai':
            return (
                self.config['openai_api_url'],
                self.config['openai_api_key'],
                {'Authorization': f'Bearer {self.config["openai_api_key"]}'}
            )
        else:
            raise ValueError(f"Unknown embedding backend: {backend}")


class CodeParser:
    """Parse source code to extract functions, classes, and methods."""
    
    # Language patterns for different programming languages
    PATTERNS = {
        'py': {
            'function': r'(?:^|\n)(def\s+(\w+)\s*\([^)]*\)\s*(?:->\s*\w+\s*)?:)',
            'class': r'(?:^|\n)(class\s+(\w+)(?:\([^)]*\))?\s*:)',
            'method': r'(?:^|\n)(\s+def\s+(\w+)\s*\([^)]*\)\s*(?:->\s*\w+\s*)?:)',
            'import': r'(?:^|\n)(?:import|from)\s+(\w+)',
            'docstring': r'"""(.*?)"""',
        },
        'js': {
            'function': r'(?:^|\n)(?:async\s+)?(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:\([^)]*\)|(?:\w+))\s*=>)',
            'class': r'(?:^|\n)(?:export\s+)?class\s+(\w+)',
            'method': r'(?:^|\n)(\s+(?:async\s+)?(?:get|set)\s+\w+|(?:^|\n)\s+(?:async\s+)?\w+\s*\([^)]*\)\s*\{)',
            'import': r'(?:^|\n)(?:import\s+(?:{\s*\w+\s*}|\*\s+as\s+\w+|\w+)\s+from\s+[\'"]|require\s*\()[\'"](\S+)[\'"]',
        },
        'ts': {
            'function': r'(?:^|\n)(?:export\s+)?(?:async\s+)?(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:\([^)]*\)|(?:\w+))\s*(?::\s*\w+)?\s*=>)',
            'class': r'(?:^|\n)(?:export\s+)?class\s+(\w+)',
            'method': r'(?:^|\n)(\s+(?:readonly\s+)?(?:get|set)\s+\w+|\s+(?:async\s+)?\w+\s*\([^)]*\)(?::\s*\w+)?\s*\{)',
            'interface': r'(?:^|\n)(?:export\s+)?interface\s+(\w+)',
            'import': r'(?:^|\n)(?:import\s+(?:{\s*\w+\s*}|\*\s+as\s+\w+|\w+)\s+from\s+|require\s*\()[\'"](\S+)[\'"]',
        },
        'java': {
            'function': r'(?:^|\n)(?:public|private|protected)?\s*(?:static)?\s*(?:\w+(?:<[^>]+>)?)\s+(\w+)\s*\([^)]*\)',
            'class': r'(?:^|\n)(?:public|private|protected)?\s*(?:abstract)?\s*class\s+(\w+)',
            'method': r'(?:^|\n)(\s+(?:public|private|protected)?\s*(?:static)?\s*\w+\s+\w+\s*\([^)]*\))',
            'import': r'(?:^|\n)import\s+([\w.]+);',
        },
        'go': {
            'function': r'(?:^|\n)(?:func\s+(\w+)|func\s+\([^)]+\)\s*(\w+))',
            'struct': r'(?:^|\n)type\s+(\w+)\s+struct',
            'import': r'(?:^|\n)import\s+(?:\(|[\'"])(\S+)',
        },
        'rs': {
            'function': r'(?:^|\n)(?:pub\s+)?(?:async\s+)?fn\s+(\w+)',
            'struct': r'(?:^|\n)(?:pub\s+)?struct\s+(\w+)',
            'impl': r'(?:^|\n)(?:pub\s+)?impl(?:\s+<\w+>)?\s+(\w+)',
            'use': r'(?:^|\n)use\s+(\S+);',
        },
        'cpp': {
            'function': r'(?:^|\n)(?:(?:inline|static|virtual|explicit)?\s*)?(?:\w+(?:<[^>]+>)?(?:\s*\*|\s*&)?\s+)+(\w+)\s*\([^)]*\)\s*(?:const)?\s*(?:{|$)',
            'class': r'(?:^|\n)(?:template\s*<[^>]+>\s*)?class\s+(\w+)',
            'namespace': r'(?:^|\n)namespace\s+(\w+)',
        },
    }
    
    def __init__(self, config: Config):
        self.config = config
        self.supported_langs = set(config.get('supported_languages', []))
    
    def get_language(self, file_path: str) -> Optional[str]:
        """Detect programming language from file extension."""
        ext = Path(file_path).suffix.lstrip('.')
        lang_map = {
            'py': 'py', 'pyw': 'py',
            'js': 'js', 'mjs': 'js', 'cjs': 'js',
            'ts': 'ts', 'tsx': 'ts', 'jsx': 'ts',
            'java': 'java',
            'go': 'go',
            'rs': 'rs',
            'c': 'cpp', 'h': 'cpp', 'cpp': 'cpp', 'cc': 'cpp', 'cxx': 'cpp', 'hpp': 'cpp',
            'rb': 'rb',
            'php': 'php',
            'cs': 'cs',
            'swift': 'swift',
            'kt': 'kt', 'kts': 'kt',
            'scala': 'scala',
            'lua': 'lua',
            'pl': 'pl', 'pm': 'pl',
            'sh': 'sh', 'bash': 'sh', 'zsh': 'sh',
        }
        return lang_map.get(ext)
    
    def should_exclude(self, file_path: str) -> bool:
        """Check if file should be excluded from indexing."""
        path = Path(file_path)
        for pattern in self.config.get('exclude_patterns', []):
            if pattern.startswith('*'):
                if path.suffix == pattern[1:]:
                    return True
            elif pattern in str(path.parts):
                return True
        return False
    
    def parse_file(self, file_path: str) -> List[CodeSnippet]:
        """Parse a source file and extract code snippets."""
        if self.should_exclude(file_path):
            return []
        
        language = self.get_language(file_path)
        if not language or language not in self.PATTERNS:
            return []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except Exception:
            return []
        
        patterns = self.PATTERNS.get(language, {})
        snippets = []
        lines = content.split('\n')
        
        # Extract functions
        if 'function' in patterns:
            for match in re.finditer(patterns['function'], content, re.MULTILINE):
                name = match.group(1) or match.group(2) if match.lastindex >= 2 else match.group(1)
                if name and not name.startswith('_'):
                    start_line = content[:match.start()].count('\n') + 1
                    snippet = self._extract_snippet_content(content, match.start(), start_line, lines, name, 'function', language, file_path)
                    if snippet:
                        snippets.append(snippet)
        
        # Extract classes
        if 'class' in patterns:
            for match in re.finditer(patterns['class'], content, re.MULTILINE):
                name = match.group(1)
                if name:
                    start_line = content[:match.start()].count('\n') + 1
                    snippet = self._extract_snippet_content(content, match.start(), start_line, lines, name, 'class', language, file_path)
                    if snippet:
                        snippets.append(snippet)
        
        return snippets
    
    def _extract_snippet_content(self, content: str, match_pos: int, start_line: int, 
                                   lines: List[str], name: str, snippet_type: str,
                                   language: str, file_path: str) -> Optional[CodeSnippet]:
        """Extract the actual content of a snippet with proper indentation detection."""
        line_start = start_line - 1
        line_end = line_start
        
        # Simple heuristic: find matching indentation
        if line_start < len(lines):
            base_indent = len(lines[line_start]) - len(lines[line_start].lstrip())
            
            # Look for end of block (next item with same or less indentation)
            for i in range(line_start + 1, min(line_start + 200, len(lines))):
                line = lines[i]
                if line.strip() and not line.strip().startswith('#') and not line.strip().startswith('//'):
                    current_indent = len(line) - len(line.lstrip())
                    if current_indent <= base_indent and line.strip():
                        break
                line_end = i
            
            if line_end <= line_start:
                line_end = min(line_start + 20, len(lines) - 1)
        
        snippet_lines = lines[line_start:line_end + 1]
        snippet_content = '\n'.join(snippet_lines)
        docstring = self._extract_docstring(snippet_content, language)
        
        return CodeSnippet(
            file_path=file_path,
            start_line=line_start + 1,
            end_line=line_end + 1,
            snippet_type=snippet_type,
            name=name,
            content=snippet_content,
            language=language,
            docstring=docstring
        )
    
    def _extract_docstring(self, content: str, language: str) -> str:
        """Extract docstring from code content."""
        if language == 'py':
            # Python docstrings
            match = re.search(r'"""(.*?)"""', content, re.DOTALL)
            if match:
                return match.group(1).strip()[:200]
        elif language in ['js', 'ts']:
            # JSDoc comments
            match = re.search(r'/\*\*(.*?)\*/', content, re.DOTALL)
            if match:
                doc = match.group(1)
                doc = re.sub(r'^\s*\*\s?', '', doc, flags=re.MULTILINE).strip()
                return doc[:200]
        return ""


class BM25:
    """BM25 ranking algorithm implementation."""
    
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.corpus_size = 0
        self.avgdl = 0
        self.doc_freqs = []
        self.idf = {}
        self.doc_len = []
        self.corpus = []
    
    def fit(self, corpus: List[str]):
        """Fit the BM25 model on corpus."""
        self.corpus = corpus
        self.corpus_size = len(corpus)
        nd = {}  # word -> number of documents with that word
        
        for document in corpus:
            self.doc_len.append(len(document.split()))
            frequencies = Counter(document.lower().split())
            for word, freq in frequencies.items():
                if word not in nd:
                    nd[word] = 0
                nd[word] += 1
        
        self.avgdl = sum(self.doc_len) / self.corpus_size if self.corpus_size > 0 else 0
        
        # Calculate IDF
        for word, freq in nd.items():
            idf = math.log(self.corpus_size - freq + 0.5) - math.log(freq + 0.5)
            self.idf[word] = idf
    
    def search(self, query: str, top_k: int = 20) -> List[Tuple[int, float]]:
        """Search the corpus and return top-k results with scores."""
        query_words = query.lower().split()
        scores = [0.0] * self.corpus_size
        
        for i, doc in enumerate(self.corpus):
            doc_lower = doc.lower()
            doc_words = set(doc_lower.split())
            doc_len = self.doc_len[i]
            
            for word in query_words:
                if word in doc_words:
                    freq = doc_lower.split().count(word)
                    numerator = self.idf.get(word, 0) * freq * (self.k1 + 1)
                    denominator = freq + self.k1 * (1 - self.b + self.b * doc_len / self.avgdl)
                    scores[i] += numerator / denominator if denominator > 0 else 0
        
        # Get top-k results
        indexed_scores = list(enumerate(scores))
        indexed_scores.sort(key=lambda x: x[1], reverse=True)
        return indexed_scores[:top_k]


class VectorStore:
    """Simple vector storage using SQLite."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = None
        self._init_db()
    
    def _init_db(self):
        """Initialize the database."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        cursor = self.conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS snippets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL,
                start_line INTEGER NOT NULL,
                end_line INTEGER NOT NULL,
                snippet_type TEXT NOT NULL,
                name TEXT NOT NULL,
                content TEXT NOT NULL,
                language TEXT NOT NULL,
                docstring TEXT,
                content_hash TEXT NOT NULL,
                indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS embeddings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snippet_id INTEGER NOT NULL,
                embedding BLOB NOT NULL,
                FOREIGN KEY (snippet_id) REFERENCES snippets(id),
                UNIQUE(snippet_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_file_path ON snippets(file_path)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_content_hash ON snippets(content_hash)
        ''')
        
        self.conn.commit()
    
    def add_snippet(self, snippet: CodeSnippet) -> int:
        """Add a snippet to the store."""
        content_hash = hashlib.md5(snippet.content.encode()).hexdigest()
        
        # Check if already exists
        cursor = self.conn.cursor()
        cursor.execute(
            'SELECT id FROM snippets WHERE content_hash = ?',
            (content_hash,)
        )
        existing = cursor.fetchone()
        
        if existing:
            return existing[0]
        
        cursor.execute('''
            INSERT INTO snippets (file_path, start_line, end_line, snippet_type, 
                                  name, content, language, docstring, content_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            snippet.file_path, snippet.start_line, snippet.end_line,
            snippet.snippet_type, snippet.name, snippet.content,
            snippet.language, snippet.docstring, content_hash
        ))
        self.conn.commit()
        return cursor.lastrowid
    
    def add_embedding(self, snippet_id: int, embedding: List[float]):
        """Add embedding for a snippet."""
        cursor = self.conn.cursor()
        
        # Serialize embedding as JSON blob
        embedding_json = json.dumps(embedding)
        
        cursor.execute('''
            INSERT OR REPLACE INTO embeddings (snippet_id, embedding)
            VALUES (?, ?)
        ''', (snippet_id, embedding_json))
        self.conn.commit()
    
    def get_all_snippets(self) -> List[CodeSnippet]:
        """Get all snippets from the store."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM snippets')
        rows = cursor.fetchall()
        
        snippets = []
        for row in rows:
            snippets.append(CodeSnippet(
                file_path=row[1],
                start_line=row[2],
                end_line=row[3],
                snippet_type=row[4],
                name=row[5],
                content=row[6],
                language=row[7],
                docstring=row[8] or ""
            ))
        return snippets
    
    def get_all_embeddings(self) -> List[Tuple[int, List[float]]]:
        """Get all embeddings from the store."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT snippet_id, embedding FROM embeddings')
        rows = cursor.fetchall()
        
        embeddings = []
        for row in rows:
            embeddings.append((row[0], json.loads(row[1])))
        return embeddings
    
    def get_snippet_by_id(self, snippet_id: int) -> Optional[CodeSnippet]:
        """Get a snippet by ID."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM snippets WHERE id = ?', (snippet_id,))
        row = cursor.fetchone()
        
        if row:
            return CodeSnippet(
                file_path=row[1],
                start_line=row[2],
                end_line=row[3],
                snippet_type=row[4],
                name=row[5],
                content=row[6],
                language=row[7],
                docstring=row[8] or ""
            )
        return None
    
    def clear(self):
        """Clear all data from the store."""
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM embeddings')
        cursor.execute('DELETE FROM snippets')
        self.conn.commit()
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
    
    def get_stats(self) -> Dict:
        """Get statistics about the index."""
        cursor = self.conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM snippets')
        snippet_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM embeddings')
        embedding_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(DISTINCT language) FROM snippets')
        language_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(DISTINCT file_path) FROM snippets')
        file_count = cursor.fetchone()[0]
        
        return {
            'snippets': snippet_count,
            'embeddings': embedding_count,
            'languages': language_count,
            'files': file_count
        }


class EmbeddingService:
    """Service for generating embeddings using various backends."""
    
    def __init__(self, config: Config):
        self.config = config
    
    def get_embedding(self, text: str) -> Optional[List[float]]:
        """Get embedding for a single text using configured backend."""
        backend = self.config.get('embedding_backend', 'glm')
        
        if backend == 'local':
            # Use TF-IDF as local fallback
            return self._tfidf_embedding(text)
        
        try:
            if backend == 'glm':
                return self._get_glm_embedding(text)
            elif backend == 'openai':
                return self._get_openai_embedding(text)
        except Exception as e:
            print(f"{Colors.RED}Error getting embedding: {e}{Colors.RESET}")
            # Fallback to TF-IDF
            return self._tfidf_embedding(text)
        
        return None
    
    def _get_glm_embedding(self, text: str) -> Optional[List[float]]:
        """Get embedding using GLM API."""
        api_url = self.config.get('glm_api_url')
        api_key = self.config.get('glm_api_key')
        
        if not api_key:
            print(f"{Colors.YELLOW}Warning: GLM_API_KEY not set, using TF-IDF fallback{Colors.RESET}")
            return self._tfidf_embedding(text)
        
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'model': self.config.get('embedding_model', 'embedding-3'),
            'input': text[:8192]  # Truncate long text
        }
        
        req = urllib.request.Request(
            api_url,
            data=json.dumps(data).encode('utf-8'),
            headers=headers,
            method='POST'
        )
        
        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result['data'][0]['embedding']
    
    def _get_openai_embedding(self, text: str) -> Optional[List[float]]:
        """Get embedding using OpenAI-compatible API."""
        api_url = self.config.get('openai_api_url')
        api_key = self.config.get('openai_api_key')
        
        if not api_key:
            print(f"{Colors.YELLOW}Warning: OPENAI_API_KEY not set, using TF-IDF fallback{Colors.RESET}")
            return self._tfidf_embedding(text)
        
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'model': self.config.get('embedding_model', 'text-embedding-3-small'),
            'input': text[:8192]
        }
        
        req = urllib.request.Request(
            api_url,
            data=json.dumps(data).encode('utf-8'),
            headers=headers,
            method='POST'
        )
        
        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result['data'][0]['embedding']
    
    def _tfidf_embedding(self, text: str) -> List[float]:
        """Generate TF-IDF based embedding as local fallback."""
        # Simple TF-IDF-like representation
        words = re.findall(r'\w+', text.lower())
        word_freq = Counter(words)
        
        # Create a simple bag-of-words vector (limited vocabulary)
        vocabulary = list(word_freq.keys())[:100]
        
        if not vocabulary:
            return [0.0] * 100
        
        vector = []
        for word in vocabulary:
            # Simple term frequency as "embedding"
            vector.append(word_freq.get(word, 0) / len(words) if words else 0)
        
        # Pad or truncate to fixed size
        while len(vector) < 100:
            vector.append(0.0)
        vector = vector[:100]
        
        # Normalize
        norm = math.sqrt(sum(x * x for x in vector))
        if norm > 0:
            vector = [x / norm for x in vector]
        
        return vector
    
    def batch_get_embeddings(self, texts: List[str], batch_size: int = 10) -> List[Optional[List[float]]]:
        """Get embeddings for multiple texts."""
        results = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            for text in batch:
                results.append(self.get_embedding(text))
        return results


class SemanticSearch:
    """Semantic search engine combining vector and BM25 search."""
    
    def __init__(self, vector_store: VectorStore, embedding_service: EmbeddingService, config: Config):
        self.vector_store = vector_store
        self.embedding_service = embedding_service
        self.config = config
    
    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if len(vec1) != len(vec2):
            # Handle dimension mismatch
            min_len = min(len(vec1), len(vec2))
            vec1 = vec1[:min_len]
            vec2 = vec2[:min_len]
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot_product / (norm1 * norm2)
    
    def search(self, query: str, max_results: int = None) -> List[SearchResult]:
        """Search using hybrid approach (semantic + keyword)."""
        if max_results is None:
            max_results = self.config.get('max_results', 20)
        
        snippets = self.vector_store.get_all_snippets()
        if not snippets:
            return []
        
        # BM25 keyword search
        bm25 = BM25()
        corpus = [s.content for s in snippets]
        bm25.fit(corpus)
        bm25_results = bm25.search(query, top_k=min(len(snippets), max_results * 2))
        
        # Semantic search
        query_embedding = self.embedding_service.get_embedding(query)
        if not query_embedding:
            # Fallback to keyword-only search
            results = []
            for idx, score in bm25_results[:max_results]:
                results.append(SearchResult(
                    snippet=snippets[idx],
                    score=score,
                    match_type='keyword'
                ))
            return results
        
        embeddings = self.vector_store.get_all_embeddings()
        embedding_dict = {e[0]: e[1] for e in embeddings}
        
        semantic_scores = []
        for idx, snippet in enumerate(snippets):
            if idx in embedding_dict:
                similarity = self.cosine_similarity(query_embedding, embedding_dict[idx])
                semantic_scores.append((idx, similarity))
        
        semantic_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Combine scores
        hybrid_weight_semantic = self.config.get('hybrid_weight_semantic', 0.7)
        hybrid_weight_keyword = self.config.get('hybrid_weight_keyword', 0.3)
        
        max_bm25 = max(s[1] for s in bm25_results) if bm25_results else 1
        max_semantic = max(s[1] for s in semantic_scores) if semantic_scores else 1
        
        combined_scores = {}
        for idx, bm25_score in bm25_results:
            norm_bm25 = bm25_score / max_bm25 if max_bm25 > 0 else 0
            combined_scores[idx] = combined_scores.get(idx, 0) + hybrid_weight_keyword * norm_bm25
        
        for idx, semantic_score in semantic_scores:
            norm_semantic = semantic_score / max_semantic if max_semantic > 0 else 0
            combined_scores[idx] = combined_scores.get(idx, 0) + hybrid_weight_semantic * norm_semantic
        
        # Sort by combined score
        sorted_results = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)
        
        results = []
        for idx, score in sorted_results[:max_results]:
            # Determine match type
            is_semantic = any(s[0] == idx for s in semantic_scores[:len(semantic_scores)//2])
            is_keyword = any(s[0] == idx for s in bm25_results[:len(bm25_results)//2])
            
            if is_semantic and is_keyword:
                match_type = 'hybrid'
            elif is_semantic:
                match_type = 'semantic'
            else:
                match_type = 'keyword'
            
            results.append(SearchResult(
                snippet=snippets[idx],
                score=score,
                match_type=match_type
            ))
        
        return results


class CodeSeeker:
    """Main CodeSeek application."""
    
    def __init__(self, project_path: str = None):
        self.project_path = Path(project_path) if project_path else Path.cwd()
        self.config = Config()
        self.parser = CodeParser(self.config)
        
        # Set up paths
        index_path = self.project_path / self.config.get('index_path', '.codeseek/index.db')
        self.vector_store = VectorStore(str(index_path))
        self.embedding_service = EmbeddingService(self.config)
        self.search_engine = SemanticSearch(self.vector_store, self.embedding_service, self.config)
    
    def index_project(self, verbose: bool = False):
        """Index all source files in the project."""
        print(f"{Colors.CYAN}{Colors.BOLD}🔍 CodeSeek Indexing...{Colors.RESET}")
        print(f"Project path: {Colors.WHITE}{self.project_path}{Colors.RESET}")
        
        # Clear existing index
        self.vector_store.clear()
        
        # Find and parse all source files
        snippets = []
        file_count = 0
        
        for ext in self.config.get('supported_languages', []):
            for file_path in self.project_path.rglob(f'*.{ext}'):
                if self.parser.should_exclude(str(file_path)):
                    continue
                
                file_snippets = self.parser.parse_file(str(file_path))
                snippets.extend(file_snippets)
                file_count += 1
                
                if verbose and file_snippets:
                    print(f"  {Colors.GREEN}✓{Colors.RESET} {file_path.relative_to(self.project_path)}: {len(file_snippets)} snippets")
        
        # Add snippets to store
        print(f"\n{Colors.CYAN}📝 Indexing {len(snippets)} code snippets from {file_count} files...{Colors.RESET}")
        
        for i, snippet in enumerate(snippets):
            snippet_id = self.vector_store.add_snippet(snippet)
            
            # Generate and store embedding
            text_to_embed = f"{snippet.name}\n{snippet.content[:1000]}"
            embedding = self.embedding_service.get_embedding(text_to_embed)
            
            if embedding:
                self.vector_store.add_embedding(snippet_id, embedding)
            
            if verbose and (i + 1) % 50 == 0:
                print(f"  Processed {i + 1}/{len(snippets)} snippets...")
        
        # Print stats
        stats = self.vector_store.get_stats()
        print(f"\n{Colors.GREEN}{Colors.BOLD}✅ Indexing complete!{Colors.RESET}")
        print(f"  📊 Snippets indexed: {Colors.WHITE}{stats['snippets']}{Colors.RESET}")
        print(f"  📁 Files indexed: {Colors.WHITE}{stats['files']}{Colors.RESET}")
        print(f"  🌍 Languages: {Colors.WHITE}{stats['languages']}{Colors.RESET}")
        print(f"  🧠 Embeddings: {Colors.WHITE}{stats['embeddings']}{Colors.RESET}")
    
    def search(self, query: str, max_results: int = None, show_content: bool = True):
        """Search the codebase."""
        if max_results is None:
            max_results = self.config.get('max_results', 20)
        
        results = self.search_engine.search(query, max_results)
        
        if not results:
            print(f"{Colors.YELLOW}No results found for: {query}{Colors.RESET}")
            return
        
        print(f"\n{Colors.CYAN}{Colors.BOLD}🔍 Search results for: '{Colors.WHITE}{query}{Colors.CYAN}'{Colors.RESET}")
        print(f"{Colors.DIM}{'─' * 60}{Colors.RESET}")
        
        for i, result in enumerate(results, 1):
            snippet = result.snippet
            
            # Header
            match_icon = {
                'semantic': '🧠',
                'keyword': '🔤',
                'hybrid': '✨'
            }.get(result.match_type, '📄')
            
            print(f"\n{Colors.BOLD}{match_icon} Result {i} [{result.match_type.upper()}]{Colors.RESET}")
            print(f"   {Colors.CYAN}{Colors.BOLD}{snippet.name}{Colors.RESET} {Colors.DIM}({snippet.snippet_type}){Colors.RESET}")
            print(f"   {Colors.DIM}{snippet.file_path}:{snippet.start_line}-{snippet.end_line}{Colors.RESET}")
            print(f"   {Colors.GREEN}Score: {result.score:.3f}{Colors.RESET}")
            
            # Docstring if available
            if snippet.docstring:
                print(f"   {Colors.YELLOW}📖 {snippet.docstring[:100]}{Colors.RESET}")
            
            # Content preview
            if show_content:
                lines = snippet.content.split('\n')[:10]
                print(f"\n   {Colors.DIM}Preview:{Colors.RESET}")
                for line in lines:
                    line = line.rstrip()
                    if len(line) > 80:
                        line = line[:77] + '...'
                    print(f"   {Colors.WHITE}{line}{Colors.RESET}")
                if len(snippet.content.split('\n')) > 10:
                    print(f"   {Colors.DIM}... ({len(snippet.content.split(chr(10))) - 10} more lines){Colors.RESET}")
            
            print(f"{Colors.DIM}{'─' * 60}{Colors.RESET}")
        
        print(f"\n{Colors.GREEN}Found {len(results)} results{Colors.RESET}")
    
    def stats(self):
        """Show index statistics."""
        stats = self.vector_store.get_stats()
        
        print(f"\n{Colors.CYAN}{Colors.BOLD}📊 CodeSeek Index Statistics{Colors.RESET}")
        print(f"{Colors.DIM}{'─' * 40}{Colors.RESET}")
        print(f"  🧩 Total snippets: {Colors.WHITE}{stats['snippets']}{Colors.RESET}")
        print(f"  📁 Total files: {Colors.WHITE}{stats['files']}{Colors.RESET}")
        print(f"  🌍 Languages: {Colors.WHITE}{stats['languages']}{Colors.RESET}")
        print(f"  🧠 Embeddings: {Colors.WHITE}{stats['embeddings']}{Colors.RESET}")
    
    def clear_index(self):
        """Clear the search index."""
        self.vector_store.clear()
        print(f"{Colors.GREEN}✅ Index cleared{Colors.RESET}")
    
    def interactive_mode(self):
        """Run in interactive TUI mode."""
        print(f"{Colors.CYAN}{Colors.BOLD}")
        print("╔══════════════════════════════════════════════════════════╗")
        print("║           🔍 CodeSeek - Interactive Search Mode          ║")
        print("║  Type your query and press Enter to search               ║")
        print("║  Commands: :quit, :clear, :stats, :reindex              ║")
        print("╚══════════════════════════════════════════════════════════╝")
        print(f"{Colors.RESET}")
        
        while True:
            try:
                query = input(f"{Colors.GREEN}codeseek> {Colors.RESET}").strip()
                
                if not query:
                    continue
                
                if query in [':quit', ':q', 'exit', 'quit']:
                    print(f"{Colors.CYAN}Goodbye! 👋{Colors.RESET}")
                    break
                
                elif query in [':clear', ':c']:
                    self.clear_index()
                
                elif query in [':stats', ':s']:
                    self.stats()
                
                elif query in [':reindex', ':r']:
                    self.index_project(verbose=True)
                
                elif query.startswith(':'):
                    print(f"{Colors.YELLOW}Unknown command: {query}{Colors.RESET}")
                
                else:
                    self.search(query)
                    
            except KeyboardInterrupt:
                print(f"\n{Colors.CYAN}Goodbye! 👋{Colors.RESET}")
                break
            except EOFError:
                break


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description=f'{Colors.CYAN}CodeSeek{Colors.RESET} - {Colors.WHITE}Lightweight Local Semantic Code Search Engine{Colors.RESET}',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f'''
{Colors.CYAN}Examples:{Colors.RESET}
  {Colors.GREEN}codeseek index{Colors.RESET}                    Index the current project
  {Colors.GREEN}codeseek search "find users"{Colors.RESET}     Search for code
  {Colors.GREEN}codeseek stats{Colors.RESET}                   Show index statistics
  {Colors.GREEN}codeseek interactive{Colors.RESET}            Start interactive mode
  {Colors.GREEN}codeseek set-backend glm{Colors.RESET}        Set embedding backend

{Colors.CYAN}Environment Variables:{Colors.RESET}
  {Colors.WHITE}GLM_API_KEY{Colors.RESET}     API key for GLM-5.1 backend
  {Colors.WHITE}OPENAI_API_KEY{Colors.RESET}  API key for OpenAI backend

{Colors.DIM}Version: {__version__}{Colors.RESET}
'''
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Index command
    index_parser = subparsers.add_parser('index', help='Index the project')
    index_parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    index_parser.add_argument('path', nargs='?', default='.', help='Project path')
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Search the codebase')
    search_parser.add_argument('query', nargs='*', help='Search query')
    search_parser.add_argument('-n', '--max-results', type=int, default=20, help='Max results')
    search_parser.add_argument('--no-content', action='store_true', help='Hide content preview')
    
    # Stats command
    subparsers.add_parser('stats', help='Show index statistics')
    
    # Clear command
    subparsers.add_parser('clear', help='Clear the index')
    
    # Interactive command
    subparsers.add_parser('interactive', aliases=['i'], help='Interactive mode')
    
    # Config command
    config_parser = subparsers.add_parser('config', help='Configure settings')
    config_parser.add_argument('action', choices=['get', 'set', 'list'], help='Config action')
    config_parser.add_argument('key', nargs='?', help='Config key')
    config_parser.add_argument('value', nargs='?', help='Config value')
    
    # Set backend command
    backend_parser = subparsers.add_parser('set-backend', help='Set embedding backend')
    backend_parser.add_argument('backend', choices=['glm', 'openai', 'local'], help='Backend type')
    
    args = parser.parse_args()
    
    # Default to interactive if no command
    if not args.command:
        seeker = CodeSeeker()
        seeker.interactive_mode()
        return
    
    # Handle commands
    if args.command == 'index':
        seeker = CodeSeeker(args.path)
        seeker.index_project(verbose=args.verbose)
    
    elif args.command == 'search':
        if not args.query:
            print(f"{Colors.RED}Error: Search query required{Colors.RESET}")
            print(f"Usage: codeseek search \"your query\"")
            return
        query = ' '.join(args.query)
        seeker = CodeSeeker()
        seeker.search(query, max_results=args.max_results, show_content=not args.no_content)
    
    elif args.command == 'stats':
        seeker = CodeSeeker()
        seeker.stats()
    
    elif args.command == 'clear':
        seeker = CodeSeeker()
        seeker.clear_index()
    
    elif args.command == 'interactive':
        seeker = CodeSeeker()
        seeker.interactive_mode()
    
    elif args.command == 'config':
        config = Config()
        if args.action == 'list':
            print(f"\n{Colors.CYAN}CodeSeek Configuration:{Colors.RESET}")
            for key, value in sorted(config.config.items()):
                if 'key' in key.lower() and value:
                    value = '***' + value[-4:]
                print(f"  {Colors.WHITE}{key}{Colors.RESET}: {value}")
        elif args.action == 'get':
            if not args.key:
                print(f"{Colors.RED}Error: Config key required{Colors.RESET}")
                return
            value = config.get(args.key)
            print(f"{args.key}: {value}")
        elif args.action == 'set':
            if not args.key or args.value is None:
                print(f"{Colors.RED}Error: Config key and value required{Colors.RESET}")
                return
            config.set(args.key, args.value)
            print(f"{Colors.GREEN}✅ {args.key} set to {args.value}{Colors.RESET}")
    
    elif args.command == 'set-backend':
        config = Config()
        config.set('embedding_backend', args.backend)
        
        backend_names = {
            'glm': 'GLM-5.1',
            'openai': 'OpenAI',
            'local': 'Local TF-IDF'
        }
        print(f"{Colors.GREEN}✅ Backend set to {backend_names.get(args.backend, args.backend)}{Colors.RESET}")
        
        if args.backend == 'local':
            print(f"{Colors.YELLOW}Note: Using local TF-IDF embeddings (no API key required){Colors.RESET}")
        elif args.backend == 'glm':
            print(f"{Colors.YELLOW}Note: Set GLM_API_KEY environment variable for embeddings{Colors.RESET}")
        elif args.backend == 'openai':
            print(f"{Colors.YELLOW}Note: Set OPENAI_API_KEY environment variable for embeddings{Colors.RESET}")


if __name__ == '__main__':
    main()
