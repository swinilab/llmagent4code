import React from "react";
import { Link, useLocation } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import AuthComponent from "./AuthComponent";
import { Button } from "./ui/button";
import {
  Users,
  Package,
  ShoppingCart,
  FileText,
  CreditCard,
  Home,
} from "lucide-react";

const Navbar: React.FC = () => {
  const { user, isAuthenticated } = useAuth();
  const location = useLocation();

  const navigation = [
    {
      name: "Dashboard",
      href: "/",
      icon: Home,
      roles: ["customer", "staff", "accountant"],
    },
    {
      name: "Customers",
      href: "/customers",
      icon: Users,
      roles: ["staff", "accountant"],
    },
    {
      name: "Products",
      href: "/products",
      icon: Package,
      roles: ["customer", "staff", "accountant"],
    },
    {
      name: "Orders",
      href: "/orders",
      icon: ShoppingCart,
      roles: ["customer", "staff", "accountant"],
    },
    {
      name: "Invoices",
      href: "/invoices",
      icon: FileText,
      roles: ["customer", "staff", "accountant"],
    },
    {
      name: "Payments",
      href: "/payments",
      icon: CreditCard,
      roles: ["customer", "accountant"],
    },
  ];

  const isActive = (href: string) => {
    return location.pathname === href;
  };

  const canAccessRoute = (route: any) => {
    if (!isAuthenticated || !user) return false;
    return route.roles.includes(user.role);
  };

  return (
    <nav className="bg-white shadow-sm border-b">
      <div className="container mx-auto px-6">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <div className="flex items-center space-x-4">
            <Link to="/" className="text-xl font-bold text-gray-900">
              OrderMan
            </Link>
          </div>

          {/* Navigation Links */}
          {isAuthenticated && (
            <div className="hidden md:flex items-center space-x-1">
              {navigation.map((item) => {
                if (!canAccessRoute(item)) return null;

                const Icon = item.icon;
                return (
                  <Link key={item.name} to={item.href}>
                    <Button
                      variant={isActive(item.href) ? "default" : "ghost"}
                      className="flex items-center space-x-2"
                    >
                      <Icon className="h-4 w-4" />
                      <span>{item.name}</span>
                    </Button>
                  </Link>
                );
              })}
            </div>
          )}

          {/* Auth Component */}
          <div className="flex items-center">
            <AuthComponent />
          </div>
        </div>

        {/* Mobile Navigation */}
        {isAuthenticated && (
          <div className="md:hidden pb-4">
            <div className="grid grid-cols-2 gap-2">
              {navigation.map((item) => {
                if (!canAccessRoute(item)) return null;

                const Icon = item.icon;
                return (
                  <Link key={item.name} to={item.href}>
                    <Button
                      variant={isActive(item.href) ? "default" : "ghost"}
                      className="w-full flex items-center justify-start space-x-2"
                      size="sm"
                    >
                      <Icon className="h-4 w-4" />
                      <span>{item.name}</span>
                    </Button>
                  </Link>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </nav>
  );
};

export default Navbar;
