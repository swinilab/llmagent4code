import React, { useState } from "react";
import { useAuth } from "../../contexts/AuthContext";
import OrderBrowser from "./OrderBrowser";
import OrderBrowserCustomer from "./OrderBrowserCustomer";
import OrderBrowserAccountant from "./OrderBrowserAccountant";
import OrderBrowserStaff from "./OrderBrowserStaff";
import OrderForm from "./OrderForm";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Plus, ShoppingCart } from "lucide-react";

const OrderIndex: React.FC = () => {
  const { user } = useAuth();
  const [showForm, setShowForm] = useState(false);
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const handleOrderCreated = () => {
    setShowForm(false);
    setRefreshTrigger((prev) => prev + 1);
  };

  // All authenticated users can create orders
  const canCreateOrders = !!user;

  const renderOrderBrowser = () => {
    switch (user?.role) {
      case "customer":
        return (
          <OrderBrowserCustomer
            refreshTrigger={refreshTrigger}
            customerId={user.id}
          />
        );
      case "accountant":
        return <OrderBrowserAccountant refreshTrigger={refreshTrigger} />;
      case "staff":
        return <OrderBrowserStaff refreshTrigger={refreshTrigger} />;
      default:
        return <OrderBrowser refreshTrigger={refreshTrigger} />;
    }
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <div className="flex items-center space-x-2">
            <ShoppingCart className="h-6 w-6" />
            <CardTitle className="text-2xl font-bold">
              Order Management
            </CardTitle>
          </div>
          {canCreateOrders && (
            <Button
              onClick={() => setShowForm(!showForm)}
              className="flex items-center space-x-2"
            >
              <Plus className="h-4 w-4" />
              <span>Create Order</span>
            </Button>
          )}
        </CardHeader>
        <CardContent>
          {showForm && canCreateOrders && (
            <div className="mb-6">
              <OrderForm
                onSuccess={handleOrderCreated}
                onCancel={() => setShowForm(false)}
                defaultCustomerId={
                  user?.role === "customer" ? user.id : undefined
                }
              />
            </div>
          )}
          {renderOrderBrowser()}
        </CardContent>
      </Card>
    </div>
  );
};

export default OrderIndex;

