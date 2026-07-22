"""
Synthetic Event Generator
Generates realistic Instagram activity for pipeline validation

Produces:
- AI reels, programming reels, career reels, entertainment reels
- Repeated creators, hashtags, captions
- Repeated viewing sessions, interests
- Different watch durations and engagement patterns

Simulates weeks of usage across multiple sessions.
"""
import json
import uuid
import random
from typing import List, Dict, Any
from datetime import datetime, timedelta


# ── REPEATED CREATORS ──────────────────────────────────────────────
AI_CREATORS = [
    "ai_explained", "two_minute_papers", "sentdex", "yannic_kilcher",
    "andrej_karpathy", "lex_fridman_clips", "aizadventures", "ml_guy",
    "the_ai_engineer", "deep_learning_daily",
]

PROGRAMMING_CREATORS = [
    "theo_t3", "fireship", "primeagen", "tsoding", "low_learn",
    "mosh_hamedani", "traversy_media", "web_dev_simplified",
    "kevin_powell", "code_with_anton",
]

CAREER_CREATORS = [
    "levelsio", "dvassallo", "shlomi_levy", "codie_sanchez",
    "sam_harris_career", "the_career_nerd", "ali_abdaal", "matt_davella",
    "elizabeth_filips", "thomas_frank",
]

ENTERTAINMENT_CREATORS = [
    "mr_beast", "zach_king", "dude_perfect", "brian_jordan_alvarez",
    "zachary_levi_fun", "emma_chamberlain", "dixie_damelio", "liza_koshy",
    "brent_rivera", "pierson_wodzinski",
]

ALL_CREATORS = AI_CREATORS + PROGRAMMING_CREATORS + CAREER_CREATORS + ENTERTAINMENT_CREATORS

# ── REPEATED HASHTAGS ──────────────────────────────────────────────
AI_HASHTAGS = [
    ["tutorial", "artificialintelligence", "machinelearning", "deeplearning", "neuralnetworks"],
    ["learning", "llm", "largelanguagemodel", "gpt", "chatgpt"],
    ["tutorial", "computervision", "opencv", "yolo", "objectdetection"],
    ["education", "reinforcementlearning", "rl", "deeprl", "openai"],
    ["course", "genai", "generativeai", "diffusion", "stablediffusion"],
]

PROGRAMMING_HASHTAGS = [
    ["tutorial", "coding", "webdev", "javascript", "typescript"],
    ["learning", "programming", "automation", "backend", "api"],
    ["react", "frontend", "webdev", "ui", "tailwind"],
    ["rust", "systemsprogramming", "performance", "lowlevel", "memorysafe"],
    ["git", "devops", "cicd", "docker", "kubernetes"],
]

CAREER_HASHTAGS = [
    ["career", "growth", "personalfinance", "remote", "freelancing"],
    ["productivity", "timemanagement", "focus", "deepwork", "habits"],
    ["careeradvice", "jobsearch", "resume", "interview", "networking"],
    ["sidehustle", "entrepreneurship", "startup", "indiemaker", "saas"],
    ["mentalhealth", "worklifebalance", "burnout", "wellness", "meditation"],
]

ENTERTAINMENT_HASHTAGS = [
    ["funny", "comedy", "memes", "humor", "viral"],
    ["gaming", "minecraft", "valorant", "fortnite", "twitch"],
    ["music", "dance", "tiktok", "trending", "challenge"],
    ["animals", "dogs", "cats", "petsoftiktok", "cute"],
    ["food", "cooking", "recipes", "foodie", "baking"],
]

ALL_HASHTAG_SETS = AI_HASHTAGS + PROGRAMMING_HASHTAGS + CAREER_HASHTAGS + ENTERTAINMENT_HASHTAGS

