import React, { useState, useEffect } from "react";
import {
  orderApi,
  customerApi,
  productApi,
  handleApiError,
} from "../../lib/api";
import type { Customer, Product } from "../../types";
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
import { AlertCircle, Save, X, Plus, Trash2, ShoppingCart } from "lucide-react";

interface OrderFormProps {
  onSuccess?: () => void;
  onCancel?: () => void;
  defaultCustomerId?: number;
}

interface OrderItem {
  productId?: number;
  name: string;
  quantity: number;
  price: number;
}

const OrderForm: React.FC<OrderFormProps> = ({
  onSuccess,
  onCancel,
  defaultCustomerId,
}) => {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [selectedCustomerId, setSelectedCustomerId] = useState<
    number | undefined
  >(defaultCustomerId);
  const [paymentMethod, setPaymentMethod] = useState<"bank" | "card" | "cash">(
    "card"
  );
  const [items, setItems] = useState<OrderItem[]>([
    { productId: undefined, name: "", quantity: 1, price: 0 },
  ]);
  const [loading, setLoading] = useState(false);
  const [dataLoading, setDataLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setDataLoading(true);
        const [customersResponse, productsResponse] = await Promise.all([
          customerApi.getAll(),
          productApi.getAll(),
        ]);
        // Handle the response - if it's already an array, use it directly
        const customersData = Array.isArray(customersResponse.data)
          ? customersResponse.data
          : customersResponse.data?.data || [];
        const productsData = Array.isArray(productsResponse.data)
          ? productsResponse.data
          : productsResponse.data?.data || [];

        setCustomers(customersData);
        setProducts(productsData);
      } catch (err) {
        console.error("Error fetching data:", err);
        const errorMessage = handleApiError(err);
        setError(`Failed to load data: ${errorMessage}`);

        // If it's a network error, provide helpful message
        if (err.code === "ERR_NETWORK" || err.message?.includes("Network")) {
          setError(
            "Cannot connect to backend server. Please ensure the backend is running on http://localhost:3000"
          );
        }
      } finally {
        setDataLoading(false);
      }
    };

    fetchData();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!selectedCustomerId) {
      setError("Please select a customer");
      return;
    }

    const validItems = items.filter(
      (item) => item.name.trim() && item.quantity > 0 && item.price > 0
    );
    if (validItems.length === 0) {
      setError("Please add at least one valid item");
      return;
    }

    const totalAmount = validItems.reduce(
      (sum, item) => sum + item.price * item.quantity,
      0
    );

    const selectedCustomer = customers.find((c) => c.id === selectedCustomerId);
    if (!selectedCustomer) {
      setError("Selected customer not found");
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const orderData: any = {
        customerId: selectedCustomerId,
        customerName: selectedCustomer.name,
        customerAddress: selectedCustomer.address,
        customerPhone: selectedCustomer.phone,
        customerBankAccount: selectedCustomer.bankAccount,
        totalAmount,
        method: paymentMethod,
        items: validItems.map((item) => ({
          productId: item.productId,
          name: item.name,
          quantity: item.quantity,
          price: item.price,
        })),
      };

      await orderApi.create(orderData);

      // Reset form
      setSelectedCustomerId(defaultCustomerId);
      setPaymentMethod("card");
      setItems([{ productId: undefined, name: "", quantity: 1, price: 0 }]);

      onSuccess?.();
    } catch (err) {
      setError(handleApiError(err));
    } finally {
      setLoading(false);
    }
  };

  const addItem = () => {
    setItems([
      ...items,
      { productId: undefined, name: "", quantity: 1, price: 0 },
    ]);
  };

  const removeItem = (index: number) => {
    if (items.length > 1) {
      setItems(items.filter((_, i) => i !== index));
    }
  };

  const updateItem = (index: number, field: keyof OrderItem, value: any) => {
    const updatedItems = [...items];
    updatedItems[index] = { ...updatedItems[index], [field]: value };

    // If a product is selected, auto-fill name and price
    if (field === "productId" && value) {
      const product = products.find((p) => p.id === value);
      if (product) {
        updatedItems[index].name = product.name;
        updatedItems[index].price = Number(product.price);
      }
    }

    setItems(updatedItems);
  };

  const getTotalAmount = () => {
    return items.reduce((sum, item) => sum + item.price * item.quantity, 0);
  };

  // Get available products for a specific dropdown (excluding already selected products)
  const getAvailableProducts = (currentIndex: number) => {
    const selectedProductIds = items
      .map((item, index) =>
        index !== currentIndex ? item.productId : undefined
      )
      .filter((id) => id !== undefined);

    return products.filter(
      (product) => !selectedProductIds.includes(product.id)
    );
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center space-x-2">
          <ShoppingCart className="h-5 w-5" />
          <span>Create New Order</span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-6">
          {error && (
            <div className="flex items-center space-x-2 p-3 bg-red-50 border border-red-200 rounded-md text-red-600">
              <AlertCircle className="h-4 w-4" />
              <span className="text-sm">{error}</span>
            </div>
          )}

          {/* Customer Selection */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="customer">
                Customer *{" "}
                {dataLoading
                  ? "(Loading...)"
                  : `(${customers.length} available)`}
              </Label>
              <select
                value={selectedCustomerId || ""}
                onChange={(e) => {
                  setSelectedCustomerId(Number(e.target.value) || undefined);
                }}
                style={{
                  width: "100%",
                  padding: "8px",
                  border: "1px solid #ccc",
                  borderRadius: "4px",
                }}
              >
                <option value="">-- Select Customer --</option>
                {customers.map((customer) => (
                  <option key={customer.id} value={customer.id}>
                    {customer.name} ({customer.phone})
                  </option>
                ))}
              </select>
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

          {/* Order Items */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <Label className="text-base font-medium">Order Items *</Label>
              <Button
                type="button"
                variant="outline"
                onClick={addItem}
                size="sm"
              >
                <Plus className="h-4 w-4 mr-1" />
                Add Item
              </Button>
            </div>

            <div className="space-y-3">
              {items.map((item, index) => (
                <Card key={index} className="p-4">
                  <div className="grid grid-cols-1 md:grid-cols-5 gap-3 items-end">
                    <div className="space-y-1">
                      <Label className="text-xs">Product (Optional)</Label>
                      <Select
                        value={item.productId?.toString() || ""}
                        onValueChange={(value) =>
                          updateItem(
                            index,
                            "productId",
                            value ? parseInt(value) : undefined
                          )
                        }
                      >
                        <SelectTrigger className="h-9">
                          <SelectValue placeholder="Select product" />
                        </SelectTrigger>
                        <SelectContent>
                          {getAvailableProducts(index).map((product) => (
                            <SelectItem
                              key={product.id}
                              value={product.id.toString()}
                            >
                              {product.name} - $
                              {Number(product.price).toFixed(2)}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="space-y-1">
                      <Label className="text-xs">Item Name *</Label>
                      <Input
                        value={item.name}
                        onChange={(e) =>
                          updateItem(index, "name", e.target.value)
                        }
                        placeholder="Item name"
                        className="h-9"
                        required
                      />
                    </div>

                    <div className="space-y-1">
                      <Label className="text-xs">Quantity *</Label>
                      <Input
                        type="number"
                        min="1"
                        value={item.quantity}
                        onChange={(e) =>
                          updateItem(
                            index,
                            "quantity",
                            parseInt(e.target.value) || 1
                          )
                        }
                        className="h-9"
                        required
                      />
                    </div>

                    <div className="space-y-1">
                      <Label className="text-xs">Unit Price ($) *</Label>
                      <Input
                        type="number"
                        step="0.01"
                        min="0"
                        value={item.price}
                        onChange={(e) =>
                          updateItem(
                            index,
                            "price",
                            parseFloat(e.target.value) || 0
                          )
                        }
                        className="h-9"
                        required
                      />
                    </div>

                    <div className="flex items-center space-x-2">
                      <div className="text-sm font-medium">
                        ${(item.price * item.quantity).toFixed(2)}
                      </div>
                      {items.length > 1 && (
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={() => removeItem(index)}
                          className="h-9 w-9 p-0 text-red-600"
                        >
                          <Trash2 className="h-3 w-3" />
                        </Button>
                      )}
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          </div>

          {/* Order Summary */}
          <div className="bg-gray-50 p-4 rounded-lg">
            <div className="flex justify-between items-center text-lg font-semibold">
              <span>Total Amount:</span>
              <span className="text-green-600">
                ${getTotalAmount().toFixed(2)}
              </span>
            </div>
          </div>

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
            <Button type="submit" disabled={loading}>
              <Save className="h-4 w-4 mr-2" />
              {loading ? "Creating..." : "Create Order"}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
};

export default OrderForm;
