import { opp, type OpportunityDef } from '@/lib/hvac/opportunityTypes';

export const VENTILATION_AGENT = {
  id: 'ventilation' as const,
  title: 'Ventilation & Air Flow Optimizations',
  href: '/agents/ventilation-airflow',
  opportunityIds: ['O10', 'O11', 'O12', 'O13'] as const,
};

export const VENTILATION_OPPORTUNITIES: OpportunityDef[] = [
  opp('O10', 'ventilation', 'Economy Cycle', 'Economy Cycle', '/agents/ventilation-airflow/economy-cycle', 'Enthalpy economizer outdoor-air free cooling.'),
  opp('O11', 'ventilation', 'Night Purge', 'Night Purge', '/agents/ventilation-airflow/night-purge', 'Night-time outdoor-air purge for removing stored building heat before occupancy.'),
  opp('O12', 'ventilation', 'Demand Control Ventilation — CO₂', 'DCV — CO₂', '/agents/ventilation-airflow/demand-ventilation', 'Occupancy- and CO₂-driven outdoor-air optimization for occupied spaces.'),
  opp('O13', 'ventilation', 'Demand Control Ventilation — CO', 'DCV — CO', '/agents/ventilation-airflow/dcv-co', 'CO-based demand ventilation for carparks, loading docks, and enclosed vehicle areas.'),
];
