export interface RuntimeErrorEvent {
  routeName: string;
  selectorKey: string;
  message: string;
  stack?: string;
}

export function reportFrontendRuntimeError(event: RuntimeErrorEvent): void {
  const payload = {
    type: 'frontend_runtime_error',
    timestamp: new Date().toISOString(),
    ...event,
  };

  console.error('[frontend-telemetry]', payload);
}
