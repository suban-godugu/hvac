import { opp, type OpportunityDef } from '@/lib/hvac/opportunityTypes';

export const SCHEDULING_AGENT = {
  id: 'scheduling' as const,
  title: 'Scheduling & Supervisory Agent',
  href: '/agents/scheduling',
  opportunityIds: ['O1', 'O2', 'O3', 'O4'] as const,
};

export const SCHEDULING_OPPORTUNITIES: OpportunityDef[] = [
  opp('O1', 'scheduling', 'Optimum Start/Stop Programming', 'Optimum Start/Stop Programming', '/agents/scheduling/optimum-start-stop', 'Thermodynamic pull-down trajectory and coasting stop.'),
  opp('O2', 'scheduling', 'Space Temperature Set Points & Control Bands', 'Space Temperature Set Points & Control Bands', '/agents/scheduling/space-temperature', 'Occupancy-driven setpoint floating and deadband expansion.'),
  opp('O3', 'scheduling', 'Master Air Handling Unit Supply Air Temperature Signal', 'Master AHU Supply Air Temperature Signal', '/agents/scheduling/master-ahu-sat', 'Guideline 36 trim and respond with rogue-zone isolation.'),
  opp('O4', 'scheduling', 'Staging of Chillers & Compressors', 'Staging of Chillers & Compressors', '/agents/scheduling/chiller-staging', 'Thermal tonnage matching and CHWS reset.'),
];
