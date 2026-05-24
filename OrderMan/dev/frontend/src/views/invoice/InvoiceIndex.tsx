import React, { useState } from "react";
import { useAuth } from "../../contexts/AuthContext";
import InvoiceBrowser from "./InvoiceBrowser";
import InvoiceForm from "./InvoiceForm";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Plus, FileText } from "lucide-react";

const InvoiceIndex: React.FC = () => {
  const { user } = useAuth();
  const [showForm, setShowForm] = useState(false);
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const handleInvoiceCreated = () => {
    setShowForm(false);
    setRefreshTrigger((prev) => prev + 1);
  };

  // Only accountants can manage invoices directly
  const canManageInvoices = user?.role === "accountant";

  return (
    <div className="container mx-auto p-6 space-y-6">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <div className="flex items-center space-x-2">
            <FileText className="h-6 w-6" />
            <CardTitle className="text-2xl font-bold">
              Invoice Management
            </CardTitle>
          </div>
          {canManageInvoices && (
            <Button
              onClick={() => setShowForm(!showForm)}
              className="flex items-center space-x-2"
            >
              <Plus className="h-4 w-4" />
              <span>Create Invoice</span>
            </Button>
          )}
        </CardHeader>
        <CardContent>
          {showForm && canManageInvoices && (
            <div className="mb-6">
              <InvoiceForm
                onSuccess={handleInvoiceCreated}
                onCancel={() => setShowForm(false)}
              />
            </div>
          )}
          <InvoiceBrowser
            refreshTrigger={refreshTrigger}
            canEdit={canManageInvoices}
            userRole={user?.role}
          />
        </CardContent>
      </Card>
    </div>
  );
};

export default InvoiceIndex;

