import React, { useState } from 'react';
import './App.css';

const API_URL = process.env.REACT_APP_API_URL || "/api";

const LoadingDots = () => (
  <div className="loading-container">
    <div className="loading-dots">
      <span /><span /><span />
    </div>
    <p className="loading-text">Ruh halin analiz ediliyor...</p>
  </div>
);

const Card = ({ item, index }) => (
  <div className="rec-card" style={{ animationDelay: `${index * 0.1}s` }}>
    <div className="rec-info">
      <h4 className="rec-title">{item.title}</h4>
      <p className="rec-creator">{item.creator}</p>
      <p className="rec-reason">{item.reason}</p>
    </div>
  </div>
);

const Section = ({ title, icon, items }) => (
  <div className="section">
    <h3 className="section-title">
      <span className="section-icon">{icon}</span>
      {title}
    </h3>
    <div className="cards-grid">
      {items.map((item, i) => <Card key={i} item={item} index={i} />)}
    </div>
  </div>
);

export default function App() {
  const [mood, setMood] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [moodColor, setMoodColor] = useState('#a78bfa');

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!mood.trim()) return;

    setLoading(true);
    setError('');
    setResult(null);

    try {
      const res = await fetch(`${API_URL}/recommend`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mood }),
      });

      if (!res.ok) {
        throw new Error('Sunucu hatası, tekrar dene.');
      }

      const data = await res.json();
      setResult(data);
      setMoodColor(data.mood_color);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app" style={{ '--mood-color': moodColor }}>
      <div className="bg-glow" />

      <header className="header">
        <div className="logo">
          <span className="logo-icon">◈</span>
          <span className="logo-text">moodwave</span>
        </div>
        <p className="tagline">Ruh haline göre müzik, film ve kitap</p>
      </header>

      <main className="main">
        <form className="mood-form" onSubmit={handleSubmit}>
          <textarea
            className="mood-input"
            value={mood}
            onChange={(e) => setMood(e.target.value)}
            placeholder="Şu an nasıl hissediyorsun? Özgürce yaz..."
            rows={3}
            disabled={loading}
          />
          <button className="submit-btn" type="submit" disabled={loading || !mood.trim()}>
            {loading ? '...' : 'Keşfet →'}
          </button>
        </form>

        {error && <div className="error-box">{error}</div>}
        {loading && <LoadingDots />}

        {result && !loading && (
          <div className="results">
            <div className="mood-card">
              <div className="mood-dot" style={{ background: moodColor }} />
              <div>
                <span className="mood-badge">{result.mood_category}</span>
                <p className="mood-summary">{result.mood_summary}</p>
              </div>
            </div>

            <Section title="Müzik" icon="♪" items={result.songs} />
            <Section title="Film" icon="◉" items={result.movies} />
            <Section title="Kitap" icon="◻" items={result.books} />
          </div>
        )}
      </main>
    </div>
  );
}