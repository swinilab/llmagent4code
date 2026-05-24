// Re-export all shared domain types
export * from '../../../shared/domain/Customer';
export * from '../../../shared/domain/Product';
export * from '../../../shared/domain/Order';
export * from '../../../shared/domain/Invoice';
export * from '../../../shared/domain/Payment';

// Frontend-specific types
export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  message: string;
  error?: string;
}

export interface PaginationParams {
  page?: number;
  limit?: number;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
}

export interface FilterParams {
  status?: string;
  customerId?: string;
  dateFrom?: string;
  dateTo?: string;
  search?: string;
}

export type LoadingState = 'idle' | 'loading' | 'succeeded' | 'failed';

export interface FormErrors {
  [key: string]: string | string[] | FormErrors;
}

export interface TableColumn<T> {
  key: keyof T;
  title: string;
  sortable?: boolean;
  render?: (value: any, record: T) => React.ReactNode;
  width?: string;
}

export interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  size?: 'sm' | 'md' | 'lg' | 'xl';
}

export interface NotificationProps {
  type: 'success' | 'error' | 'warning' | 'info';
  message: string;
  description?: string;
  duration?: number;
}