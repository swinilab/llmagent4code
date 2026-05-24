import React, { useEffect, useState } from "react";
import { orderApi, invoiceApi, handleApiError } from "../../lib/api";
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
  FileText,
  DollarSign,
  TrendingUp,
  Calendar,
} from "lucide-react";

interface OrderBrowserAccountantProps {
  refreshTrigger?: number;
}

const OrderBrowserAccountant: React.FC<OrderBrowserAccountantProps> = ({
  refreshTrigger = 0,
}) => {
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [processingInvoices, setProcessingInvoices] = useState<Set<number>>(
    new Set()
  );

  const fetchOrders = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await orderApi.getAll();
      // Filter orders that need financial attention
      const ordersNeedingAttention = response.data.filter((order) =>
        ["accepted", "paid", "shipped"].includes(order.status)
      );
      setOrders(ordersNeedingAttention);
    } catch (err) {
      setError(handleApiError(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOrders();
  }, [refreshTrigger]);

  const handleSendInvoice = async (orderId: number) => {
    setProcessingInvoices((prev) => new Set([...prev, orderId]));
    try {
      await invoiceApi.send(orderId);
      // Refresh orders to update status
      await fetchOrders();
    } catch (err) {
      setError(handleApiError(err));
    } finally {
      setProcessingInvoices((prev) => {
        const newSet = new Set(prev);
        newSet.delete(orderId);
        return newSet;
      });
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "accepted":
        return "bg-blue-100 text-blue-800";
      case "paid":
        return "bg-green-100 text-green-800";
      case "shipped":
        return "bg-purple-100 text-purple-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  const getFinancialPriority = (order: Order) => {
    if (order.status === "accepted") return "High - Invoice Needed";
    if (order.status === "paid") return "Medium - Payment Received";
    if (order.status === "shipped") return "Low - Monitor";
    return "Normal";
  };

  const getTotalRevenue = () => {
    return orders
      .filter((order) => order.status === "paid" || order.status === "shipped")
      .reduce((sum, order) => sum + Number(order.totalAmount), 0);
  };

  const getPendingInvoices = () => {
    return orders.filter((order) => order.status === "accepted").length;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-lg">Loading financial data...</div>
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
      {/* Financial Summary */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <TrendingUp className="h-5 w-5 text-green-600" />
              <div>
                <div className="text-sm text-gray-600">Revenue (Paid)</div>
                <div className="text-2xl font-bold text-green-600">
                  ${getTotalRevenue().toFixed(2)}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <FileText className="h-5 w-5 text-blue-600" />
              <div>
                <div className="text-sm text-gray-600">Pending Invoices</div>
                <div className="text-2xl font-bold text-blue-600">
                  {getPendingInvoices()}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <Calendar className="h-5 w-5 text-purple-600" />
              <div>
                <div className="text-sm text-gray-600">Orders to Review</div>
                <div className="text-2xl font-bold text-purple-600">
                  {orders.length}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Orders Table */}
      <Card>
        <CardHeader>
          <CardTitle>Financial Order Overview</CardTitle>
        </CardHeader>
        <CardContent>
          {orders.length === 0 ? (
            <div className="text-center p-8">
              <div className="text-gray-500">
                No orders requiring financial attention
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
                  <TableHead>Date</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {orders.map((order) => (
                  <TableRow key={order.id}>
                    <TableCell className="font-medium">#{order.id}</TableCell>
                    <TableCell>
                      <div>
                        <div className="font-medium">{order.customerName}</div>
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
                      <div className="text-sm">
                        {getFinancialPriority(order)}
                      </div>
                    </TableCell>
                    <TableCell className="text-sm text-gray-600">
                      {new Date(order.orderDate).toLocaleDateString()}
                    </TableCell>
                    <TableCell>
                      {order.status === "accepted" && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleSendInvoice(order.id)}
                          disabled={processingInvoices.has(order.id)}
                          className="text-blue-600"
                        >
                          <FileText className="h-3 w-3 mr-1" />
                          {processingInvoices.has(order.id)
                            ? "Sending..."
                            : "Send Invoice"}
                        </Button>
                      )}
                      {order.status === "paid" && (
                        <Badge variant="secondary" className="text-green-600">
                          Invoice Paid
                        </Badge>
                      )}
                      {order.status === "shipped" && (
                        <Badge variant="secondary" className="text-purple-600">
                          Completed
                        </Badge>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default OrderBrowserAccountant;

