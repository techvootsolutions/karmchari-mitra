# -*- coding: utf-8 -*-
"""
Language Detection Utility
Detects language from text input and supports Gujarati, Hindi, English, and other languages
"""

import logging
import re
from typing import Optional, Dict

_logger = logging.getLogger(__name__)

# Try to import langdetect library
LANGDETECT_AVAILABLE = False
try:
    from langdetect import detect, detect_langs, LangDetectException
    LANGDETECT_AVAILABLE = True
except ImportError:
    _logger.warning("langdetect library not available. Install with: pip install langdetect")
    LANGDETECT_AVAILABLE = False


class LanguageDetector:
    """Language detection utility for multi-language conversation support"""
    
    # Language code mappings
    LANGUAGE_MAP = {
        'gu': 'gujarati',
        'hi': 'hindi',
        'en': 'english',
        'mr': 'marathi',
        'ta': 'tamil',
        'te': 'telugu',
        'kn': 'kannada',
        'ml': 'malayalam',
        'bn': 'bengali',
        'pa': 'punjabi',
    }
    
    # Common words/phrases for quick detection
    GUJARATI_KEYWORDS = [
        'હા', 'ના', 'આભાર', 'નમસ્તે', 'કેમ', 'છે', 'છું', 'છે', 'છો',
        'મારું', 'તમારું', 'આ', 'તે', 'અને', 'પણ', 'જે', 'કે', 'માટે'
    ]
    
    HINDI_KEYWORDS = [
        'हाँ', 'नहीं', 'धन्यवाद', 'नमस्ते', 'कैसे', 'है', 'हूं', 'हो', 'हैं',
        'मेरा', 'तुम्हारा', 'यह', 'वह', 'और', 'भी', 'जो', 'कि', 'के लिए'
    ]
    
    def __init__(self):
        """Initialize language detector"""
        self.detected_language = 'en'  # Default to English
        self.detection_confidence = 0.0
        
    def detect_language(self, text: str) -> str:
        """
        Detect language from text input
        
        Args:
            text: Input text to analyze
            
        Returns:
            Language code (gu, hi, en, etc.)
        """
        if not text or not text.strip():
            return 'en'  # Default to English for empty text
        
        text = text.strip()
        
        # First, try keyword-based detection for Indian languages
        gujarati_score = self._count_keywords(text, self.GUJARATI_KEYWORDS)
        hindi_score = self._count_keywords(text, self.HINDI_KEYWORDS)
        
        # If strong keyword match, use that
        if gujarati_score >= 2:
            self.detected_language = 'gu'
            self.detection_confidence = min(gujarati_score / 5.0, 1.0)
            _logger.info(f"Detected Gujarati from keywords (score: {gujarati_score})")
            return 'gu'
        
        if hindi_score >= 2:
            self.detected_language = 'hi'
            self.detection_confidence = min(hindi_score / 5.0, 1.0)
            _logger.info(f"Detected Hindi from keywords (score: {hindi_score})")
            return 'hi'
        
        # Check for Unicode ranges (more reliable for Indian languages)
        if self._has_gujarati_script(text):
            self.detected_language = 'gu'
            self.detection_confidence = 0.9
            _logger.info("Detected Gujarati from Unicode script")
            return 'gu'
        
        if self._has_hindi_script(text):
            self.detected_language = 'hi'
            self.detection_confidence = 0.9
            _logger.info("Detected Hindi from Unicode script")
            return 'hi'
        
        # Use langdetect library if available
        if LANGDETECT_AVAILABLE:
            try:
                detected = detect(text)
                self.detected_language = detected
                # Get confidence
                langs = detect_langs(text)
                if langs:
                    self.detection_confidence = langs[0].prob
                _logger.info(f"Detected language using langdetect: {detected} (confidence: {self.detection_confidence})")
                return detected
            except LangDetectException as e:
                _logger.warning(f"Language detection failed: {e}")
            except Exception as e:
                _logger.warning(f"Error in language detection: {e}")
        
        # Default to English
        self.detected_language = 'en'
        self.detection_confidence = 0.5
        return 'en'
    
    def _count_keywords(self, text: str, keywords: list) -> int:
        """Count occurrences of keywords in text"""
        count = 0
        text_lower = text.lower()
        for keyword in keywords:
            if keyword.lower() in text_lower:
                count += 1
        return count
    
    def _has_gujarati_script(self, text: str) -> bool:
        """Check if text contains Gujarati script characters"""
        # Gujarati Unicode range: U+0A80 to U+0AFF
        gujarati_pattern = re.compile(r'[\u0A80-\u0AFF]')
        return bool(gujarati_pattern.search(text))
    
    def _has_hindi_script(self, text: str) -> bool:
        """Check if text contains Devanagari script characters (Hindi, Marathi, etc.)"""
        # Devanagari Unicode range: U+0900 to U+097F
        devanagari_pattern = re.compile(r'[\u0900-\u097F]')
        return bool(devanagari_pattern.search(text))
    
    def get_language_name(self, lang_code: str) -> str:
        """Get human-readable language name from code"""
        return self.LANGUAGE_MAP.get(lang_code, lang_code)
    
    def get_greeting_message(self, lang_code: str, candidate_name: str, agent_name: str, company_name: str) -> str:
        """
        Get greeting message in the specified language
        
        Args:
            lang_code: Language code (gu, hi, en)
            candidate_name: Candidate's name
            agent_name: Agent's name
            company_name: Company name
            
        Returns:
            Greeting message in the specified language
        """
        greetings = {
            'en': f"Hi {candidate_name}, this is {agent_name} from {company_name}. "
                  f"I hope I'm not catching you at a bad time. "
                  f"Please note that we prefer to conduct this conversation in English, "
                  f"but if you're more comfortable speaking in another language, please feel free to do so, "
                  f"and I'll continue the conversation in the language you prefer.",
            'gu': f"નમસ્તે {candidate_name}, આ {agent_name} છે {company_name} માંથી. "
                  f"આશા છે કે હું તમને અનુકૂળ સમયે કૉલ કરી રહ્યો છું. "
                  f"કૃપા કરીને નોંધ કરો કે અમે આ વાતચીત અંગ્રેજીમાં કરવાનું પસંદ કરીએ છીએ, "
                  f"પરંતુ જો તમે અન્ય ભાષામાં વધુ આરામદાયક છો, તો કૃપા કરીને આગળ વધો, "
                  f"અને હું તમારી પસંદની ભાષામાં વાતચીત ચાલુ રાખીશ.",
            'hi': f"नमस्ते {candidate_name}, यह {agent_name} है {company_name} से. "
                  f"आशा है कि मैं आपको सुविधाजनक समय पर कॉल कर रहा हूं. "
                  f"कृपया ध्यान दें कि हम इस बातचीत को अंग्रेजी में करना पसंद करते हैं, "
                  f"लेकिन यदि आप किसी अन्य भाषा में अधिक सहज हैं, तो कृपया आगे बढ़ें, "
                  f"और मैं आपकी पसंद की भाषा में बातचीत जारी रखूंगा।",
        }
        
        return greetings.get(lang_code, greetings['en'])
    
    def should_switch_language(self, text: str, current_lang: str = 'en') -> tuple:
        """
        Check if language should be switched based on candidate response
        
        Args:
            text: Candidate's response text
            current_lang: Current conversation language
            
        Returns:
            Tuple of (should_switch: bool, detected_lang: str)
        """
        detected = self.detect_language(text)
        
        # If detected language is different from current and confidence is high
        if detected != current_lang and self.detection_confidence > 0.6:
            return True, detected
        
        return False, current_lang
    
    def translate_question(self, text: str, target_lang: str) -> str:
        """
        Translate question text to target language
        
        Args:
            text: Question text in English
            target_lang: Target language code (gu, hi, en, etc.)
            
        Returns:
            Translated text
        """
        if target_lang == 'en' or not text:
            return text
        
        # Translation mappings for common questions
        translations = {
            'gu': {
                'Could you please give us a brief introduction about yourself?': 'કૃપા કરીને તમારી જાત વિશે સંક્ષિપ્ત પરિચય આપશો?',
                'May I know your current position?': 'શું હું તમારી વર્તમાન સ્થિતિ જાણી શકું?',
                'What is your current salary?': 'તમારો વર્તમાન પગાર શું છે?',
                'What would be your expected salary for this role?': 'આ ભૂમિકા માટે તમારો અપેક્ષિત પગાર શું હશે?',
                'What is your notice period with your current employer?': 'તમારા વર્તમાન નોકરદાતા સાથે તમારી નોટિસ સમયગાળો શું છે?',
                'I\'m calling to follow up on your resume submission for the': 'હું તમારા રેસ્યુમ સબમિશનની અનુવર્તી ક્રિયા માટે કૉલ કરી રહ્યો છું',
                'position. Is now a good time to talk?': 'સ્થિતિ. શું હવે વાત કરવાનો સારો સમય છે?',
                'Great! I need to gather a few more pieces of information to complete your application.': 'સરસ! તમારી અરજી પૂર્ણ કરવા માટે મને થોડી વધુ માહિતી એકત્રિત કરવાની જરૂર છે.',
                'Thank you for providing these details.': 'આ વિગતો પ્રદાન કરવા બદલ આભાર.',
            },
            'hi': {
                'Could you please give us a brief introduction about yourself?': 'क्या आप कृपया अपने बारे में एक संक्षिप्त परिचय दे सकते हैं?',
                'May I know your current position?': 'क्या मैं आपकी वर्तमान स्थिति जान सकता हूं?',
                'What is your current salary?': 'आपका वर्तमान वेतन क्या है?',
                'What would be your expected salary for this role?': 'इस भूमिका के लिए आपका अपेक्षित वेतन क्या होगा?',
                'What is your notice period with your current employer?': 'आपके वर्तमान नियोक्ता के साथ आपकी नोटिस अवधि क्या है?',
                'I\'m calling to follow up on your resume submission for the': 'मैं आपके रेज़्यूमे सबमिशन का अनुवर्ती करने के लिए कॉल कर रहा हूं',
                'position. Is now a good time to talk?': 'स्थिति। क्या अब बात करने का अच्छा समय है?',
                'Great! I need to gather a few more pieces of information to complete your application.': 'बढ़िया! मुझे आपके आवेदन को पूरा करने के लिए कुछ और जानकारी एकत्र करने की आवश्यकता है।',
                'Thank you for providing these details.': 'इन विवरणों को प्रदान करने के लिए धन्यवाद।',
            },
        }
        
        # Get translations for target language
        lang_translations = translations.get(target_lang, {})
        
        # Try exact match first
        if text in lang_translations:
            return lang_translations[text]
        
        # Try partial matches for dynamic content
        for eng_text, translated_text in lang_translations.items():
            if eng_text.lower() in text.lower():
                # Replace the English part with translation
                return text.replace(eng_text, translated_text)
        
        # If no translation found, return original text
        # The AI will handle translation based on context
        return text
    
    def get_translated_flow(self, flow: list, target_lang: str) -> list:
        """
        Translate entire conversation flow to target language
        
        Args:
            flow: List of conversation flow steps
            target_lang: Target language code
            
        Returns:
            Translated flow
        """
        if target_lang == 'en':
            return flow
        
        translated_flow = []
        for step in flow:
            translated_step = step.copy()
            if step.get('message'):
                translated_step['message'] = self.translate_question(step['message'], target_lang)
            translated_flow.append(translated_step)
        
        return translated_flow
