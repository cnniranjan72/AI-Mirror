"""
GET /profile — Returns persona + alignment + RL suggestions
"""

import logging
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.services import persona as persona_svc, rl_layer, feature_engineering
from app.db.postgres import fetch

logger = logging.getLogger(__name__)
router = APIRouter()


class ProfileResponse(BaseModel):
    user_id: str
    persona_label: Optional[str] = None
    description: Optional[str] = None
    traits: dict = {}
    interest_vector: dict = {}
    behavior_vector: dict = {}
    strengths: list = []
    weaknesses: list = []
    recommendations: list = []
    confidence: float = 0
    alignment: Optional[dict] = None
    suggestion: Optional[dict] = None
    created_at: Optional[str] = None


@router.get("/profile", response_model=ProfileResponse)
async def get_profile(user_id: str = Query(default="default")):
    """
    Returns the latest persona profile with alignment and RL suggestions.
    """
    try:
        # Get latest persona
        persona = await persona_svc.get_latest_persona(user_id)

        if not persona:
            return ProfileResponse(
                user_id=user_id,
                persona_label="No Data",
                description="No behavioral data collected yet. Start browsing Instagram Reels with the extension enabled.",
                recommendations=["Install and enable the AIMirror Chrome extension", "Browse Instagram Reels normally"],
            )

        # Fetch recent events for feature engineering
        rows = await fetch(
            """
            SELECT username, caption, hashtags, watch_time, session_id
            FROM events WHERE user_id = $1
            ORDER BY created_at DESC LIMIT 100
            """,
            user_id,
        )

        event_dicts = [
            {
                "username": r["username"],
                "caption": r["caption"],
                "hashtags": r["hashtags"] if isinstance(r["hashtags"], list) else [],
                "watch_time": float(r["watch_time"]),
                "session_id": r["session_id"],
            }
            for r in rows
        ]

        features = feature_engineering.compute_features(event_dicts)

        # Compute alignment and suggestion
        alignment = rl_layer.compute_alignment(persona, features)
        suggestion = rl_layer.suggest_action(alignment, features)

        return ProfileResponse(
            user_id=user_id,
            persona_label=persona.get("persona_label"),
            description=persona.get("description", ""),
            traits=persona.get("traits", {}),
            interest_vector=persona.get("interest_vector", {}),
            behavior_vector=persona.get("behavior_vector", {}),
            strengths=persona.get("strengths", []),
            weaknesses=persona.get("weaknesses", []),
            recommendations=persona.get("recommendations", []),
            confidence=persona.get("confidence", 0),
            alignment=alignment,
            suggestion=suggestion,
            created_at=persona.get("created_at"),
        )

    except Exception as e:
        logger.exception("Profile fetch failed")
        raise HTTPException(status_code=500, detail=str(e))
