from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models.category import Category


def get_categories(db: Session):
    return db.query(Category).order_by(Category.id.desc()).all()


def get_category(db: Session, category_id: int):
    return db.query(Category).filter(Category.id == category_id).first()


def get_category_by_name(db: Session, name: str):
    return db.query(Category).filter(Category.name == name).first()


def create_category(db: Session, data):
    exists = get_category_by_name(db, data.name)
    if exists:
        raise HTTPException(status_code=400, detail="Category name already exists")

    category = Category(name=data.name)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def update_category(db: Session, category_id: int, data):
    category = get_category(db, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    update_data = data.model_dump(exclude_unset=True)

    if "name" in update_data:
        same_name = get_category_by_name(db, update_data["name"])
        if same_name and same_name.id != category.id:
            raise HTTPException(status_code=400, detail="Category name already exists")
        category.name = update_data["name"]

    db.commit()
    db.refresh(category)
    return category


def delete_category(db: Session, category_id: int):
    category = get_category(db, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    db.delete(category)
    db.commit()