# ── REPEATED CAPTIONS ──────────────────────────────────────────────
AI_CAPTIONS = [
    "This AI model is absolutely mind-blowing 🤯",
    "The future of machine learning is here!",
    "I can't believe what this neural network can do",
    "Deep learning explained in 60 seconds",
    "GPT-5 is going to change everything",
    "Why everyone should learn AI right now",
    "This is how neural networks actually work",
    "The most impressive AI demo I've seen",
]

PROGRAMMING_CAPTIONS = [
    "I built the same app in 5 different languages",
    "This coding trick saved me 10 hours",
    "TypeScript vs JavaScript - which should you learn?",
    "The most underrated programming language",
    "My VS Code setup for maximum productivity",
    "Clean code principles that changed everything",
    "Why everyone is learning Rust now",
    "I automated my entire workflow with Python",
]

CAREER_CAPTIONS = [
    "How I went from zero to six figures remotely",
    "The productivity hack that changed my life",
    "Why you should quit your job and start building",
    "My daily routine for maximum output",
    "How to negotiate your salary like a pro",
    "The best career advice nobody talks about",
    "I built a business while working full time",
    "Why remote work is the future",
]

ENTERTAINMENT_CAPTIONS = [
    "This is the funniest thing I've seen all week 😂",
    "Wait for the end... I promise it's worth it",
    "How is this even possible?!",
    "The most satisfying video you'll watch today",
    "I can't stop watching this",
    "My reaction when... 😭",
    "This deserves more views",
    "POV: You finally understand the assignment",
]

ALL_CAPTIONS = AI_CAPTIONS + PROGRAMMING_CAPTIONS + CAREER_CAPTIONS + ENTERTAINMENT_CAPTIONS

# ── AUDIO TRACKS ──────────────────────────────────────────────────
AUDIO_TRACKS = [
    "Original Audio", "Sunny Day", "Happy Vibes", "Trending Sound #42",
    "Epic Background", "Chill Lofi", "Upbeat Pop", "Ambient Study",
    "Nightcore Mix", "Phonk Remix",
]


