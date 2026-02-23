import { Component, type ErrorInfo, type ReactNode } from 'react';
import { useLocation } from 'react-router-dom';

import { reportFrontendRuntimeError } from '@/app/lib/telemetry';
import { Button } from '@/app/components/ui/button';

interface BoundaryProps {
  children: ReactNode;
  routeName: string;
  selectorKey: string;
  title: string;
  description: string;
}

interface BoundaryState {
  hasError: boolean;
}

class LocalErrorBoundaryInner extends Component<BoundaryProps, BoundaryState> {
  state: BoundaryState = { hasError: false };

  static getDerivedStateFromError(): BoundaryState {
    return { hasError: true };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    reportFrontendRuntimeError({
      routeName: this.props.routeName,
      selectorKey: this.props.selectorKey,
      message: error.message,
      stack: errorInfo.componentStack ?? error.stack,
    });
  }

  handleRetry = () => {
    this.setState({ hasError: false });
  };

  render() {
    if (!this.state.hasError) {
      return this.props.children;
    }

    return (
      <div className="rounded-lg border border-destructive/50 bg-destructive/5 p-4 space-y-2">
        <p className="text-sm font-medium text-destructive">{this.props.title}</p>
        <p className="text-xs text-muted-foreground">{this.props.description}</p>
        <Button size="sm" variant="outline" onClick={this.handleRetry}>Try again</Button>
      </div>
    );
  }
}

export function LocalErrorBoundary(props: Omit<BoundaryProps, 'routeName'>) {
  const location = useLocation();

  return <LocalErrorBoundaryInner {...props} routeName={location.pathname} />;
}
