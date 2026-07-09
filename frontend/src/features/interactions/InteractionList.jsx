import React, { useState, useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { fetchInteractions, fetchAuditLogs } from './interactionSlice';

const InteractionList = () => {
  const dispatch = useDispatch();
  const { interactionsList, auditLogs } = useSelector((state) => state.interaction);
  const [tab, setTab] = useState('interactions'); // 'interactions' | 'audit'
  const [expandedAudit, setExpandedAudit] = useState(null); // ID of expanded audit log row

  useEffect(() => {
    dispatch(fetchInteractions());
    dispatch(fetchAuditLogs());
  }, [dispatch]);

  const toggleExpandAudit = (id) => {
    setExpandedAudit(expandedAudit === id ? null : id);
  };

  return (
    <div className="card history-container glass-container">
      <div className="card-header history-tabs flex-row border-bottom">
        <button
          type="button"
          className={`tab-btn ${tab === 'interactions' ? 'active' : ''}`}
          onClick={() => setTab('interactions')}
        >
          Recent Logs ({interactionsList.length})
        </button>
        <button
          type="button"
          className={`tab-btn ${tab === 'audit' ? 'active' : ''}`}
          onClick={() => setTab('audit')}
        >
          Compliance Audit Ledger ({auditLogs.length})
        </button>
      </div>

      <div className="history-content-scroll">
        {tab === 'interactions' ? (
          interactionsList.length === 0 ? (
            <div className="no-records-card">No interactions logged yet. Choose a mode to get started!</div>
          ) : (
            interactionsList.map((inter) => (
              <div key={inter.id} className="history-item-card">
                <div className="flex-row justify-between mb-5 align-center">
                  <span className="hcp-name-title">HCP ID: {inter.hcp_id}</span>
                  <div className="flex-row gap-5">
                    <span className={`badge badge-mode badge-mode-${inter.entry_mode}`}>
                      {inter.entry_mode === 'chat' ? '🤖 Chat-Assisted' : '📝 Structured'}
                    </span>
                    <span className={`badge badge-sentiment badge-sentiment-${inter.sentiment.toLowerCase()}`}>
                      {inter.sentiment}
                    </span>
                  </div>
                </div>

                <div className="meta-grid">
                  <div><strong>Channel:</strong> {inter.channel}</div>
                  <div><strong>Duration:</strong> {inter.duration_minutes} mins</div>
                  <div><strong>Date:</strong> {new Date(inter.interaction_datetime).toLocaleString()}</div>
                  <div><strong>Follow-up:</strong> {inter.follow_up_date || 'None'}</div>
                </div>

                {inter.products_discussed.length > 0 && (
                  <div className="mt-5 text-xs">
                    <strong>Discussed:</strong> {inter.products_discussed.join(', ')}
                  </div>
                )}

                {inter.samples_dropped && inter.samples_dropped.length > 0 && (
                  <div className="mt-5 text-xs text-secondary-color">
                    <strong>Distributed Samples:</strong>{' '}
                    {inter.samples_dropped.map((s, idx) => (
                      <span key={idx} className="sample-tag-item">
                        {s.product_name} (Lot: {s.lot_number}) × {s.qty}
                      </span>
                    ))}
                  </div>
                )}

                {inter.next_best_action && (
                  <div className="mt-5 text-xs action-callout">
                    <strong>Next Action:</strong> {inter.next_best_action}
                  </div>
                )}

                <div className="summary-section mt-10">
                  <p className="summary-heading">Summary Ledger</p>
                  <p className="summary-body">{inter.summary}</p>
                </div>
              </div>
            ))
          )
        ) : (
          auditLogs.length === 0 ? (
            <div className="no-records-card">No audit events generated yet.</div>
          ) : (
            auditLogs.map((log) => {
              const isExpanded = expandedAudit === log.id;
              return (
                <div key={log.id} className="audit-log-row-item">
                  <div className="flex-row justify-between align-center" onClick={() => toggleExpandAudit(log.id)}>
                    <div className="cursor-pointer">
                      <span className="font-bold text-sm">
                        Interaction #{log.interaction_id} — {log.change_type.toUpperCase()}
                      </span>
                      <div className="text-xs text-muted">
                        By User #{log.changed_by} at {new Date(log.changed_at).toLocaleString()}
                      </div>
                    </div>
                    <button className="expand-indicator-btn">{isExpanded ? '▼' : '▶'}</button>
                  </div>

                  {isExpanded && (
                    <div className="audit-diff-panel mt-10">
                      <p className="text-xs font-bold border-bottom pb-5 mb-5">Change Differential Ledger:</p>
                      {log.change_type === 'create' ? (
                        <div className="diff-grid text-xs">
                          {Object.entries(log.diff_json?.changes || {}).map(([key, val]) => (
                            <div key={key} className="diff-row">
                              <span className="diff-key">{key}:</span>
                              <span className="diff-added">{String(val)}</span>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div className="diff-grid text-xs">
                          {Object.entries(log.diff_json || {}).map(([key, diffObj]) => (
                            <div key={key} className="diff-row flex-column gap-2 mb-5">
                              <span className="diff-key">{key}:</span>
                              <div className="flex-row gap-10">
                                <span className="diff-removed">Old: {JSON.stringify(diffObj.old)}</span>
                                <span className="diff-added">New: {JSON.stringify(diffObj.new)}</span>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })
          )
        )}
      </div>
    </div>
  );
};

export default InteractionList;
