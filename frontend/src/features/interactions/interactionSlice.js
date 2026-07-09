import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import axios from 'axios';

const API_BASE = 'http://localhost:8000/api';

// Async Thunks
export const fetchHcps = createAsyncThunk(
  'interaction/fetchHcps',
  async (query = '') => {
    const response = await axios.get(`${API_BASE}/hcps${query ? `?q=${query}` : ''}`);
    return response.data;
  }
);

export const fetchProducts = createAsyncThunk(
  'interaction/fetchProducts',
  async () => {
    const response = await axios.get(`${API_BASE}/products`);
    return response.data;
  }
);

export const fetchSamples = createAsyncThunk(
  'interaction/fetchSamples',
  async () => {
    const response = await axios.get(`${API_BASE}/samples`);
    return response.data;
  }
);

export const fetchInteractions = createAsyncThunk(
  'interaction/fetchInteractions',
  async () => {
    const response = await axios.get(`${API_BASE}/interactions`);
    return response.data;
  }
);

export const fetchAuditLogs = createAsyncThunk(
  'interaction/fetchAuditLogs',
  async () => {
    const response = await axios.get(`${API_BASE}/audit-logs`);
    return response.data;
  }
);

export const createInteraction = createAsyncThunk(
  'interaction/createInteraction',
  async (interactionData, { rejectWithValue, dispatch }) => {
    try {
      const response = await axios.post(`${API_BASE}/interactions`, interactionData);
      dispatch(fetchInteractions());
      dispatch(fetchAuditLogs());
      return response.data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to log interaction');
    }
  }
);

export const sendChatMessage = createAsyncThunk(
  'interaction/sendChatMessage',
  async ({ message, threadId, activeHcpId }, { rejectWithValue }) => {
    try {
      const response = await axios.post(`${API_BASE}/agent/chat`, {
        message,
        thread_id: threadId,
        active_hcp_id: activeHcpId
      });
      return response.data; // { messages, thread_id, pending_extraction, warning }
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Error communicating with assistant');
    }
  }
);

const checkDraftCompliance = (pending, hcps, samples) => {
  if (!pending) return null;
  
  const hcpId = pending.hcp_id;
  const hcp = hcps.find(h => h.id === Number(hcpId));
  if (!hcp) {
    return "HCP not found in database.";
  }
  
  if (!hcp.npi_id || hcp.npi_id.length < 10) {
    return `HCP NPI ID ${hcp.npi_id || ''} is invalid or suspended.`;
  }
  
  if (pending.samples_dropped) {
    for (const sDrop of pending.samples_dropped) {
      const qty = sDrop.qty;
      if (qty <= 0) {
        return "Sample quantity must be greater than zero.";
      }
      if (qty > 10) {
        return `Non-compliant: Quantity of ${qty} exceeds the single-transaction limit of 10 samples.`;
      }
      
      const sample = samples.find(s => s.id === Number(sDrop.sample_id));
      if (sample) {
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        const expiry = new Date(sample.expiry_date);
        expiry.setHours(0, 0, 0, 0);
        if (expiry < today) {
          return `Non-compliant: Lot '${sample.lot_number}' expired on ${sample.expiry_date} and cannot be distributed.`;
        }
      }
    }
  }
  
  return null;
};

const initialFormState = {
  hcp_id: '',
  channel: 'visit',
  interaction_datetime: new Date().toISOString().substring(0, 16), // YYYY-MM-DDTHH:MM
  duration_minutes: 15,
  discussion_topics: [],
  products_discussed: [],
  sentiment: 'positive',
  samples_dropped: [], // [{ product_id: '', sample_id: '', qty: 1 }]
  materials_shared: ['Clinical Brochure'],
  next_best_action: '',
  follow_up_date: '',
  raw_transcript: '',
  summary: ''
};

