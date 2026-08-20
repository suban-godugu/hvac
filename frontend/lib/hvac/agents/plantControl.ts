import { opp, type OpportunityDef } from '@/lib/hvac/opportunityTypes';

export const PLANT_CONTROL_AGENT = {
  id: 'plant-control' as const,
  title: 'Plant Control Parameter Optimizations',
  href: '/agents/plant-control',
  opportunityIds: ['O5', 'O6', 'O7', 'O8', 'O9'] as const,
};

export const PLANT_CONTROL_OPPORTUNITIES: OpportunityDef[] = [
  opp('O5', 'plant-control', 'Duct Static Pressure Reset', 'Duct Static Pressure Reset', '/agents/plant-control/duct-static-pressure', 'Trim-and-respond duct static pressure for fan kW reduction.'),
  opp('O6-O8', 'plant-control', 'Temperature Reset', 'Temperature Reset', '/agents/plant-control/temperature-reset', 'HHW, CHW, and CW loop temperature reset.'),
  opp('O9', 'plant-control', 'Retrofit of Electronic Expansion Valve', 'Retrofit of Electronic Expansion Valve', '/agents/plant-control/electronic-expansion-valve', 'TXV to EXV retrofit engineering assessment.'),
];
