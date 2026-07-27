-- AIMirror V9: persistent Guardian alert log (in-app push-equivalent)

CREATE TABLE IF NOT EXISTS guardian_alerts (
    id SERIAL PRIMARY KEY,
    alert_id TEXT UNIQUE NOT NULL,
    user_id TEXT NOT NULL,
    risk_level TEXT NOT NULL,
    risk_score FLOAT NOT NULL,
    risk_factors JSONB DEFAULT '[]',
    acknowledged BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_guardian_alerts_user ON guardian_alerts(user_id);
CREATE INDEX IF NOT EXISTS idx_guardian_alerts_created ON guardian_alerts(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_guardian_alerts_unack ON guardian_alerts(user_id, acknowledged) WHERE acknowledged = FALSE;
