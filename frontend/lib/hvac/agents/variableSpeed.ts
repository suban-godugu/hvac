import { opp, type OpportunityDef } from '@/lib/hvac/opportunityTypes';

export const VARIABLE_SPEED_AGENT = {
  id: 'variable-speed' as const,
  title: 'Variable Speed Systems',
  href: '/agents/variable-speed',
  opportunityIds: ['O14', 'O15', 'O16'] as const,
};

export const VARIABLE_SPEED_OPPORTUNITIES: OpportunityDef[] = [
  opp('O14', 'variable-speed', 'Optimised Secondary Chilled Water Pumping', 'Optimised Secondary CHW Pumping', '/agents/variable-speed/chilled-water-pump', 'Secondary CHW pump speed vs differential pressure.'),
  opp('O15', 'variable-speed', 'Variable Head Pressure Control — Air-Cooled Condensers', 'Variable Head Pressure — Air-Cooled', '/agents/variable-speed/air-cooled-head-pressure', 'Air-cooled condenser head-pressure control.'),
  opp('O16', 'variable-speed', 'Variable Head Pressure Control — Water-Cooled Condensers', 'Variable Head Pressure — Water-Cooled', '/agents/variable-speed/water-cooled-head-pressure', 'Optimize condenser-water head pressure and pumping energy during part-load operation while maintaining safe refrigeration-system operation.'),
];
