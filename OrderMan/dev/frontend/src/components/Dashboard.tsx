import React from "react";
import { useAuth } from "../contexts/AuthContext";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
// import { Button } from "./ui/button"; // Unused for now
import { Link } from "react-router-dom";
import {
  Users,
  Package,
  ShoppingCart,
  FileText,
  CreditCard,
  TrendingUp,
  Activity,
} from "lucide-react";

const Dashboard: React.FC = () => {
  const { user } = useAuth();

  const getDashboardContent = () => {
    switch (user?.role) {
      case "customer":
        return (
          <div className="space-y-6">
            <div className="text-center">
              <h2 className="text-2xl font-bold text-gray-900 mb-2">
                Welcome, {user.name}!
              </h2>
              <p className="text-gray-600">
                Manage your orders and track your purchases
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <Card className="hover:shadow-lg transition-shadow cursor-pointer">
                <Link to="/products">
                  <CardHeader className="flex flex-row items-center space-y-0 pb-2">
                    <Package className="h-6 w-6 text-blue-600" />
                    <CardTitle className="ml-2">Browse Products</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-gray-600">
                      Explore our product catalog and find what you need
                    </p>
                  </CardContent>
                </Link>
              </Card>

              <Card className="hover:shadow-lg transition-shadow cursor-pointer">
                <Link to="/orders">
                  <CardHeader className="flex flex-row items-center space-y-0 pb-2">
                    <ShoppingCart className="h-6 w-6 text-green-600" />
                    <CardTitle className="ml-2">My Orders</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-gray-600">
                      View your order history and track current orders
                    </p>
                  </CardContent>
                </Link>
              </Card>

              <Card className="hover:shadow-lg transition-shadow cursor-pointer">
                <Link to="/invoices">
                  <CardHeader className="flex flex-row items-center space-y-0 pb-2">
                    <FileText className="h-6 w-6 text-purple-600" />
                    <CardTitle className="ml-2">My Invoices</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-gray-600">
                      View invoices and billing information
                    </p>
                  </CardContent>
                </Link>
              </Card>

              <Card className="hover:shadow-lg transition-shadow cursor-pointer">
                <Link to="/payments">
                  <CardHeader className="flex flex-row items-center space-y-0 pb-2">
                    <CreditCard className="h-6 w-6 text-orange-600" />
                    <CardTitle className="ml-2">Make Payment</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-gray-600">
                      Pay your invoices and view payment history
                    </p>
                  </CardContent>
                </Link>
              </Card>
            </div>
          </div>
        );

      case "staff":
        return (
          <div className="space-y-6">
            <div className="text-center">
              <h2 className="text-2xl font-bold text-gray-900 mb-2">
                Staff Dashboard
              </h2>
              <p className="text-gray-600">
                Manage orders, products, and customer requests
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <Card className="hover:shadow-lg transition-shadow cursor-pointer">
                <Link to="/orders">
                  <CardHeader className="flex flex-row items-center space-y-0 pb-2">
                    <Activity className="h-6 w-6 text-red-600" />
                    <CardTitle className="ml-2">Process Orders</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-gray-600">
                      Accept, ship, and manage customer orders
                    </p>
                  </CardContent>
                </Link>
              </Card>

              <Card className="hover:shadow-lg transition-shadow cursor-pointer">
                <Link to="/products">
                  <CardHeader className="flex flex-row items-center space-y-0 pb-2">
                    <Package className="h-6 w-6 text-blue-600" />
                    <CardTitle className="ml-2">Manage Products</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-gray-600">
                      Add, edit, and manage product catalog
                    </p>
                  </CardContent>
                </Link>
              </Card>

              <Card className="hover:shadow-lg transition-shadow cursor-pointer">
                <Link to="/customers">
                  <CardHeader className="flex flex-row items-center space-y-0 pb-2">
                    <Users className="h-6 w-6 text-green-600" />
                    <CardTitle className="ml-2">Customer Management</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-gray-600">
                      View and manage customer information
                    </p>
                  </CardContent>
                </Link>
              </Card>
            </div>
          </div>
        );

      case "accountant":
        return (
          <div className="space-y-6">
            <div className="text-center">
              <h2 className="text-2xl font-bold text-gray-900 mb-2">
                Financial Dashboard
              </h2>
              <p className="text-gray-600">
                Manage invoices, payments, and financial reports
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <Card className="hover:shadow-lg transition-shadow cursor-pointer">
                <Link to="/orders">
                  <CardHeader className="flex flex-row items-center space-y-0 pb-2">
                    <TrendingUp className="h-6 w-6 text-blue-600" />
                    <CardTitle className="ml-2">Revenue Tracking</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-gray-600">
                      Monitor orders and revenue streams
                    </p>
                  </CardContent>
                </Link>
              </Card>

              <Card className="hover:shadow-lg transition-shadow cursor-pointer">
                <Link to="/invoices">
                  <CardHeader className="flex flex-row items-center space-y-0 pb-2">
                    <FileText className="h-6 w-6 text-purple-600" />
                    <CardTitle className="ml-2">Invoice Management</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-gray-600">
                      Create and send invoices to customers
                    </p>
                  </CardContent>
                </Link>
              </Card>

              <Card className="hover:shadow-lg transition-shadow cursor-pointer">
                <Link to="/payments">
                  <CardHeader className="flex flex-row items-center space-y-0 pb-2">
                    <CreditCard className="h-6 w-6 text-green-600" />
                    <CardTitle className="ml-2">Payment Processing</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-gray-600">
                      Process and track customer payments
                    </p>
                  </CardContent>
                </Link>
              </Card>

              <Card className="hover:shadow-lg transition-shadow cursor-pointer">
                <Link to="/customers">
                  <CardHeader className="flex flex-row items-center space-y-0 pb-2">
                    <Users className="h-6 w-6 text-orange-600" />
                    <CardTitle className="ml-2">Customer Accounts</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-gray-600">
                      Manage customer financial records
                    </p>
                  </CardContent>
                </Link>
              </Card>
            </div>
          </div>
        );

      default:
        return (
          <div className="text-center">
            <h2 className="text-2xl font-bold text-gray-900 mb-4">
              Welcome to OrderMan
            </h2>
            <p className="text-gray-600 mb-6">
              Please log in to access the system
            </p>
          </div>
        );
    }
  };

  return <div className="container mx-auto p-6">{getDashboardContent()}</div>;
};

export default Dashboard;
