// In-Memory Repository Implementation for Local Deployment

export interface IRepository<T> {
  findById(id: string): Promise<T | null>;
  findAll(): Promise<T[]>;
  create(entity: T): Promise<T>;
  update(id: string, entity: Partial<T>): Promise<T | null>;
  delete(id: string): Promise<boolean>;
  findByQuery(query: Partial<T>): Promise<T[]>;
}

export class MemoryRepository<T extends { id: string }> implements IRepository<T> {
  protected store: Map<string, T> = new Map();

  async findById(id: string): Promise<T | null> {
    return this.store.get(id) || null;
  }

  async findAll(): Promise<T[]> {
    return Array.from(this.store.values());
  }

  async create(entity: T): Promise<T> {
    this.store.set(entity.id, entity);
    return entity;
  }

  async update(id: string, entity: Partial<T>): Promise<T | null> {
    const existing = this.store.get(id);
    if (!existing) return null;
    const updated = { ...existing, ...entity, id } as T;
    this.store.set(id, updated);
    return updated;
  }

  async delete(id: string): Promise<boolean> {
    return this.store.delete(id);
  }

  async findByQuery(query: Partial<T>): Promise<T[]> {
    return Array.from(this.store.values()).filter(item => {
      return Object.entries(query).every(([key, value]) => {
        return item[key as keyof T] === value;
      });
    });
  }

  async clear(): Promise<void> {
    this.store.clear();
  }

  getCount(): number {
    return this.store.size;
  }
}
