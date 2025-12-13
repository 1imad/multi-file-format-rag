import { useState, useEffect } from 'react'
import './App.css'
import Chat from './components/Chat'
import Auth from './components/Auth'

function App() {
  const [token, setToken] = useState<string | null>(null);

  useEffect(() => {
    // Check if token exists in localStorage on mount
    const storedToken = localStorage.getItem('token');
    if (storedToken) {
      setToken(storedToken);
    }
  }, []);

  const handleLogin = (newToken: string) => {
    setToken(newToken);
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    setToken(null);
  };

  if (!token) {
    return <Auth onLogin={handleLogin} />;
  }

  return (
    <div>
      <Chat 
        apiUrl="http://localhost:8000" 
        systemPrompt="default"
        token={token}
        onLogout={handleLogout}
      />
    </div>
  );
}

export default App
