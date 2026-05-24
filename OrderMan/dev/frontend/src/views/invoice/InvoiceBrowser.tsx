import React, { useEffect, useState } from "react";
import { invoiceApi, orderApi, handleApiError } from "../../lib/api";
import { Invoice, Order } from "../../types";
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
import { AlertCircle, Send, Eye, DollarSign, Calendar } from "lucide-react";

interface InvoiceBrowserProps {
  refreshTrigger?: number;
  canEdit?: boolean;
  userRole?: string;
}

const InvoiceBrowser: React.FC<InvoiceBrowserProps> = ({
  refreshTrigger = 0,
  canEdit = false,
  userRole,
}) => {
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [orders, setOrders] = useState<Record<number, Order>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [processingSend, setProcessingSend] = useState<Set<number>>(new Set());

  const fetchInvoices = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await invoiceApi.getAll();
      setInvoices(response.data);

      // Fetch related orders
      const orderIds = [
        ...new Set(response.data.map((invoice) => invoice.orderId)),
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
    } catch (err) {
      setError(handleApiError(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchInvoices();
  }, [refreshTrigger]);

  const handleSendInvoice = async (orderId: number) => {
    setProcessingSend((prev) => new Set([...prev, orderId]));
    try {
      await invoiceApi.send(orderId);
      await fetchInvoices(); // Refresh to update status
    } catch (err) {
      setError(handleApiError(err));
    } finally {
      setProcessingSend((prev) => {
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
      case "issued":
        return "bg-blue-100 text-blue-800";
      case "paid":
        return "bg-green-100 text-green-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  const getTotalInvoiced = () => {
    return invoices.reduce((sum, invoice) => sum + Number(invoice.amount), 0);
  };

  const getPaidInvoices = () => {
    return invoices.filter((invoice) => invoice.status === "paid").length;
  };

  const getPendingInvoices = () => {
    return invoices.filter((invoice) => invoice.status === "pending").length;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-lg">Loading invoices...</div>
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
      {/* Invoice Summary - Only for accountants */}
      {userRole === "accountant" && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center space-x-2">
                <DollarSign className="h-5 w-5 text-green-600" />
                <div>
                  <div className="text-sm text-gray-600">Total Invoiced</div>
                  <div className="text-2xl font-bold text-green-600">
                    ${getTotalInvoiced().toFixed(2)}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4">
              <div className="flex items-center space-x-2">
                <Calendar className="h-5 w-5 text-blue-600" />
                <div>
                  <div className="text-sm text-gray-600">Paid Invoices</div>
                  <div className="text-2xl font-bold text-blue-600">
                    {getPaidInvoices()}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4">
              <div className="flex items-center space-x-2">
                <AlertCircle className="h-5 w-5 text-yellow-600" />
                <div>
                  <div className="text-sm text-gray-600">Pending</div>
                  <div className="text-2xl font-bold text-yellow-600">
                    {getPendingInvoices()}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Invoices Table */}
      <Card>
        <CardHeader>
          <CardTitle>Invoices ({invoices.length})</CardTitle>
        </CardHeader>
        <CardContent>
          {invoices.length === 0 ? (
            <div className="text-center p-8">
              <div className="text-gray-500">No invoices found</div>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Invoice ID</TableHead>
                  <TableHead>Order ID</TableHead>
                  <TableHead>Customer</TableHead>
                  <TableHead>Amount</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Payment Method</TableHead>
                  <TableHead>Date</TableHead>
                  {canEdit && <TableHead>Actions</TableHead>}
                </TableRow>
              </TableHeader>
              <TableBody>
                {invoices.map((invoice) => {
                  const order = orders[invoice.orderId];
                  const isSending = processingSend.has(invoice.orderId);

                  return (
                    <TableRow key={invoice.id}>
                      <TableCell className="font-medium">
                        #{invoice.id}
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">#{invoice.orderId}</Badge>
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
                          <span>${Number(invoice.amount).toFixed(2)}</span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge className={getStatusColor(invoice.status)}>
                          {invoice.status.toUpperCase()}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">
                          {invoice.method.toUpperCase()}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-sm text-gray-600">
                        {new Date(invoice.date).toLocaleDateString()}
                      </TableCell>
                      {canEdit && (
                        <TableCell>
                          <div className="flex space-x-2">
                            <Button
                              variant="outline"
                              size="sm"
                              className="h-8 w-8 p-0"
                              title="View Invoice"
                            >
                              <Eye className="h-3 w-3" />
                            </Button>
                            {invoice.status === "pending" && (
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() =>
                                  handleSendInvoice(invoice.orderId)
                                }
                                disabled={isSending}
                                className="text-blue-600"
                                title="Send Invoice"
                              >
                                <Send className="h-3 w-3" />
                              </Button>
                            )}
                          </div>
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

export default InvoiceBrowser;
