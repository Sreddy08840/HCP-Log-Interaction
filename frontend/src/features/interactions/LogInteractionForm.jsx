import React from 'react';
import { useSelector } from 'react-redux';

const LogInteractionForm = () => {
  const { chat, products, samples } = useSelector((state) => state.interaction);
  const draft = chat.pendingExtraction;

  // Render check status for checkboxes
  const isProductChecked = (prodName) => {
    return draft?.products_discussed?.includes(prodName) || false;
  };

  const isTopicChecked = (topic) => {
    return draft?.discussion_topics?.includes(topic) || false;
  };

  return (
    <div className="card glass-container programmatic-mode">
      <div className="card-header">
        <div className="flex-row justify-between align-center">
          <h2>Log Interaction — Programmatic Form</h2>
          <span className="badge badge-warning">🔒 READ-ONLY LEDGER</span>
        </div>
        <p className="card-subtitle">
          This form is updated exclusively by the AI Copilot on the right panel. Manual input is disabled.
        </p>
      </div>

      {!draft ? (
        <div className="no-records-card py-40">
          <p className="font-bold mb-5">Waiting for AI Input...</p>
          <p className="text-xs text-muted">
            Describe your visit to the AI Assistant on the right panel (e.g., "Log a 20min visit with Dr. Mehta today...") to populate this form.
          </p>
        </div>
      ) : (
        <div className="form-grid">
          {/* Resolved HCP */}
          <div className="form-group full-width">
            <label className="form-label">Resolved Healthcare Professional (HCP)</label>
            <input
              type="text"
              value={draft.hcp_name ? `${draft.hcp_name} (ID: ${draft.hcp_id})` : 'Unresolved HCP'}
              readOnly
              className="form-input read-only-input"
            />
          </div>

          {/* Channel & DateTime */}
          <div className="form-group">
            <label className="form-label">Interaction Channel</label>
            <input
              type="text"
              value={draft.channel ? draft.channel.toUpperCase() : ''}
              readOnly
              className="form-input read-only-input"
            />
          </div>

          <div className="form-group">
            <label className="form-label">Date & Time</label>
            <input
              type="text"
              value={draft.interaction_datetime ? new Date(draft.interaction_datetime).toLocaleString() : ''}
              readOnly
              className="form-input read-only-input"
            />
          </div>

          {/* Duration & Sentiment */}
          <div className="form-group">
            <label className="form-label">Duration (minutes)</label>
            <input
              type="number"
              value={draft.duration_minutes || 0}
              readOnly
              className="form-input read-only-input"
            />
          </div>

          <div className="form-group">
            <label className="form-label">Sentiment</label>
            <input
              type="text"
              value={draft.sentiment ? draft.sentiment.toUpperCase() : ''}
              readOnly
              className="form-input read-only-input"
            />
          </div>

          {/* Products Discussed & Topics */}
          <div className="form-group full-width flex-row gap-20">
            <div className="flex-1">
              <label className="form-label">Products Discussed</label>
              <div className="checkbox-group disabled-group">
                {products.map((p) => (
                  <label key={p.id} className="checkbox-label disabled-label">
                    <input
                      type="checkbox"
                      checked={isProductChecked(p.name)}
                      disabled
                    />
                    <span>{p.name}</span>
                  </label>
                ))}
              </div>
            </div>
            <div className="flex-1">
              <label className="form-label">Discussion Topics</label>
              <div className="checkbox-group disabled-group">
                {['Product Presentation', 'Efficacy Review', 'Safety Profile', 'Dosage Options', 'Competitor Comparison', 'Sample distribution'].map((topic) => (
                  <label key={topic} className="checkbox-label disabled-label">
                    <input
                      type="checkbox"
                      checked={isTopicChecked(topic)}
                      disabled
                    />
                    <span>{topic}</span>
                  </label>
                ))}
              </div>
            </div>
          </div>

          {/* Samples Dropped */}
          <div className="form-group full-width border-top pt-15">
            <label className="form-label mb-10">Distributed Samples</label>

            {!draft.samples_dropped || draft.samples_dropped.length === 0 ? (
              <p className="no-records-card text-xs">No samples distributed.</p>
            ) : (
              <div className="samples-table">
                {draft.samples_dropped.map((row, index) => {
                  const lotExpiry = samples.find(s => s.id === row.sample_id)?.expiry_date;
                  const isExpired = lotExpiry ? new Date(lotExpiry) < new Date() : false;

                  return (
                    <div key={index} className="sample-row align-center gap-10 mb-5">
                      <div className="flex-2 text-xs">
                        <strong>Product:</strong> {row.product_name || 'Unknown'}
                      </div>
                      <div className="flex-2 text-xs">
                        <strong>Lot:</strong> {row.lot_number || 'Unknown'}
                      </div>
                      <div className="flex-1 text-xs">
                        <strong>Qty:</strong> {row.qty}
                      </div>
                      <div className="flex-1 text-center">
                        {lotExpiry && (
                          <span className={`expiry-tag ${isExpired ? 'expired' : 'active'}`}>
                            Exp: {lotExpiry}
                          </span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Follow-up Details */}
          <div className="form-group pt-15 border-top">
            <label className="form-label">Next Best Action</label>
            <input
              type="text"
              value={draft.next_best_action || ''}
              readOnly
              className="form-input read-only-input"
            />
          </div>

          <div className="form-group pt-15 border-top">
            <label className="form-label">Follow-up Date</label>
            <input
              type="text"
              value={draft.follow_up_date || 'None'}
              readOnly
              className="form-input read-only-input"
            />
          </div>

          {/* Meeting Notes */}
          <div className="form-group full-width">
            <label className="form-label">Interaction Summary</label>
            <textarea
              rows="3"
              value={draft.summary || ''}
              readOnly
              className="form-textarea read-only-input"
            ></textarea>
          </div>
        </div>
      )}
    </div>
  );
};

export default LogInteractionForm;
