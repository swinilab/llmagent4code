import React, { useEffect, useState } from "react";
import { customerApi, handleApiError } from "../../lib/api";
import { Customer } from "../../types";
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
  Edit,
  Trash2,
  Phone,
  MapPin,
  CreditCard,
} from "lucide-react";

interface CustomerBrowserProps {
  refreshTrigger?: number;
  canEdit?: boolean;
}

const CustomerBrowser: React.FC<CustomerBrowserProps> = ({
  refreshTrigger = 0,
  canEdit = false,
}) => {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchCustomers = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await customerApi.getAll();
      setCustomers(response.data);
    } catch (err) {
      setError(handleApiError(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCustomers();
  }, [refreshTrigger]);

  const handleDelete = async (id: number) => {
    if (!confirm("Are you sure you want to delete this customer?")) {
      return;
    }

    try {
      await customerApi.delete(id);
      setCustomers(customers.filter((customer) => customer.id !== id));
    } catch (err) {
      setError(handleApiError(err));
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-lg">Loading customers...</div>
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

  if (customers.length === 0) {
    return (
      <Card>
        <CardContent className="text-center p-8">
          <div className="text-gray-500">No customers found</div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Customer List ({customers.length})</CardTitle>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>ID</TableHead>
              <TableHead>Name</TableHead>
              <TableHead>Contact</TableHead>
              <TableHead>Address</TableHead>
              <TableHead>Bank Account</TableHead>
              <TableHead>Orders</TableHead>
              <TableHead>Created</TableHead>
              {canEdit && <TableHead>Actions</TableHead>}
            </TableRow>
          </TableHeader>
          <TableBody>
            {customers.map((customer) => (
              <TableRow key={customer.id}>
                <TableCell className="font-medium">#{customer.id}</TableCell>
                <TableCell>
                  <div className="font-medium">{customer.name}</div>
                </TableCell>
                <TableCell>
                  <div className="flex items-center space-x-1 text-sm text-gray-600">
                    <Phone className="h-3 w-3" />
                    <span>{customer.phone}</span>
                  </div>
                </TableCell>
                <TableCell>
                  <div className="flex items-center space-x-1 text-sm text-gray-600">
                    <MapPin className="h-3 w-3" />
                    <span className="max-w-xs truncate">
                      {customer.address}
                    </span>
                  </div>
                </TableCell>
                <TableCell>
                  {customer.bankAccount ? (
                    <div className="flex items-center space-x-1 text-sm">
                      <CreditCard className="h-3 w-3" />
                      <span>{customer.bankAccount}</span>
                    </div>
                  ) : (
                    <span className="text-gray-400">Not provided</span>
                  )}
                </TableCell>
                <TableCell>
                  <Badge variant="secondary">
                    {customer.orders?.length || 0} orders
                  </Badge>
                </TableCell>
                <TableCell className="text-sm text-gray-600">
                  {new Date(customer.createdAt).toLocaleDateString()}
                </TableCell>
                {canEdit && (
                  <TableCell>
                    <div className="flex space-x-2">
                      <Button
                        variant="outline"
                        size="sm"
                        className="h-8 w-8 p-0"
                        title="Edit Customer"
                      >
                        <Edit className="h-3 w-3" />
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        className="h-8 w-8 p-0 text-red-600 hover:text-red-700"
                        onClick={() => handleDelete(customer.id)}
                        title="Delete Customer"
                      >
                        <Trash2 className="h-3 w-3" />
                      </Button>
                    </div>
                  </TableCell>
                )}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
};

export default CustomerBrowser;

