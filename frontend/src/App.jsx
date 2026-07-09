import React, { useEffect } from 'react';
import { useDispatch } from 'react-redux';
import {
  fetchProducts,
  fetchSamples,
  fetchHcps
} from './features/interactions/interactionSlice';
import LogInteractionForm from './features/interactions/LogInteractionForm';
import LogInteractionChat from './features/interactions/LogInteractionChat';
import InteractionList from './features/interactions/InteractionList';

function App() {
  const dispatch = useDispatch();

  // Fetch initial catalog data on mount
  useEffect(() => {
    dispatch(fetchProducts());
    dispatch(fetchSamples());
    dispatch(fetchHcps(''));
  }, [dispatch]);

  return (
    <div className="app-container">
      {/* Top Navigation / Dashboard Header */}
      <header className="app-header glass-header">
        <div className="header-brand">
          <span className="brand-logo">🧬</span>
          <div>
            <h1>MedicaCRM</h1>
            <p className="header-subtitle">HCP Relationship Management • AI-First Portal</p>
          </div>
        </div>
        
        <div className="header-user">
          <div className="user-avatar">SR</div>
          <div className="user-details">
            <span className="user-name">Sarah Rep</span>
            <span className="user-role">Territory Manager • TERR-01</span>
          </div>
        </div>
      </header>

      {/* Main Split Screen Layout */}
      <main className="dashboard-grid">
        {/* Left Panel: Programmatic Read-Only Form */}
        <section className="logging-pane">
          <LogInteractionForm />
        </section>

        {/* Right Panel: AI Chat Control Center */}
        <section className="chat-pane">
          <LogInteractionChat />
        </section>
      </main>

      {/* Bottom Panel: History & Audit Trails */}
      <footer className="history-pane">
        <InteractionList />
      </footer>
    </div>
  );
}

export default App;
