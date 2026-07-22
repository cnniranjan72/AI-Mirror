import { BrowserRouter as Router } from 'react-router-dom'
import AppShell from './components/layout/AppShell'
import './styles/design-system.css'
import './App.css'

function App() {
  return (
    <Router>
      <AppShell />
    </Router>
  )
}

export default App
