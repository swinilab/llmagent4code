from fastapi import APIRouter, HTTPException
import uuid

from app.models import ProductCreateDTO, ProductDTO
from app.repositories import ProductRepository

router = APIRouter()

@router.post('', response_model=ProductDTO)
def create_product(dto: ProductCreateDTO):
    product_id = str(uuid.uuid4())
    product = ProductDTO(
        id=product_id,
        description=dto.description,
        price=dto.price,
    )
    ProductRepository.create(product)
    return product

@router.get('/{product_id}', response_model=ProductDTO)
def get_product(product_id: str):
    prod = ProductRepository.get_by_id(product_id)
    if not prod:
        raise HTTPException(status_code=404, detail='Product not found')
    return prod
