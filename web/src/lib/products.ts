import api from "./api";

export interface Product {
  id: number;
  name: string;
  category: string;
  is_active: boolean;
}

export async function fetchProducts(): Promise<Product[]> {
  const res = await api.get("/products");
  return res.data;
}

export async function createProduct(data: { name: string; category: string }): Promise<Product> {
  const res = await api.post("/products", data);
  return res.data;
}

export async function updateProduct(id: number, data: { name: string; category: string }): Promise<Product> {
  const res = await api.put(`/products/${id}`, data);
  return res.data;
}

export async function deleteProduct(id: number): Promise<void> {
  await api.delete(`/products/${id}`);
}
