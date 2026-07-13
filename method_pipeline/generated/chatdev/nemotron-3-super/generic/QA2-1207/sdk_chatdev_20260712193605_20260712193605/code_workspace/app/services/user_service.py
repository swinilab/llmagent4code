from app.repositories import UserRepository
from app.schemas import UserCreate, UserUpdate, UserInDB
from app.models import User
from app.database import get_db
from fastapi import Depends
from typing import Optional
from sqlalchemy.orm import Session

class UserService:
    def __init__(self, db: Session = Depends(get_db)):
        self.repository = UserRepository(db)

    def get_user_by_id(self, user_id: int) -> Optional[UserInDB]:
        user = self.repository.get(user_id)
        if user:
            return UserInDB.from_orm(user)
        return None

    def get_user_by_username(self, username: str) -> Optional[UserInDB]:
        user = self.repository.get_by_username(username)
        if user:
            return UserInDB.from_orm(user)
        return None

    def get_user_by_email(self, email: str) -> Optional[UserInDB]:
        user = self.repository.get_by_email(email)
        if user:
            return UserInDB.from_orm(user)
        return None

    def create_user(self, user_in: UserCreate) -> UserInDB:
        # In a real app, hash the password
        hashed_password = user_in.password  # TODO: hash
        user_data = user_in.dict()
        user_data["hashed_password"] = hashed_password
        del user_data["password"]
        user = self.repository.create(user_data)
        return UserInDB.from_orm(user)

    def update_user(self, user_id: int, user_in: UserUpdate) -> Optional[UserInDB]:
        user_data = user_in.dict(exclude_unset=True)
        user = self.repository.update(user_id, user_data)
        if user:
            return UserInDB.from_orm(user)
        return None

    def delete_user(self, user_id: int) -> bool:
        return self.repository.delete(user_id)