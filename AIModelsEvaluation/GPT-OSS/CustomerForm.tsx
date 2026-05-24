import { useState } from "react";
import { CustomerApi } from "../../api";
import { Customer } from "../../domain";

export const CustomerForm = () => {
  const [data, setData] = useState<Omit<Customer, "id">>({
    name: "",
    address: "",
    phone: "",
    bankAccount: "",
  });

  const submit = async () => {
    await CustomerApi.create(data);
    window.location.reload(); // simple refresh
  };

  return (
    <form onSubmit={(e) => { e.preventDefault(); submit(); }}>
      <input placeholder="Name" value={data.name} onChange={(e) => setData({ ...data, name: e.target.value })} />
      <input placeholder="Address" value={data.address} onChange={(e) => setData({ ...data, address: e.target.value })} />
      <input placeholder="Phone" value={data.phone} onChange={(e) => setData({ ...data, phone: e.target.value })} />
      <input placeholder="Bank Account" value={data.bankAccount} onChange={(e) => setData({ ...data, bankAccount: e.target.value })} />
      <button type="submit">Create</button>
    </form>
  );
};