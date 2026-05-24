import React, { useState } from "react";
import { useAuth } from "../../contexts/AuthContext";
import PaymentBrowser from "./PaymentBrowser";
import PaymentForm from "./PaymentForm";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Plus, CreditCard } from "lucide-react";

const PaymentIndex: React.FC = () => {
  const { user } = useAuth();
  const [showForm, setShowForm] = useState(false);
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const handlePaymentCreated = () => {
    setShowForm(false);
    setRefreshTrigger((prev) => prev + 1);
  };

  // Customers and accountants can create payments
  const canCreatePayments =
    user?.role === "customer" || user?.role === "accountant";
  // Only accountants can manage all payments
  const canManagePayments = user?.role === "accountant";

  return (
    <div className="container mx-auto p-6 space-y-6">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <div className="flex items-center space-x-2">
            <CreditCard className="h-6 w-6" />
            <CardTitle className="text-2xl font-bold">
              Payment Management
            </CardTitle>
          </div>
          {canCreatePayments && (
            <Button
              onClick={() => setShowForm(!showForm)}
              className="flex items-center space-x-2"
            >
              <Plus className="h-4 w-4" />
              <span>Make Payment</span>
            </Button>
          )}
        </CardHeader>
        <CardContent>
          {showForm && canCreatePayments && (
            <div className="mb-6">
              <PaymentForm
                onSuccess={handlePaymentCreated}
                onCancel={() => setShowForm(false)}
                userRole={user?.role}
                userId={user?.id}
              />
            </div>
          )}
          <PaymentBrowser
            refreshTrigger={refreshTrigger}
            canEdit={canManagePayments}
            userRole={user?.role}
            userId={user?.id}
          />
        </CardContent>
      </Card>
    </div>
  );
};

export default PaymentIndex;
