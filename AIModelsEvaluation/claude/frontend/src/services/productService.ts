import { api } from './api';
import { Product, CreateProductRequest, UpdateProductRequest, ApiResponse } from '../types';

export class ProductService {
  private baseUrl = '/products';

  async getAllProducts(): Promise<ApiResponse<Product[]>> {
    return api.get<Product[]>(this.baseUrl);
  }

  async getActiveProducts(): Promise<ApiResponse<Product[]>> {
    return api.get<Product[]>(`${this.baseUrl}/active`);
  }

  async getProductById(id: string): Promise<ApiResponse<Product>> {
    return api.get<Product>(`${this.baseUrl}/${id}`);
  }

  async createProduct(data: CreateProductRequest): Promise<ApiResponse<Product>> {
    return api.post<Product>(this.baseUrl, data);
  }

  async updateProduct(data: UpdateProductRequest): Promise<ApiResponse<Product>> {
    return api.put<Product>(`${this.baseUrl}/${data.id}`, data);
  }

  async deleteProduct(id: string): Promise<ApiResponse<void>> {
    return api.delete<void>(`${this.baseUrl}/${id}`);
  }

  async updateProductStock(id: string, quantity: number): Promise<ApiResponse<Product>> {
    return api.put<Product>(`${this.baseUrl}/${id}/stock`, { quantity });
  }

  async searchProducts(query: string): Promise<ApiResponse<Product[]>> {
    return api.get<Product[]>(`${this.baseUrl}/search`, { q: query });
  }

  async getProductsByCategory(category: string): Promise<ApiResponse<Product[]>> {
    return api.get<Product[]>(`${this.baseUrl}/category/${category}`);
  }
}

export const productService = new ProductService();