import React, { useState, useRef, useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import {
  sendChatMessage,
  updatePendingExtractionField,
  clearPendingExtraction,
  fetchInteractions,
  fetchAuditLogs
} from './interactionSlice';

const STANDARD_TOPICS = [
  'Product Presentation',
  'Efficacy Review',
  'Safety Profile',
  'Dosage Options',
  'Competitor Comparison',
  'Sample distribution'
];

const LogInteractionChat = () => {
  const dispatch = useDispatch();
  const { chat, products, samples, submitSuccess } = useSelector((state) => state.interaction);
  const [input, setInput] = useState('');
  const chatEndRef = useRef(null);

  // Auto-scroll chat to bottom when messages or pending draft changes
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chat.messages, chat.pendingExtraction, chat.loading]);

  const handleSend = (e) => {
    e.preventDefault();
    if (!input.trim() || chat.loading) return;

    dispatch(sendChatMessage({
      message: input,
      threadId: chat.threadId,
      activeHcpId: null // We could bind to active HCP if set
    }));
    setInput('');
  };

  const handleConfirmDraft = () => {
    dispatch(sendChatMessage({
      message: 'Confirm',
      threadId: chat.threadId
    })).then(() => {
      // Refresh interactions list & audit logs after confirm save
      dispatch(fetchInteractions());
      dispatch(fetchAuditLogs());
    });
  };

  const handleCancelDraft = () => {
    dispatch(clearPendingExtraction());
  };

  // Helper to update fields on the pending draft card
  const handleDraftFieldChange = (field, value) => {
    dispatch(updatePendingExtractionField({ field, value }));
  };

  // Helper to handle sample qty change inside the draft card
  const handleDraftSampleQty = (index, value) => {
    const updated = chat.pendingExtraction.samples_dropped.map((s, idx) => {
      if (idx === index) {
        return { ...s, qty: parseInt(value) || 0 };
      }
      return s;
    });
    dispatch(updatePendingExtractionField({ field: 'samples_dropped', value: updated }));
  };

  return (
    <div className="card chat-container glass-container">
      <div className="card-header flex-row justify-between align-center">
        <div>
          <h2>AI Copilot Assistant</h2>
          <p className="card-subtitle">Speak or type your visit summary, and the assistant will structure it</p>
        </div>
        {chat.warning && (
          <div className="badge badge-warning text-xs">
            {chat.warning}
          </div>
        )}
      </div>

      {/* Messages Scroll Area */}
      <div className="chat-messages-area">
        {chat.messages.map((msg, index) => (
          <div key={index} className={`chat-message-bubble ${msg.role === 'user' ? 'user-bubble' : 'assistant-bubble'}`}>
            <div className="bubble-sender">{msg.role === 'user' ? 'You' : 'Assistant'}</div>
            <div className="bubble-content">{msg.content}</div>
          </div>
        ))}

        {/* Inline Pending Extraction Draft Card */}
        {chat.pendingExtraction && (
          <div className="draft-card-inline">
            <div className="draft-card-header">
              <span className="draft-badge">Pending Confirmation</span>
              <h3>Extracted Visit Details</h3>
            </div>
            
            <div className="draft-card-body">
              {/* HCP */}
              <div className="draft-field">
                <span className="draft-label">HCP Name:</span>
                <span className="draft-value font-bold">{chat.pendingExtraction.hcp_name || 'Unresolved HCP'}</span>
              </div>

              {/* Channel */}
              <div className="draft-field">
                <span className="draft-label">Channel:</span>
                <select
                  value={chat.pendingExtraction.channel}
                  onChange={(e) => handleDraftFieldChange('channel', e.target.value)}
                  className="draft-input-select"
                >
                  <option value="visit">In-Person Visit</option>
                  <option value="call">Phone Call</option>
                  <option value="virtual">Virtual Meeting</option>
                  <option value="email">Email</option>
                </select>
              </div>

              {/* Sentiment */}
              <div className="draft-field">
                <span className="draft-label">Sentiment:</span>
                <select
                  value={chat.pendingExtraction.sentiment}
                  onChange={(e) => handleDraftFieldChange('sentiment', e.target.value)}
                  className="draft-input-select"
                >
                  <option value="positive">Positive</option>
                  <option value="neutral">Neutral</option>
                  <option value="negative">Negative</option>
                  <option value="objection">Objection Raised</option>
                </select>
              </div>

              {/* Duration */}
              <div className="draft-field">
                <span className="draft-label">Duration:</span>
                <div className="flex-row align-center gap-5">
                  <input
                    type="number"
                    value={chat.pendingExtraction.duration_minutes}
                    onChange={(e) => handleDraftFieldChange('duration_minutes', parseInt(e.target.value) || 0)}
                    className="draft-input-text w-60"
                  />
                  <span className="text-xs">min</span>
                </div>
              </div>



              {/* Discussion Products */}
              <div className="draft-field flex-column mt-5 align-start w-full">
                <span className="draft-label block mb-5">Products Discussed:</span>
                <div className="draft-checkbox-group">
                  {products.map((p) => {
                    const isChecked = chat.pendingExtraction.products_discussed?.includes(p.name);
                    return (
                      <label key={p.id} className="draft-checkbox-label">
                        <input
                          type="checkbox"
                          checked={isChecked || false}
                          onChange={(e) => {
                            const current = chat.pendingExtraction.products_discussed || [];
                            const updated = e.target.checked
                              ? [...current, p.name]
                              : current.filter(name => name !== p.name);
                            handleDraftFieldChange('products_discussed', updated);
                          }}
                        />
                        <span>{p.name}</span>
                      </label>
                    );
                  })}
                </div>
              </div>

              {/* Discussion Topics */}
              <div className="draft-field flex-column mt-5 align-start w-full">
                <span className="draft-label block mb-5">Discussion Topics:</span>
                <div className="draft-checkbox-group">
                  {STANDARD_TOPICS.map((topic) => {
                    const isChecked = chat.pendingExtraction.discussion_topics?.includes(topic);
                    return (
                      <label key={topic} className="draft-checkbox-label">
                        <input
                          type="checkbox"
                          checked={isChecked || false}
                          onChange={(e) => {
                            const current = chat.pendingExtraction.discussion_topics || [];
                            const updated = e.target.checked
                              ? [...current, topic]
                              : current.filter(t => t !== topic);
                            handleDraftFieldChange('discussion_topics', updated);
                          }}
                        />
                        <span>{topic}</span>
                      </label>
                    );
                  })}
                </div>
              </div>

              {/* Samples */}
              <div className="draft-samples-section">
                <span className="draft-label font-bold block mb-5">Samples Dropped:</span>
                {chat.pendingExtraction.samples_dropped?.length === 0 ? (
                  <span className="text-xs italic text-muted">No samples dropped.</span>
                ) : (
                  chat.pendingExtraction.samples_dropped.map((sample, idx) => {
                    const expiry = samples.find(s => s.id === sample.sample_id)?.expiry_date;
                    const isExpired = expiry ? new Date(expiry) < new Date() : false;
                    
                    return (
                      <div key={idx} className="draft-sample-row">
                        <div className="flex-2 text-xs">
                          {sample.product_name} <span className="text-muted">(Lot: {sample.lot_number})</span>
                        </div>
                        <div className="flex-1 flex-row align-center gap-5 justify-end">
                          <span className="text-xs">Qty:</span>
                          <input
                            type="number"
                            value={sample.qty}
                            min="1"
                            max="10"
                            onChange={(e) => handleDraftSampleQty(idx, e.target.value)}
                            className="draft-input-text w-50"
                          />
                        </div>
                        {expiry && (
                          <div className={`expiry-tag-chat ${isExpired ? 'expired' : 'active'}`}>
                            {isExpired ? 'Expired' : 'Valid'}
                          </div>
                        )}
                      </div>
                    );
                  })
                )}
              </div>

              {/* Next Best Action */}
              <div className="draft-field flex-column mt-5 align-start w-full">
                <span className="draft-label block">Next Best Action:</span>
                <input
                  type="text"
                  value={chat.pendingExtraction.next_best_action || ''}
                  onChange={(e) => handleDraftFieldChange('next_best_action', e.target.value)}
                  className="draft-input-text w-full mt-2"
                />
              </div>

              {/* Follow up date */}
              <div className="draft-field">
                <span className="draft-label">Follow-up Date:</span>
                <input
                  type="date"
                  value={chat.pendingExtraction.follow_up_date || ''}
                  onChange={(e) => handleDraftFieldChange('follow_up_date', e.target.value)}
                  className="draft-input-text"
                />
              </div>

              {/* Summary Notes */}
              <div className="draft-field flex-column mt-5 align-start w-full">
                <span className="draft-label block">Summary:</span>
                <textarea
                  rows="2"
                  value={chat.pendingExtraction.summary || ''}
                  onChange={(e) => handleDraftFieldChange('summary', e.target.value)}
                  className="draft-textarea w-full mt-2"
                ></textarea>
              </div>

              {/* Local Warning Banner inside Card */}
              {chat.warning && (
                <div className="draft-warning-banner">
                  ⚠️ {chat.warning}
                </div>
              )}
            </div>

            <div className="draft-card-footer flex-row gap-10 justify-end">
              <button onClick={handleCancelDraft} className="btn btn-secondary btn-sm">
                Cancel
              </button>
              <button 
                onClick={handleConfirmDraft} 
                className="btn btn-primary btn-sm"
                disabled={!!chat.warning}
              >
                Confirm & Save
              </button>
            </div>
          </div>
        )}

        {/* Typing indicator */}
        {chat.loading && (
          <div className="chat-message-bubble assistant-bubble">
            <div className="typing-indicator">
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>
        )}

        <div ref={chatEndRef} />
      </div>

      {/* Message input */}
      <form onSubmit={handleSend} className="chat-input-bar">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="E.g., Met Dr. Mehta today. Discussed CardioX. Dropped 5 units of lot CX10-2027. Cautiously positive."
          className="chat-input"
          disabled={chat.loading}
        />
        <button type="submit" className="btn btn-primary btn-chat-send" disabled={chat.loading || !input.trim()}>
          Send
        </button>
      </form>
    </div>
  );
};

export default LogInteractionChat;
