export class Product {
	id: number;
	name: string;
	description: string;
	price: number;
	image: string;
	createdAt: Date;
	updatedAt: Date;

	constructor(
		id: number,
		name: string,
		description: string,
		price: number,
		image: string,
		createdAt?: Date,
		updatedAt?: Date
	) {
		this.id = id;
		this.name = name;
		this.description = description;
		this.price = price;
		this.image = image;
		this.createdAt = createdAt || new Date();
		this.updatedAt = updatedAt || new Date();
	}
}

export default Product;
