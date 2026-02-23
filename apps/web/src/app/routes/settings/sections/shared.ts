export const SECRET_MASK = '••••••••';

export function parseValidationRule(rule: string): { minLength?: number; regex?: RegExp } {
  if (rule.startsWith('min_length:')) {
    const min = Number(rule.split(':')[1]);
    return Number.isFinite(min) ? { minLength: min } : {};
  }
  if (rule.startsWith('regex:')) {
    const pattern = rule.slice('regex:'.length);
    try {
      return { regex: new RegExp(pattern) };
    } catch {
      return {};
    }
  }
  return {};
}

export function getErrorMessage(error: unknown): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return 'Request failed. Please try again.';
}
