"""
Analytics and A/B Testing Framework
Tracks user behavior and enables A/B testing experiments
"""
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Analytics event types"""
    # User events
    USER_SIGNUP = "user.signup"
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"
    
    # Meme generation events
    MEME_GENERATED = "meme.generated"
    MEME_DOWNLOADED = "meme.downloaded"
    MEME_SHARED = "meme.shared"
    MEME_LIKED = "meme.liked"
    
    # Feature usage
    TEMPLATE_VIEWED = "template.viewed"
    GALLERY_VIEWED = "gallery.viewed"
    SETTINGS_CHANGED = "settings.changed"
    
    # Error events
    ERROR_OCCURRED = "error.occurred"
    API_ERROR = "api.error"


class ExperimentStatus(str, Enum):
    """A/B test experiment statuses"""
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


@dataclass
class AnalyticsEvent:
    """Analytics event"""
    event_type: EventType
    user_id: str
    timestamp: str
    properties: Dict[str, Any]
    session_id: Optional[str] = None
    event_id: Optional[str] = None
    
    def __post_init__(self):
        if not self.event_id:
            self.event_id = str(uuid.uuid4())
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Experiment:
    """A/B test experiment"""
    experiment_id: str
    name: str
    description: str
    status: ExperimentStatus
    variants: Dict[str, float]  # variant_name: percentage
    start_date: str
    end_date: Optional[str] = None
    
    def is_active(self) -> bool:
        return self.status == ExperimentStatus.RUNNING
    
    def get_variant_for_user(self, user_id: str) -> str:
        """Consistently assign variant to user"""
        # Hash user_id to get consistent variant assignment
        user_hash = hash(f"{self.experiment_id}:{user_id}") % 100
        
        cumulative = 0
        for variant, percentage in sorted(self.variants.items()):
            cumulative += percentage
            if user_hash < cumulative:
                return variant
        
        return list(self.variants.keys())[0]


class AnalyticsTracker:
    """Tracks user analytics events"""
    
    def __init__(self, storage_backend=None):
        """
        Initialize analytics tracker
        
        Args:
            storage_backend: Optional backend for event storage (redis, db, etc.)
        """
        self.storage = storage_backend
        self.events: List[AnalyticsEvent] = []
    
    async def track_event(
        self,
        event_type: EventType,
        user_id: str,
        properties: Optional[Dict] = None,
        session_id: Optional[str] = None,
    ) -> AnalyticsEvent:
        """Track an analytics event"""
        event = AnalyticsEvent(
            event_type=event_type,
            user_id=user_id,
            timestamp=datetime.utcnow().isoformat(),
            properties=properties or {},
            session_id=session_id,
        )
        
        # Store event
        self.events.append(event)
        
        # Persist if backend available
        if self.storage:
            try:
                await self.storage.store_event(event)
            except Exception as e:
                logger.error(f"Failed to store event: {e}")
        
        logger.debug(f"Event tracked: {event_type} for user {user_id}")
        return event
    
    async def get_user_events(
        self,
        user_id: str,
        event_type: Optional[EventType] = None,
        limit: int = 100,
    ) -> List[AnalyticsEvent]:
        """Get user's analytics events"""
        events = [e for e in self.events if e.user_id == user_id]
        
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        
        return events[-limit:]
    
    def get_event_summary(self) -> Dict:
        """Get summary of tracked events"""
        summary = {}
        for event in self.events:
            event_type = event.event_type.value
            if event_type not in summary:
                summary[event_type] = 0
            summary[event_type] += 1
        
        return summary


