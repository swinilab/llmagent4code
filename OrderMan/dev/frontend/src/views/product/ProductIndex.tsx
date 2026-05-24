import React, { useState } from "react";
import { useAuth } from "../../contexts/AuthContext";
import ProductBrowser from "./ProductBrowser";
import ProductForm from "./ProductForm";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Plus, Package } from "lucide-react";

const ProductIndex: React.FC = () => {
  const { user } = useAuth();
  const [showForm, setShowForm] = useState(false);
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const handleProductCreated = () => {
    setShowForm(false);
    setRefreshTrigger((prev) => prev + 1);
  };

  // Only staff can manage products
  const canManageProducts = user?.role === "staff";

  return (
    <div className="container mx-auto p-6 space-y-6">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <div className="flex items-center space-x-2">
            <Package className="h-6 w-6" />
            <CardTitle className="text-2xl font-bold">
              Product Catalog
            </CardTitle>
          </div>
          {canManageProducts && (
            <Button
              onClick={() => setShowForm(!showForm)}
              className="flex items-center space-x-2"
            >
              <Plus className="h-4 w-4" />
              <span>Add Product</span>
            </Button>
          )}
        </CardHeader>
        <CardContent>
          {showForm && canManageProducts && (
            <div className="mb-6">
              <ProductForm
                onSuccess={handleProductCreated}
                onCancel={() => setShowForm(false)}
              />
            </div>
          )}
          <ProductBrowser
            refreshTrigger={refreshTrigger}
            canEdit={canManageProducts}
          />
        </CardContent>
      </Card>
    </div>
  );
};

export default ProductIndex;

