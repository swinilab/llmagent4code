// App Context for State Management

import React, { createContext, useContext, useState, ReactNode } from 'react';
import { Customer, Order, Product } from '../types';

interface AppState {
  customers: Customer[];
  orders: Order[];
  products: Product[];
  currentCustomer: Customer | null;
  currentOrder: Order | null;
  sessionId: string;
}

interface AppContextType extends AppState {
  setCustomers: (customers: Customer[]) => void;
  setOrders: (orders: Order[]) => void;
  setProducts: (products: Product[]) => void;
  setCurrentCustomer: (customer: Customer | null) => void;
  setCurrentOrder: (order: Order | null) => void;
  refreshSession: () => void;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export function AppProvider({ children }: { children: ReactNode }) {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [orders, setOrders] = useState<Order[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [currentCustomer, setCurrentCustomer] = useState<Customer | null>(null);
  const [currentOrder, setCurrentOrder] = useState<Order | null>(null);
  const [sessionId, setSessionId] = useState<string>(() => {
    return 'session-' + Math.random().toString(36).substring(2, 15);
  });

  const refreshSession = () => {
    setSessionId('session-' + Math.random().toString(36).substring(2, 15));
  };

  const value: AppContextType = {
    customers,
    orders,
    products,
    currentCustomer,
    currentOrder,
    sessionId,
    setCustomers,
    setOrders,
    setProducts,
    setCurrentCustomer,
    setCurrentOrder,
    refreshSession
  };

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp() {
  const context = useContext(AppContext);
  if (context === undefined) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
}
