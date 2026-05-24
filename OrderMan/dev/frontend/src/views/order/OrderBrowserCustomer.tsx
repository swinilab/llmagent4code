import React, { useEffect, useState } from "react";
import { orderApi, handleApiError } from "../../lib/api";
import { Order } from "../../types";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "../../components/ui/card";
import { Badge } from "../../components/ui/badge";
import { AlertCircle, Package, DollarSign, Calendar } from "lucide-react";

interface OrderBrowserCustomerProps {
  refreshTrigger?: number;
  customerId: number;
}

const OrderBrowserCustomer: React.FC<OrderBrowserCustomerProps> = ({
  refreshTrigger = 0,
  customerId,
}) => {
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchOrders = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await orderApi.getByCustomer(customerId);
      setOrders(response.data);
    } catch (err) {
      setError(handleApiError(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (customerId) {
      fetchOrders();
    }
  }, [refreshTrigger, customerId]);

  const getStatusColor = (status: string) => {
    switch (status) {
      case "pending":
        return "bg-yellow-100 text-yellow-800";
      case "accepted":
        return "bg-blue-100 text-blue-800";
      case "paid":
        return "bg-green-100 text-green-800";
      case "shipped":
        return "bg-purple-100 text-purple-800";
      case "closed":
        return "bg-gray-100 text-gray-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  const getStatusMessage = (status: string) => {
    switch (status) {
      case "pending":
        return "Your order is being reviewed";
      case "accepted":
        return "Your order has been accepted and is being prepared";
      case "paid":
        return "Payment received, preparing for shipment";
      case "shipped":
        return "Your order is on its way!";
      case "closed":
        return "Order completed";
      default:
        return "";
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-lg">Loading your orders...</div>
      </div>
    );
  }

  if (error) {
    return (
      <Card className="border-red-200">
        <CardContent className="flex items-center space-x-2 p-4 text-red-600">
          <AlertCircle className="h-5 w-5" />
          <span>Error: {error}</span>
        </CardContent>
      </Card>
    );
  }

  if (orders.length === 0) {
    return (
      <Card>
        <CardContent className="text-center p-8">
          <Package className="h-12 w-12 mx-auto text-gray-400 mb-4" />
          <div className="text-gray-500">You haven't placed any orders yet</div>
          <div className="text-sm text-gray-400 mt-1">
            Start shopping to see your orders here!
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <div className="text-lg font-medium">My Orders ({orders.length})</div>
      <div className="grid gap-4">
        {orders.map((order) => (
          <Card key={order.id} className="overflow-hidden">
            <CardHeader className="bg-gray-50 pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg">Order #{order.id}</CardTitle>
                <Badge className={getStatusColor(order.status)}>
                  {order.status.toUpperCase()}
                </Badge>
              </div>
              <div className="text-sm text-gray-600">
                {getStatusMessage(order.status)}
              </div>
            </CardHeader>
            <CardContent className="pt-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="space-y-2">
                  <div className="flex items-center space-x-2 text-sm">
                    <Calendar className="h-4 w-4 text-gray-400" />
                    <span className="text-gray-600">Order Date</span>
                  </div>
                  <div className="font-medium">
                    {new Date(order.orderDate).toLocaleDateString()}
                  </div>
                </div>

                <div className="space-y-2">
                  <div className="flex items-center space-x-2 text-sm">
                    <DollarSign className="h-4 w-4 text-gray-400" />
                    <span className="text-gray-600">Total Amount</span>
                  </div>
                  <div className="font-medium text-green-600">
                    ${Number(order.totalAmount).toFixed(2)}
                  </div>
                </div>

                <div className="space-y-2">
                  <div className="flex items-center space-x-2 text-sm">
                    <Package className="h-4 w-4 text-gray-400" />
                    <span className="text-gray-600">Items</span>
                  </div>
                  <div className="font-medium">
                    {order.items?.length || 0} items
                  </div>
                </div>
              </div>

              {order.items && order.items.length > 0 && (
                <div className="mt-4">
                  <div className="text-sm text-gray-600 mb-2">Order Items:</div>
                  <div className="space-y-2">
                    {order.items.map((item, index) => (
                      <div
                        key={index}
                        className="flex justify-between items-center py-1 px-2 bg-gray-50 rounded"
                      >
                        <div>
                          <span className="font-medium">{item.name}</span>
                          <span className="text-gray-600 ml-2">
                            x{item.quantity}
                          </span>
                        </div>
                        <div className="font-medium">
                          ${(Number(item.price) * item.quantity).toFixed(2)}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="mt-4 pt-3 border-t flex justify-between items-center">
                <div className="text-sm text-gray-600">
                  Payment:{" "}
                  <Badge variant="outline">{order.method.toUpperCase()}</Badge>
                </div>
                <div className="text-right">
                  <div className="text-sm text-gray-600">Total</div>
                  <div className="text-lg font-bold text-green-600">
                    ${Number(order.totalAmount).toFixed(2)}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
};

export default OrderBrowserCustomer;

