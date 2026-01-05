# -*- coding: utf-8 -*-

import json
import logging
from typing import Dict, Optional

_logger = logging.getLogger(__name__)


class AICallService:
    """Service for AI-powered call analysis and statistics"""

    def __init__(self, config: Dict):
        """
        Initialize AI Call Service

        Args:
            config: Configuration dictionary with AI settings
        """
        self.config = config
        self.ai_model = config.get('ai_model', 'openai')
        self.api_key = config.get('ai_api_key', '')
        self.endpoint = config.get('ai_endpoint', '')

    def analyze_call(self, transcript: str, call_data: Dict) -> Dict:
        """
        Analyze call transcript and generate statistics

        Args:
            transcript: Full call transcript
            call_data: Additional call data (duration, questions asked, etc.)

        Returns:
            Dictionary with analysis results
        """
        try:
            # Basic analysis (can be enhanced with actual AI API calls)
            analysis = {
                'communication_score': self._calculate_communication_score(transcript, call_data),
                'sentiment_score': self._calculate_sentiment(transcript),
                'engagement_level': self._determine_engagement(transcript, call_data),
                'response_time_avg': call_data.get('avg_response_time', 0),
                'clarity_score': self._calculate_clarity(transcript),
                'professionalism_score': self._calculate_professionalism(transcript),
                'interest_level': self._determine_interest(transcript),
                'analysis_text': self._generate_analysis_text(transcript, call_data),
                'statistics': self._generate_statistics(transcript, call_data)
            }

            return analysis
        except Exception as e:
            _logger.error(f"Error analyzing call: {e}")
            return self._get_default_analysis()

    def _calculate_communication_score(self, transcript: str, call_data: Dict) -> float:
        """Calculate overall communication score (0-10)"""
        # Simple heuristic-based scoring (can be replaced with AI)
        score = 7.0  # Base score

        # Adjust based on transcript length (more conversation = better)
        word_count = len(transcript.split())
        if word_count > 500:
            score += 1.0
        elif word_count > 200:
            score += 0.5

        # Adjust based on duration (longer calls often indicate better engagement)
        duration = call_data.get('duration', 0)
        if duration > 10:
            score += 0.5
        elif duration > 5:
            score += 0.2

        # Adjust based on questions answered
        questions_answered = call_data.get('questions_answered', 0)
        total_questions = call_data.get('total_questions', 1)
        if total_questions > 0:
            answer_ratio = questions_answered / total_questions
            score += answer_ratio * 1.0

        return min(10.0, max(0.0, score))

    def _calculate_sentiment(self, transcript: str) -> float:
        """Calculate sentiment score (-1 to 1)"""
        # Simple keyword-based sentiment (can be enhanced with NLP)
        positive_words = ['yes', 'great', 'excellent', 'interested', 'excited', 'perfect', 'wonderful']
        negative_words = ['no', 'not', 'unfortunately', 'sorry', 'cannot', 'unable']

        transcript_lower = transcript.lower()
        positive_count = sum(1 for word in positive_words if word in transcript_lower)
        negative_count = sum(1 for word in negative_words if word in transcript_lower)

        total = positive_count + negative_count
        if total == 0:
            return 0.0

        # Normalize to -1 to 1
        sentiment = (positive_count - negative_count) / max(total, 1)
        return max(-1.0, min(1.0, sentiment))

    def _determine_engagement(self, transcript: str, call_data: Dict) -> str:
        """Determine engagement level"""
        word_count = len(transcript.split())
        duration = call_data.get('duration', 0)

        # High engagement indicators
        if word_count > 500 and duration > 10:
            return 'very_high'
        elif word_count > 300 and duration > 7:
            return 'high'
        elif word_count > 150 and duration > 5:
            return 'medium'
        else:
            return 'low'

    def _calculate_clarity(self, transcript: str) -> float:
        """Calculate clarity score (0-10)"""
        # Simple heuristic (can be enhanced with NLP)
        score = 7.0

        # Check for complete sentences
        sentences = transcript.split('.')
        if len(sentences) > 5:
            score += 1.0

        # Check for question marks (indicates engagement)
        if '?' in transcript:
            score += 0.5

        return min(10.0, max(0.0, score))

    def _calculate_professionalism(self, transcript: str) -> float:
        """Calculate professionalism score (0-10)"""
        score = 7.0

        # Professional language indicators
        professional_words = ['thank you', 'please', 'appreciate', 'opportunity', 'experience']
        professional_count = sum(1 for word in professional_words if word in transcript.lower())

        score += min(2.0, professional_count * 0.3)

        return min(10.0, max(0.0, score))

    def _determine_interest(self, transcript: str) -> str:
        """Determine candidate interest level"""
        transcript_lower = transcript.lower()

        high_interest_words = ['very interested', 'excited', 'perfect fit', 'looking forward', 'definitely']
        low_interest_words = ['not sure', 'maybe', 'consider', 'think about']
        not_interested_words = ['not interested', 'not looking', 'not available', 'decline']

        high_count = sum(1 for phrase in high_interest_words if phrase in transcript_lower)
        low_count = sum(1 for phrase in low_interest_words if phrase in transcript_lower)
        not_count = sum(1 for phrase in not_interested_words if phrase in transcript_lower)

        if not_count > 0:
            return 'not_interested'
        elif high_count >= 2:
            return 'very_high'
        elif high_count >= 1:
            return 'high'
        elif low_count > 0:
            return 'low'
        else:
            return 'moderate'

    def _generate_analysis_text(self, transcript: str, call_data: Dict) -> str:
        """Generate human-readable analysis text"""
        duration = call_data.get('duration', 0)
        questions_answered = call_data.get('questions_answered', 0)
        total_questions = call_data.get('total_questions', 0)

        analysis = f"""
Call Analysis Summary:
- Call Duration: {duration:.1f} minutes
- Questions Answered: {questions_answered}/{total_questions}
- Communication Quality: {'Good' if self._calculate_communication_score(transcript, call_data) > 7 else 'Needs Improvement'}
- Candidate Engagement: {self._determine_engagement(transcript, call_data).replace('_', ' ').title()}
- Interest Level: {self._determine_interest(transcript).replace('_', ' ').title()}

Overall Assessment:
The candidate demonstrated {'strong' if self._calculate_communication_score(transcript, call_data) > 7 else 'moderate'} communication skills
and showed {'high' if self._determine_interest(transcript) in ['high', 'very_high'] else 'moderate'} interest in the position.
        """
        return analysis.strip()

    def _generate_statistics(self, transcript: str, call_data: Dict) -> Dict:
        """Generate detailed statistics"""
        word_count = len(transcript.split())
        sentences = transcript.split('.')
        questions = transcript.count('?')

        return {
            'word_count': word_count,
            'sentence_count': len([s for s in sentences if s.strip()]),
            'question_count': questions,
            'duration_minutes': call_data.get('duration', 0),
            'questions_asked': call_data.get('total_questions', 0),
            'questions_answered': call_data.get('questions_answered', 0),
            'response_rate': call_data.get('questions_answered', 0) / max(call_data.get('total_questions', 1), 1),
            'words_per_minute': word_count / max(call_data.get('duration', 1), 1)
        }

    def _get_default_analysis(self) -> Dict:
        """Return default analysis if error occurs"""
        return {
            'communication_score': 0.0,
            'sentiment_score': 0.0,
            'engagement_level': 'low',
            'response_time_avg': 0.0,
            'clarity_score': 0.0,
            'professionalism_score': 0.0,
            'interest_level': 'moderate',
            'analysis_text': 'Analysis unavailable',
            'statistics': {}
        }

