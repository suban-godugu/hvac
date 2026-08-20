import { ApiError } from '@/lib/api/client';

/** Surface backend dispatch/verify/rollback blocker codes in the studio. */
export function actionErrorText(err: unknown, fallback = 'Request failed'): string {
  if (err instanceof ApiError) {
    const code = err.code ? `${err.code}: ` : '';
    return `Dispatch blocked: ${code}${err.message}`;
  }
  if (err instanceof Error && err.message) return err.message;
  return fallback;
}
