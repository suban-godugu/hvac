import { opp, type OpportunityDef } from '@/lib/hvac/opportunityTypes';

export const OPERATIONS_AGENT = {
  id: 'operations' as const,
  title: 'Operations & Maintenance',
  href: '/agents/operations-maintenance',
  opportunityIds: ['O17', 'O18', 'O19', 'O20'] as const,
};

export const OPERATIONS_OPPORTUNITIES: OpportunityDef[] = [
  opp('O17', 'operations', 'Energy Management Planning', 'Energy Management Planning', '/agents/operations-maintenance/energy-management-planning', 'Identify energy-management opportunities, inefficient operating periods, energy targets, baseline deviations, and optimization opportunities.'),
  opp('O18', 'operations', 'Energy Management Training & Awareness', 'Energy Management Training & Awareness', '/agents/operations-maintenance/training-awareness', 'Identify operator/occupant training opportunities related to HVAC energy efficiency and operational behavior.'),
  opp('O19', 'operations', 'Energy Efficiency Maintenance', 'Energy Efficiency Maintenance', '/agents/operations-maintenance/equipment-maintenance', 'Efficiency-focused maintenance practices that avoid unnecessary HVAC energy use.'),
  opp('O20', 'operations', 'Management of System Control Software', 'Management of System Control Software', '/agents/operations-maintenance/control-software', 'Monitor HVAC control-system health and identify software/configuration issues affecting energy efficiency and safe operation.'),
];
