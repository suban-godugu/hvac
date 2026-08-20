import { create } from 'zustand';
import { AgentMode, ActionRecord, Zone, SupervisoryCycleResponse } from './types';
import { setAgentMode as apiSetAgentMode } from './api';

interface SupervisoryStoreState {
  data: SupervisoryCycleResponse | null;
  activeTab: 'ALL' | 'O1' | 'O2' | 'O3' | 'O4';
  selectedZone: Zone | null;
  selectedActionForAudit: ActionRecord | null;
  isLimitsModalOpen: boolean;
  demandMethod: 'TRIM_RESPOND' | 'WEIGHTED' | 'THIRD_HIGHEST';
  lastTelemetryTimestamp: number | null;
  isStale: boolean;
  agentMode: AgentMode;
  telemetryAgeSec: number;
  isSimulatorConnected: boolean;

  setData: (data: SupervisoryCycleResponse) => void;
  setActiveTab: (tab: 'ALL' | 'O1' | 'O2' | 'O3' | 'O4') => void;
  setSelectedZone: (zone: Zone | null) => void;
  setSelectedActionForAudit: (action: ActionRecord | null) => void;
  setIsLimitsModalOpen: (open: boolean) => void;
  setDemandMethod: (method: 'TRIM_RESPOND' | 'WEIGHTED' | 'THIRD_HIGHEST') => void;
  setAgentMode: (mode: AgentMode) => Promise<void>;
  updateTelemetryHeartbeat: () => void;
}

export const useSupervisoryStore = create<SupervisoryStoreState>((set, get) => ({
  data: null,
  activeTab: 'ALL',
  selectedZone: null,
  selectedActionForAudit: null,
  isLimitsModalOpen: false,
  demandMethod: 'TRIM_RESPOND',
  lastTelemetryTimestamp: null,
  isStale: false,
  agentMode: 'AUTO',
  telemetryAgeSec: 0,
  isSimulatorConnected: false,

  setData: (data) => set({ data, agentMode: data.mode || get().agentMode }),
  setActiveTab: (tab) => set({ activeTab: tab }),
  setSelectedZone: (zone) => set({ selectedZone: zone }),
  setSelectedActionForAudit: (action) => set({ selectedActionForAudit: action }),
  setIsLimitsModalOpen: (open) => set({ isLimitsModalOpen: open }),
  setDemandMethod: (method) => set({ demandMethod: method }),
  setAgentMode: async (mode) => {
    set({ agentMode: mode });
    try {
      await apiSetAgentMode(mode);
    } catch (err) {
      console.error('Failed to update agent mode via API:', err);
    }
  },
  updateTelemetryHeartbeat: () => set({ lastTelemetryTimestamp: Date.now(), isStale: false }),
}));
