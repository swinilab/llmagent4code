import React, { useState, useEffect } from "react";
import {
  paymentApi,
  invoiceApi,
  orderApi,
  handleApiError,
} from "../../lib/api";
import type { PaymentFormData, Invoice, Order } from "../../types";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../../components/ui/select";
import { AlertCircle, Save, X, CreditCard } from "lucide-react";

interface PaymentFormProps {
  onSuccess?: () => void;
  onCancel?: () => void;
  userRole?: string;
  userId?: number;
  initialData?: Partial<PaymentFormData>;
}

const PaymentForm: React.FC<PaymentFormProps> = ({
  onSuccess,
  onCancel,
  userRole,
  userId,
  initialData,
}) => {
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [orders, setOrders] = useState<Record<number, Order>>({});
  const [selectedInvoiceId, setSelectedInvoiceId] = useState<
    number | undefined
  >(initialData?.invoiceId);
  const [paymentMethod, setPaymentMethod] = useState<"bank" | "card" | "cash">(
    initialData?.method || "card"
  );
  const [amount, setAmount] = useState<number>(initialData?.amount || 0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchInvoices = async () => {
      try {
        const response = await invoiceApi.getAll();

        // Both customers and accountants can pay any issued invoice
        const availableInvoices = response.data.filter(
          (invoice) => invoice.status === "issued" // Only issued invoices can be paid
        );

        // Fetch all orders for display purposes
        const orderIds = [
          ...new Set(availableInvoices.map((invoice) => invoice.orderId)),
        ];
        const orderPromises = orderIds.map((id) => orderApi.getById(id));
        const orderResponses = await Promise.allSettled(orderPromises);

        const ordersMap: Record<number, Order> = {};
        orderResponses.forEach((result, index) => {
          if (result.status === "fulfilled" && result.value.data) {
            ordersMap[orderIds[index]] = result.value.data;
          }
        });
        setOrders(ordersMap);

        setInvoices(availableInvoices);
      } catch (err) {
        setError(handleApiError(err));
      }
    };

    fetchInvoices();
  }, [userRole, userId]);

  useEffect(() => {
    // Auto-fill amount and method when invoice is selected
    if (selectedInvoiceId) {
      const selectedInvoice = invoices.find(
        (invoice) => invoice.id === selectedInvoiceId
      );
      if (selectedInvoice) {
        setAmount(Number(selectedInvoice.amount));
        setPaymentMethod(selectedInvoice.method);
      }
    }
  }, [selectedInvoiceId, invoices]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!selectedInvoiceId) {
      setError("Please select an invoice to pay");
      return;
    }

    if (amount <= 0) {
      setError("Please enter a valid payment amount");
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const paymentData: PaymentFormData = {
        invoiceId: selectedInvoiceId,
        amount,
        method: paymentMethod,
      };

      await paymentApi.create(paymentData);

      // Reset form
      setSelectedInvoiceId(undefined);
      setAmount(0);
      setPaymentMethod("card");

      onSuccess?.();
    } catch (err) {
      setError(handleApiError(err));
    } finally {
      setLoading(false);
    }
  };

  const selectedInvoice = invoices.find(
    (invoice) => invoice.id === selectedInvoiceId
  );
  const selectedOrder = selectedInvoice
    ? orders[selectedInvoice.orderId]
    : null;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center space-x-2">
          <CreditCard className="h-5 w-5" />
          <span>Make Payment</span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="flex items-center space-x-2 p-3 bg-red-50 border border-red-200 rounded-md text-red-600">
              <AlertCircle className="h-4 w-4" />
              <span className="text-sm">{error}</span>
            </div>
          )}

          <div className="space-y-2">
            <Label htmlFor="invoice">
              Select Invoice to Pay * ({invoices.length} available)
            </Label>
            <select
              value={selectedInvoiceId || ""}
              onChange={(e) => {
                setSelectedInvoiceId(Number(e.target.value) || undefined);
              }}
              style={{
                width: "100%",
                padding: "8px",
                border: "1px solid #ccc",
                borderRadius: "4px",
              }}
            >
              <option value="">-- Select Invoice --</option>
              {invoices.map((invoice) => {
                const order = orders[invoice.orderId];
                return (
                  <option key={invoice.id} value={invoice.id}>
                    Invoice #{invoice.id} -{" "}
                    {order?.customerName || "Loading..."} - $
                    {Number(invoice.amount).toFixed(2)}
                  </option>
                );
              })}
            </select>
          </div>

          {selectedInvoice && selectedOrder && (
            <Card className="bg-gray-50">
              <CardContent className="p-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                  <div>
                    <div className="font-medium text-gray-700">
                      Invoice Details
                    </div>
                    <div>Invoice #{selectedInvoice.id}</div>
                    <div>
                      Date:{" "}
                      {new Date(selectedInvoice.date).toLocaleDateString()}
                    </div>
                    <div>
                      Status:{" "}
                      <span className="capitalize">
                        {selectedInvoice.status}
                      </span>
                    </div>
                  </div>
                  <div>
                    <div className="font-medium text-gray-700">
                      Order Details
                    </div>
                    <div>Order #{selectedOrder.id}</div>
                    <div>Customer: {selectedOrder.customerName}</div>
                    <div>Items: {selectedOrder.items?.length || 0}</div>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="amount">Payment Amount ($) *</Label>
              <Input
                id="amount"
                type="number"
                step="0.01"
                min="0"
                value={amount}
                onChange={(e) => setAmount(parseFloat(e.target.value) || 0)}
                placeholder="0.00"
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="method">Payment Method *</Label>
              <select
                value={paymentMethod}
                onChange={(e) =>
                  setPaymentMethod(e.target.value as "bank" | "card" | "cash")
                }
                style={{
                  width: "100%",
                  padding: "8px",
                  border: "1px solid #ccc",
                  borderRadius: "4px",
                }}
              >
                <option value="card">Credit Card</option>
                <option value="bank">Bank Transfer</option>
                <option value="cash">Cash</option>
              </select>
            </div>
          </div>

          {invoices.length === 0 && (
            <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-md">
              <div className="text-sm text-yellow-800">
                <strong>No issued invoices available for payment.</strong>
                <br />
                <br />
                Workflow: 1) Place order → 2) Staff accepts order → 3)
                Accountant sends invoice → 4) Anyone can pay here
              </div>
            </div>
          )}

          <div className="flex justify-end space-x-2 pt-4">
            {onCancel && (
              <Button
                type="button"
                variant="outline"
                onClick={onCancel}
                disabled={loading}
              >
                <X className="h-4 w-4 mr-2" />
                Cancel
              </Button>
            )}
            <Button type="submit" disabled={loading || invoices.length === 0}>
              <Save className="h-4 w-4 mr-2" />
              {loading ? "Processing..." : "Make Payment"}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
};

export default PaymentForm;