const interactionSlice = createSlice({
  name: 'interaction',
  initialState: {
    activeMode: 'form', // 'form' | 'chat'
    form: initialFormState,
    formErrors: {},
    chat: {
      messages: [
        {
          role: 'assistant',
          content: 'Hello! I am your AI assistant. Tell me about your HCP visit to log an interaction, or ask me for details.'
        }
      ],
      threadId: null,
      pendingExtraction: null,
      warning: null,
      loading: false,
      error: null
    },
    hcps: [],
    products: [],
    samples: [],
    interactionsList: [],
    auditLogs: [],
    loadingMetadata: false,
    submitSuccess: false,
    submitError: null
  },
  reducers: {
    setMode: (state, action) => {
      state.activeMode = action.payload;
    },
    updateFormField: (state, action) => {
      const { field, value } = action.payload;
      state.form[field] = value;
      // Clear error on change
      if (state.formErrors[field]) {
        delete state.formErrors[field];
      }
    },
    resetForm: (state) => {
      state.form = {
        ...initialFormState,
        interaction_datetime: new Date().toISOString().substring(0, 16)
      };
      state.formErrors = {};
      state.submitSuccess = false;
      state.submitError = null;
    },
    setFormErrors: (state, action) => {
      state.formErrors = action.payload;
    },
    updatePendingExtractionField: (state, action) => {
      if (state.chat.pendingExtraction) {
        const { field, value } = action.payload;
        state.chat.pendingExtraction[field] = value;
        
        // Re-check compliance dynamically
        const warning = checkDraftCompliance(
          state.chat.pendingExtraction,
          state.hcps,
          state.samples
        );
        state.chat.warning = warning;
      }
    },
    clearPendingExtraction: (state) => {
      state.chat.pendingExtraction = null;
      state.chat.warning = null;
    },
    resetChat: (state) => {
      state.chat = {
        messages: [
          {
            role: 'assistant',
            content: 'Hello! I am your AI assistant. Tell me about your HCP visit to log an interaction, or ask me for details.'
          }
        ],
        threadId: null,
        pendingExtraction: null,
        warning: null,
        loading: false,
        error: null
      };
    }
  },
  extraReducers: (builder) => {
    builder
      // Fetch HCPs
      .addCase(fetchHcps.fulfilled, (state, action) => {
        state.hcps = action.payload;
      })
      // Fetch Products
      .addCase(fetchProducts.fulfilled, (state, action) => {
        state.products = action.payload;
      })
      // Fetch Samples
      .addCase(fetchSamples.fulfilled, (state, action) => {
        state.samples = action.payload;
      })
      // Fetch Interactions
      .addCase(fetchInteractions.fulfilled, (state, action) => {
        state.interactionsList = action.payload;
      })
      // Fetch Audit Logs
      .addCase(fetchAuditLogs.fulfilled, (state, action) => {
        state.auditLogs = action.payload;
      })
      // Create Interaction
      .addCase(createInteraction.pending, (state) => {
        state.submitSuccess = false;
        state.submitError = null;
      })
      .addCase(createInteraction.fulfilled, (state) => {
        state.submitSuccess = true;
        state.submitError = null;
        state.form = {
          ...initialFormState,
          interaction_datetime: new Date().toISOString().substring(0, 16)
        };
      })
      .addCase(createInteraction.rejected, (state, action) => {
        state.submitSuccess = false;
        state.submitError = action.payload;
      })
      // Chat message sending
      .addCase(sendChatMessage.pending, (state) => {
        state.chat.loading = true;
        state.chat.error = null;
      })
      .addCase(sendChatMessage.fulfilled, (state, action) => {
        state.chat.loading = false;
        state.chat.messages = action.payload.messages;
        state.chat.threadId = action.payload.thread_id;
        state.chat.pendingExtraction = action.payload.pending_extraction;
        state.chat.warning = action.payload.warning;
      })
      .addCase(sendChatMessage.rejected, (state, action) => {
        state.chat.loading = false;
        state.chat.error = action.payload;
      });
  }
});

export const {
  setMode,
  updateFormField,
  resetForm,
  setFormErrors,
  updatePendingExtractionField,
  clearPendingExtraction,
  resetChat
} = interactionSlice.actions;

export default interactionSlice.reducer;
