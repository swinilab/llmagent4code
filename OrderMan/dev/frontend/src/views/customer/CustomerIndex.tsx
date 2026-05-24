import React, { useState } from "react";
import { useAuth } from "../../contexts/AuthContext";
import CustomerBrowser from "./CustomerBrowser";
import CustomerForm from "./CustomerForm";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Plus, Users } from "lucide-react";

const CustomerIndex: React.FC = () => {
  const { user } = useAuth();
  const [showForm, setShowForm] = useState(false);
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const handleCustomerCreated = () => {
    setShowForm(false);
    setRefreshTrigger((prev) => prev + 1);
  };

  // Only staff and accountants can manage customers
  const canManageCustomers =
    user?.role === "staff" || user?.role === "accountant";

  return (
    <div className="container mx-auto p-6 space-y-6">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <div className="flex items-center space-x-2">
            <Users className="h-6 w-6" />
            <CardTitle className="text-2xl font-bold">
              Customer Management
            </CardTitle>
          </div>
          {canManageCustomers && (
            <Button
              onClick={() => setShowForm(!showForm)}
              className="flex items-center space-x-2"
            >
              <Plus className="h-4 w-4" />
              <span>Add Customer</span>
            </Button>
          )}
        </CardHeader>
        <CardContent>
          {showForm && canManageCustomers && (
            <div className="mb-6">
              <CustomerForm
                onSuccess={handleCustomerCreated}
                onCancel={() => setShowForm(false)}
              />
            </div>
          )}
          <CustomerBrowser
            refreshTrigger={refreshTrigger}
            canEdit={canManageCustomers}
          />
        </CardContent>
      </Card>
    </div>
  );
};

export default CustomerIndex;

