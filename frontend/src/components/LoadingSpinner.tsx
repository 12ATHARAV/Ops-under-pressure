import React from 'react';

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  label?: string;
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  size = 'md',
  className = '',
  label,
}) => {
  const sizeClasses = {
    sm: 'w-4 h-4 border-2',
    md: 'w-6 h-6 border-2',
    lg: 'w-10 h-10 border-3',
  };

  return (
    <div className={`flex items-center justify-center gap-2 ${className}`}>
      <div
        className={`${sizeClasses[size]} border-indigo-600 border-t-transparent rounded-full animate-spin`}
        role="status"
        aria-label={label || 'Loading'}
      />
      {label && <span className="text-sm text-gray-500 font-medium">{label}</span>}
    </div>
  );
};

export default LoadingSpinner;
