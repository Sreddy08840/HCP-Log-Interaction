import { configureStore } from '@reduxjs/toolkit';
import interactionReducer from '../features/interactions/interactionSlice';

export const store = configureStore({
  reducer: {
    interaction: interactionReducer
  }
});
