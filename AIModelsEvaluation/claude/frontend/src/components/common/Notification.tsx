import React, { useEffect, useState } from 'react';
import { NotificationProps } from '../../types';

interface NotificationManagerProps {
  notifications: (NotificationProps & { id: string })[];
  onRemove: (id: string) => void;
}

const NotificationManager: React.FC<NotificationManagerProps> = ({
  notifications,
  onRemove,
}) => {
  return (
    <div className="fixed top-4 right-4 z-50 space-y-4">
      {notifications.map((notification) => (
        <Notification
          key={notification.id}
          {...notification}
          onClose={() => onRemove(notification.id)}
        />
      ))}
    </div>
  );
};

interface SingleNotificationProps extends NotificationProps {
  onClose: () => void;
}

const Notification: React.FC<SingleNotificationProps> = ({
  type,
  message,
  description,
  duration = 5000,
  onClose,
}) => {
  const [isVisible, setIsVisible] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => {
      setIsVisible(false);
      setTimeout(onClose, 300); // Allow fade out animation
    }, duration);

    return () => clearTimeout(timer);
  }, [duration, onClose]);

  const typeStyles = {
    success: {
      bg: 'bg-success-50',
      border: 'border-success-200',
      icon: '✓',
      iconColor: 'text-success-400',
      textColor: 'text-success-800',
    },
    error: {
      bg: 'bg-error-50',
      border: 'border-error-200',
      icon: '✕',
      iconColor: 'text-error-400',
      textColor: 'text-error-800',
    },
    warning: {
      bg: 'bg-warning-50',
      border: 'border-warning-200',
      icon: '⚠',
      iconColor: 'text-warning-400',
      textColor: 'text-warning-800',
    },
    info: {
      bg: 'bg-primary-50',
      border: 'border-primary-200',
      icon: 'ⓘ',
      iconColor: 'text-primary-400',
      textColor: 'text-primary-800',
    },
  };

  const styles = typeStyles[type];

  return (
    <div
      className={`max-w-sm w-full ${styles.bg} ${styles.border} border rounded-lg shadow-lg transform transition-all duration-300 ${
        isVisible ? 'translate-x-0 opacity-100' : 'translate-x-full opacity-0'
      }`}
    >
      <div className="p-4">
        <div className="flex">
          <div className="flex-shrink-0">
            <span className={`inline-flex items-center justify-center h-5 w-5 ${styles.iconColor}`}>
              {styles.icon}
            </span>
          </div>
          <div className="ml-3 w-0 flex-1">
            <p className={`text-sm font-medium ${styles.textColor}`}>
              {message}
            </p>
            {description && (
              <p className={`mt-1 text-sm ${styles.textColor} opacity-90`}>
                {description}
              </p>
            )}
          </div>
          <div className="ml-4 flex-shrink-0 flex">
            <button
              onClick={() => {
                setIsVisible(false);
                setTimeout(onClose, 300);
              }}
              className={`inline-flex ${styles.textColor} hover:opacity-75 focus:outline-none`}
            >
              <span className="sr-only">Close</span>
              <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
                <path
                  fillRule="evenodd"
                  d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                  clipRule="evenodd"
                />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default NotificationManager;