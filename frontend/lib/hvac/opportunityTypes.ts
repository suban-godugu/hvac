export type HvacSectionId =
  | 'scheduling'
  | 'plant-control'
  | 'ventilation'
  | 'variable-speed'
  | 'operations';

export interface OpportunityDef {
  id: string;
  section: HvacSectionId;
  sectionTitle: string;
  sectionHref: string;
  title: string;
  shortLabel: string;
  route: string;
  description: string;
}

export const HVAC_SECTIONS: {
  id: HvacSectionId;
  title: string;
  href: string;
}[] = [
  { id: 'scheduling', title: 'Scheduling & Supervisory Agent', href: '/agents/scheduling' },
  { id: 'plant-control', title: 'Plant Control Parameter Optimizations', href: '/agents/plant-control' },
  { id: 'ventilation', title: 'Ventilation & Air Flow Optimizations', href: '/agents/ventilation-airflow' },
  { id: 'variable-speed', title: 'Variable Speed Systems', href: '/agents/variable-speed' },
  { id: 'operations', title: 'Operations & Maintenance', href: '/agents/operations-maintenance' },
];

const sectionMeta = (id: HvacSectionId) => HVAC_SECTIONS.find((s) => s.id === id)!;

export function opp(
  id: string,
  section: HvacSectionId,
  title: string,
  shortLabel: string,
  route: string,
  description: string
): OpportunityDef {
  const s = sectionMeta(section);
  return {
    id,
    section,
    sectionTitle: s.title,
    sectionHref: s.href,
    title,
    shortLabel,
    route,
    description,
  };
}