class SyntheticEventGenerator:
    """
    Generates realistic synthetic Instagram behavioral events.

    Simulates weeks of usage with:
    - Repeated creators (user follows specific creators)
    - Repeated hashtags (user engages with specific topics)
    - Repeated captions (creator reposts / similar content)
    - Repeated viewing sessions (user scrolls at specific times)
    - Repeated interests (AI, programming, career, entertainment)
    - Different watch durations (scrolling vs deep engagement)
    - Different engagement patterns (liking, saving, sharing)
    """

    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)
        random.seed(seed)

        # Session patterns: (hour, day_of_week, duration_minutes, probability)
        self.session_patterns = [
            # Morning commute browsing (short sessions, scroll quickly)
            {"hour": 8, "days": [0, 1, 2, 3, 4], "duration": 15, "prob": 0.3},
            # Lunch break (mixed engagement)
            {"hour": 12, "days": [0, 1, 2, 3, 4, 5, 6], "duration": 20, "prob": 0.5},
            # Evening deep scroll (long sessions, high engagement)
            {"hour": 19, "days": [0, 1, 2, 3, 4], "duration": 45, "prob": 0.7},
            # Weekend morning (relaxed browsing)
            {"hour": 10, "days": [5, 6], "duration": 60, "prob": 0.8},
            # Late night (casual scrolling, entertainment mostly)
            {"hour": 22, "days": [0, 1, 2, 3, 4, 5, 6], "duration": 30, "prob": 0.4},
            # Weekend evening (deep engagement)
            {"hour": 20, "days": [5, 6], "duration": 90, "prob": 0.9},
        ]

    def _pick_hashtag_set(self, category: str) -> List[str]:
        if category == "ai":
            return list(self.rng.choice(AI_HASHTAGS))
        elif category == "programming":
            return list(self.rng.choice(PROGRAMMING_HASHTAGS))
        elif category == "career":
            return list(self.rng.choice(CAREER_HASHTAGS))
        else:
            return list(self.rng.choice(ENTERTAINMENT_HASHTAGS))

    def _pick_caption(self, category: str, idx: int) -> str:
        captions = {
            "ai": AI_CAPTIONS,
            "programming": PROGRAMMING_CAPTIONS,
            "career": CAREER_CAPTIONS,
            "entertainment": ENTERTAINMENT_CAPTIONS,
        }.get(category, ENTERTAINMENT_CAPTIONS)
        return captions[idx % len(captions)]

    def _pick_creator(self, category: str, idx: int) -> str:
        creators = {
            "ai": AI_CREATORS,
            "programming": PROGRAMMING_CREATORS,
            "career": CAREER_CREATORS,
            "entertainment": ENTERTAINMENT_CREATORS,
        }.get(category, ENTERTAINMENT_CREATORS)
        return creators[idx % len(creators)]

    def _pick_audio(self) -> str:
        return self.rng.choice(AUDIO_TRACKS)

    def _generate_watch_time(self, category: str) -> float:
        """Generate realistic watch times by content category."""
        if category == "ai":
            # Longer watch for educational content (3-60s, avg 25s)
            return max(1.0, self.rng.gauss(25, 12))
        elif category == "programming":
            # Medium watch for tutorials (2-45s, avg 20s)
            return max(1.0, self.rng.gauss(20, 10))
        elif category == "career":
            # Variable watch for career (1-40s, avg 15s)
            return max(1.0, self.rng.gauss(15, 8))
        else:
            # Shorter watch for entertainment (1-30s, avg 10s)
            return max(1.0, self.rng.gauss(10, 7))

    def _generate_engagement(self, category: str, watch_time: float) -> Dict[str, bool]:
        """Generate realistic engagement patterns."""
        like = self.rng.random() < (0.4 if category in ("ai", "programming") else 0.25)
        save = self.rng.random() < (0.15 if category == "ai" else 0.05)
        share = self.rng.random() < 0.05
        # Longer watch time increases engagement probability
        if watch_time > 20:
            like = like or self.rng.random() < 0.3
            save = save or self.rng.random() < 0.1
        return {"liked": like, "saved": save, "shared": share, "commented": False}

    def generate_session_events(
        self,
        start_time: datetime,
        session_id: str,
        events_in_session: int = 15,
    ) -> List[Dict[str, Any]]:
        """
        Generate a single session of browsing events.

        Args:
            start_time: Session start time
            session_id: Unique session ID
            events_in_session: Number of reels viewed in this session

        Returns:
            List of raw event dicts (Chrome Extension format)
        """
        events = []

        # Determine session focus - repeated interests with high probability
        session_categories = ["ai", "ai", "programming", "programming", "career", "entertainment"]

        for i in range(events_in_session):
            # Pick content category (weighted: AI and programming appear more)
            category = self.rng.choice(session_categories)

            # We pick a repeat index so that same creators/captions/hashtags cycle
            repeat_idx = i // 3  # Every 3rd event reuses a previous creator/caption pattern

            creator = self._pick_creator(category, repeat_idx)
            caption = self._pick_caption(category, repeat_idx)
            hashtags = self._pick_hashtag_set(category)
            audio = self._pick_audio()
            watch_time = self._generate_watch_time(category)
            engagement = self._generate_engagement(category, watch_time)

            # Time increments (5-30 seconds between reels)
            event_time = start_time + timedelta(seconds=i * self.rng.randint(5, 30))

            # Reel ID (repeated pattern for same content by same creator)
            reel_id = f"reel_{category}_{repeat_idx}_{i}"

            event = {
                "reel_id": reel_id,
                "username": creator,
                "caption": caption,
                "hashtags": hashtags,
                "audio": audio,
                "watch_time": round(watch_time, 1),
                "liked": engagement["liked"],
                "saved": engagement["saved"],
                "shared": engagement["shared"],
                "timestamp": event_time.isoformat(),
                "session_id": session_id,
            }
            events.append(event)

        return events

    def generate_weeks_of_activity(
        self,
        num_weeks: int = 3,
        user_id: str = "test_user_001",
    ) -> List[Dict[str, Any]]:
        """
        Generate weeks of Instagram browsing activity.

        Creates realistic daily sessions with:
        - Repeated creators across sessions
        - Repeated hashtags across sessions
        - Repeated captions across sessions
        - Repeated session IDs within sessions
        - Repeated interest categories (AI/programming/career/entertainment)
        - Different watch durations per content type
        - Different engagement patterns per content type

        Args:
            num_weeks: Number of weeks to simulate
            user_id: User ID for the events

        Returns:
            List of event dicts ready for ingest API
        """
        all_events = []
        start_date = datetime(2026, 6, 1, 0, 0, 0)
        session_counter = 0

        for week in range(num_weeks):
            for day_offset in range(7):
                current_day = start_date + timedelta(weeks=week, days=day_offset)

                for pattern in self.session_patterns:
                    # Check if this session pattern applies today
                    if current_day.weekday() not in pattern["days"]:
                        continue

                    # Probabilistic session occurrence
                    if self.rng.random() > pattern["prob"]:
                        continue

                    # Calculate number of events based on session duration
                    # ~20 seconds per reel average
                    avg_reel_time = 20
                    events_in_session = max(3, pattern["duration"] * 60 // avg_reel_time)
                    events_in_session = min(events_in_session, 40)
                    events_in_session = self.rng.randint(
                        max(3, events_in_session - 5),
                        min(40, events_in_session + 5)
                    )

                    # Create session timestamp
                    session_time = current_day.replace(
                        hour=pattern["hour"],
                        minute=self.rng.randint(0, 59),
                        second=0
                    )

                    session_id = f"synthetic_sess_{user_id}_w{week}_d{day_offset}_s{session_counter}"
                    session_counter += 1

                    session_events = self.generate_session_events(
                        start_time=session_time,
                        session_id=session_id,
                        events_in_session=events_in_session,
                    )
                    all_events.extend(session_events)

        # Shuffle events (they come out of order from the extension)
        self.rng.shuffle(all_events)

        return all_events


def generate_test_payload(
    num_weeks: int = 2,
    user_id: str = "test_user_001",
    events_per_session: int = 12,
    seed: int = 42,
) -> Dict[str, Any]:
    """
    Generate a complete test payload for the /ingest endpoint.

    Args:
        num_weeks: Number of weeks to simulate
        user_id: User ID for events
        events_per_session: Events per session
        seed: Random seed for reproducibility

    Returns:
        Dict ready to POST to /ingest
    """
    generator = SyntheticEventGenerator(seed=seed)
    events = generator.generate_weeks_of_activity(
        num_weeks=num_weeks,
        user_id=user_id,
    )
    return {
        "user_id": user_id,
        "events": events,
    }


if __name__ == "__main__":
    import sys

    num_weeks = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    payload = generate_test_payload(num_weeks=num_weeks)

    # Print summary
    events = payload["events"]
    unique_creators = set(e["username"] for e in events)
    unique_sessions = set(e["session_id"] for e in events)
    unique_reels = set(e["reel_id"] for e in events)
    unique_hashtags = set(
        h for e in events for h in e["hashtags"]
    )

    print(f"Generated {len(events)} events across {len(unique_sessions)} sessions")
    print(f"  Unique creators: {len(unique_creators)}")
    print(f"  Unique reels:    {len(unique_reels)}")
    print(f"  Unique hashtags: {len(unique_hashtags)}")
    print(f"  User:            {payload['user_id']}")
    print(f"  Weeks simulated: {num_weeks}")

    # Save to file
    output_path = f"playground/test_payload_{num_weeks}w.json"
    with open(output_path, "w") as f:
        json.dump(payload, f, indent=2, default=str)
    print(f"\nSaved to {output_path}")