class ABTestingFramework:
    """A/B testing framework for experiments"""
    
    def __init__(self, storage_backend=None):
        self.storage = storage_backend
        self.experiments: Dict[str, Experiment] = {}
    
    async def create_experiment(
        self,
        name: str,
        description: str,
        variants: Dict[str, float],
        start_date: str,
        end_date: Optional[str] = None,
    ) -> Experiment:
        """Create new experiment"""
        # Validate variant percentages sum to 100
        total_percentage = sum(variants.values())
        if not (99.5 <= total_percentage <= 100.5):  # Allow for float rounding
            raise ValueError(f"Variant percentages must sum to 100, got {total_percentage}")
        
        experiment = Experiment(
            experiment_id=str(uuid.uuid4()),
            name=name,
            description=description,
            status=ExperimentStatus.DRAFT,
            variants=variants,
            start_date=start_date,
            end_date=end_date,
        )
        
        self.experiments[experiment.experiment_id] = experiment
        
        if self.storage:
            await self.storage.store_experiment(experiment)
        
        logger.info(f"Created experiment: {name} (ID: {experiment.experiment_id})")
        return experiment
    
    async def start_experiment(self, experiment_id: str) -> Experiment:
        """Start experiment"""
        if experiment_id not in self.experiments:
            raise ValueError(f"Experiment {experiment_id} not found")
        
        experiment = self.experiments[experiment_id]
        experiment.status = ExperimentStatus.RUNNING
        
        if self.storage:
            await self.storage.update_experiment(experiment)
        
        logger.info(f"Started experiment: {experiment.name}")
        return experiment
    
    def get_user_variant(self, user_id: str, experiment_id: str) -> Optional[str]:
        """Get variant for user in experiment"""
        if experiment_id not in self.experiments:
            return None
        
        experiment = self.experiments[experiment_id]
        if not experiment.is_active():
            return None
        
        return experiment.get_variant_for_user(user_id)
    
    async def get_experiment_results(self, experiment_id: str) -> Dict:
        """Get results of experiment"""
        if experiment_id not in self.experiments:
            raise ValueError(f"Experiment {experiment_id} not found")
        
        # In production, would aggregate metrics from events
        return {
            "experiment_id": experiment_id,
            "status": "results_pending",
            "note": "Results would be aggregated from analytics events",
        }


class UserFeedbackCollector:
    """Collects user feedback"""
    
    def __init__(self, storage_backend=None):
        self.storage = storage_backend
        self.feedback_items: List[Dict] = []
    
    async def submit_feedback(
        self,
        user_id: str,
        feedback_type: str,  # bug, feature_request, general
        message: str,
        metadata: Optional[Dict] = None,
    ) -> Dict:
        """Submit user feedback"""
        feedback = {
            "feedback_id": str(uuid.uuid4()),
            "user_id": user_id,
            "type": feedback_type,
            "message": message,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow().isoformat(),
            "status": "new",
        }
        
        self.feedback_items.append(feedback)
        
        if self.storage:
            await self.storage.store_feedback(feedback)
        
        logger.info(f"Feedback received from {user_id}: {feedback_type}")
        return feedback
    
    async def get_feedback(
        self,
        feedback_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict]:
        """Get feedback items"""
        items = self.feedback_items.copy()
        
        if feedback_type:
            items = [f for f in items if f["type"] == feedback_type]
        
        if status:
            items = [f for f in items if f["status"] == status]
        
        return items[-limit:]
    
    async def update_feedback_status(
        self,
        feedback_id: str,
        new_status: str,
        response: Optional[str] = None,
    ) -> Dict:
        """Update feedback status"""
        for feedback in self.feedback_items:
            if feedback["feedback_id"] == feedback_id:
                feedback["status"] = new_status
                if response:
                    feedback["response"] = response
                    feedback["responded_at"] = datetime.utcnow().isoformat()
                
                if self.storage:
                    await self.storage.update_feedback(feedback)
                
                return feedback
        
        raise ValueError(f"Feedback {feedback_id} not found")


# Analytics event tracking helpers
class AnalyticsHelper:
    """Helper functions for analytics tracking"""
    
    @staticmethod
    def get_meme_properties(meme_data: Dict) -> Dict:
        """Extract meme properties for analytics"""
        return {
            "template_id": meme_data.get("template_id"),
            "generation_time": meme_data.get("generation_time"),
            "model_used": meme_data.get("model_used"),
            "success": meme_data.get("success", True),
        }
    
    @staticmethod
    def get_user_properties(user_data: Dict) -> Dict:
        """Extract user properties for analytics"""
        return {
            "tier": user_data.get("tier", "free"),
            "signup_date": user_data.get("created_at"),
            "provider": user_data.get("provider", "email"),
        }
    
    @staticmethod
    def get_session_properties(request) -> Dict:
        """Extract session properties from request"""
        return {
            "user_agent": request.headers.get("user-agent"),
            "ip_address": request.client.host if request.client else None,
            "referrer": request.headers.get("referer"),
        }
