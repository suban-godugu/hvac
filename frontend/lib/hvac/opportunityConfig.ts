import type { HvacSectionId, OpportunityDef } from '@/lib/hvac/opportunityTypes';
import { HVAC_SECTIONS } from '@/lib/hvac/opportunityTypes';
import { OPERATIONS_OPPORTUNITIES } from '@/lib/hvac/agents/operations';
import { PLANT_CONTROL_OPPORTUNITIES } from '@/lib/hvac/agents/plantControl';
import { SCHEDULING_OPPORTUNITIES } from '@/lib/hvac/agents/scheduling';
import { VARIABLE_SPEED_OPPORTUNITIES } from '@/lib/hvac/agents/variableSpeed';
import { VENTILATION_OPPORTUNITIES } from '@/lib/hvac/agents/ventilation';

export type { HvacSectionId, OpportunityDef };
export { HVAC_SECTIONS };

export const OPPORTUNITIES: OpportunityDef[] = [
  ...SCHEDULING_OPPORTUNITIES,
  ...PLANT_CONTROL_OPPORTUNITIES,
  ...VENTILATION_OPPORTUNITIES,
  ...VARIABLE_SPEED_OPPORTUNITIES,
  ...OPERATIONS_OPPORTUNITIES,
];

export function opportunitiesForSection(section: HvacSectionId): OpportunityDef[] {
  return OPPORTUNITIES.filter((o) => o.section === section);
}

export function getOpportunity(id: string): OpportunityDef | undefined {
  return OPPORTUNITIES.find((o) => o.id === id);
}

const groupedReset = () => getOpportunity('O6-O8')!;

export const TEMP_RESET_OPPS: OpportunityDef[] = [
  {
    ...groupedReset(),
    id: 'O6',
    title: 'Heating Hot Water Reset',
    shortLabel: 'Heating Hot Water',
    route: '/agents/plant-control/temperature-reset?mode=HHW',
    description: 'Lowest HHW flow temperature that still meets heating demand; boost only at peak.',
  },
  {
    ...groupedReset(),
    id: 'O7',
    title: 'Chilled Water Reset',
    shortLabel: 'Chilled Water',
    route: '/agents/plant-control/temperature-reset?mode=CHW',
    description: 'Raise CHW supply temperature in mild weather without losing dehumidification when it matters.',
  },
  {
    ...groupedReset(),
    id: 'O8',
    title: 'Condenser Water Reset',
    shortLabel: 'Condenser Water',
    route: '/agents/plant-control/temperature-reset?mode=CW',
    description: 'Track wet-bulb with tower approach so CW is not held at a constant high temperature.',
  },
];

/** Catalog rows for dashboards: O6/O7/O8 as separate cards instead of grouped O6–O8. */
export function fleetOpportunityCards(): OpportunityDef[] {
  const out: OpportunityDef[] = [];
  for (const o of OPPORTUNITIES) {
    if (o.id === 'O6-O8') out.push(...TEMP_RESET_OPPS);
    else out.push(o);
  }
  return out;
}
