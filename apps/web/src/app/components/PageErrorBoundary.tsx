import { Component, type ErrorInfo, type ReactNode } from 'react';

type PageErrorBoundaryProps = {
  pageName: string;
  children: ReactNode;
};

type PageErrorBoundaryState = {
  hasError: boolean;
};

class PageErrorBoundary extends Component<PageErrorBoundaryProps, PageErrorBoundaryState> {
  state: PageErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(): PageErrorBoundaryState {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error(`[${this.props.pageName}] runtime render error`, error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="rounded-2xl border border-destructive/40 bg-destructive/5 p-4 text-sm text-destructive">
          Something went wrong while loading this page. Please refresh or try again.
        </div>
      );
    }

    return this.props.children;
  }
}

export default PageErrorBoundary;
