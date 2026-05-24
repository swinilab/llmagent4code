import React, { useEffect, useState } from "react";
import { orderApi, handleApiError } from "../../lib/api";
import { Order } from "../../types";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../../components/ui/table";
import { Badge } from "../../components/ui/badge";
import {
  AlertCircle,
  CheckCircle,
  Truck,
  Package,
  DollarSign,
} from "lucide-react";

interface OrderBrowserStaffProps {
  refreshTrigger?: number;
}

const OrderBrowserStaff: React.FC<OrderBrowserStaffProps> = ({
  refreshTrigger = 0,
}) => {
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [processingOrders, setProcessingOrders] = useState<Set<number>>(
    new Set()
  );

  const fetchOrders = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await orderApi.getAll();
      // Show all orders but sort by priority (active orders first, closed orders at bottom)
      const allOrders = response.data.sort((a, b) => {
        // Closed orders go to bottom
        if (a.status === "closed" && b.status !== "closed") return 1;
        if (b.status === "closed" && a.status !== "closed") return -1;

        // Among active orders, sort by priority: pending > paid > shipped > accepted
        const statusPriority = {
          pending: 4,
          paid: 3,
          shipped: 2,
          accepted: 1,
          closed: 0,
        };

        return (
          (statusPriority[b.status] || 0) - (statusPriority[a.status] || 0)
        );
      });
      setOrders(allOrders);
    } catch (err) {
      setError(handleApiError(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOrders();
  }, [refreshTrigger]);

  const handleOrderAction = async (
    orderId: number,
    action: "receive" | "ship" | "close"
  ) => {
    setProcessingOrders((prev) => new Set([...prev, orderId]));
    try {
      switch (action) {
        case "receive":
          await orderApi.receive(orderId);
          break;
        case "ship":
          await orderApi.ship(orderId);
          break;
        case "close":
          await orderApi.close(orderId);
          break;
      }
      // Refresh orders to update status
      await fetchOrders();
    } catch (err) {
      setError(handleApiError(err));
    } finally {
      setProcessingOrders((prev) => {
        const newSet = new Set(prev);
        newSet.delete(orderId);
        return newSet;
      });
    }
  };

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

  const getNextAction = (order: Order) => {
    switch (order.status) {
      case "pending":
        return {
          label: "Accept Order",
          action: "receive" as const,
          icon: CheckCircle,
          variant: "default" as const,
        };
      case "paid":
        return {
          label: "Ship Order",
          action: "ship" as const,
          icon: Truck,
          variant: "secondary" as const,
        };
      case "shipped":
        return {
          label: "Close Order",
          action: "close" as const,
          icon: CheckCircle,
          variant: "outline" as const,
        };
      case "closed":
        return null; // No action for closed orders
      default:
        return null;
    }
  };

  const getStaffPriority = (order: Order) => {
    if (order.status === "pending") return "High - Needs Review";
    if (order.status === "accepted") return "Accepted - Awaiting Invoice";
    if (order.status === "paid") return "High - Ready to Ship";
    if (order.status === "shipped") return "Medium - Ready to Close";
    if (order.status === "closed") return "Completed";
    return "Normal";
  };

  const getPendingCount = () => {
    return orders.filter((order) => order.status === "pending").length;
  };

  const getReadyToShip = () => {
    return orders.filter((order) => order.status === "paid").length;
  };

  const getReadyToClose = () => {
    return orders.filter((order) => order.status === "shipped").length;
  };

  const getClosedCount = () => {
    return orders.filter((order) => order.status === "closed").length;
  };

  const getActiveCount = () => {
    return orders.filter((order) => order.status !== "closed").length;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-lg">Loading orders...</div>
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

  return (
    <div className="space-y-6">
      {/* Staff Summary */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <AlertCircle className="h-5 w-5 text-yellow-600" />
              <div>
                <div className="text-sm text-gray-600">Pending Review</div>
                <div className="text-2xl font-bold text-yellow-600">
                  {getPendingCount()}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <Truck className="h-5 w-5 text-green-600" />
              <div>
                <div className="text-sm text-gray-600">Ready to Ship</div>
                <div className="text-2xl font-bold text-green-600">
                  {getReadyToShip()}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <CheckCircle className="h-5 w-5 text-purple-600" />
              <div>
                <div className="text-sm text-gray-600">Ready to Close</div>
                <div className="text-2xl font-bold text-purple-600">
                  {getReadyToClose()}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <Package className="h-5 w-5 text-blue-600" />
              <div>
                <div className="text-sm text-gray-600">Active / Closed</div>
                <div className="text-2xl font-bold text-blue-600">
                  {getActiveCount()} / {getClosedCount()}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Orders Table */}
      <Card>
        <CardHeader>
          <CardTitle>Order Processing Queue</CardTitle>
        </CardHeader>
        <CardContent>
          {orders.length === 0 ? (
            <div className="text-center p-8">
              <Package className="h-12 w-12 mx-auto text-gray-400 mb-4" />
              <div className="text-gray-500">
                No orders need attention right now
              </div>
              <div className="text-sm text-gray-400 mt-1">
                Great job! All orders are processed.
              </div>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Order ID</TableHead>
                  <TableHead>Customer</TableHead>
                  <TableHead>Amount</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Priority</TableHead>
                  <TableHead>Items</TableHead>
                  <TableHead>Date</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {orders.map((order) => {
                  const nextAction = getNextAction(order);
                  const isProcessing = processingOrders.has(order.id);

                  return (
                    <TableRow key={order.id}>
                      <TableCell className="font-medium">#{order.id}</TableCell>
                      <TableCell>
                        <div>
                          <div className="font-medium">
                            {order.customerName}
                          </div>
                          <div className="text-sm text-gray-600">
                            {order.customerPhone}
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center space-x-1 font-medium text-green-600">
                          <DollarSign className="h-3 w-3" />
                          <span>${Number(order.totalAmount).toFixed(2)}</span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge className={getStatusColor(order.status)}>
                          {order.status.toUpperCase()}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <div className="text-sm">{getStaffPriority(order)}</div>
                      </TableCell>
                      <TableCell>
                        <Badge variant="secondary">
                          {order.items?.length || 0} items
                        </Badge>
                      </TableCell>
                      <TableCell className="text-sm text-gray-600">
                        {new Date(order.orderDate).toLocaleDateString()}
                      </TableCell>
                      <TableCell>
                        {nextAction && (
                          <Button
                            variant={nextAction.variant}
                            size="sm"
                            onClick={() =>
                              handleOrderAction(order.id, nextAction.action)
                            }
                            disabled={isProcessing}
                            className="flex items-center space-x-1"
                          >
                            <nextAction.icon className="h-3 w-3" />
                            <span>
                              {isProcessing
                                ? "Processing..."
                                : nextAction.label}
                            </span>
                          </Button>
                        )}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default OrderBrowserStaff;
