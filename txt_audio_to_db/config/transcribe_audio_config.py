"""
Transcription Configuration Module

This module provides centralized configuration for audio transcription operations.
All configurable parameters are organized in class-based dictionary structures
for maximum flexibility and programmatic access.

Usage:
    from config.transcribe_audio_config import TranscriptionConfig
    
    # Access configuration
    model = TranscriptionConfig.MODELS['main']
    
    # Override for specific use case
    config = TranscriptionConfig()
    config.MODELS['main'] = 'custom-model'
"""


class TranscriptionConfig:
    """
    Central configuration class for audio transcription.
    
    All settings are organized as class attributes for easy access and modification.
    This structure supports both direct class access and instance-based overrides.
    """
    
    # ============================================================================
    # MODEL CONFIGURATION
    # ============================================================================
    MODELS = {
        'main': 'gpt-4o-transcribe',           # Primary transcription model (higher accuracy)
        'detect': 'gpt-4o-mini-transcribe',    # Fast probe model for language detection (cheaper/faster)
    }
    
    # ============================================================================
    # FILE FORMAT CONFIGURATION
    # ============================================================================
    ALLOWED_EXTENSIONS = {
        '.mp3',   # MPEG Audio Layer III
        '.m4a',   # MPEG-4 Audio
        '.wav',   # Waveform Audio File Format
    }
    
    # ============================================================================
    # TRANSCRIPTION DEFAULTS
    # ============================================================================
    DEFAULTS = {
        'temperature': 0.0,          # Decoding temperature (0.0 = deterministic, 1.0 = creative)
        'probe_seconds': 25,         # Duration (seconds) to sample for language detection
        'language_routing': False,   # Enable language routing by default (False = let Whisper auto-detect)
    }
    
    # ============================================================================
    # LANGUAGE DETECTION CONFIGURATION
    # ============================================================================
    # Keywords and patterns used for text-based language detection
    # These are used when --language-routing is enabled
    
    LANGUAGE_KEYWORDS = {
        'pt': [  # Portuguese
            'obrigado', 'obrigada', 'obrigado pela', 'isto é', 'um teste',
            'gravação', 'atenção', 'alô', 'olá', 'sim', 'não', 'por favor',
            'muito obrigado', 'bom dia', 'boa tarde', 'boa noite', 'tchau',
            'desculpe', 'com licença', 'tudo bem', 'de nada'
        ],
        'es': [  # Spanish
            'gracias', 'por favor', 'hola', 'adiós', 'sí', 'no',
            'muchas gracias', 'esto es', 'una prueba', 'grabación', 'atención',
            'buenos días', 'buenas tardes', 'buenas noches', 'perdón',
            'con permiso', 'de nada', 'hasta luego'
        ],
        'en': [  # English
            'thank you', 'thanks', 'hello', 'hi', 'goodbye', 'yes', 'no',
            'please', 'this is', 'a test', 'recording', 'attention',
            'good morning', 'good afternoon', 'good evening', 'sorry',
            'excuse me', 'you\'re welcome', 'see you'
        ],
        'fr': [  # French
            'merci', 'bonjour', 'au revoir', 'oui', 'non', 's\'il vous plaît',
            'ceci est', 'un test', 'enregistrement', 'attention',
            'bonne journée', 'bonsoir', 'pardon', 'excusez-moi',
            'de rien', 'à bientôt', 'salut'
        ],
        'de': [  # German
            'danke', 'hallo', 'auf wiedersehen', 'ja', 'nein', 'bitte',
            'das ist', 'ein test', 'aufnahme', 'aufmerksamkeit',
            'guten morgen', 'guten tag', 'guten abend', 'entschuldigung',
            'tschüss', 'bis bald'
        ],
        'it': [  # Italian
            'grazie', 'ciao', 'arrivederci', 'sì', 'no', 'per favore',
            'questo è', 'un test', 'registrazione', 'attenzione',
            'buongiorno', 'buonasera', 'scusa', 'prego', 'a presto'
        ],
        'nl': [  # Dutch
            'dank je', 'dank u', 'hallo', 'dag', 'ja', 'nee', 'alstublieft',
            'dit is', 'een test', 'opname', 'aandacht',
            'goedemorgen', 'goedemiddag', 'goedenavond', 'sorry',
            'tot ziens', 'graag gedaan'
        ],
        'ru': [  # Russian (transliterated)
            'spasibo', 'privet', 'do svidaniya', 'da', 'net', 'pozhaluysta',
            'eto', 'test', 'zapis', 'vnimanie'
        ],
        'zh': [  # Chinese (common pinyin)
            'xiexie', 'nihao', 'zaijian', 'shi', 'bu', 'qing',
            'zhe shi', 'ceshi', 'luyin', 'zhuyi'
        ],
        'ja': [  # Japanese (common romanji)
            'arigatou', 'konnichiwa', 'sayonara', 'hai', 'iie', 'onegai',
            'kore wa', 'tesuto', 'rokuga', 'chuui'
        ],
    }
    
    # ============================================================================
    # FFMPEG CONFIGURATION
    # ============================================================================
    FFMPEG_SETTINGS = {
        'audio_channels': 1,         # Mono audio for probe
        'sample_rate': 16000,        # 16kHz sample rate (good balance of quality/size)
        'hide_banner': True,         # Hide FFmpeg banner in output
        'loglevel': 'error',         # Only show errors
    }
    
    # ============================================================================
    # API CONFIGURATION
    # ============================================================================
    API_SETTINGS = {
        'response_format_probe': 'text',     # Format for language detection probe
        'response_format_main': 'json',      # Format for main transcription
        'timeout': 300,                      # API timeout in seconds (5 minutes)
        'max_retries': 3,                    # Maximum retry attempts for API calls
    }
    
    # ============================================================================
    # TEMP FILE CONFIGURATION
    # ============================================================================
    TEMP_SETTINGS = {
        'probe_prefix': 'stt_probe_',        # Prefix for temporary probe files
        'cleanup_on_exit': True,              # Automatically cleanup temp files
    }
    
    # ============================================================================
    # LOGGING CONFIGURATION
    # ============================================================================
    LOGGING_SETTINGS = {
        'log_dir': 'logs',                   # Default log directory (relative to CWD)
        'console_level': 'INFO',             # Default console log level
        'file_level': 'DEBUG',               # Default file log level
        'enable_file_logging': False,        # Disable file logging by default (can be enabled via CLI)
    }
    
    # ============================================================================
    # EXIT CODES
    # ============================================================================
    EXIT_CODES = {
        'success': 0,
        'usage_error': 1,
        'file_error': 2,
        'api_error': 3,
        'ffmpeg_error': 4,
    }
    
    # ============================================================================
    # HELPER METHODS
    # ============================================================================
    
    @classmethod
    def get_model(cls, model_type='main'):
        """
        Get model name by type.
        
        Args:
            model_type: 'main' or 'detect'
            
        Returns:
            Model name string
        """
        return cls.MODELS.get(model_type, cls.MODELS['main'])
    
    @classmethod
    def get_default(cls, key, default=None):
        """
        Get default configuration value.
        
        Args:
            key: Configuration key
            default: Fallback value if key not found
            
        Returns:
            Configuration value or default
        """
        return cls.DEFAULTS.get(key, default)
    
    @classmethod
    def get_language_keywords(cls, language_code):
        """
        Get keyword list for specific language.
        
        Args:
            language_code: ISO-639-1 language code (e.g., 'en', 'pt')
            
        Returns:
            List of keywords or empty list
        """
        return cls.LANGUAGE_KEYWORDS.get(language_code, [])
    
    @classmethod
    def get_supported_languages(cls):
        """
        Get list of supported languages for keyword detection.
        
        Returns:
            List of ISO-639-1 language codes
        """
        return list(cls.LANGUAGE_KEYWORDS.keys())
    
    @classmethod
    def is_extension_allowed(cls, extension):
        """
        Check if file extension is allowed.
        
        Args:
            extension: File extension (with or without dot)
            
        Returns:
            Boolean indicating if extension is allowed
        """
        if not extension.startswith('.'):
            extension = f'.{extension}'
        return extension.lower() in cls.ALLOWED_EXTENSIONS
    
    @classmethod
    def get_probe_model(cls):
        """Get the model used for language detection probe."""
        return cls.get_model('detect')
    
    @classmethod
    def get_main_model(cls):
        """Get the model used for main transcription."""
        return cls.get_model('main')
    
    @classmethod
    def get_log_dir(cls):
        """Get the default log directory."""
        return cls.LOGGING_SETTINGS['log_dir']
    
    @classmethod
    def get_client(cls, api_key=None, timeout=None, max_retries=None):
        """
        Create a configured OpenAI client instance.
        
        Args:
            api_key: Optional API key (defaults to OPENAI_API_KEY env var)
            timeout: Optional timeout override (defaults to config)
            max_retries: Optional retry count override (defaults to config)
            
        Returns:
            Configured OpenAI client instance
            
        Raises:
            ImportError: If OpenAI SDK is not installed
            ValueError: If API key is not provided and not in environment
        """
        try:
            from openai import OpenAI
        except ImportError as e:
            raise ImportError(f"Failed to import OpenAI SDK. Install with: pip install openai\nDetail: {e}")
        
        # Get API key
        if api_key is None:
            import os
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable is not set")
        
        # Get settings from config (only client-relevant settings)
        client_settings = {
            'timeout': timeout if timeout is not None else cls.API_SETTINGS['timeout'],
            'max_retries': max_retries if max_retries is not None else cls.API_SETTINGS['max_retries']
        }
        
        # Create client with configuration
        return OpenAI(api_key=api_key, **client_settings)
    
    @classmethod
    def load_env_file(cls, env_path=None):
        """
        Load environment variables from .env file if it exists.
        
        This is a convenience function that tries to load a .env file
        without requiring python-dotenv as a hard dependency.
        
        Args:
            env_path: Optional path to .env file (defaults to .env in CWD)
            
        Returns:
            Boolean indicating if .env file was loaded successfully
        """
        import os
        from pathlib import Path
        
        if env_path is None:
            env_path = Path.cwd() / ".env"
        else:
            env_path = Path(env_path)
        
        if not env_path.exists():
            return False
        
        try:
            # Try to use python-dotenv if available
            import dotenv
            dotenv.load_dotenv(env_path)
            return True
        except ImportError:
            # Fallback: simple .env parsing without external dependencies
            try:
                with open(env_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            key = key.strip()
                            value = value.strip().strip('"').strip("'")
                            if key and value:
                                os.environ[key] = value
                return True
            except Exception:
                return False

