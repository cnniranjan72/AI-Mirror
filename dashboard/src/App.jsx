import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom'
import Overview from './pages/Overview'
import Sessions from './pages/Sessions'
import SessionDetail from './pages/SessionDetail'
import Analytics from './pages/Analytics'
import './App.css'

function App() {
  return (
    <Router>
      <div className="app">
        <nav className="navbar">
          <div className="container">
            <div className="nav-content">
              <div className="nav-brand">
                <span className="nav-icon">🪞</span>
                <span className="nav-title">AIMirror</span>
              </div>
              <div className="nav-links">
                <Link to="/" className="nav-link">Overview</Link>
                <Link to="/sessions" className="nav-link">Sessions</Link>
                <Link to="/analytics" className="nav-link">Analytics</Link>
              </div>
            </div>
          </div>
        </nav>

        <main className="main-content">
          <Routes>
            <Route path="/" element={<Overview />} />
            <Route path="/sessions" element={<Sessions />} />
            <Route path="/sessions/:sessionId" element={<SessionDetail />} />
            <Route path="/analytics" element={<Analytics />} />
          </Routes>
        </main>

        <footer className="footer">
          <div className="container">
            <p>AIMirror - Behavioral Digital Twin for Social Media Transparency</p>
          </div>
        </footer>
      </div>
    </Router>
  )
}

export default App
