import { useEffect, useState } from "react";
import { CustomerApi } from "../../api";
import { ProductApi } from "../../api";
import { OrderApi } from "../../api";
import { Customer } from "../../domain";
import { Product } from "../../domain";

export const OrderCreate = () => {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [selectedCust, setSelectedCust] = useState<string>("");
  const [orderItems, setOrderItems] = useState<{ productId: string; quantity: number }[]>([]);

  useEffect(() => {
    CustomerApi.getAll().then((r) => setCustomers(r.data));
    ProductApi.getAll().then((r) => setProducts(r.data));
  }, []);

  const addItem = () =>
    setOrderItems([...orderItems, { productId: "", quantity: 1 }]);

  const submit = async () => {
    if (!selectedCust) return alert("Choose customer");
    await OrderApi.create(selectedCust, orderItems);
    window.location.reload();
  };

  return (
    <div>
      <h2>Create Order</h2>
      <select value={selectedCust} onChange={(e) => setSelectedCust(e.target.value)}>
        <option value="">Select customer</option>
        {customers.map((c) => (
          <option key={c.id} value={c.id}>
            {c.name}
          </option>
        ))}
      </select>

      <h3>Items</h3>
      {orderItems.map((item, idx) => (
        <div key={idx}>
          <select
            value={item.productId}
            onChange={(e) => {
              const newItems = [...orderItems];
              newItems[idx].productId = e.target.value;
              setOrderItems(newItems);
            }}
          >
            <option value="">Select product</option>
            {products.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
          <input
            type="number"
            min="1"
            value={item.quantity}
            onChange={(e) => {
              const newItems = [...orderItems];
              newItems[idx].quantity = parseInt(e.target.value);
              setOrderItems(newItems);
            }}
          />
        </div>
      ))}

      <button onClick={addItem}>Add Item</button>
      <button onClick={submit}>Create</button>
    </div>
  );
};