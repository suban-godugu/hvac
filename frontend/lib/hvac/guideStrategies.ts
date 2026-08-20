import { GUIDE_STRATEGIES as GUIDE_STRATEGIES_A } from './guideStrategiesA';
import { GUIDE_STRATEGIES_B } from './guideStrategiesB';
import type { GuideStrategy } from './guideTypes';

export const GUIDE_STRATEGIES: GuideStrategy[] = [...GUIDE_STRATEGIES_A, ...GUIDE_STRATEGIES_B];

export function getGuideStrategy(id: number): GuideStrategy | undefined {
  return GUIDE_STRATEGIES.find((s) => s.id === id);
}
