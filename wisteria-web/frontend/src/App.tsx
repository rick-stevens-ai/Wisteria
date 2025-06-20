import React, { useState, useEffect } from 'react';
import { apiService } from './services/api';
import { Session, Hypothesis, Model } from './types/hypothesis';

function App() {
  const [models, setModels] = useState<Model[]>([]);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [currentSession, setCurrentSession] = useState<Session | null>(null);
  const [currentHypothesis, setCurrentHypothesis] = useState<Hypothesis | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Form states
  const [researchGoal, setResearchGoal] = useState('');
  const [selectedModel, setSelectedModel] = useState('');
  const [feedback, setFeedback] = useState('');

  useEffect(() => {
    loadModels();
    loadSessions();
  }, []);

  const loadModels = async () => {
    const result = await apiService.getModels();
    if (result.data) {
      setModels(result.data);
    } else {
      setError(result.error || 'Failed to load models');
    }
  };

  const loadSessions = async () => {
    const result = await apiService.getSessions();
    if (result.data) {
      setSessions(result.data);
    } else {
      setError(result.error || 'Failed to load sessions');
    }
  };

  const createNewSession = async () => {
    if (!researchGoal.trim() || !selectedModel) {
      setError('Please provide a research goal and select a model');
      return;
    }

    setLoading(true);
    setError(null);

    const result = await apiService.createSession(researchGoal, selectedModel);
    if (result.data) {
      setCurrentSession(result.data);
      setSessions([result.data, ...sessions]);
      setResearchGoal('');
      setSelectedModel('');
    } else {
      setError(result.error || 'Failed to create session');
    }
    setLoading(false);
  };

  const generateHypothesis = async () => {
    if (!currentSession) return;

    setLoading(true);
    setError(null);

    const result = await apiService.generateHypothesis(currentSession.id);
    if (result.data) {
      setCurrentHypothesis(result.data);
      // Refresh session to get updated hypothesis count
      const sessionResult = await apiService.getSession(currentSession.id);
      if (sessionResult.data) {
        setCurrentSession(sessionResult.data);
      }
    } else {
      setError(result.error || 'Failed to generate hypothesis');
    }
    setLoading(false);
  };

  const improveHypothesis = async () => {
    if (!currentSession || !currentHypothesis || !feedback.trim()) return;

    setLoading(true);
    setError(null);

    const result = await apiService.improveHypothesis(currentSession.id, currentHypothesis.id, feedback);
    if (result.data) {
      setCurrentHypothesis(result.data);
      setFeedback('');
      // Refresh session
      const sessionResult = await apiService.getSession(currentSession.id);
      if (sessionResult.data) {
        setCurrentSession(sessionResult.data);
      }
    } else {
      setError(result.error || 'Failed to improve hypothesis');
    }
    setLoading(false);
  };

  const generateNewHypothesis = async () => {
    if (!currentSession) return;

    setLoading(true);
    setError(null);

    const result = await apiService.generateNewHypothesis(currentSession.id);
    if (result.data) {
      setCurrentHypothesis(result.data);
      // Refresh session
      const sessionResult = await apiService.getSession(currentSession.id);
      if (sessionResult.data) {
        setCurrentSession(sessionResult.data);
      }
    } else {
      setError(result.error || 'Failed to generate new hypothesis');
    }
    setLoading(false);
  };

  const selectSession = async (session: Session) => {
    setCurrentSession(session);
    setCurrentHypothesis(null);
    
    // Load session details with hypotheses
    const result = await apiService.getSession(session.id);
    if (result.data && result.data.hypotheses && result.data.hypotheses.length > 0) {
      setCurrentHypothesis(result.data.hypotheses[result.data.hypotheses.length - 1]);
    }
  };

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#f9fafb' }}>
      <div className="container">
        <div className="header">
          <h1>Wisteria Research Hypothesis Generator</h1>
        </div>

        {error && (
          <div className="alert alert-error">
            {error}
          </div>
        )}

        <div className="grid">
          {/* Left Panel - Sessions */}
          <div>
            <div className="card">
              <h2>Sessions</h2>
              
              {/* Create New Session */}
              <div className="card" style={{ marginBottom: '1.5rem' }}>
                <h3 style={{ fontSize: '1rem', fontWeight: '500', marginBottom: '0.75rem' }}>Create New Session</h3>
                <div>
                  <div className="form-group">
                    <textarea
                      value={researchGoal}
                      onChange={(e) => setResearchGoal(e.target.value)}
                      placeholder="Enter your research goal..."
                      className="form-control"
                      style={{ height: '80px' }}
                    />
                  </div>
                  <div className="form-group">
                    <select
                      value={selectedModel}
                      onChange={(e) => setSelectedModel(e.target.value)}
                      className="form-control"
                    >
                      <option value="">Select a model</option>
                      {models.map((model) => (
                        <option key={model.shortname} value={model.shortname}>
                          {model.shortname} ({model.model_name})
                        </option>
                      ))}
                    </select>
                  </div>
                  <button
                    onClick={createNewSession}
                    disabled={loading || !researchGoal.trim() || !selectedModel}
                    className="btn btn-primary w-full"
                  >
                    {loading ? 'Creating...' : 'Create Session'}
                  </button>
                </div>
              </div>

              {/* Session List */}
              <div>
                {sessions.map((session) => (
                  <div
                    key={session.id}
                    onClick={() => selectSession(session)}
                    className={`session-item ${currentSession?.id === session.id ? 'active' : ''}`}
                  >
                    <h4>{session.research_goal}</h4>
                    <p>{session.model_shortname}</p>
                    <p style={{ fontSize: '0.75rem', color: '#9ca3af' }}>
                      {new Date(session.created_at).toLocaleDateString()}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Right Panel - Hypothesis Viewer */}
          <div>
            <div className="card">
              {currentSession ? (
                <div>
                  <div className="hypothesis-header">
                    <h2>Session: {currentSession.research_goal}</h2>
                    <span className="text-gray-500">
                      Model: {currentSession.model_shortname}
                    </span>
                  </div>

                  {!currentHypothesis ? (
                    <div className="text-center p-8">
                      <p className="text-gray-500 mb-4">No hypothesis generated yet</p>
                      <button
                        onClick={generateHypothesis}
                        disabled={loading}
                        className="btn btn-success"
                      >
                        {loading ? 'Generating...' : 'Generate First Hypothesis'}
                      </button>
                    </div>
                  ) : (
                    <div>
                      {/* Hypothesis Display */}
                      <div className="hypothesis">
                        <div className="hypothesis-header">
                          <h3 className="hypothesis-title">
                            Hypothesis #{currentHypothesis.hypothesis_number} v{currentHypothesis.version}
                          </h3>
                          <p className="hypothesis-meta">
                            Type: {currentHypothesis.hypothesis_type}
                          </p>
                        </div>
                        
                        <div className="hypothesis-section">
                          <h4>Title</h4>
                          <p>{currentHypothesis.title}</p>
                        </div>

                        <div className="hypothesis-section">
                          <h4>Description</h4>
                          <p>{currentHypothesis.description}</p>
                        </div>

                        <div className="hypothesis-section">
                          <h4>Hallmarks Analysis</h4>
                          <div className="hallmarks-grid">
                            {Object.entries(currentHypothesis.hallmarks).map(([key, value]) => (
                              <div key={key} className="hallmark-item">
                                <h5>{key.replace('_', ' ')}:</h5>
                                <p>{value}</p>
                              </div>
                            ))}
                          </div>
                        </div>

                        {currentHypothesis.references.length > 0 && (
                          <div className="hypothesis-section">
                            <h4>References</h4>
                            <div>
                              {currentHypothesis.references.map((ref, index) => (
                                <div key={index} style={{ marginBottom: '0.5rem' }}>
                                  <p style={{ fontWeight: '500', fontSize: '0.875rem' }}>{ref.citation}</p>
                                  <p style={{ color: '#6b7280', fontSize: '0.875rem' }}>{ref.annotation}</p>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>

                      {/* Action Buttons */}
                      <div className="border-t pt-4">
                        <div className="mb-4">
                          <h4>Provide Feedback</h4>
                          <textarea
                            value={feedback}
                            onChange={(e) => setFeedback(e.target.value)}
                            placeholder="Enter your feedback to improve this hypothesis..."
                            className="form-control"
                            style={{ height: '80px' }}
                          />
                        </div>
                        
                        <div className="flex space-x-4">
                          <button
                            onClick={improveHypothesis}
                            disabled={loading || !feedback.trim()}
                            className="btn btn-warning"
                          >
                            {loading ? 'Improving...' : 'Improve Hypothesis'}
                          </button>
                          <button
                            onClick={generateNewHypothesis}
                            disabled={loading}
                            className="btn btn-danger"
                          >
                            {loading ? 'Generating...' : 'Generate New Hypothesis'}
                          </button>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center p-8 text-gray-500">
                  Select a session to view hypotheses
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
