import React, { Suspense } from 'react';
import PropTypes from 'prop-types';
import Skeleton from '../components/Skeleton';
import { ErrorBoundary } from 'react-error-boundary';

/**
 * @function withModelLoader
 * @description A Higher-Order Component (HOC) that wraps a given React component in a Suspense fallback UI.
 * It is designed to dynamically load lazily imported components and show a skeleton while loading,
 * and also provides an ErrorBoundary for robust error handling.
 * @param {React.LazyExoticComponent<React.ComponentType<any>>} Component - The lazily loaded component to wrap.
 * @param {object} [config={}] - Configuration object for the component.
 * @param {string} [config.modelName='Unknown'] - A name used for the fallback skeleton and error message.
 * @returns {React.FC} A new React component that renders the wrapped component inside Suspense and ErrorBoundary.
 */
export function withModelLoader(Component, config = {}) {
  const { modelName = 'Unknown' } = config;

  /**
   * @function WrappedComponent
   * @description The component returned by the `withModelLoader` HOC.
   * It renders the provided `Component` within a `Suspense` boundary with a `Skeleton` fallback
   * and an `ErrorBoundary` for error handling.
   * @param {object} props - The props passed to the wrapped component.
   * @returns {React.ReactElement} The rendered component with loading and error fallbacks.
   */
  return function WrappedComponent(props) {
    if (!Component) {
      return <div>{modelName} Component not found</div>;
    }

    return (
      // <ErrorBoundary>
        <Suspense fallback={<Skeleton name={modelName} />}>
          <Component {...config} {...props} />
        </Suspense>
      // </ErrorBoundary>
    );
  };
}

withModelLoader.propTypes = {
  Component: PropTypes.elementType.isRequired,
  config: PropTypes.shape({
    modelName: PropTypes.string,
  }),
};