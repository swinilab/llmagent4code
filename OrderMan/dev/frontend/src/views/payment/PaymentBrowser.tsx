import React, { useEffect, useState } from "react";
import {
  paymentApi,
  invoiceApi,
  orderApi,
  handleApiError,
} from "../../lib/api";
import { Payment, Invoice, Order } from "../../types";
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
  DollarSign,
  Calendar,
  TrendingUp,
} from "lucide-react";

interface PaymentBrowserProps {
  refreshTrigger?: number;
  canEdit?: boolean;
  userRole?: string;
  userId?: number;
}

const PaymentBrowser: React.FC<PaymentBrowserProps> = ({
  refreshTrigger = 0,
  canEdit = false,
  userRole,
  userId,
}) => {
  const [payments, setPayments] = useState<Payment[]>([]);
  const [invoices, setInvoices] = useState<Record<number, Invoice>>({});
  const [orders, setOrders] = useState<Record<number, Order>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [processingAccept, setProcessingAccept] = useState<Set<number>>(
    new Set()
  );

  const fetchPayments = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await paymentApi.getAll();

      // Filter payments based on user role
      let filteredPayments = response.data;
      if (userRole === "customer" && userId) {
        // For customers, only show their own payments
        // We'll need to fetch invoices and orders first to check ownership
        const invoiceIds = [
          ...new Set(response.data.map((payment) => payment.invoiceId)),
        ];
        const invoicePromises = invoiceIds.map((id) => invoiceApi.getById(id));
        const invoiceResponses = await Promise.allSettled(invoicePromises);

        const customerInvoiceIds = new Set<number>();
        
        // Get orders for each invoice to check customer ownership
        for (let i = 0; i < invoiceResponses.length; i++) {
          const result = invoiceResponses[i];
          if (result.status === "fulfilled" && result.value.data) {
            const invoice = result.value.data;
            try {
              const orderResponse = await orderApi.getById(invoice.orderId);
              if (orderResponse.data && orderResponse.data.customerId === userId) {
                customerInvoiceIds.add(invoiceIds[i]);
              }
            } catch (orderErr) {
              console.warn(`Could not fetch order ${invoice.orderId}:`, orderErr);
            }
          }
        }

        filteredPayments = response.data.filter((payment) =>
          customerInvoiceIds.has(payment.invoiceId)
        );
      }

      setPayments(filteredPayments);

      // Fetch related invoices and orders
      const invoiceIds = [
        ...new Set(filteredPayments.map((payment) => payment.invoiceId)),
      ];
      const invoicePromises = invoiceIds.map((id) => invoiceApi.getById(id));
      const invoiceResponses = await Promise.allSettled(invoicePromises);

      const invoicesMap: Record<number, Invoice> = {};
      const orderIds = new Set<number>();

      invoiceResponses.forEach((result, index) => {
        if (result.status === "fulfilled" && result.value.data) {
          const invoice = result.value.data;
          invoicesMap[invoiceIds[index]] = invoice;
          orderIds.add(invoice.orderId);
        }
      });
      setInvoices(invoicesMap);

      // Fetch orders
      const orderPromises = Array.from(orderIds).map((id) =>
        orderApi.getById(id)
      );
      const orderResponses = await Promise.allSettled(orderPromises);

      const ordersMap: Record<number, Order> = {};
      orderResponses.forEach((result, index) => {
        if (result.status === "fulfilled" && result.value.data) {
          ordersMap[Array.from(orderIds)[index]] = result.value.data;
        }
      });
      setOrders(ordersMap);
    } catch (err) {
      setError(handleApiError(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPayments();
  }, [refreshTrigger, userRole, userId]);

  const handleAcceptPayment = async (paymentId: number) => {
    setProcessingAccept((prev) => new Set([...prev, paymentId]));
    try {
      await paymentApi.accept(paymentId);
      await fetchPayments(); // Refresh to update status
    } catch (err) {
      setError(handleApiError(err));
    } finally {
      setProcessingAccept((prev) => {
        const newSet = new Set(prev);
        newSet.delete(paymentId);
        return newSet;
      });
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "pending":
        return "bg-yellow-100 text-yellow-800";
      case "completed":
        return "bg-green-100 text-green-800";
      case "failed":
        return "bg-red-100 text-red-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  const getTotalPayments = () => {
    return payments
      .filter((payment) => payment.status === "completed")
      .reduce((sum, payment) => sum + Number(payment.amount), 0);
  };

  const getPendingPayments = () => {
    return payments.filter((payment) => payment.status === "pending").length;
  };

  const getCompletedPayments = () => {
    return payments.filter((payment) => payment.status === "completed").length;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-lg">Loading payments...</div>
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
      {/* Payment Summary - For accountants */}
      {userRole === "accountant" && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center space-x-2">
                <TrendingUp className="h-5 w-5 text-green-600" />
                <div>
                  <div className="text-sm text-gray-600">Total Received</div>
                  <div className="text-2xl font-bold text-green-600">
                    ${getTotalPayments().toFixed(2)}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4">
              <div className="flex items-center space-x-2">
                <CheckCircle className="h-5 w-5 text-blue-600" />
                <div>
                  <div className="text-sm text-gray-600">Completed</div>
                  <div className="text-2xl font-bold text-blue-600">
                    {getCompletedPayments()}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4">
              <div className="flex items-center space-x-2">
                <Calendar className="h-5 w-5 text-yellow-600" />
                <div>
                  <div className="text-sm text-gray-600">Pending</div>
                  <div className="text-2xl font-bold text-yellow-600">
                    {getPendingPayments()}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Payments Table */}
      <Card>
        <CardHeader>
          <CardTitle>
            {userRole === "customer" ? "My Payments" : "All Payments"} (
            {payments.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {payments.length === 0 ? (
            <div className="text-center p-8">
              <div className="text-gray-500">
                {userRole === "customer"
                  ? "No payments made yet"
                  : "No payments found"}
              </div>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Payment ID</TableHead>
                  <TableHead>Invoice ID</TableHead>
                  <TableHead>Customer</TableHead>
                  <TableHead>Amount</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Method</TableHead>
                  <TableHead>Date</TableHead>
                  {canEdit && <TableHead>Actions</TableHead>}
                </TableRow>
              </TableHeader>
              <TableBody>
                {payments.map((payment) => {
                  const invoice = invoices[payment.invoiceId];
                  const order = invoice ? orders[invoice.orderId] : null;
                  const isAccepting = processingAccept.has(payment.id);

                  return (
                    <TableRow key={payment.id}>
                      <TableCell className="font-medium">
                        #{payment.id}
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">#{payment.invoiceId}</Badge>
                      </TableCell>
                      <TableCell>
                        {order ? (
                          <div>
                            <div className="font-medium">
                              {order.customerName}
                            </div>
                            <div className="text-sm text-gray-600">
                              {order.customerPhone}
                            </div>
                          </div>
                        ) : (
                          <span className="text-gray-400">Loading...</span>
                        )}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center space-x-1 font-medium text-green-600">
                          <DollarSign className="h-3 w-3" />
                          <span>${Number(payment.amount).toFixed(2)}</span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge className={getStatusColor(payment.status)}>
                          {payment.status.toUpperCase()}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">
                          {payment.method.toUpperCase()}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-sm text-gray-600">
                        {new Date(payment.date).toLocaleDateString()}
                      </TableCell>
                      {canEdit && (
                        <TableCell>
                          {payment.status === "pending" && (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleAcceptPayment(payment.id)}
                              disabled={isAccepting}
                              className="text-green-600"
                            >
                              <CheckCircle className="h-3 w-3 mr-1" />
                              {isAccepting ? "Processing..." : "Accept"}
                            </Button>
                          )}
                          {payment.status === "completed" && (
                            <Badge
                              variant="secondary"
                              className="text-green-600"
                            >
                              Completed
                            </Badge>
                          )}
                        </TableCell>
                      )}
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

export default PaymentBrowser;

