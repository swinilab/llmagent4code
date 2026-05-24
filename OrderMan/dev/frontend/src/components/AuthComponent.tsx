import React from "react";
import { useAuth } from "../contexts/AuthContext";
import { Button } from "./ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "./ui/card";

interface AuthComponentProps {
  variant?: "navbar" | "center";
}

const AuthComponent: React.FC<AuthComponentProps> = ({
  variant = "navbar",
}) => {
  const { user, login, logout, isAuthenticated } = useAuth();

  if (isAuthenticated && user) {
    return (
      <div className="flex items-center space-x-4">
        <span className="text-sm text-gray-600">
          Welcome, {user.name} ({user.role})
        </span>
        <Button variant="outline" size="sm" onClick={logout}>
          Logout
        </Button>
      </div>
    );
  }

  if (variant === "center") {
    return (
      <Card className="w-96">
        <CardHeader>
          <CardTitle>Demo Login</CardTitle>
          <CardDescription>
            Choose your role to access the system. No authentication required
            for demo purposes.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <Button
            onClick={() => login("customer")}
            className="w-full"
            variant="default"
          >
            Login as Customer
          </Button>
          <Button
            onClick={() => login("staff")}
            className="w-full"
            variant="secondary"
          >
            Login as Staff
          </Button>
          <Button
            onClick={() => login("accountant")}
            className="w-full"
            variant="outline"
          >
            Login as Accountant
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="flex items-center space-x-2">
      <Button onClick={() => login("customer")} variant="default" size="sm">
        Login as Customer
      </Button>
      <Button onClick={() => login("staff")} variant="secondary" size="sm">
        Login as Staff
      </Button>
      <Button onClick={() => login("accountant")} variant="outline" size="sm">
        Login as Accountant
      </Button>
    </div>
  );
};

export default AuthComponent;
