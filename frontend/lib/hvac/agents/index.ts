export { SCHEDULING_AGENT, SCHEDULING_OPPORTUNITIES } from './scheduling';
export { PLANT_CONTROL_AGENT, PLANT_CONTROL_OPPORTUNITIES } from './plantControl';
export { VENTILATION_AGENT, VENTILATION_OPPORTUNITIES } from './ventilation';
export { VARIABLE_SPEED_AGENT, VARIABLE_SPEED_OPPORTUNITIES } from './variableSpeed';
export { OPERATIONS_AGENT, OPERATIONS_OPPORTUNITIES } from './operations';

import { SCHEDULING_AGENT } from './scheduling';
import { PLANT_CONTROL_AGENT } from './plantControl';
import { VENTILATION_AGENT } from './ventilation';
import { VARIABLE_SPEED_AGENT } from './variableSpeed';
import { OPERATIONS_AGENT } from './operations';

/** The five HVAC agents in sidebar order. */
export const HVAC_AGENTS = [
  SCHEDULING_AGENT,
  PLANT_CONTROL_AGENT,
  VENTILATION_AGENT,
  VARIABLE_SPEED_AGENT,
  OPERATIONS_AGENT,
] as const;
