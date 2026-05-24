import { PrismaClient } from '@prisma/client';
import Product from '../../../modules/product/Product';
import DomModel from '../../../modules/DomModel';

const prisma = new PrismaClient();

class ProductService {
	private createProductFromRecord(record: any): Product {
		console.log(`[ProductService] Creating product instance from record: ID=${record.id}`);
		try {
			const product = new Product(
				record.id,
				record.name,
				record.description,
				Number(record.price),
				record.image,
				record.createdAt,
				record.updatedAt
			);
			console.log(`[ProductService] Product instance created successfully: ID=${product.id}, Name=${product.name}, Price=${product.price}`);
			DomModel.addProduct(product);
			return product;
		} catch (error) {
			console.error(`[ProductService] Error creating product from record:`, error);
			throw error;
		}
	}

	async fetchProducts(): Promise<Product[]> {
		console.log(`[ProductService] Fetching all products`);
		try {
			const productRecords = await prisma.product.findMany({
				orderBy: { createdAt: 'desc' },
			});
			console.log(`[ProductService] Found ${productRecords.length} products in database`);
			return productRecords.map(record =>
				this.createProductFromRecord(record)
			);
		} catch (error) {
			console.error(`[ProductService] Error fetching products:`, error);
			throw error;
		}
	}

	async fetchProductDetails(productId: number): Promise<Product | null> {
		console.log(`[ProductService] Fetching product details: ID=${productId}`);
		let product = DomModel.getProductById(productId);
		if (!product) {
			console.log(`[ProductService] Product not found in cache, fetching from database: ID=${productId}`);
			const productRecord = await prisma.product.findUnique({
				where: { id: productId },
			});
			if (productRecord) {
				console.log(`[ProductService] Product found in database: ID=${productId}`);
				product = this.createProductFromRecord(productRecord);
			} else {
				console.log(`[ProductService] Product not found in database: ID=${productId}`);
			}
		} else {
			console.log(`[ProductService] Product found in cache: ID=${productId}`);
		}
		return product || null;
	}

	async updateProduct(
		productId: number,
		productData: Partial<{
			name: string;
			description: string;
			price: number;
			image: string;
		}>
	): Promise<Product | null> {
		try {
			const productRecord = await prisma.product.update({
				where: { id: productId },
				data: productData,
			});
			return this.createProductFromRecord(productRecord);
		} catch (error) {
			console.error('Error updating product:', error);
			return null;
		}
	}

	async createProduct(data: {
		name: string;
		description: string;
		price: number;
		image: string;
	}): Promise<Product> {
		const productRecord = await prisma.product.create({ data });
		return this.createProductFromRecord(productRecord);
	}

	// Delete Product
	async deleteProduct(productId: number): Promise<boolean> {
		try {
			await prisma.product.delete({
				where: { id: productId },
			});
			return true;
		} catch (error) {
			console.error('Error deleting product:', error);
			return false;
		}
	}
}

export default ProductService;
