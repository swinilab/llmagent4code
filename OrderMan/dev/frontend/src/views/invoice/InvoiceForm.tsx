import React, { useState, useEffect } from "react";
import { invoiceApi, orderApi, handleApiError } from "../../lib/api";
import type { InvoiceFormData, Order } from "../../types";
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
import { AlertCircle, Save, X, FileText } from "lucide-react";

interface InvoiceFormProps {
  onSuccess?: () => void;
  onCancel?: () => void;
  initialData?: Partial<InvoiceFormData>;
}

const InvoiceForm: React.FC<InvoiceFormProps> = ({
  onSuccess,
  onCancel,
  initialData,
}) => {
  const [orders, setOrders] = useState<Order[]>([]);
  const [selectedOrderId, setSelectedOrderId] = useState<number | undefined>(
    initialData?.orderId
  );
  const [paymentMethod, setPaymentMethod] = useState<"bank" | "card" | "cash">(
    initialData?.method || "card"
  );
  const [amount, setAmount] = useState<number>(initialData?.amount || 0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchOrders = async () => {
      try {
        const response = await orderApi.getAll();
        // Only show orders that are accepted (ready for invoicing)
        const acceptedOrders = response.data.filter(
          (order) => order.status === "accepted" || order.status === "paid"
        );
        setOrders(acceptedOrders);
      } catch (err) {
        setError(handleApiError(err));
      }
    };

    fetchOrders();
  }, []);

  useEffect(() => {
    // Auto-fill amount when order is selected
    if (selectedOrderId) {
      const selectedOrder = orders.find(
        (order) => order.id === selectedOrderId
      );
      if (selectedOrder) {
        setAmount(Number(selectedOrder.totalAmount));
        setPaymentMethod(selectedOrder.method);
      }
    }
  }, [selectedOrderId, orders]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!selectedOrderId) {
      setError("Please select an order");
      return;
    }

    if (amount <= 0) {
      setError("Please enter a valid amount");
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const invoiceData: InvoiceFormData = {
        orderId: selectedOrderId,
        amount,
        method: paymentMethod,
      };

      await invoiceApi.create(invoiceData);

      // Reset form
      setSelectedOrderId(undefined);
      setAmount(0);
      setPaymentMethod("card");

      onSuccess?.();
    } catch (err) {
      setError(handleApiError(err));
    } finally {
      setLoading(false);
    }
  };

  const selectedOrder = orders.find((order) => order.id === selectedOrderId);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center space-x-2">
          <FileText className="h-5 w-5" />
          <span>Create New Invoice</span>
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
            <Label htmlFor="order">Select Order *</Label>
            <Select
              value={selectedOrderId?.toString() || ""}
              onValueChange={(value) => setSelectedOrderId(parseInt(value))}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select an order to invoice" />
              </SelectTrigger>
              <SelectContent>
                {orders.map((order) => (
                  <SelectItem key={order.id} value={order.id.toString()}>
                    Order #{order.id} - {order.customerName} - $
                    {Number(order.totalAmount).toFixed(2)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {selectedOrder && (
            <Card className="bg-gray-50">
              <CardContent className="p-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                  <div>
                    <div className="font-medium text-gray-700">Customer</div>
                    <div>{selectedOrder.customerName}</div>
                    <div className="text-gray-600">
                      {selectedOrder.customerPhone}
                    </div>
                  </div>
                  <div>
                    <div className="font-medium text-gray-700">
                      Order Details
                    </div>
                    <div>
                      Status:{" "}
                      <span className="capitalize">{selectedOrder.status}</span>
                    </div>
                    <div>Items: {selectedOrder.items?.length || 0}</div>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="amount">Invoice Amount ($) *</Label>
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
              <Select
                value={paymentMethod}
                onValueChange={(value: any) => setPaymentMethod(value)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="card">Credit Card</SelectItem>
                  <SelectItem value="bank">Bank Transfer</SelectItem>
                  <SelectItem value="cash">Cash</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {orders.length === 0 && (
            <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-md">
              <div className="text-sm text-yellow-800">
                No orders available for invoicing. Orders must be in "accepted"
                status to create invoices.
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
            <Button type="submit" disabled={loading || orders.length === 0}>
              <Save className="h-4 w-4 mr-2" />
              {loading ? "Creating..." : "Create Invoice"}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
};

export default InvoiceForm;


